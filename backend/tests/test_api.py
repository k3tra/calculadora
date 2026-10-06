import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.preprocess import preprocess

client = TestClient(app)


def make_png(w=3000, h=1000):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_preprocess_resizes_and_grays():
    img = Image.open(io.BytesIO(preprocess(make_png())))
    assert img.width == 1500 and img.mode == "L"


def test_scan_rejects_bad_type():
    r = client.post("/api/scan", files={"file": ("a.txt", b"hola", "text/plain")})
    assert r.status_code == 415


def test_scan_rejects_too_large(monkeypatch):
    monkeypatch.setattr("app.main.settings.max_image_bytes", 10)
    r = client.post("/api/scan", files={"file": ("a.png", make_png(50, 50), "image/png")})
    assert r.status_code == 413


def test_scan_rejects_corrupt_image():
    r = client.post("/api/scan", files={"file": ("a.png", b"no-es-png", "image/png")})
    assert r.status_code == 400
