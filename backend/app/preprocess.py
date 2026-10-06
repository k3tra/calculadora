import io

from PIL import Image, ImageOps


class ImageTooLarge(ValueError):
    """La imagen declara demasiados píxeles."""


def preprocess(data: bytes, max_width: int = 1500, max_pixels: int = 40_000_000) -> bytes:
    """EXIF transpose, grayscale, autocontrast and downscale to ~max_width px; returns PNG."""
    img = Image.open(io.BytesIO(data))
    # Image.open solo lee la cabecera: se comprueba el tamaño declarado ANTES de decodificar píxeles.
    if img.width * img.height > max_pixels:
        raise ImageTooLarge(f"{img.width}x{img.height} supera {max_pixels} píxeles")
    img = ImageOps.exif_transpose(img)
    img = ImageOps.autocontrast(ImageOps.grayscale(img))
    if img.width > max_width:
        img = img.resize((max_width, round(img.height * max_width / img.width)), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
