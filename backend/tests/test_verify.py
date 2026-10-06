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
    draft = SolutionDraft(pasos=[], resultado_latex="2x", resultado_sympy="2*x")
    assert verify("derivada", "f(x) = x^2", draft).estado == "verificado"


def test_timeout_mata_el_proceso():
    t = time.time()
    with pytest.raises(TimeoutError):
        run_with_timeout(time.sleep, (30,), 1)
    assert time.time() - t < 10
