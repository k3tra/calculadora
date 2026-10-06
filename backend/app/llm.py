import anthropic
from fastapi import HTTPException

from .config import settings

FALLBACK_BETA = "server-side-fallback-2026-07-01"

_client: anthropic.AsyncAnthropic | None = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key or None)
    return _client


async def parse_json(*, model, system, content, output_format, effort=None):
    """Call Claude and return the validated Pydantic instance, mapping API errors to HTTP errors."""
    extra = {"output_config": {"effort": effort}} if effort else {}
    try:
        resp = await get_client().beta.messages.parse(
            model=model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=output_format,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            **extra,
        )
    except anthropic.RateLimitError:
        raise HTTPException(429, "Límite de peticiones de la API alcanzado, inténtalo en unos segundos")
    except anthropic.APIConnectionError:
        raise HTTPException(503, "No se pudo conectar con la API de Anthropic")
    except anthropic.APIStatusError as e:
        raise HTTPException(502, f"Error de la API de Anthropic ({e.status_code})")
    if resp.stop_reason == "refusal":
        raise HTTPException(422, "El modelo ha rechazado procesar este contenido")
    if resp.parsed_output is None:
        raise HTTPException(502, "Respuesta del modelo no válida")
    return resp.parsed_output
