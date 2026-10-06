"""Exportación de la resolución a .tex y PDF (Tectonic).

El LaTeX viene de un modelo y del usuario y se compila en el servidor, así que se trata como
entrada no fiable: las fórmulas pasan por una lista blanca de comandos y entornos (sin \\input,
\\write, \\def...), el texto normal se escapa y Tectonic corre con --untrusted.
"""

import logging
import re
import subprocess
import tempfile
import threading
from pathlib import Path

from .config import BACKEND_DIR, settings
from .schemas import ExportRequest

log = logging.getLogger(__name__)

TEMPLATE = BACKEND_DIR / "templates" / "solucion.tex"
MAX_LEN = 5000
MAX_PASOS = 40


class InvalidLatex(ValueError):
    """Contenido que no se puede exportar (422)."""


class CompileError(RuntimeError):
    """Tectonic falló o excedió el tiempo (502)."""


class TectonicMissing(RuntimeError):
    """No se encuentra el ejecutable de Tectonic (503)."""


def _words(s: str) -> frozenset[str]:
    return frozenset(s.split())


ALLOWED_CMDS = _words("""
frac dfrac tfrac cfrac sqrt binom dbinom tbinom
sin cos tan cot sec csc arcsin arccos arctan sinh cosh tanh coth log ln exp lg lim limsup liminf sup inf max min
det dim gcd deg arg ker Pr
int iint iiint oint sum prod coprod bigcup bigcap partial nabla infty
cdot cdots ldots dots vdots ddots times div pm mp ast star circ bullet oplus otimes
leq geq le ge ll gg neq ne approx equiv sim simeq cong propto
to rightarrow leftarrow leftrightarrow Rightarrow Leftarrow Leftrightarrow mapsto longrightarrow longleftarrow
implies impliedby iff uparrow downarrow
quad qquad enspace thinspace medspace thickspace
left right big Big bigg Bigg bigl bigr Bigl Bigr biggl biggr Biggl Biggr middle
langle rangle lvert rvert lVert rVert lfloor rfloor lceil rceil vert Vert
text textbf textit mathrm mathbf mathit mathsf mathtt mathbb mathcal mathfrak mathscr operatorname
overline underline overbrace underbrace hat bar vec dot ddot tilde widehat widetilde check breve acute grave
boxed displaystyle textstyle scriptstyle limits nolimits mathop substack stackrel overset underset
xrightarrow xleftarrow phantom not bmod pmod mod
forall exists nexists in notin ni subset subseteq supset supseteq cup cap emptyset varnothing setminus
neg land lor wedge vee lnot therefore because
prime degree angle perp parallel triangle
ell hbar Re Im aleph
alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa lambda mu nu xi pi varpi
rho varrho sigma varsigma tau upsilon phi varphi chi psi omega
Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega
begin end
""")
ALLOWED_ENVS = _words("matrix pmatrix bmatrix Bmatrix vmatrix Vmatrix cases aligned array gathered split")
# Símbolos de control permitidos tras la barra (\, \; \{ \} \\ ...). Excluye \[ \] \( \) \^ etc.
ALLOWED_SYMS = frozenset(",;:!{}%&_#$| \\")

_ENV_NAME = re.compile(r"\{([A-Za-z]+\*?)\}")
_LETTERS = re.compile(r"[A-Za-z]+")


def sanitize_math(latex: str) -> str:
    """Devuelve la fórmula lista para ir dentro de \\[ ... \\], o lanza InvalidLatex."""
    s = re.sub(r"\s*\n\s*", " ", latex.strip())
    if not s:
        raise InvalidLatex("fórmula vacía")
    if len(s) > MAX_LEN:
        raise InvalidLatex("fórmula demasiado larga")
    # TeX convierte ^^5c en "\" (y ^^M, ^^@... en caracteres de control) ANTES de interpretar comandos:
    # permitiría escribir \input saltándose la lista blanca. "^^" no es LaTeX matemático legítimo.
    if "^^" in s:
        raise InvalidLatex("secuencia no permitida: ^^")
    depth = 0
    envs: list[str] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 >= n:
                raise InvalidLatex("barra invertida al final de la fórmula")
            m = _LETTERS.match(s, i + 1)
            if m:
                name = m.group()
                if name not in ALLOWED_CMDS:
                    raise InvalidLatex(f"comando LaTeX no permitido: \\{name}")
                i = m.end()
                if name in ("begin", "end"):
                    e = _ENV_NAME.match(s, i)
                    if not e or e.group(1).rstrip("*") not in ALLOWED_ENVS:
                        raise InvalidLatex(f"entorno LaTeX no permitido tras \\{name}")
                    env = e.group(1)
                    if name == "begin":
                        envs.append(env)
                    elif not envs or envs.pop() != env:
                        raise InvalidLatex("entornos begin/end mal anidados")
                    i = e.end()
                continue
            if s[i + 1] not in ALLOWED_SYMS:
                raise InvalidLatex(f"secuencia no permitida: \\{s[i + 1]}")
            i += 2
            continue
        if c in "%$#":
            raise InvalidLatex(f"carácter no permitido sin escapar: {c}")
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                raise InvalidLatex("llaves desbalanceadas")
        elif ord(c) < 32 and c != "\t":
            raise InvalidLatex("carácter de control no permitido")
        i += 1
    if depth != 0 or envs:
        raise InvalidLatex("llaves o entornos sin cerrar")
    return s


_TEXT_ESCAPES = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
    "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    "<": r"\textless{}", ">": r"\textgreater{}", "|": r"\textbar{}",
}


def _escape(text: str) -> str:
    return "".join(_TEXT_ESCAPES.get(c, c) for c in text if c == "\t" or ord(c) >= 32)


def _normalize(text: str) -> str:
    if len(text) > MAX_LEN:
        raise InvalidLatex("texto demasiado largo")
    return re.sub(r"\s+", " ", text.strip())


def escape_text(text: str) -> str:
    """Texto normal (explicaciones, enunciado) a LaTeX seguro."""
    return _escape(_normalize(text))


_INLINE_MATH = re.compile(r"\$([^$]+)\$")


def render_rich_text(text: str) -> str:
    """Texto con matemáticas en línea entre $...$.

    El texto se escapa y cada fórmula pasa por sanitize_math. Si los $ no cuadran o una fórmula
    no es válida, ese fragmento se deja como texto literal en vez de fallar la exportación.
    """
    text = _normalize(text)
    if text.count("$") % 2:
        return _escape(text)
    out, last = [], 0
    for m in _INLINE_MATH.finditer(text):
        out.append(_escape(text[last:m.start()]))
        try:
            out.append(f"${sanitize_math(m.group(1))}$")
        except InvalidLatex:
            out.append(_escape(m.group(0)))
        last = m.end()
    out.append(_escape(text[last:]))
    return "".join(out)


def _verificacion_text(req: ExportRequest) -> str:
    v = req.verificacion
    if v.estado == "verificado":
        return r"\textbf{Verificación:} resultado verificado con SymPy."
    if v.estado == "no_verificado":
        extra = f" ({escape_text(v.detalle)})" if v.detalle else ""
        return r"\textbf{Atención:} el resultado no pudo verificarse con SymPy" + extra + "."
    return r"\textbf{Verificación:} este resultado no se ha podido verificar automáticamente."


def render_tex(req: ExportRequest) -> str:
    if len(req.pasos) > MAX_PASOS:
        raise InvalidLatex(f"demasiados pasos (máximo {MAX_PASOS})")
    pasos = []
    for n, p in enumerate(req.pasos, 1):
        try:
            formula = sanitize_math(p.latex)
        except InvalidLatex as e:
            raise InvalidLatex(f"paso {n}: {e}")
        pasos.append(f"\\item {render_rich_text(p.explicacion)}\n\\[ {formula} \\]")
    try:
        enunciado = sanitize_math(req.latex)
        resultado = sanitize_math(req.resultado_latex)
    except InvalidLatex as e:
        raise InvalidLatex(f"enunciado o resultado: {e}")
    values = {
        "ENUNCIADO_TEXTO": render_rich_text(req.enunciado_texto),
        "ENUNCIADO_LATEX": enunciado,
        "PASOS": "\n".join(pasos),
        "RESULTADO": resultado,
        "VERIFICACION": _verificacion_text(req),
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    # Una sola pasada: el contenido insertado no se vuelve a interpretar como marcador.
    return re.sub(r"<<([A-Z_]+)>>", lambda m: values[m.group(1)], template)


_slots = threading.BoundedSemaphore(settings.pdf_max_concurrent)


def compile_pdf(tex: str) -> bytes:
    with _slots, tempfile.TemporaryDirectory() as d:
        (Path(d) / "solucion.tex").write_text(tex, encoding="utf-8")
        cmd = [settings.tectonic_bin, "--untrusted", "--chatter", "minimal", "solucion.tex"]
        try:
            proc = subprocess.run(cmd, cwd=d, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=settings.pdf_timeout_s)
        except FileNotFoundError:
            raise TectonicMissing("Tectonic no está instalado en el servidor")
        except subprocess.TimeoutExpired:
            raise CompileError("La compilación del PDF tardó demasiado")
        pdf = Path(d) / "solucion.pdf"
        if proc.returncode != 0 or not pdf.exists():
            log.error("tectonic falló (%s): %s", proc.returncode, (proc.stderr or "")[-1500:])
            raise CompileError("No se pudo compilar el PDF")
        return pdf.read_bytes()
