"""Verificación independiente del resultado con SymPy.

`resultado_sympy` y `enunciado_sympy` los escribe un LLM: nunca se pasan a eval/sympify sin
restricciones. Se validan contra una lista blanca de nombres y se evalúan sin builtins; además todo
el cálculo corre en un proceso aparte con tiempo límite (simplify puede colgarse).

El enunciado se obtiene de dos fuentes que se contrastan cuando ambas están disponibles: la
transcripción a SymPy del modelo (inequívoca) y el LaTeX leído de la imagen, interpretado con
parse_latex (que falla o interpreta mal formas habituales como `x^2(x-1)` o `\\sin(x)(x+1)`).
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
    "sin", "cos", "tan", "cot", "sec", "csc", "asin", "acos", "atan", "acot", "asec", "acsc",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "exp", "log", "sqrt", "Abs", "sign",
    "pi", "E", "oo", "I", "Rational", "Eq", "Integral", "Limit", "Derivative",
)}
_FUNCS.update({"ln": sp.log, "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan, "abs": sp.Abs})
# Reales: con variables complejas SymPy deriva log(Abs(x)) como Derivative(re(x), x) y no se puede evaluar.
_SYMS = {n: sp.Symbol(n, real=True) for n in "xyztnabck"}
_LOCALS = {**_FUNCS, **_SYMS}
# parse_expr emite estos nombres al transformar literales y símbolos.
_GLOBALS = {"__builtins__": {}, "Integer": sp.Integer, "Float": sp.Float,
            "Rational": sp.Rational, "Symbol": sp.Symbol}
_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)
_ALLOWED_CHARS = re.compile(r"^[A-Za-z0-9_+\-*/^()\[\],.=\s]+$")
_ATTRIBUTE = re.compile(r"[A-Za-z_\)\]]\s*\.")


class Unverifiable(Exception):
    pass


def safe_parse(text: str, what: str = "resultado_sympy"):
    text = text.strip()
    if not text or len(text) > MAX_LEN:
        raise Unverifiable(f"{what} vacío o demasiado largo")
    if not _ALLOWED_CHARS.match(text) or _ATTRIBUTE.search(text):
        raise Unverifiable(f"{what} contiene caracteres no permitidos")
    for name in re.findall(r"[A-Za-z_]\w*", text):
        if name not in _LOCALS:
            raise Unverifiable(f"nombre no permitido en {what}: {name}")
    try:
        return parse_expr(text, local_dict=_LOCALS, global_dict=dict(_GLOBALS),
                          transformations=_TRANSFORMS)
    except Exception as e:
        raise Unverifiable(f"no se pudo interpretar {what} ({type(e).__name__})")


_PREFIX = re.compile(r"^\s*[A-Za-z]\w*\s*(\(\s*[A-Za-z]\s*\))?\s*=\s*")
_FUNC_NAMES = r"(?:sin|cos|tan|cot|sec|csc|ln|log|exp|arcsin|arccos|arctan|sinh|cosh|tanh)"
# Lo que parse_latex (lark) no sabe leer o lee mal: se hace explícito el producto.
_POW_THEN_FACTOR = re.compile(
    # Los límites de \int, \sum o \prod (_{a}^{b}) no son una potencia: se capturan para dejarlos intactos.
    r"(\\(?:i{1,3}nt|oint|sum|prod)\s*_(?:\{[^{}]*\}|[A-Za-z0-9]))?"
    r"(\^\{[^{}]*\}|\^[A-Za-z0-9])\s*"
    r"(?=\(|\\left\s*\(|\\(?:sin|cos|tan|cot|sec|csc|ln|log|exp|sqrt|frac|dfrac|arcsin|arccos|arctan|sinh|cosh|tanh)\b)"
)
_FUNC_THEN_PAREN = re.compile(r"(\\" + _FUNC_NAMES + r"\s*\([^()]*\))\s*(?=\()")


def _normalize_latex(s: str) -> str:
    s = s.replace("\\ ", " ")  # parse_latex no admite "barra-espacio" (sí \, \; \! \quad)
    # x^2(x-1), x^2\sin(x): falla sin el producto explícito (salvo en los límites de \int, \sum...)
    s = _POW_THEN_FACTOR.sub(lambda m: m.group(0) if m.group(1) else f"{m.group(2)} \\cdot ", s)
    s = _FUNC_THEN_PAREN.sub(r"\1 \\cdot ", s)  # \sin(x)(x+1) se lee como sin(x(x+1)) si no
    return s


def parse_enunciado(latex: str, quitar_prefijo: bool):
    s = _normalize_latex(latex.strip())
    if quitar_prefijo and s.count("=") == 1:
        s = _PREFIX.sub("", s)
    try:
        expr = parse_latex(s, backend="lark")
    except Exception as e:
        raise Unverifiable(f"no se pudo interpretar el enunciado ({type(e).__name__})")
    if not isinstance(expr, sp.Basic):  # árbol ambiguo de lark
        raise Unverifiable("el enunciado LaTeX es ambiguo")
    # parse_latex lee la "e" de e^{x} como una variable, no como el número de Euler.
    expr = expr.subs(sp.Symbol("e"), sp.E)
    # Mismas variables (reales) que las de safe_parse, para que las dos lecturas sean comparables.
    return expr.xreplace({a: sp.Symbol(a.name, real=True) for a in expr.atoms(sp.Symbol)})


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
    a, b = sp.sympify(a), sp.sympify(b)
    num = _num_equal(a, b)
    if num is True:
        return True
    return sp.simplify(a - b) == 0


def _close(a, b, tol=1e-6) -> bool:
    """Igualdad numérica de dos valores (sin símbolos libres)."""
    try:
        da, db = complex(sp.N(a)), complex(sp.N(b))
    except (TypeError, ValueError):
        return False
    if any(cmath.isnan(v) or cmath.isinf(v) for v in (da, db)):
        return False
    return abs(da - db) <= tol * (1 + abs(da))


def _mismatch(referencia, candidato) -> tuple[str, str]:
    return "no_verificado", f"SymPy obtiene {referencia}, pero el resultado indicado es {candidato}"


# --- Qué problema se está verificando -------------------------------------------------------

def _signature(tipo: str, obj):
    """Reduce el enunciado a lo comparable: (expresiones equivalentes entre sí, datos exactos)."""
    if tipo == "derivada":
        return [obj.expr if isinstance(obj, sp.Derivative) else obj], ()
    if tipo == "integral":
        if not isinstance(obj, sp.Integral):
            raise Unverifiable("el enunciado no es una integral reconocible")
        return [obj.function], tuple(obj.limits[0])
    if tipo == "ecuacion":
        return [obj.lhs - obj.rhs if isinstance(obj, sp.Eq) else obj], ()
    if tipo == "limite":
        if not isinstance(obj, sp.Limit):
            raise Unverifiable("el enunciado no es un límite reconocible")
        f, x, punto = obj.args[:3]
        return [f], (x, punto)
    raise Unverifiable("tipo sin verificador")


def _same_problem(tipo: str, a, b) -> bool:
    (ea,), da = _signature(tipo, a)
    (eb,), db = _signature(tipo, b)
    if da != db:
        return False
    return equivalent(ea, eb) or (tipo == "ecuacion" and equivalent(ea, -eb))


def _problem(tipo: str, latex: str, enunciado_sympy: str):
    """Devuelve (objeto SymPy del problema, nota para el detalle)."""
    quitar = tipo != "ecuacion"
    del_latex, error_latex = None, ""
    try:
        del_latex = parse_enunciado(latex, quitar_prefijo=quitar)
    except Unverifiable as e:
        error_latex = str(e)
    del_modelo, error_modelo = None, ""
    if enunciado_sympy.strip():
        try:
            del_modelo = safe_parse(enunciado_sympy, "enunciado_sympy")
        except Unverifiable as e:
            error_modelo = str(e)

    if del_modelo is not None and del_latex is not None:
        if not _same_problem(tipo, del_modelo, del_latex):
            raise Unverifiable("el enunciado transcrito a SymPy no coincide con el LaTeX leído: no se verifica")
        return del_modelo, ""
    if del_modelo is not None:
        return del_modelo, " (enunciado transcrito por el modelo: el LaTeX no se pudo interpretar de forma independiente)"
    if del_latex is not None:
        return del_latex, ""
    raise Unverifiable(error_latex + (f"; {error_modelo}" if error_modelo else ""))


# --- Comprobaciones por tipo ----------------------------------------------------------------

def _check_derivada(obj, cand):
    if isinstance(obj, sp.Derivative):
        ref = obj.doit()
    else:
        ref = sp.diff(obj, _var(obj))
    if equivalent(ref, cand):
        return "verificado", "La derivada coincide con la calculada por SymPy"
    return _mismatch(ref, cand)


def _valor_numerico(integral):
    """Valor de una integral definida (también impropia) por cuadratura numérica; si no, simbólico."""
    try:
        v = integral.evalf()
        if v.is_number and v.is_finite:
            return v
    except Exception:
        pass
    ref = integral.doit()
    if isinstance(ref, sp.Integral):
        raise Unverifiable("SymPy no pudo calcular la integral definida")
    return ref


def _check_integral(obj, cand):
    var = obj.variables[0]
    if obj.limits[0][1:]:  # definida
        if cand.has(sp.oo, -sp.oo, sp.zoo, sp.nan):
            raise Unverifiable("integral divergente: no se verifica")
        ref = _valor_numerico(obj)
        if _close(ref, cand):
            return "verificado", "El valor coincide con la integral calculada numéricamente por SymPy"
        return "no_verificado", f"SymPy obtiene ≈ {sp.N(ref, 8)}, pero el resultado indicado vale ≈ {sp.N(cand, 8)}"
    if equivalent(sp.diff(cand, var), obj.function):
        return "verificado", "La derivada de la primitiva coincide con el integrando"
    return "no_verificado", f"La derivada de {cand} no es el integrando {obj.function}"


def _check_ecuacion(obj, cand):
    eq = obj.lhs - obj.rhs if isinstance(obj, sp.Eq) else obj
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


def _check_limite(obj, cand):
    ref = obj.doit()
    if isinstance(ref, sp.Limit):
        raise Unverifiable("SymPy no pudo calcular el límite")
    same = ref == cand if ref.has(sp.oo, sp.zoo) or cand.has(sp.oo, sp.zoo) else equivalent(ref, cand)
    if same:
        return "verificado", "El límite coincide con el calculado por SymPy"
    return _mismatch(ref, cand)


_CHECKS = {"derivada": _check_derivada, "integral": _check_integral,
           "ecuacion": _check_ecuacion, "limite": _check_limite}


def check(tipo: str, enunciado: str, resultado_sympy: str, enunciado_sympy: str = "") -> tuple[str, str]:
    """Núcleo síncrono; devuelve (estado, detalle)."""
    fn = _CHECKS.get(tipo)
    if fn is None:
        return "no_verificable", "Este tipo de ejercicio no se puede verificar automáticamente"
    try:
        obj, nota = _problem(tipo, enunciado, enunciado_sympy)
        estado, detalle = fn(obj, safe_parse(resultado_sympy))
        return estado, detalle + (nota if estado == "verificado" else "")
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
    args = (tipo, enunciado, draft.resultado_sympy, draft.enunciado_sympy)
    try:
        estado, detalle = run_with_timeout(check, args, TIMEOUT_S)
    except TimeoutError:
        return Verificacion(estado="no_verificable", detalle="La verificación tardó demasiado")
    except Exception as e:
        return Verificacion(estado="no_verificable", detalle=f"Error al verificar ({e})")
    return Verificacion(estado=estado, detalle=detalle)
