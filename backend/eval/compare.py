"""Comparación de dos LaTeX: ¿el que leyó la app es el mismo ejercicio que el correcto?

Resultados:
  exacto       → iguales tras normalizar la forma (espacios, \\left, x^{2} / x^2, \\dfrac…)
  equivalente  → distinta forma pero SymPy los evalúa igual en varios puntos (p. ej. x\\sin(x) / x\\cdot\\sin(x))
  distinto     → SymPy los evalúa distinto: error de lectura casi seguro
  revisar      → no se pudo decidir (LaTeX que SymPy no lee, comparación no concluyente): mirar a mano
"""

import re

import sympy as sp

from app.verify import Unverifiable, _num_equal, parse_enunciado, run_with_timeout

_DROP = re.compile(r"\\left(?![a-z])|\\right(?![a-z])|\\displaystyle|\\[,;:!]|\\quad|\\qquad|\\ |\s+|\\cdot|\*")
_PREFIX = re.compile(r"^[A-Za-z]\w*(\([a-z,\s]+\))?=")


def normalizar(s: str) -> str:
    s = s.replace(r"\dfrac", r"\frac").replace(r"\tfrac", r"\frac").replace(r"\operatorname{", "{")
    s = s.replace(r"\mathrm{d}", "d").replace(r"\,", "")
    # \sin x → \sin(x): el argumento sin paréntesis es la misma lectura (antes de quitar espacios)
    s = re.sub(r"\\(sin|cos|tan|cot|sec|csc|ln|log|exp|arcsin|arccos|arctan)\s+([A-Za-z0-9]+)", r"\\\1(\2)", s)
    s = _DROP.sub("", s)
    for _ in range(3):  # llaves de un solo símbolo: x^{2} → x^2, e^{x} → e^x
        s = re.sub(r"\{([A-Za-z0-9+\-])\}", r"\1", s)
    s = re.sub(r"\\to|\\rightarrow", r"\\to", s)
    return _PREFIX.sub("", s) if s.count("=") == 1 else s


def _sympy(verdad: str, leido: str):
    """Corre en un proceso aparte. Devuelve 'equivalente' | 'distinto' | 'revisar'."""
    try:
        a, b = parse_enunciado(verdad, True), parse_enunciado(leido, True)
    except Unverifiable:
        return "revisar"
    if isinstance(a, sp.Eq) and isinstance(b, sp.Eq):  # una ecuación vale igual por un lado o por el otro
        a, b = a.lhs - a.rhs, b.lhs - b.rhs
        sign = _num_equal(a, -b)
        res = _num_equal(a, b)
        res = True if (res or sign) else res
    else:
        try:
            res = _num_equal(a, b)
        except Exception:
            return "revisar"
    return {True: "equivalente", False: "distinto", None: "revisar"}[res]


def comparar(verdad: str, leido: str) -> str:
    if normalizar(verdad) == normalizar(leido):
        return "exacto"
    try:
        return run_with_timeout(_sympy, (verdad, leido), 20)
    except Exception:
        return "revisar"
