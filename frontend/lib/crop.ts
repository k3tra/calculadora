export type Rect = { x: number; y: number; width: number; height: number };

function newCanvas(width: number, height: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.round(width));
  c.height = Math.max(1, Math.round(height));
  return c;
}

/**
 * Carga la imagen ya enderezada según su EXIF y reducida a maxSide px (limita memoria y el tope de
 * canvas de iOS). Los recortes y giros trabajan sobre este canvas.
 */
export async function loadWorkCanvas(file: File, maxSide = 2000): Promise<HTMLCanvasElement> {
  const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
  const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const canvas = newCanvas(bmp.width * scale, bmp.height * scale);
  canvas.getContext("2d")?.drawImage(bmp, 0, 0, canvas.width, canvas.height);
  bmp.close();
  return canvas;
}

/** Gira 90° en sentido horario. */
export function rotate90(src: HTMLCanvasElement): HTMLCanvasElement {
  const out = newCanvas(src.height, src.width);
  const ctx = out.getContext("2d");
  if (ctx) {
    ctx.translate(out.width, 0);
    ctx.rotate(Math.PI / 2);
    ctx.drawImage(src, 0, 0);
  }
  return out;
}

/** Recorta un rectángulo en píxeles del canvas, limitado a sus bordes. */
export function cropCanvas(src: HTMLCanvasElement, r: Rect): HTMLCanvasElement {
  const x = Math.min(Math.max(0, Math.round(r.x)), src.width - 1);
  const y = Math.min(Math.max(0, Math.round(r.y)), src.height - 1);
  const w = Math.min(Math.max(1, Math.round(r.width)), src.width - x);
  const h = Math.min(Math.max(1, Math.round(r.height)), src.height - y);
  const out = newCanvas(w, h);
  out.getContext("2d")?.drawImage(src, x, y, w, h, 0, 0, w, h);
  return out;
}

/** Convierte un recorte en porcentaje (0-100, relativo a la imagen) a píxeles del canvas. */
export function percentToRect(p: Rect, canvas: { width: number; height: number }): Rect {
  return {
    x: (p.x / 100) * canvas.width,
    y: (p.y / 100) * canvas.height,
    width: (p.width / 100) * canvas.width,
    height: (p.height / 100) * canvas.height,
  };
}

/** JPEG: resuelve a la vez HEIC, EXIF y el límite de tamaño de subida. */
export function canvasToFile(canvas: HTMLCanvasElement, name = "ejercicio.jpg", quality = 0.9): Promise<File> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(new File([blob], name, { type: "image/jpeg" })) : reject(new Error("No se pudo codificar la imagen"))),
      "image/jpeg",
      quality,
    );
  });
}
