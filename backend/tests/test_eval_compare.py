"""El comparador de la evaluación de lectura (eval/compare.py): sin API. Si falla, la medición de pago se pierde."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "eval"))
from compare import comparar, normalizar  # noqa: E402
from corpus import CASOS  # noqa: E402


def test_cada_verdad_del_corpus_se_compara_exacta_consigo_misma():
    assert [l for _, _, _, l in CASOS if normalizar(l) != normalizar(l)] == []
    assert [l for _, _, _, l in CASOS if comparar(l, l) != "exacto"] == []


@pytest.mark.parametrize("verdad,leido", [
    (r"f(x) = x^{2}\sin(x)", r"f(x)=x^2 \cdot \sin(x)"),
    (r"f(x) = \frac{x^{2}+1}{x-3}", r"f(x) = \dfrac{x^2+1}{x-3}"),
    (r"\lim_{x\to 0^{+}} x\ln(x)", r"\lim_{x\to 0^+} x\ln(x)"),
    (r"\lim_{x\to 0}\frac{\sin(x)}{x}", r"\lim_{x\rightarrow 0}\frac{\sin x}{x}"),
])
def test_misma_lectura_con_otra_forma(verdad, leido):
    assert comparar(verdad, leido) == "exacto"


def test_equivalente_y_distinto():
    assert comparar(r"x^{2}-5x+6=0", r"x^2-5x=-6") == "equivalente"
    assert comparar(r"f(x) = x^{x}", r"f(x) = x^2") == "distinto"
    assert comparar(r"x^{2}-5x+6=0", r"x^2+5x+6=0") == "distinto"
