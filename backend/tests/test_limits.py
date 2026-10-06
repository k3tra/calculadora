import io
import struct
import zlib

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.limits import Limiter, scan_limiter, solve_limiter
from app.main import app
from app.preprocess import ImageTooLarge, preprocess

client = TestClient(app)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def png(w=60, h=40):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def header_only_png(w, h):
    """PNG diminuto que DECLARA w x h píxeles: no se puede decodificar sin gastar memoria."""
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00"))
            + chunk(b"IEND", b""))


# --- Limiter (con reloj falso) ---

def test_cupo_por_minuto_y_se_recupera_con_el_tiempo():
    clock = Clock()
    lim = Limiter("t", per_minute=3, max_concurrent=99, clock=clock)
    for _ in range(3):
        lim.acquire()
        lim.release()
    with pytest.raises(HTTPException) as e:
        lim.acquire()
    assert e.value.status_code == 429
    assert int(e.value.headers["Retry-After"]) == 60
    clock.t += 30
    with pytest.raises(HTTPException) as e:
        lim.acquire()
    assert int(e.value.headers["Retry-After"]) == 30
    clock.t += 31  # pasados 60 s desde la primera petición
    lim.acquire()


def test_concurrencia_se_libera_con_release():
    lim = Limiter("t", per_minute=99, max_concurrent=2, clock=Clock())
    lim.acquire()
    lim.acquire()
    with pytest.raises(HTTPException) as e:
        lim.acquire()
    assert e.value.status_code == 429
    lim.release()
    lim.acquire()


def test_rechazar_no_ocupa_hueco():
    lim = Limiter("t", per_minute=1, max_concurrent=5, clock=Clock())
    lim.acquire()
    for _ in range(3):
        with pytest.raises(HTTPException):
            lim.acquire()
    assert lim._inflight == 1 and len(lim._hits) == 1


# --- Endpoints ---

def test_scan_429_al_pasar_el_cupo(monkeypatch):
    monkeypatch.setattr(settings, "mock_llm", True)
    monkeypatch.setattr(scan_limiter, "per_minute", 2)
    files = lambda: {"file": ("a.png", png(), "image/png")}  # noqa: E731
    assert client.post("/api/scan", files=files()).status_code == 200
    assert client.post("/api/scan", files=files()).status_code == 200
    r = client.post("/api/scan", files=files())
    assert r.status_code == 429
    assert "Retry-After" in r.headers and "Límite" in r.json()["detail"]


def test_solve_429_al_pasar_el_cupo(monkeypatch):
    monkeypatch.setattr(settings, "mock_llm", True)
    monkeypatch.setattr(solve_limiter, "per_minute", 1)
    body = {"latex": "x^2", "tipo": "derivada"}
    assert client.post("/api/solve", json=body).status_code == 200
    assert client.post("/api/solve", json=body).status_code == 429


def test_429_por_concurrencia_y_se_libera(monkeypatch):
    monkeypatch.setattr(settings, "mock_llm", True)
    monkeypatch.setattr(solve_limiter, "max_concurrent", 1)
    solve_limiter.acquire()  # simula una petición en curso
    body = {"latex": "x^2", "tipo": "derivada"}
    r = client.post("/api/solve", json=body)
    assert r.status_code == 429 and "en curso" in r.json()["detail"]
    solve_limiter.release()
    assert client.post("/api/solve", json=body).status_code == 200


def test_el_hueco_se_libera_aunque_la_peticion_falle():
    r = client.post("/api/scan", files={"file": ("a.txt", b"hola", "text/plain")})
    assert r.status_code == 415
    assert scan_limiter._inflight == 0


def test_los_endpoints_sin_gasto_no_tienen_limite(monkeypatch):
    monkeypatch.setattr(scan_limiter, "per_minute", 0)
    monkeypatch.setattr(solve_limiter, "per_minute", 0)
    assert client.get("/api/health").status_code == 200


# --- Tope de píxeles ---

def test_preprocess_rechaza_demasiados_pixeles_sin_decodificar():
    with pytest.raises(ImageTooLarge):
        preprocess(header_only_png(7000, 7000), max_pixels=40_000_000)


def test_scan_413_si_la_imagen_declara_demasiados_pixeles():
    r = client.post("/api/scan", files={"file": ("a.png", header_only_png(7000, 7000), "image/png")})
    assert r.status_code == 413 and "píxeles" in r.json()["detail"]


def test_scan_acepta_justo_por_debajo_del_tope(monkeypatch):
    monkeypatch.setattr(settings, "mock_llm", True)
    monkeypatch.setattr(settings, "max_image_pixels", 2400)  # 60x40 = 2400
    assert client.post("/api/scan", files={"file": ("a.png", png(60, 40), "image/png")}).status_code == 200
    assert client.post("/api/scan", files={"file": ("a.png", png(61, 40), "image/png")}).status_code == 413
