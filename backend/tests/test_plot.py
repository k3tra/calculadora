"""Graficadora 2D: muestreo por tipo, asíntotas, dominio, seguridad, validaciones y limitador."""

import pytest
import sympy as sp
from fastapi.testclient import TestClient

from app.limits import plot_limiter
from app.main import app
from app.plot import _Sin, _compile, _eval, build_plot
from app.schemas import Plot2D
from app.verify import _LOCALS

client = TestClient(app)


def bp(tipo, enun, res="", x_min=None, x_max=None):
    return build_plot(tipo, enun, res, x_min, x_max, None, None, 41)


def serie(d, rol="f"):
    return next(s for s in d["series"] if s["rol"] == rol)


def xs(d, rol="f"):
    return [p[0] for seg in serie(d, rol)["segmentos"] for p in seg]


# --- Qué se dibuja según el tipo ---

def test_derivada_dibuja_f_y_su_derivada():
    d = bp("derivada", "x**2*sin(x)")
    assert d["kind"] == "2d" and d["variable"] == "x"
    assert [s["rol"] for s in d["series"]] == ["f", "derivada"]
    assert d["x_range"] == [-5.0, 5.0]


def test_derivada_con_envoltorio_derivative():
    d = bp("derivada", "Derivative(x**2, x)")
    assert [s["rol"] for s in d["series"]] == ["f", "derivada"]


def test_integral_indefinida_dibuja_la_primitiva_solo_si_lo_es():
    ok = bp("integral", "Integral(x*exp(x), x)", "(x - 1)*exp(x)")
    assert [s["rol"] for s in ok["series"]] == ["f", "primitiva"]
    mala = bp("integral", "Integral(x*exp(x), x)", "x*exp(x)")
    assert [s["rol"] for s in mala["series"]] == ["f"]
    vacia = bp("integral", "Integral(x*exp(x), x)", "")
    assert [s["rol"] for s in vacia["series"]] == ["f"]


def test_integral_definida_sombrea_el_area_y_centra_la_vista():
    d = bp("integral", "Integral(x**2, (x, 0, 1))", "1/3")
    assert d["area"] == {"a": 0.0, "b": 1.0, "serie": 0}
    assert d["x_range"][0] < 0 and d["x_range"][1] > 1 and d["x_range"][1] - d["x_range"][0] < 3


def test_integral_impropia_no_sombrea():
    d = bp("integral", "Integral(1/(x**3 + 1), (x, 1, oo))", "pi/(3*sqrt(3)) - log(2)/3")
    assert d["kind"] == "2d" and d["area"] is None


def test_ecuacion_dibuja_ambos_lados_y_solo_las_soluciones_verdaderas():
    d = bp("ecuacion", "Eq(x**2, 4)", "[2, -2, 7]")
    assert [s["rol"] for s in d["series"]] == ["izquierda", "derecha"]
    assert sorted(p["x"] for p in d["puntos"]) == [-2.0, 2.0]   # el 7 no cumple la ecuación y se descarta


def test_limite_marca_el_punto_hueco():
    d = bp("limite", "Limit(sin(x)/x, x, 0)", "1")
    assert d["puntos"] == [{"x": 0.0, "y": 1.0, "label": "límite", "hueco": True}]


def test_limite_infinito_no_marca_punto():
    d = bp("limite", "LimitPlus(1/x, x, 0)", "oo")
    assert d["kind"] == "2d" and d["puntos"] == []


def test_otro_tipo_con_una_variable_dibuja_la_funcion():
    d = bp("otro", "x**3 - x")
    assert [s["rol"] for s in d["series"]] == ["f"]


# --- Asíntotas, dominio y escala ---

def test_asintota_de_1_sobre_x_no_une_los_dos_lados():
    d = bp("otro", "1/x")
    segs = serie(d)["segmentos"]
    assert len(segs) >= 2
    assert all(not (min(p[0] for p in s) < 0 < max(p[0] for p in s)) for s in segs)


def test_tangente_se_corta_en_cada_asintota():
    assert len(serie(bp("otro", "tan(x)"))["segmentos"]) >= 3


def test_dos_polos_dan_tres_tramos():
    assert len(serie(bp("otro", "1/(x**2 - 9)"))["segmentos"]) >= 3


def test_dominio_real_sqrt_y_log():
    assert min(xs(bp("otro", "sqrt(x)"))) >= 0
    assert min(xs(bp("otro", "log(x)"))) > 0


def test_si_casi_nada_es_valido_se_acerca_la_vista():
    d = bp("otro", "asin(x)")        # solo existe en [-1, 1]
    assert d["x_range"][1] - d["x_range"][0] < 5
    assert all(-1.0001 <= x <= 1.0001 for x in xs(d))


def test_funcion_constante_tiene_ventana_finita_alrededor():
    d = bp("otro", "sin(x)**2 + cos(x)**2")
    assert d["y_range"][0] < 1 < d["y_range"][1]


def test_funcion_que_se_dispara_no_aplasta_la_escala():
    d = bp("otro", "exp(x)")
    assert d["y_range"][1] - d["y_range"][0] < 500


def test_rango_pedido_se_respeta():
    assert bp("otro", "x**2", x_min=-1, x_max=2)["x_range"] == [-1.0, 2.0]


def test_la_salida_esta_redondeada():
    d = bp("otro", "x**2*sin(x) + 1/3")
    for seg in serie(d)["segmentos"]:
        for x, y in seg:
            assert len(repr(x).lstrip("-").replace(".", "").lstrip("0")) <= 7
            assert len(repr(y).lstrip("-").replace(".", "").lstrip("0")) <= 7


# --- No se grafica: nunca error, solo un motivo propio ---

@pytest.mark.parametrize("enun,fragmento", [
    ("x**2 + a", "parámetros"),
    ("z**2", "z es el eje de altura"),
    ("5", "ninguna variable"),
    ("", "sin enunciado"),
    ("__import__('os')", "no permitidos"),
    ("x.__class__", "no permitidos"),
    ("open('x')", "no permitido"),
])
def test_no_se_grafica_con_motivo_propio(enun, fragmento):
    d = bp("otro", enun)
    assert d["kind"] == "none" and fragmento in d["motivo"]
    assert "Traceback" not in d["motivo"] and "\\" not in d["motivo"]


def test_expresion_demasiado_grande_no_se_compila():
    x = sp.Symbol("x", real=True)
    grande = sp.Add(*[x**i for i in range(2, 400)])
    with pytest.raises(_Sin):
        _compile(grande, [x])


# --- Todas las funciones de la lista blanca se pueden evaluar ---

_UNARIAS = ["sin", "cos", "tan", "cot", "sec", "csc", "asin", "acos", "atan", "acot", "asec", "acsc",
            "sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "exp", "log", "sqrt", "Abs", "sign",
            "ln", "arcsin", "arccos", "arctan", "abs"]


@pytest.mark.parametrize("nombre", _UNARIAS)
def test_lambdify_evalua_toda_la_lista_blanca(nombre):
    x = sp.Symbol("x", real=True)
    fn = _compile(_LOCALS[nombre](x), [x])
    for v in (0.5, 2.0, -0.5, 0.0):
        r = _eval(fn, v)
        assert r is None or isinstance(r, float)


# --- Endpoint (proceso aparte con tiempo límite) ---

def test_endpoint_devuelve_una_grafica_valida():
    r = client.post("/api/plot", json={"tipo": "derivada", "enunciado_sympy": "x**2*sin(x)"})
    assert r.status_code == 200
    p = Plot2D(**r.json())
    assert [s.rol for s in p.series] == ["f", "derivada"]


def test_endpoint_corta_una_expresion_patologica():
    r = client.post("/api/plot", json={"tipo": "otro", "enunciado_sympy": "9**9**9"})
    assert r.status_code == 200
    assert r.json() == {"kind": "none", "motivo": "La gráfica tardó demasiado"}


def test_endpoint_no_filtra_detalles_internos():
    r = client.post("/api/plot", json={"tipo": "otro", "enunciado_sympy": "__import__('os').system('x')"})
    assert r.status_code == 200 and r.json()["kind"] == "none"
    texto = r.text
    assert "Traceback" not in texto and "backend" not in texto and "site-packages" not in texto


@pytest.mark.parametrize("cuerpo", [
    {"enunciado_sympy": "x", "x_min": 3, "x_max": 1},
    {"enunciado_sympy": "x", "x_min": 1},
    {"enunciado_sympy": "x", "n": 500},
    {"enunciado_sympy": "x", "n": 5},
    {"enunciado_sympy": "x" * 600},
    {"enunciado_sympy": "x", "resultado_sympy": "x" * 600},
    {"enunciado_sympy": "x", "x_min": -1e9, "x_max": 1e9},
    {"enunciado_sympy": "x", "x_min": 0, "x_max": 1e-9},
    {"enunciado_sympy": "x", "y_min": 2, "y_max": 1},
    {"enunciado_sympy": "x", "x_min": "NaN", "x_max": 1},
    {"enunciado_sympy": "x", "tipo": "inventado"},
])
def test_endpoint_rechaza_peticiones_invalidas(cuerpo):
    assert client.post("/api/plot", json=cuerpo).status_code == 422


def test_endpoint_tiene_su_propio_limitador(monkeypatch):
    monkeypatch.setattr(plot_limiter, "per_minute", 1)
    cuerpo = {"tipo": "otro", "enunciado_sympy": "x**2"}
    assert client.post("/api/plot", json=cuerpo).status_code == 200
    r = client.post("/api/plot", json=cuerpo)
    assert r.status_code == 429 and "Retry-After" in r.headers


# --- Superficies 3D: z = f(x, y) ---

def test_superficie_silla_de_montar():
    d = bp("otro", "x**2 - y**2")
    assert d["kind"] == "3d"
    assert len(d["x"]) == len(d["y"]) == 41 and len(d["z"]) == 41 and all(len(f) == 41 for f in d["z"])
    assert d["x"][0] == -3.0 and d["x"][-1] == 3.0 and d["y"][0] == -3.0 and d["y"][-1] == 3.0
    assert d["z_range"] == [-9.0, 9.0]
    assert d["z"][0][0] == 0.0          # z[j][i] = f(x[i], y[j]): en (-3, -3) vale 9 - 9


def test_indices_z_j_i_son_y_luego_x():
    d = build_plot("otro", "x - 10*y", "", None, None, None, None, 11)
    # z[j][i] = f(x[i], y[j]) = x[i] - 10 y[j]
    for j in (0, 3, 10):
        for i in (0, 5, 10):
            assert abs(d["z"][j][i] - (d["x"][i] - 10 * d["y"][j])) < 1e-3


def test_malla_y_rango_se_pueden_pedir():
    d = build_plot("otro", "sin(x)*cos(y)", "", -1, 1, -2, 2, 11)
    assert (len(d["x"]), len(d["y"])) == (11, 11)
    assert (d["x"][0], d["x"][-1], d["y"][0], d["y"][-1]) == (-1.0, 1.0, -2.0, 2.0)


def test_polos_dan_huecos_no_picos():
    d = bp("otro", "1/(x**2 - y**2)")
    nulos = sum(v is None for f in d["z"] for v in f)
    assert nulos > 0
    lo, hi = d["z_range"]
    assert all(lo <= v <= hi for f in d["z"] for v in f if v is not None)
    assert hi - lo < 100          # no hay picos de miles de unidades


def test_dominio_parcial_deja_huecos_en_los_cuadrantes_invalidos():
    d = bp("otro", "log(x*y)")
    i_neg = next(i for i, x in enumerate(d["x"]) if x < -1)
    i_pos = next(i for i, x in enumerate(d["x"]) if x > 1)
    j_pos = next(j for j, y in enumerate(d["y"]) if y > 1)
    assert d["z"][j_pos][i_neg] is None       # x < 0, y > 0: log de negativo
    assert d["z"][j_pos][i_pos] is not None    # x > 0, y > 0


def test_si_casi_nada_es_valido_se_acerca_la_vista_en_3d():
    d = bp("otro", "sqrt(1 - x**2 - y**2)")    # solo existe en el disco unidad
    assert d["x"][-1] - d["x"][0] < 4
    validos = sum(v is not None for f in d["z"] for v in f)
    assert validos / 41**2 > 0.3


def test_integral_doble_usa_su_rectangulo():
    d = bp("integral", "Integral(x*y, (x, 0, 1), (y, 0, 2))")
    assert d["kind"] == "3d"
    assert d["x"][0] < 0 and d["x"][-1] > 1 and d["x"][-1] < 1.5
    assert d["y"][0] < 0 and d["y"][-1] > 2 and d["y"][-1] < 2.5


def test_derivada_parcial_dibuja_la_funcion():
    assert bp("derivada", "Derivative(x**2*y, x)")["kind"] == "3d"


@pytest.mark.parametrize("enun,fragmento", [
    ("Eq(x**2 + y**2, 4)", "dos variables"),
    ("x*y*z", "z es el eje de altura"),
    ("x*y*t", "parámetros"),
    ("x + y + a", "parámetros"),
])
def test_3d_no_soportado_da_motivo(enun, fragmento):
    d = bp("otro", enun)
    assert d["kind"] == "none" and fragmento in d["motivo"]


def test_endpoint_devuelve_una_superficie_valida():
    from app.schemas import Plot3D
    r = client.post("/api/plot", json={"tipo": "otro", "enunciado_sympy": "x**2 - y**2", "n": 11})
    assert r.status_code == 200
    p = Plot3D(**r.json())
    assert len(p.z) == 11 and p.z_range == (-9.0, 9.0)
