import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import llm
from app.config import settings
from app.main import app
from app.schemas import ScanResult, Solution

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_on(monkeypatch):
    monkeypatch.setattr(settings, "mock_llm", True)

    def boom(*a, **k):  # con MOCK_LLM nunca debe llegar a crearse un cliente de la API
        raise AssertionError("se intentó llamar a la API de Anthropic")

    monkeypatch.setattr(llm, "get_client", boom)


def png():
    buf = io.BytesIO()
    Image.new("RGB", (200, 80), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_scan_mock_devuelve_un_resultado_valido():
    r = client.post("/api/scan", files={"file": ("a.png", png(), "image/png")})
    assert r.status_code == 200
    scan = ScanResult(**r.json())
    assert scan.tipo == "derivada" and "$" in scan.enunciado_texto


def test_solve_mock_devuelve_una_solucion_valida():
    r = client.post("/api/solve", json={"latex": "x^2", "tipo": "derivada"})
    assert r.status_code == 200
    sol = Solution(**r.json())
    assert len(sol.pasos) == 3 and sol.verificacion.estado == "no_verificable"


def test_scan_mock_sigue_validando_la_imagen():
    r = client.post("/api/scan", files={"file": ("a.txt", b"hola", "text/plain")})
    assert r.status_code == 415


def test_mock_se_exporta_a_tex():
    sol = client.post("/api/solve", json={"latex": "x^2", "tipo": "derivada"}).json()
    r = client.post("/api/export/tex", json={
        "latex": "x^2", "enunciado_texto": "", "pasos": sol["pasos"],
        "resultado_latex": sol["resultado_latex"], "verificacion": sol["verificacion"],
    })
    assert r.status_code == 200 and "$u = x^2$" in r.text


@pytest.mark.parametrize("latex,esperado", [
    ("x^2 - y^2", "x**2 - y**2"),
    (r"\sin(x) \cdot y", "x**2 - y**2"),
    ("x^2", "x**2*sin(x)"),
    (r"\sqrt{x} + \frac{1}{x}", "x**2*sin(x)"),     # los comandos con "y" dentro no cuentan
    (r"\int x \, dx", "x**2*sin(x)"),
])
def test_solve_mock_elige_2d_o_3d_segun_la_y_suelta(latex, esperado):
    r = client.post("/api/solve", json={"latex": latex, "tipo": "otro"})
    assert r.status_code == 200 and r.json()["enunciado_sympy"] == esperado
