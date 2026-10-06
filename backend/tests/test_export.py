import io
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app import export
from app.config import settings
from app.export import InvalidLatex, escape_text, render_rich_text, render_tex, sanitize_math
from app.main import app
from app.schemas import ExportRequest, Paso, Verificacion

client = TestClient(app)

TECTONIC = shutil.which(settings.tectonic_bin) or (
    settings.tectonic_bin if Path(settings.tectonic_bin).exists() else None
)


def req(**over):
    base = dict(
        latex=r"f(x) = x^{2} \cdot \sin(x)",
        enunciado_texto="Calcula la derivada de f(x) = x^2 * sin(x)",
        pasos=[Paso(explicacion="Regla del producto: (uv)' = u'v + uv'", latex=r"(uv)' = u'v + uv'")],
        resultado_latex=r"f'(x) = 2x\sin(x) + x^{2}\cos(x)",
        verificacion=Verificacion(estado="verificado", detalle="ok"),
    )
    base.update(over)
    return ExportRequest(**base)


@pytest.mark.parametrize("ok", [
    r"f(x) = x^{2} \cdot \sin(x)",
    r"\frac{x^2+1}{\sin x}",
    r"\int_{0}^{1} x e^{x}\,dx",
    r"\begin{cases} x & x>0 \\ -x & x\le 0 \end{cases}",
    r"\left( \frac{a}{b} \right)^{\!2}",
    r"x \in \{1, 2\} \quad 50\%",
    "a +\n b",
])
def test_sanitize_acepta_matematicas_normales(ok):
    assert sanitize_math(ok)


@pytest.mark.parametrize("malo", [
    r"\input{/etc/passwd}",
    r"\input{C:/Windows/win.ini}",
    r"\include{secret}",
    r"\openin1=secret.txt",
    r"\immediate\write18{calc}",
    r"\write18{calc}",
    r"\usepackage{shellesc}",
    r"\def\x{y}",
    r"\catcode`\%=12",
    r"\csname input\endcsname",
    r"\verbatiminput{x}",
    r"\href{http://x}{y}",
    r"x \] hola \[ y",
    r"x \) y",
    "x % comentario",
    "a $ b",
    "a # b",
    r"\begin{document}",
    r"\begin{matrix} a \end{pmatrix}",
    "}{",
    "{",
    "a \\",
    "",
    "   ",
    "a" * 6000,
])
def test_sanitize_rechaza_peligroso(malo):
    with pytest.raises(InvalidLatex):
        sanitize_math(malo)


def test_escape_text_neutraliza_caracteres_especiales():
    out = escape_text(r"\input{x} & 100% $a$ #1 _b_ ~ ^ < > |")
    assert "\\input" not in out.replace(r"\textbackslash{}input", "")
    for c in "&%$#_":
        assert f"\\{c}" in out
    assert "{x}" not in out  # llaves escapadas


def test_rich_text_renderiza_matematicas_en_linea_y_conserva_espacios():
    out = render_rich_text(r"con u = $x^{2}$ y v = $\sin(x)$, listo")
    assert out == r"con u = $x^{2}$ y v = $\sin(x)$, listo"


def test_rich_text_escapa_el_texto_de_alrededor():
    out = render_rich_text(r"100% de $a_1$ & #1")
    assert out == r"100\% de $a_1$ \& \#1"


def test_rich_text_con_dolar_suelto_queda_como_texto():
    assert render_rich_text("cuesta 5$ hoy") == r"cuesta 5\$ hoy"


def test_rich_text_con_formula_peligrosa_queda_como_texto_literal():
    out = render_rich_text(r"mira $\input{C:/x}$ aqui y $x^2$")
    assert "\\input" not in out.replace(r"\textbackslash{}input", "")
    assert out.endswith("$x^2$")


def test_render_usa_matematicas_en_linea_en_las_explicaciones():
    tex = render_tex(req(pasos=[Paso(explicacion="Sea $u = x^{2}$", latex="u")]))
    assert r"\item Sea $u = x^{2}$" in tex


def test_render_incluye_todo_y_no_reinterpreta_marcadores():
    tex = render_tex(req(enunciado_texto="<<PASOS>> <<RESULTADO>>"))
    assert r"\textless{}\textless{}PASOS\textgreater{}" in tex
    assert tex.count(r"\item") == 1
    assert r"\boxed{f'(x) = 2x\sin(x) + x^{2}\cos(x)}" in tex
    assert "resultado verificado con SymPy" in tex
    assert "<<" not in tex.replace(r"\textless", "")


def test_render_rechaza_formula_peligrosa_indicando_el_paso():
    r = req(pasos=[Paso(explicacion="ok", latex="x"), Paso(explicacion="mal", latex=r"\input{a}")])
    with pytest.raises(InvalidLatex, match="paso 2"):
        render_tex(r)


def test_render_aviso_si_no_verificado():
    tex = render_tex(req(verificacion=Verificacion(estado="no_verificado", detalle="SymPy obtiene 2*x")))
    assert "Atención" in tex and "2*x" in tex


def test_endpoint_tex():
    r = client.post("/api/export/tex", json=req().model_dump())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-tex")
    assert "solucion.tex" in r.headers["content-disposition"]
    assert r"\begin{document}" in r.text


def test_endpoint_422_si_latex_peligroso():
    r = client.post("/api/export/tex", json=req(resultado_latex=r"\write18{x}").model_dump())
    assert r.status_code == 422 and "no permitido" in r.json()["detail"]


def test_endpoint_pdf_sin_tectonic_da_503(monkeypatch):
    monkeypatch.setattr(settings, "tectonic_bin", "no-existe-tectonic-xyz")
    r = client.post("/api/export/pdf", json=req().model_dump())
    assert r.status_code == 503


def test_endpoint_pdf_error_de_compilacion_da_502(monkeypatch):
    def boom(tex):
        raise export.CompileError("No se pudo compilar el PDF")

    monkeypatch.setattr("app.main.compile_pdf", boom)
    r = client.post("/api/export/pdf", json=req().model_dump())
    assert r.status_code == 502


@pytest.mark.skipif(TECTONIC is None, reason="Tectonic no está instalado")
def test_pdf_real_contiene_el_texto_y_no_filtra_archivos():
    r = req(enunciado_texto=r"Calcula la derivada, ñandú ¿qué? \input{C:/Windows/win.ini} 100% & $x$")
    resp = client.post("/api/export/pdf", json=r.model_dump())
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(resp.content)).pages)
    assert "Resolución" in text and "Calcula la derivada" in text
    assert "input" in text  # el texto literal sale impreso, no se ejecuta
    assert "[fonts]" not in text and "for 16-bit app support" not in text  # contenido de win.ini


# --- Endurecimiento: "^^5c" es la barra invertida en TeX y saltaba la lista blanca ---
# Comprobado: con `tectonic --untrusted`, \input de una ruta absoluta SÍ lee el fichero y lo imprime en el PDF;
# el filtro es la única barrera.

@pytest.mark.parametrize("malo", [
    r"x^^5cinput{a}",
    r"\text{^^5cinput{C:/x}}",
    r"a^^M b",
    r"x^^^^5c",
])
def test_sanitize_rechaza_doble_circunflejo(malo):
    with pytest.raises(InvalidLatex, match=r"\^\^"):
        sanitize_math(malo)


def test_sanitize_sigue_aceptando_circunflejos_normales():
    assert sanitize_math(r"x^{2} + y^3 + e^{x^{2}}")


def test_texto_normal_con_doble_circunflejo_se_escapa():
    assert "^^" not in escape_text("^^5cinput{x}")


def test_formula_en_linea_con_doble_circunflejo_queda_como_texto_literal():
    out = render_rich_text(r"mira $\text{^^5cinput{C:/x}}$ fin")
    assert "^^" not in out
    assert "$" not in out.replace(r"\$", "")


def test_endpoint_422_con_doble_circunflejo_en_un_paso():
    body = req(pasos=[Paso(explicacion="ok", latex=r"\text{^^5cinput{C:/x}}")]).model_dump()
    r = client.post("/api/export/tex", json=body)
    assert r.status_code == 422 and "^^" in r.json()["detail"]


@pytest.mark.skipif(TECTONIC is None, reason="Tectonic no está instalado")
def test_pdf_real_no_filtra_ficheros_locales_por_ninguna_via(tmp_path):
    secreto = tmp_path / "secreto.txt"
    secreto.write_text("CANARIO-SECRETO-98765\n", encoding="utf-8")
    ruta = secreto.as_posix()
    leer = "^^5cinput{" + ruta + "}"
    r = req(
        enunciado_texto=leer + " y $\text{" + leer + "}$",   # texto plano y fórmula en línea
        pasos=[Paso(explicacion=leer, latex="x")],
    )
    resp = client.post("/api/export/pdf", json=r.model_dump())
    assert resp.status_code == 200
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(resp.content)).pages)
    assert "CANARIO" not in text
