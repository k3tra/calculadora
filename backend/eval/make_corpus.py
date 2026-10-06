"""Genera las imágenes del corpus sintético en eval/corpus/ (gratis, sin API).

Uso (desde backend/):  .venv/Scripts/python -X utf8 eval/make_corpus.py
Requiere Tectonic (backend/bin/tectonic) y PyMuPDF (requirements-eval.txt).
Cada ejercicio se compila a PDF, se rasteriza y, según la variante, se degrada como una foto de móvil:
  limpio  → PNG sin tocar
  foto    → giro leve, luz desigual, desenfoque suave, ruido, JPEG
  dura    → lo anterior más fuerte y con menos resolución
"""

import io
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import pymupdf
from PIL import Image, ImageChops, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
from corpus import CASOS  # noqa: E402

AQUI = Path(__file__).parent
OUT = AQUI / "corpus"
TECTONIC = os.environ.get("TECTONIC_BIN", str(AQUI.parent / "bin" / "tectonic" / "tectonic.exe"))

TEX = r"""\documentclass[12pt]{article}
\usepackage{amsmath,amssymb}
\usepackage[paperwidth=16cm,paperheight=8cm,margin=0.6cm]{geometry}
\pagestyle{empty}\setlength{\parindent}{0pt}
\begin{document}
%(texto)s:
\[ %(latex)s \]
\end{document}
"""


def render_pdf(texto: str, latex: str, work: Path) -> bytes:
    tex = work / "e.tex"
    tex.write_text(TEX % {"texto": texto, "latex": latex}, encoding="utf-8")
    r = subprocess.run([TECTONIC, str(tex), "--outdir", str(work)], capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise RuntimeError(f"Tectonic falló con {latex!r}: {r.stderr[-400:]}")
    return (work / "e.pdf").read_bytes()


def rasterize(pdf: bytes, dpi: int) -> Image.Image:
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    pix = doc[0].get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    bbox = ImageOps.invert(img.convert("L")).getbbox()  # recorta el blanco sobrante
    if bbox:
        img = img.crop(bbox)
    return ImageOps.expand(img, border=int(dpi * 0.25), fill="white")


def degradar(img: Image.Image, rng: random.Random, dura: bool) -> Image.Image:
    w, h = img.size
    if dura:  # menos resolución: la letra queda pequeña, como una foto lejana
        img = img.resize((int(w * 0.7), int(h * 0.7)), Image.BILINEAR)
        w, h = img.size
    # Papel y luz desigual: degradado lineal que oscurece un lado.
    grad = Image.linear_gradient("L").rotate(rng.choice([0, 90, 180, 270])).resize((w, h))
    fuerza = 0.4 if dura else 0.22
    sombra = ImageOps.colorize(grad, black=(int(255 * (1 - fuerza)),) * 3, white=(255, 255, 255))
    img = ImageChops.multiply(img, sombra)
    img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.9, 1.3) if dura else rng.uniform(0.4, 0.7)))
    ruido = Image.effect_noise((w, h), 18 if dura else 10).convert("RGB")  # media 128: se resta para quedar en 0
    img = ImageChops.add(img, ruido, scale=1.0, offset=-128)
    ang = rng.uniform(2, 4) * rng.choice([-1, 1]) if dura else rng.uniform(0.8, 2.5) * rng.choice([-1, 1])
    return img.rotate(ang, resample=Image.BICUBIC, expand=True, fillcolor=(235, 235, 232))


def main() -> None:
    OUT.mkdir(exist_ok=True)
    manifest = []
    with tempfile.TemporaryDirectory() as tmp:
        for n, (categoria, tipo, texto, latex) in enumerate(CASOS, 1):
            variante = ("limpio", "foto", "dura")[n % 3]
            rng = random.Random(n)
            pdf = render_pdf(texto, latex, Path(tmp))
            img = rasterize(pdf, 130 if variante == "limpio" else 150)
            buf = io.BytesIO()
            if variante == "limpio":
                nombre = f"{n:02d}_{categoria}_{variante}.png"
                img.save(OUT / nombre)
            else:
                nombre = f"{n:02d}_{categoria}_{variante}.jpg"
                degradar(img, rng, variante == "dura").save(OUT / nombre, quality=55 if variante == "dura" else 72)
            buf.close()
            manifest.append({"archivo": nombre, "categoria": categoria, "variante": variante, "tipo": tipo, "latex": latex})
            print(f"{nombre}")
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(manifest)} imágenes en {OUT}")


if __name__ == "__main__":
    main()
