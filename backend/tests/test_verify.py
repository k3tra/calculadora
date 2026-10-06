import time

import pytest

from app.schemas import SolutionDraft
from app.verify import check, run_with_timeout, safe_parse, Unverifiable, verify


def estado(tipo, enunciado, resultado):
    return check(tipo, enunciado, resultado)[0]


def test_derivada_correcta_con_prefijo():
    assert estado("derivada", r"f(x) = x^{2} \cdot \sin(x)", "2*x*sin(x) + x**2*cos(x)") == "verificado"


def test_derivada_forma_equivalente():
    assert estado("derivada", r"x^{2} \cdot \sin(x)", "x*(2*sin(x) + x*cos(x))") == "verificado"


def test_derivada_incorrecta_da_motivo():
    est, detalle = check("derivada", r"f(x) = x^{2}", "x")
    assert est == "no_verificado" and "2*x" in detalle


def test_integral_indefinida():
    assert estado("integral", r"\int x e^{x}\,dx", "(x - 1)*exp(x)") == "verificado"
    assert estado("integral", r"\int x e^{x}\,dx", "x*exp(x)") == "no_verificado"


def test_integral_definida():
    assert estado("integral", r"\int_{0}^{1} x^{2}\,dx", "1/3") == "verificado"
    assert estado("integral", r"\int_{0}^{1} x^{2}\,dx", "1/2") == "no_verificado"


def test_ecuacion_completa_e_incompleta():
    assert estado("ecuacion", "x^2 - 5x + 6 = 0", "[2, 3]") == "verificado"
    assert estado("ecuacion", "x^2 - 5x + 6 = 0", "[2]") == "no_verificado"
    assert estado("ecuacion", "x^2 - 5x + 6 = 0", "[2, 4]") == "no_verificado"


def test_limite():
    assert estado("limite", r"\lim_{x \to 0} \frac{\sin x}{x}", "1") == "verificado"
    assert estado("limite", r"\lim_{x \to 0} \frac{\sin x}{x}", "0") == "no_verificado"


def test_tipo_otro_no_verificable():
    assert estado("otro", "lo que sea", "1") == "no_verificable"


@pytest.mark.parametrize("malo", [
    "__import__('os').system('echo hola')",
    "open('x')",
    "x.__class__",
    "(1).real",
    "lambda: 1",
    "a" * 600,
    "",
])
def test_resultado_malicioso_se_rechaza(malo):
    with pytest.raises(Unverifiable):
        safe_parse(malo)
    assert estado("derivada", "x^2", malo) == "no_verificable"


def test_verify_en_proceso_aparte():
    draft = SolutionDraft(pasos=[], resultado_latex="2x", resultado_sympy="2*x", enunciado_sympy="x**2")
    assert verify("derivada", "f(x) = x^2", draft).estado == "verificado"


def test_timeout_mata_el_proceso():
    t = time.time()
    with pytest.raises(TimeoutError):
        run_with_timeout(time.sleep, (30,), 1)
    assert time.time() - t < 10


# --- Regresiones del diagnóstico de integrales reales (enunciados que SymPy leía mal o no leía) ---

from app.verify import _normalize_latex, parse_enunciado  # noqa: E402

CASO1 = r"\int_{1}^{\infty} \frac{1}{x^3 + 1} \ dx"          # integral impropia con "\ " antes de dx
CASO2 = r"\int \frac{x + 3}{x^2(x - 1)} \, dx"                # potencia seguida de paréntesis
E1 = "Integral(1/(x**3 + 1), (x, 1, oo))"
E2 = "Integral((x + 3)/(x**2*(x - 1)), x)"
VALOR1 = "pi/(3*sqrt(3)) - log(2)/3"                          # ≈ 0.37355
PRIMITIVA2 = "3/x - 4*log(Abs(x)) + 4*log(Abs(x - 1))"        # fracciones parciales


def test_normalizador_arregla_barra_espacio_y_potencia_seguida_de_factor():
    assert r"\ " not in _normalize_latex(r"x \ dx")
    assert r"\cdot" in _normalize_latex(r"x^2(x-1)")
    assert r"\cdot" in _normalize_latex(r"x^{2}\sin(x)")
    assert r"\cdot" in _normalize_latex(r"e^{x}(x+1)")
    assert r"\cdot" in _normalize_latex(r"\sin(x)(x+1)")


def test_normalizador_no_toca_los_limites_de_integral_ni_suma():
    for s in (r"\int_{1}^{\infty} \frac{1}{x} dx", r"\int_0^1 \sin(x) dx",
              r"\sum_{n=1}^{\infty} \frac{1}{n}", r"\int_{a}^{b} (x+1) dx"):
        assert "cdot" not in _normalize_latex(s), s


def test_los_dos_enunciados_reales_se_interpretan_solo_con_latex():
    assert parse_enunciado(CASO1, True).limits[0][1:] == (1, sp_oo())
    assert parse_enunciado(CASO2, True).function is not None


def sp_oo():
    import sympy
    return sympy.oo


def test_integral_impropia_se_verifica_numericamente():
    assert estado("integral", CASO1, VALOR1) == "verificado"
    assert check("integral", CASO1, VALOR1, E1)[0] == "verificado"


def test_integral_impropia_con_valor_incorrecto_da_ambos_valores():
    est, detalle = check("integral", CASO1, "pi/(3*sqrt(3)) + log(2)/3", E1)
    assert est == "no_verificado" and "0.3735" in detalle and "0.8356" in detalle


def test_integral_divergente_no_se_verifica():
    assert estado("integral", CASO1, "oo") == "no_verificable"


def test_fracciones_parciales_con_log_abs_se_verifica():
    # Antes daba "no verificado": con variables complejas d/dx log(Abs(x)) quedaba como Derivative(re(x), x).
    assert estado("integral", CASO2, PRIMITIVA2) == "verificado"
    assert check("integral", CASO2, PRIMITIVA2, E2)[0] == "verificado"
    assert estado("integral", CASO2, "3/x - 4*log(abs(x)) + 4*log(abs(x - 1))") == "verificado"


def test_fracciones_parciales_con_signo_mal_se_rechaza():
    assert check("integral", CASO2, "-3/x - 4*log(Abs(x)) + 4*log(Abs(x - 1))", E2)[0] == "no_verificado"


def test_integral_de_1_sobre_x_con_log_abs():
    assert estado("integral", r"\int \frac{1}{x} \, dx", "log(Abs(x))") == "verificado"


def test_formas_que_antes_se_leian_mal_o_fallaban():
    assert estado("integral", r"\int e^{x}(x+1) \, dx", "x*exp(x)") == "verificado"
    assert estado("derivada", r"f(x) = x^{2}\sin(x)", "2*x*sin(x) + x**2*cos(x)") == "verificado"
    assert estado("derivada", r"f(x) = (x-1)^2(x+1)", "2*(x-1)*(x+1) + (x-1)**2") == "verificado"


def test_enunciado_sympy_que_contradice_al_latex_no_se_verifica():
    est, detalle = check("integral", CASO2, PRIMITIVA2, "Integral((x + 3)/(x**2*(x + 1)), x)")
    assert est == "no_verificable" and "no coincide" in detalle


def test_si_el_latex_no_se_puede_leer_se_usa_la_transcripcion_del_modelo_y_se_avisa():
    est, detalle = check("integral", r"\int \mathbf{x^2}(x-1)^2 \, dx", "x**5/5 - x**4/2 + x**3/3",
                         "Integral(x**2*(x - 1)**2, x)")
    assert est == "verificado" and "transcrito por el modelo" in detalle


def test_enunciado_sympy_malicioso_se_ignora_y_se_usa_el_latex():
    for malo in ("__import__('os').system('echo hola')", "x.__class__", "open('x')"):
        assert check("derivada", "x^{2}", "2*x", malo) == ("verificado", "La derivada coincide con la calculada por SymPy")


def test_enunciado_sympy_malicioso_con_latex_ilegible_no_verifica():
    est, detalle = check("derivada", r"\comandoinventado{x^2}", "2*x", "__import__('os')")
    assert est == "no_verificable" and "enunciado_sympy" in detalle


def test_otros_tipos_con_enunciado_sympy():
    assert check("ecuacion", "x^2 - 5x + 6 = 0", "[2, 3]", "Eq(x**2 - 5*x + 6, 0)")[0] == "verificado"
    assert check("limite", r"\lim_{x \to 0} \frac{\sin x}{x}", "1", "Limit(sin(x)/x, x, 0)")[0] == "verificado"
    assert check("derivada", r"f(x) = \frac{x^{2}+1}{\sin x}",
                 "(2*x*sin(x) - (x**2+1)*cos(x))/sin(x)**2", "(x**2+1)/sin(x)")[0] == "verificado"


# --- Endurecimiento: falsos "verificado" detectados en la revisión crítica ---

def test_derivada_de_valor_absoluto_no_acepta_1():
    # 1 solo es la derivada de |x| para x>0: se prueban también puntos negativos.
    assert estado("derivada", r"f(x) = |x|", "1") == "no_verificado"
    assert check("derivada", r"f(x) = \left|x\right|", "1", "Abs(x)")[0] == "no_verificado"
    assert estado("derivada", r"f(x) = \sqrt{x^2}", "1") == "no_verificado"
    assert estado("derivada", r"f(x) = |x|", "sign(x)") == "verificado"


def test_dominio_real_no_da_falsas_alarmas_con_logaritmos():
    assert estado("derivada", r"f(x) = \ln(x^{2})", "2/x") == "verificado"
    assert estado("integral", r"\int \frac{1}{x} \, dx", "log(Abs(x))") == "verificado"


@pytest.mark.parametrize("latex,resultado,modelo", [
    (r"\lim_{x \to 0} \frac{|x|}{x}", "1", "Limit(Abs(x)/x, x, 0)"),
    (r"\lim_{x \to 0} \frac{|x|}{x}", "1", ""),
    (r"\lim_{x \to 0} \frac{1}{x}", "oo", "Limit(1/x, x, 0)"),
    (r"\lim_{x \to 0} \frac{1}{x}", "oo", ""),
])
def test_limite_bilateral_que_no_existe_no_se_da_por_verificado(latex, resultado, modelo):
    assert check("limite", latex, resultado, modelo)[0] == "no_verificado"


def test_limite_bilateral_inexistente_se_acepta_si_el_resultado_lo_dice():
    assert check("limite", r"\lim_{x \to 0} \frac{|x|}{x}", "nan", "Limit(Abs(x)/x, x, 0)")[0] == "verificado"


def test_limites_laterales_y_su_direccion():
    assert check("limite", r"\lim_{x \to 0^+} \frac{1}{x}", "oo", "LimitPlus(1/x, x, 0)")[0] == "verificado"
    assert check("limite", r"\lim_{x \to 0^-} \frac{1}{x}", "-oo", "LimitMinus(1/x, x, 0)")[0] == "verificado"
    # El modelo transcribe como bilateral un enunciado lateral: las dos lecturas no coinciden.
    assert check("limite", r"\lim_{x \to 0^+} \frac{1}{x}", "oo", "Limit(1/x, x, 0)")[0] == "no_verificable"


def test_limite_normal_sigue_verificandose():
    assert check("limite", r"\lim_{x \to 0} \frac{\sin x}{x}", "1", "Limit(sin(x)/x, x, 0)")[0] == "verificado"
    assert check("limite", r"\lim_{x \to 2} \frac{1}{x^{2}}", "1/4", "Limit(1/x**2, x, 2)")[0] == "verificado"
