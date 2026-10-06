"""Mide la calidad de lectura (imagen → LaTeX) sobre el corpus. LLAMA A LA API DE PAGO (modelo OCR_MODEL).

Uso (desde backend/):
  PYTHONPATH=. .venv/Scripts/python -X utf8 eval/run_eval.py [--limit N] [--dir eval/corpus] [--solo categoria]
Corpus: una carpeta con manifest.json (lo crea make_corpus.py) o, para fotos reales, imágenes `NN.jpg` con un
`NN.txt` al lado que contenga el LaTeX correcto en la primera línea y, opcionalmente, el tipo en la segunda.
Escribe eval/results/AAAA-MM-DD_HHMM.json y un resumen por categoría y variante. Se salta nada: cada imagen es 1 llamada.
"""

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from compare import comparar  # noqa: E402

from app.ocr import image_to_latex  # noqa: E402
from app.preprocess import preprocess  # noqa: E402

AQUI = Path(__file__).parent
CONCURRENCIA = 3


def cargar(carpeta: Path) -> list[dict]:
    manifest = carpeta / "manifest.json"
    if manifest.exists():
        casos = json.loads(manifest.read_text(encoding="utf-8"))
    else:
        casos = []
        for img in sorted(p for p in carpeta.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}):
            txt = img.with_suffix(".txt")
            if not txt.exists():
                print(f"(sin .txt, se omite) {img.name}")
                continue
            lineas = txt.read_text(encoding="utf-8").splitlines()
            casos.append({"archivo": img.name, "categoria": "real", "variante": "real",
                          "tipo": lineas[1].strip() if len(lineas) > 1 else "", "latex": lineas[0].strip()})
    for c in casos:
        c["ruta"] = str(carpeta / c["archivo"])
    return casos


async def medir(caso: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        t0 = time.monotonic()
        leido, tipo, conf, veredicto, error = "", "", 0.0, "error", None
        try:
            png = preprocess(Path(caso["ruta"]).read_bytes())
            r = await image_to_latex(png)
            leido, tipo, conf = r.latex, r.tipo, r.confianza
        except Exception as e:  # HTTPException del backend, red, etc.
            error = f"{type(e).__name__}: {getattr(e, 'detail', e)}"
        if error is None:
            # Lo pagado (leido) ya está a salvo: si el comparador falla, solo queda "revisar".
            try:
                veredicto = comparar(caso["latex"], leido)
            except Exception as e:
                veredicto, error = "revisar", f"comparador: {type(e).__name__}"
        return {**{k: v for k, v in caso.items() if k != "ruta"}, "leido": leido, "tipo_leido": tipo,
                "confianza": conf, "veredicto": veredicto, "error": error, "segundos": round(time.monotonic() - t0, 1)}


def resumen(res: list[dict]) -> None:
    def tabla(titulo: str, clave: str) -> None:
        grupos: dict[str, list[dict]] = defaultdict(list)
        for r in res:
            grupos[r[clave]].append(r)
        print(f"\n{titulo:<16}{'n':>3} {'ok':>4} {'exacto':>7} {'equiv':>6} {'distinto':>9} {'revisar':>8} {'error':>6}")
        for k, rs in sorted(grupos.items()):
            c = lambda v: sum(r["veredicto"] == v for r in rs)  # noqa: E731
            ok = c("exacto") + c("equivalente")
            print(f"{k:<16}{len(rs):>3} {100 * ok / len(rs):>3.0f}% {c('exacto'):>7} {c('equivalente'):>6} "
                  f"{c('distinto'):>9} {c('revisar'):>8} {c('error'):>6}")

    tabla("categoría", "categoria")
    tabla("variante", "variante")
    tipos = [r for r in res if r.get("tipo") and r["veredicto"] != "error"]
    if tipos:
        print(f"\ntipo bien clasificado: {sum(r['tipo'] == r['tipo_leido'] for r in tipos)}/{len(tipos)}")
    mal = [r for r in res if r["veredicto"] not in ("exacto", "equivalente")]
    if mal:
        print("\nPara revisar:")
        for r in mal:
            print(f"  [{r['veredicto']}] {r['archivo']} (conf {r['confianza']:.2f})\n     verdad: {r['latex']}\n     leído : {r['leido']}"
                  + (f"\n     error : {r['error']}" if r["error"] else ""))
    ok_conf = [r["confianza"] for r in res if r["veredicto"] in ("exacto", "equivalente")]
    mal_conf = [r["confianza"] for r in res if r["veredicto"] == "distinto"]
    if ok_conf and mal_conf:
        print(f"\nconfianza media: aciertos {sum(ok_conf) / len(ok_conf):.2f} · fallos {sum(mal_conf) / len(mal_conf):.2f}")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(AQUI / "corpus"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--solo", default="")
    a = ap.parse_args()
    casos = cargar(Path(a.dir))
    if a.solo:
        casos = [c for c in casos if c["categoria"] == a.solo]
    if a.limit:
        casos = casos[: a.limit]
    print(f"{len(casos)} imágenes → {len(casos)} llamadas de pago al modelo de lectura")
    sem = asyncio.Semaphore(CONCURRENCIA)
    res = await asyncio.gather(*(medir(c, sem) for c in casos))
    out = AQUI / "results"
    out.mkdir(exist_ok=True)
    f = out / f"{time.strftime('%Y-%m-%d_%H%M')}.json"
    f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    resumen(res)
    print(f"\nGuardado en {f}")


if __name__ == "__main__":
    asyncio.run(main())
