"use client";

import { useEffect, useMemo, useState } from "react";
import ReactCrop, { type Crop, type PercentCrop } from "react-image-crop";
import "react-image-crop/dist/ReactCrop.css";
import { canvasToFile, cropCanvas, loadWorkCanvas, percentToRect, rotate90 } from "@/lib/crop";

type Props = {
  file: File;
  /** Imagen final lista para enviar (JPEG recortado o completa). */
  onDone: (file: File) => void;
  /** Se usa la imagen original tal cual (si el navegador no puede decodificarla). */
  onUseOriginal: (file: File) => void;
};

const BTN = "rounded-lg border border-black/20 px-4 py-3 text-sm dark:border-white/30";

export default function CropEditor({ file, onDone, onUseOriginal }: Props) {
  const [canvas, setCanvas] = useState<HTMLCanvasElement | null>(null);
  const [failed, setFailed] = useState(false);
  const [crop, setCrop] = useState<Crop>();
  const [done, setDone] = useState<PercentCrop>();
  const [busy, setBusy] = useState(false);

  // El padre pone una key distinta por cada foto elegida, así que el estado empieza limpio.
  useEffect(() => {
    let cancelled = false;
    loadWorkCanvas(file)
      .then((c) => !cancelled && setCanvas(c))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [file]);

  const src = useMemo(() => canvas?.toDataURL("image/jpeg", 0.85), [canvas]);

  function rotate() {
    if (!canvas) return;
    setCanvas(rotate90(canvas));
    setCrop(undefined);
    setDone(undefined);
  }

  async function finish(useCrop: boolean) {
    if (!canvas) return;
    setBusy(true);
    try {
      const target =
        useCrop && done && done.width > 0 && done.height > 0
          ? cropCanvas(canvas, percentToRect(done, canvas))
          : canvas;
      onDone(await canvasToFile(target));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  if (failed) {
    return (
      <div className="flex flex-col gap-3 rounded-lg bg-amber-50 p-4 text-sm text-amber-900">
        <p>No se pudo preparar la imagen para recortarla (formato no compatible con este navegador).</p>
        <button type="button" onClick={() => onUseOriginal(file)} className={BTN}>
          Enviar sin recortar
        </button>
      </div>
    );
  }

  if (!src) return <p className="text-sm opacity-70">Preparando imagen…</p>;

  const hasCrop = !!done && done.width > 0 && done.height > 0;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm opacity-70">Arrastra para marcar solo el ejercicio, o usa la imagen completa.</p>
      <div className="flex justify-center rounded-lg border border-black/10 p-2 dark:border-white/15">
        <ReactCrop
          crop={crop}
          onChange={(_, percent) => {
            // La selección en vivo es la fuente de verdad: no dependemos de onComplete (se dispara
            // solo al soltar el puntero y, si no llega, el botón quedaría bloqueado).
            setCrop(percent);
            setDone(percent);
          }}
          minWidth={20}
          minHeight={20}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={src} alt="Imagen del ejercicio" className="max-h-[60vh] w-auto max-w-full" />
        </ReactCrop>
      </div>
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={() => finish(true)} disabled={!hasCrop || busy} className={`${BTN} bg-blue-600 text-white disabled:opacity-50`}>
          Usar recorte
        </button>
        <button type="button" onClick={() => finish(false)} disabled={busy} className={BTN}>
          Usar imagen completa
        </button>
        <button type="button" onClick={rotate} disabled={busy} className={BTN}>
          Girar 90°
        </button>
      </div>
    </div>
  );
}
