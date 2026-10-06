import base64

from .config import settings
from .llm import parse_json
from .mock import MOCK_SCAN
from .schemas import ScanResult

SYSTEM = (
    "Eres un transcriptor de ejercicios de matemáticas. Lee la imagen (impresa o a mano) y "
    "devuelve el enunciado. El campo latex debe usar solo comandos compatibles con KaTeX, "
    "sin delimitadores $ ni \\[ \\]. En enunciado_texto, cualquier expresión matemática va entre $...$ "
    "en LaTeX (por ejemplo $x^2$ o $\\sin(x)$), nunca como x^2 en texto plano. "
    "Si algo es ilegible, haz tu mejor lectura y baja la confianza."
)


async def image_to_latex(png: bytes) -> ScanResult:
    if settings.mock_llm:
        return MOCK_SCAN
    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png",
                       "data": base64.standard_b64encode(png).decode()},
        },
        {"type": "text", "text": "Transcribe el ejercicio de esta imagen."},
    ]
    return await parse_json(model=settings.ocr_model, system=SYSTEM, content=content,
                            output_format=ScanResult)
