/** Miniatura JPEG como data URL (cabe en sessionStorage, a diferencia de un blob: URL o la imagen original). */
export async function thumbnail(file: File, maxWidth = 800): Promise<string | null> {
  try {
    const bmp = await createImageBitmap(file);
    const scale = Math.min(1, maxWidth / bmp.width);
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bmp.width * scale);
    canvas.height = Math.round(bmp.height * scale);
    canvas.getContext("2d")?.drawImage(bmp, 0, 0, canvas.width, canvas.height);
    bmp.close();
    return canvas.toDataURL("image/jpeg", 0.7);
  } catch {
    return null;
  }
}
