"""Verificación independiente del resultado con SymPy.

`resultado_sympy` lo escribe un LLM: nunca se pasa a eval/sympify sin restricciones.
Se valida contra una lista blanca de nombres y se evalúa sin builtins; además todo el
cálculo corre en un proceso aparte con tiempo límite (simplify puede colgarse).
"""

import cmath
import multiprocessing as mp
import queue
import re

import sympy as sp
from sympy.parsing.latex import parse_latex
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from .schemas import SolutionDraft, Tipo, Verificacion

TIMEOUT_S = 15
MAX_LEN = 500

_FUNCS = {n: getattr(sp, n) for n in (
    "sin", "cos", "tan", "cot", "sec", "csc", "asin", "acos", "atan",
    "sinh", "cosh", "tanh", "exp", "log", "sqrt", "Abs", "pi", "E", "oo", "I", "Rational", "Eq",
)}
_FUNCS.update({"ln": sp.log, "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan})
_SYMS = {n: sp.Symbol(n) for n in "xyztnabck"}
_LOCALS = {**_FUNCS, **_SYMS}
# parse_expr emite estos nombres al transformar literales y símbolos.
_GLOBALS = {"__builtins__": {}, "Integer": sp.Integer, "Float": sp.Float,
            "Rational": sp.Rational, "Symbol": sp.Symbol}
_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
_ALLOWED_CHARS = re.compile(r"^[A-Za-z0-9_+\-*/^()\[\],.=\s]+$")
_ATTRIBUTE = re.compile(r"[A-Za-z_\)\]]\s*\.")


class Unverifiable(Exception):
    pass


def safe_parse(text: str):
    text = text.strip()
    if not text or len(text) > MAX_LEN:
        raise Unverifiable("resultado_sympy vacío o demasiado largo")
    if not _ALLOWED_CHARS.match(text) or _ATTRIBUTE.search(text):
        raise Unverifiable("resultado_sympy contiene caracteres no permitidos")
    for name in re.findall(r"[A-Za-z_]\w*", text):
        if name not in _LOCALS:
            raise Unverifiable(f"nombre no permitido en resultado_sympy: {name}")
    try:
        return parse_expr(text, local_dict=_LOCALS, global_dict=dict(_GLOBALS),
                          transformations=_TRANSFORMS)
    except Exception as e:
        raise Unverifiable(f"no se pudo interpretar resultado_sympy ({type(e).__name__})")


_PREFIX = re.compile(r"^\s*[A-Za-z]\w*\s*(\(\s*[A-Za-z]\s*\))?\s*=\s*")


def parse_enunciado(latex: str, quitar_prefijo: bool):
    s = latex.strip()
    if quitar_prefijo and s.count("=") == 1:
        s = _PREFIX.sub("", s)
    try:
        expr = parse_latex(s, backend="lark")
    except Exception as e:
        raise Unverifiable(f"no se pudo interpretar el enunciado ({type(e).__name__})")
    if not isinstance(expr, sp.Basic):  # árbol ambiguo de lark
        raise Unverifiable("el enunciado LaTeX es ambiguo")
    # parse_latex lee la "e" de e^{x} como una variable, no como el número de Euler.
    return expr.subs(sp.Symbol("e"), sp.E)


def _var(expr):
    syms = expr.free_symbols
    if len(syms) == 1:
        return next(iter(syms))
    return _SYMS["x"] if _SYMS["x"] in syms or not syms else sorted(syms, key=str)[0]


def _num_equal(a, b):
    """True/False si hay puntos válidos suficientes, None si no es concluyente."""
    syms = sorted(a.free_symbols | b.free_symbols, key=str)
    ok = 0
    for base in (0.7, 1.3, 1.9, 2.4, 3.1):
        sub = {s: base + 0.37 * i for i, s in enumerate(syms)}
        try:
            da, db = complex(a.subs(sub).evalf()), complex(b.subs(sub).evalf())
        except (TypeError, ValueError):
            continue
        if any(cmath.isnan(v) or cmath.isinf(v) for v in (da, db)):
            continue
        if abs(da - db) > 1e-7 * (1 + abs(da)):
            return False
        ok += 1
    return True if ok >= 3 else None


def equivalent(a, b) -> bool:
    num = _num_equal(a, b)
    if num is True:
        return True
    return sp.simplify(a - b) == 0


def _mismatch(referencia, candidato) -> tuple[str, str]:
    return "no_verificado", f"SymPy obtiene {referencia}, pero el resultado indicado es {candidato}"


def _check_derivada(enunciado, cand):
    expr = parse_enunciado(enunciado, quitar_prefijo=True)
    if isinstance(expr, sp.Derivative):
        ref = expr.doit()
    else:
        ref = sp.diff(expr, _var(expr))
    if equivalent(ref, cand):
        return "verificado", "La derivada coincide con la calculada por SymPy"
    return _mismatch(ref, cand)


def _check_integral(enunciado, cand):
    expr = parse_enunciado(enunciado, quitar_prefijo=True)
    if not isinstance(expr, sp.Integral):
        raise Unverifiable("el enunciado no es una integral reconocible")
    var = expr.variables[0]
    if expr.limits[0][1:]:  # definida
        ref = expr.doit()
        if isinstance(ref, sp.Integral):
            raise Unverifiable("SymPy no pudo calcular la integral definida")
        if equivalent(ref, cand):
            return "verificado", "El valor coincide con el calculado por SymPy"
        return _mismatch(ref, cand)
    if equivalent(sp.diff(cand, var), expr.function):
        return "verificado", "La derivada de la primitiva coincide con el integrando"
    return "no_verificado", f"La derivada de {cand} no es el integrando {expr.function}"


def _check_ecuacion(enunciado, cand):
    expr = parse_enunciado(enunciado, quitar_prefijo=False)
    eq = expr.lhs - expr.rhs if isinstance(expr, sp.Eq) else expr
    var = _var(eq)
    items = list(cand) if isinstance(cand, (list, tuple, set, sp.Set)) else [cand]
    sols = [i.rhs if isinstance(i, sp.Eq) else i for i in items]
    if not sols:
        raise Unverifiable("sin soluciones que comprobar")
    for s in sols:
        r = eq.subs(var, s)
        if _num_equal(r, sp.Integer(0)) is False and sp.simplify(r) != 0:
            return "no_verificado", f"{var} = {s} no cumple la ecuación (da {sp.simplify(r)})"
    if eq.is_polynomial(var):
        ref = [r for r in sp.solve(eq, var) if abs(complex(r.evalf()).imag) < 1e-9]
        dados = {round(float(sp.re(sp.N(s))), 8) for s in sols}
        if len(dados) < len(ref):
            return "no_verificado", f"SymPy encuentra {len(ref)} soluciones reales y solo se indican {len(dados)}: {ref}"
        return "verificado", "Las soluciones cumplen la ecuación y están todas"
    return "verificado", "Las soluciones cumplen la ecuación (no se comprobó que sean todas)"


def _check_limite(enunciado, cand):
    expr = parse_enunciado(enunciado, quitar_prefijo=True)
    if not isinstance(expr, sp.Limit):
        raise Unverifiable("el enunciado no es un límite reconocible")
    ref = expr.doit()
    if isinstance(ref, sp.Limit):
        raise Unverifiable("SymPy no pudo calcular el límite")
    same = ref == cand if ref.has(sp.oo, sp.zoo) or cand.has(sp.oo, sp.zoo) else equivalent(ref, cand)
    if same:
        return "verificado", "El límite coincide con el calculado por SymPy"
    return _mismatch(ref, cand)


_CHECKS = {"derivada": _check_derivada, "integral": _check_integral,
           "ecuacion": _check_ecuacion, "limite": _check_limite}


def check(tipo: str, enunciado: str, resultado_sympy: str) -> tuple[str, str]:
    """Núcleo síncrono; devuelve (estado, detalle)."""
    fn = _CHECKS.get(tipo)
    if fn is None:
        return "no_verificable", "Este tipo de ejercicio no se puede verificar automáticamente"
    try:
        return fn(enunciado, safe_parse(resultado_sympy))
    except Unverifiable as e:
        return "no_verificable", str(e)
    except Exception as e:
        return "no_verificable", f"Error al verificar ({type(e).__name__})"


def _worker(q, fn, args):
    try:
        q.put(("ok", fn(*args)))
    except Exception as e:
        q.put(("err", f"{type(e).__name__}: {e}"))


def run_with_timeout(fn, args, timeout):
    """Ejecuta fn en un proceso aparte y lo mata si excede el tiempo."""
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_worker, args=(q, fn, args), daemon=True)
    p.start()
    try:
        kind, val = q.get(timeout=timeout)
    except queue.Empty:
        p.kill()
        p.join()
        raise TimeoutError(f"excedió {timeout}s")
    p.join()
    if kind == "err":
        raise RuntimeError(val)
    return val


def verify(tipo: Tipo, enunciado: str, draft: SolutionDraft) -> Verificacion:
    try:
        estado, detalle = run_with_timeout(check, (tipo, enunciado, draft.resultado_sympy), TIMEOUT_S)
    except TimeoutError:
        return Verificacion(estado="no_verificable", detalle="La verificación tardó demasiado")
    except Exception as e:
        return Verificacion(estado="no_verificable", detalle=f"Error al verificar ({e})")
    return Verificacion(estado=estado, detalle=detalle)
