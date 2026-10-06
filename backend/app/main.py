import asyncio

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .export import CompileError, InvalidLatex, TectonicMissing, compile_pdf, render_tex
from .limits import plot_limiter, scan_limiter, solve_limiter
from .ocr import image_to_latex
from .plot import plot
from .preprocess import ImageTooLarge, preprocess
from .schemas import ExportRequest, Plot, PlotRequest, ScanResult, Solution, SolveRequest
from .solver import solve

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}

app = FastAPI(title="Ejercicios LaTeX")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/scan", response_model=ScanResult,
          dependencies=[Depends(scan_limiter.dependency())])
async def scan(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Formato no admitido: usa PNG, JPEG o WebP")
    data = await file.read(settings.max_image_bytes + 1)
    if len(data) > settings.max_image_bytes:
        raise HTTPException(413, "La imagen supera el límite de 10 MB")
    try:
        # Trabajo de CPU: en un hilo para no bloquear el servidor con fotos grandes.
        png = await asyncio.to_thread(preprocess, data, settings.max_image_width, settings.max_image_pixels)
    except ImageTooLarge:
        raise HTTPException(413, "La imagen tiene demasiados píxeles")
    except Exception:
        raise HTTPException(400, "No se pudo leer la imagen")
    return await image_to_latex(png)


@app.post("/api/solve", response_model=Solution,
          dependencies=[Depends(solve_limiter.dependency())])
async def solve_endpoint(req: SolveRequest):
    return await solve(req)


@app.post("/api/plot", response_model=Plot,
          dependencies=[Depends(plot_limiter.dependency())])
async def plot_endpoint(req: PlotRequest):
    # No llama a la API de pago. El cálculo corre en un proceso aparte con tiempo límite.
    return await asyncio.to_thread(plot, req)


def _attachment(content: bytes | str, media_type: str, filename: str) -> Response:
    return Response(content, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def _render(req: ExportRequest) -> str:
    try:
        return render_tex(req)
    except InvalidLatex as e:
        raise HTTPException(422, f"No se puede exportar: {e}")


@app.post("/api/export/tex")
async def export_tex(req: ExportRequest):
    return _attachment(_render(req), "application/x-tex; charset=utf-8", "solucion.tex")


@app.post("/api/export/pdf")
async def export_pdf(req: ExportRequest):
    tex = _render(req)
    try:
        pdf = await asyncio.to_thread(compile_pdf, tex)
    except TectonicMissing as e:
        raise HTTPException(503, str(e))
    except CompileError as e:
        raise HTTPException(502, str(e))
    return _attachment(pdf, "application/pdf", "solucion.pdf")
