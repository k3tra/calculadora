from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
_LOCAL_TECTONIC = BACKEND_DIR / "bin" / "tectonic" / "tectonic.exe"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    ocr_model: str = "claude-sonnet-5-5"
    solve_model: str = "claude-opus-5-5"
    cors_origins: str = "http://localhost:3000"
    max_image_bytes: int = 10 * 1024 * 1024
    max_image_width: int = 1500
    # Protege frente a "bombas de descompresión": un PNG pequeño puede declarar miles de millones de píxeles.
    max_image_pixels: int = 40_000_000
    # Límite de gasto (globales, no por IP): scan usa Sonnet, solve usa Opus y puede reintentar.
    scan_per_minute: int = 20
    solve_per_minute: int = 10
    max_concurrent_scan: int = 4
    max_concurrent_solve: int = 3
    # Ruta a Tectonic; por defecto el de backend/bin si existe, y si no el del PATH.
    tectonic_bin: str = str(_LOCAL_TECTONIC) if _LOCAL_TECTONIC.exists() else "tectonic"
    pdf_timeout_s: int = 180
    pdf_max_concurrent: int = 2
    # Respuestas fijas en /api/scan y /api/solve: pruebas sin API key ni coste.
    mock_llm: bool = False


settings = Settings()
