"""Muestreo de funciones para la graficadora: curvas 2D y superficies z = f(x, y).

Nunca llama a la API de pago. La expresión viene de `enunciado_sympy` / `resultado_sympy`, que escribe un
LLM: se interpreta con `safe_parse` (lista blanca de nombres, sin builtins) y TODO el cálculo —también el
parseo, porque `9**9**9` cuelga ya al interpretarlo— corre en un proceso aparte con tiempo límite
(`run_with_timeout`), nunca en el proceso del servidor.

`build_plot` es síncrona, devuelve siempre un dict (`{"kind": "none", "motivo": ...}` ante cualquier fallo) y el
`motivo` solo lleva textos propios: jamás el texto de una excepción ni rutas.
"""

import cmath
import json
import time

import sympy as sp
from pydantic import TypeAdapter

from .schemas import Plot, Plot2D, Plot3D, PlotNone, PlotRequest
from .verify import Unverifiable, _num_equal, parse_enunciado, run_with_timeout, safe_parse

TIMEOUT_S = 6          # el proceso hijo se mata pasado este tiempo
BUDGET_S = 3.0         # corte interno, antes del timeout, para devolver un motivo en vez de nada
MAX_OPS = 300          # tamaño máximo de la expresión (sp.count_ops)
MAX_BYTES = 300_000    # tamaño máximo de la respuesta serializada
N_1D = 400             # muestras de una curva 2D
DEFAULT_X = (-5.0, 5.0)
DEFAULT_3D = (-3.0, 3.0)   # rango por defecto de x e y en una superficie
MIN_VALID = 0.3


class _Sin(Exception):
    """No hay gráfica; el texto es el motivo (siempre propio)."""


def _none(motivo: str) -> dict:
    return {"kind": "none", "motivo": motivo}


def _r(v: float) -> float:
    return float(f"{v:.5g}")


def _eval(fn, *args):
    """Valor real de fn(*args), o None si el punto no sirve (dominio no real, división por cero, desbordamiento...)."""
    try:
        v = complex(fn(*args))
    except Exception:
        return None
    if cmath.isnan(v) or cmath.isinf(v) or abs(v.imag) > 1e-9:
        return None
    return v.real


def _compile(expr, symbols):
    if sp.count_ops(expr) > MAX_OPS:
        raise _Sin("la expresión es demasiado grande para graficarla")
    return sp.lambdify(symbols, expr, modules="mpmath")


def _unwrap(obj):
    """(clase, contenido, extras): quita el envoltorio Derivative/Integral/Limit/Eq del enunciado."""
    if isinstance(obj, sp.Derivative):
        return "expr", obj.expr, {}
    if isinstance(obj, sp.Integral):
        return "integral", obj.function, {"limites": [tuple(lim) for lim in obj.limits]}
    if isinstance(obj, sp.Limit):
        f, _x, punto, _dir = obj.args
        return "limite", f, {"punto": punto}
    if isinstance(obj, sp.Eq):
        return "eq", (obj.lhs, obj.rhs), {}
    return "expr", obj, {}


def _classify(exprs):
    """('2d', [var]) | ('3d', [x, y]); lanza _Sin si no se puede graficar."""
    syms = set()
    for e in exprs:
        syms |= e.free_symbols
    names = {s.name: s for s in syms}
    if not names:
        raise _Sin("el enunciado no tiene ninguna variable que graficar")
    if len(names) == 1 and next(iter(names)) in ("x", "y", "t"):
        return "2d", [next(iter(names.values()))]
    if set(names) == {"x", "y"}:
        return "3d", [names["x"], names["y"]]
    if "z" in names:
        raise _Sin("usa x e y: z es el eje de altura")
    raise _Sin("la expresión tiene parámetros o más de dos variables: no se puede graficar")


# --- Escala vertical -----------------------------------------------------------------------------

def _window(valores):
    """Ventana vertical robusta: percentiles 5-95 más margen; el rango completo si cabe en 3 veces eso."""
    vs = sorted(valores)
    n = len(vs)
    lo, hi = vs[int(0.05 * (n - 1))], vs[int(0.95 * (n - 1))]
    span = hi - lo
    if span < 1e-12:                      # constante (o casi): ±1 alrededor
        return lo - 1.0, lo + 1.0
    ymin, ymax = lo - 0.15 * span, hi + 0.15 * span
    full = vs[-1] - vs[0]
    if full <= 3 * (ymax - ymin):         # cabe: se enseña todo
        pad = 0.05 * full
        return vs[0] - pad, vs[-1] + pad
    return ymin, ymax


def _segments(xs, ys, fn, ymin, ymax):
    """Tramos continuos: se corta en los huecos de dominio y en los polos (asíntotas verticales)."""
    alto = ymax - ymin
    segs, cur, prev = [], [], None

    def cerrar():
        nonlocal cur
        if len(cur) >= 2:
            segs.append(cur)
        cur = []

    for x, y in zip(xs, ys):
        if y is None or y > ymax + 10 * alto or y < ymin - 10 * alto:
            cerrar()
            prev = None
            continue
        if prev is not None:
            px, py = prev
            if abs(y - py) > 2 * alto:
                medio = _eval(fn, (x + px) / 2)
                polo = medio is None or abs(medio) > max(abs(py), abs(y))
                lados_opuestos = (py > ymax and y < ymin) or (py < ymin and y > ymax)
                if polo or lados_opuestos:
                    cerrar()
        cur.append((_r(x), _r(y)))
        prev = (x, y)
    cerrar()
    return segs


# --- 2D ----------------------------------------------------------------------------------------

def _finito(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def _soluciones(resultado_sympy: str):
    """Valores reales de resultado_sympy (lista, conjunto, Eq(x, v) o un solo valor)."""
    try:
        r = safe_parse(resultado_sympy)
    except Unverifiable:
        return []
    items = list(r) if isinstance(r, (list, tuple, set, sp.Set)) else [r]
    out = []
    for i in items:
        v = _finito(sp.N(i.rhs if isinstance(i, sp.Eq) else i))
        if v is not None:
            out.append(v)
    return out


def _plot_2d(tipo, clase, contenido, extras, var, resultado_sympy, x_min, x_max, t0):
    series = []   # (label, rol, expr)
    puntos, area, pistas = [], None, []
    nombre = var.name

    if clase == "eq":
        lhs, rhs = contenido
        series += [("lado izquierdo", "izquierda", lhs), ("lado derecho", "derecha", rhs)]
        pistas = _soluciones(resultado_sympy)
    elif clase == "integral":
        series.append((f"f({nombre})", "f", contenido))
        lim = extras["limites"][0]
        if len(lim) == 3:
            a, b = _finito(lim[1]), _finito(lim[2])
            if a is not None and b is not None and a != b:
                area = (min(a, b), max(a, b))
        else:   # indefinida: la primitiva solo se dibuja si de verdad lo es
            try:
                F = safe_parse(resultado_sympy)
                if F.free_symbols <= {var} and _num_equal(sp.diff(F, var), contenido) is True:
                    series.append((f"F({nombre})", "primitiva", F))
            except Unverifiable:
                pass
    elif clase == "limite":
        series.append((f"f({nombre})", "f", contenido))
        a = _finito(extras["punto"])
        L = _soluciones(resultado_sympy)
        if a is not None and len(L) == 1:
            puntos.append((a, L[0], "límite", True))
        if a is not None:
            pistas = [a]
    else:
        series.append((f"f({nombre})", "f", contenido))
        if tipo == "derivada":
            series.append((f"f'({nombre})", "derivada", sp.diff(contenido, var)))

    if x_min is not None:
        candidatos = [(float(x_min), float(x_max))]
    else:
        if area is not None:
            m = 0.3 * (area[1] - area[0])
            primero = (area[0] - m, area[1] + m)
        elif clase == "limite" and pistas:
            primero = (pistas[0] - 5, pistas[0] + 5)
        else:
            lo, hi = DEFAULT_X
            if pistas:
                lo, hi = min(lo, min(pistas)), max(hi, max(pistas))
                m = 0.2 * (hi - lo)
                lo, hi = lo - m, hi + m
            primero = (lo, hi)
        candidatos = [primero]

    compiladas = [(lab, rol, e, _compile(e, [var])) for lab, rol, e in series]

    def muestrear(lo, hi):
        xs = [lo + (hi - lo) * i / (N_1D - 1) for i in range(N_1D)]
        valores = []
        for _lab, _rol, _e, fn in compiladas:
            valores.append([_eval(fn, x) for x in xs])
            if time.monotonic() - t0 > BUDGET_S:
                raise _Sin("la gráfica tardó demasiado")
        return xs, valores, sum(v is not None for v in valores[0]) / N_1D

    lo, hi = candidatos[0]
    xs, valores, validos = muestrear(lo, hi)
    if validos < MIN_VALID and x_min is None:
        # Casi nada es real en el rango por defecto (asin, log de algo pequeño...): se acerca la vista
        # a donde sí hay valores.
        con_valor = [x for x, v in zip(xs, valores[0]) if v is not None]
        if con_valor:
            a, b = min(con_valor), max(con_valor)
            m = 0.2 * (b - a) if b > a else 1.0
            lo2, hi2 = a - m, b + m
            xs2, valores2, validos2 = muestrear(lo2, hi2)
            if validos2 > validos:
                lo, hi, xs, valores = lo2, hi2, xs2, valores2
    if not any(v is not None for ys in valores for v in ys):
        raise _Sin("la función no toma valores reales en el rango representado")

    ymin, ymax = _window([v for ys in valores for v in ys if v is not None])
    salida = []
    for (lab, rol, _e, fn), ys in zip(compiladas, valores):
        segs = _segments(xs, ys, fn, ymin, ymax)
        if segs:
            salida.append({"label": lab, "rol": rol, "segmentos": segs})
    if not salida:
        raise _Sin("no hay tramos continuos que dibujar")

    # Puntos (soluciones de una ecuación): solo si realmente cumplen l = r.
    pts = []
    if clase == "eq":
        fl, fr = compiladas[0][3], compiladas[1][3]
        for s in pistas:
            l, r = _eval(fl, s), _eval(fr, s)
            if l is not None and r is not None and abs(l - r) < 1e-6 and lo <= s <= hi:
                pts.append({"x": _r(s), "y": _r(r), "label": f"{nombre} = {_r(s)}", "hueco": False})
    for x, y, lab, hueco in puntos:
        if lo <= x <= hi:
            pts.append({"x": _r(x), "y": _r(y), "label": lab, "hueco": hueco})

    return {
        "kind": "2d",
        "variable": nombre,
        "x_range": [_r(lo), _r(hi)],
        "y_range": [_r(ymin), _r(ymax)],
        "series": salida,
        "puntos": pts,
        "area": {"a": _r(area[0]), "b": _r(area[1]), "serie": 0} if area else None,
    }


# --- 3D: superficie z = f(x, y) -------------------------------------------------------------------

def _linspace(lo, hi, n):
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


def _plot_3d(clase, contenido, extras, xy, x_min, x_max, y_min, y_max, n, t0):
    if clase == "eq":
        raise _Sin("las ecuaciones con dos variables aún no se grafican")
    x_sym, y_sym = xy
    rx = ry = DEFAULT_3D
    if clase == "integral":   # integral doble: el rectángulo de integración (más un 20 %)
        for lim in extras["limites"]:
            if len(lim) == 3 and lim[0].name in ("x", "y"):
                a, b = _finito(lim[1]), _finito(lim[2])
                if a is not None and b is not None and a != b:
                    lo, hi = min(a, b), max(a, b)
                    m = 0.2 * (hi - lo)
                    if lim[0].name == "x":
                        rx = (lo - m, hi + m)
                    else:
                        ry = (lo - m, hi + m)
    if x_min is not None:
        rx = (float(x_min), float(x_max))
    if y_min is not None:
        ry = (float(y_min), float(y_max))

    fn = _compile(contenido, [x_sym, y_sym])

    def muestrear(rx, ry):
        xs, ys = _linspace(*rx, n), _linspace(*ry, n)
        z = []
        for yv in ys:
            z.append([_eval(fn, xv, yv) for xv in xs])
            if time.monotonic() - t0 > BUDGET_S:
                raise _Sin("la gráfica tardó demasiado")
        return xs, ys, z, sum(v is not None for fila in z for v in fila) / (n * n)

    xs, ys, z, validos = muestrear(rx, ry)
    if validos < MIN_VALID and x_min is None and y_min is None:
        # Casi nada es real en el rango por defecto (un disco, log de algo pequeño...): se acerca la vista.
        celdas = [(xs[i], ys[j]) for j, fila in enumerate(z) for i, v in enumerate(fila) if v is not None]
        if celdas:
            ax, bx = min(c[0] for c in celdas), max(c[0] for c in celdas)
            ay, by = min(c[1] for c in celdas), max(c[1] for c in celdas)
            mx, my = 0.2 * (bx - ax) or 1.0, 0.2 * (by - ay) or 1.0
            nuevo = muestrear((ax - mx, bx + mx), (ay - my, by + my))
            if nuevo[3] > validos:
                xs, ys, z, validos = nuevo
    valores = [v for fila in z for v in fila if v is not None]
    if not valores:
        raise _Sin("la función no toma valores reales en el rango representado")

    # Los polos (1/(x²-y²)...) dan picos infinitos: lo que se sale de la ventana robusta es un hueco, no un pico.
    lo, hi = _window(valores)
    alto = hi - lo
    z = [[None if v is None or v < lo - alto or v > hi + alto else v for v in fila] for fila in z]
    kept = [v for fila in z for v in fila if v is not None]
    zmin, zmax = min(kept), max(kept)
    if zmax - zmin < 1e-12:
        zmin, zmax = zmin - 1.0, zmax + 1.0
    return {
        "kind": "3d",
        "label": "f(x, y)",
        "x": [_r(v) for v in xs],
        "y": [_r(v) for v in ys],
        "z": [[None if v is None else _r(v) for v in fila] for fila in z],
        "z_range": [_r(zmin), _r(zmax)],
    }


# --- Punto de entrada ---------------------------------------------------------------------------

def build_plot(tipo, enunciado_sympy, resultado_sympy, x_min, x_max, y_min, y_max, n, enunciado_latex="") -> dict:
    """Corre en el proceso hijo. Siempre devuelve un dict serializable.

    Si llega `enunciado_latex` (entrada libre del usuario) se interpreta con `parse_enunciado`, quitando un
    prefijo `f(x) =` / `z =`; si no, `enunciado_sympy` pasa por `safe_parse`.
    """
    t0 = time.monotonic()
    try:
        if enunciado_latex.strip():
            obj = parse_enunciado(enunciado_latex, True)
        elif enunciado_sympy.strip():
            obj = safe_parse(enunciado_sympy, "enunciado_sympy")
        else:
            raise _Sin("sin enunciado en SymPy: no se puede graficar")
        clase, contenido, extras = _unwrap(obj)
        exprs = list(contenido) if clase == "eq" else [contenido]
        dim, simbolos = _classify(exprs)
        if dim == "3d":
            data = _plot_3d(clase, contenido, extras, simbolos, x_min, x_max, y_min, y_max, n, t0)
        else:
            data = _plot_2d(tipo, clase, contenido, extras, simbolos[0], resultado_sympy, x_min, x_max, t0)
        if len(json.dumps(data)) > MAX_BYTES:
            raise _Sin("la gráfica es demasiado grande")
        return data
    except _Sin as e:
        return _none(str(e))
    except Unverifiable as e:
        return _none(str(e))
    except Exception:
        return _none("no se puede graficar esta expresión")


_adapter = TypeAdapter(Plot)


def plot(req: PlotRequest) -> Plot2D | Plot3D | PlotNone:
    """Calcula la gráfica en un proceso aparte con tiempo límite; ante cualquier fallo, PlotNone."""
    args = (req.tipo, req.enunciado_sympy, req.resultado_sympy,
            req.x_min, req.x_max, req.y_min, req.y_max, req.n, req.enunciado_latex)
    try:
        return _adapter.validate_python(run_with_timeout(build_plot, args, TIMEOUT_S))
    except TimeoutError:
        return PlotNone(kind="none", motivo="La gráfica tardó demasiado")
    except Exception:
        return PlotNone(kind="none", motivo="no se puede graficar esta expresión")
