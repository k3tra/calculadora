"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import CropEditor from "@/components/CropEditor";
import LatexEditor from "@/components/LatexEditor";
import LatexView from "@/components/LatexView";
import RichText from "@/components/RichText";
import { scan, type ScanResult, type Tipo } from "@/lib/api";
import { newId } from "@/lib/history";
import { thumbnail } from "@/lib/thumbnail";

const LOW_CONFIDENCE = 0.7;
const TIPOS: { id: Tipo; texto: string }[] = [
  { id: "derivada", texto: "Derivada" },
  { id: "integral", texto: "Integral" },
  { id: "ecuacion", texto: "Ecuación" },
  { id: "limite", texto: "Límite" },
  { id: "otro", texto: "Otro" },
];
const PICK_BTN =
  "flex-1 cursor-pointer rounded-lg border border-black/20 px-4 py-4 text-center font-medium " +
  "focus-within:ring-2 focus-within:ring-blue-500 dark:border-white/30 sm:flex-none";

export default function ScanPage() {
  const router = useRouter();
  // raw: lo que eligió el usuario; file: la imagen final (recortada) que se envía.
  const [raw, setRaw] = useState<File | null>(null);
  const [pickId, setPickId] = useState(0); // key del CropEditor: una por foto elegida
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [manual, setManual] = useState(false); // ejercicio escrito a mano: sin imagen ni lectura de pago
  const [latex, setLatex] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  function resetResult() {
    setResult(null);
    setLatex("");
    setError(null);
  }

  function onPick(input: HTMLInputElement) {
    const f = input.files?.[0] ?? null;
    input.value = ""; // permite volver a elegir la misma foto
    setRaw(f);
    setPickId((n) => n + 1);
    setFile(null);
    setManual(false);
    resetResult();
  }

  function onWrite() {
    setRaw(null);
    setFile(null);
    setError(null);
    setLatex("");
    setManual(true);
    setResult({ enunciado_texto: "", latex: "", tipo: "otro", confianza: 1 });
  }

  function onCropped(f: File) {
    setFile(f);
    resetResult();
  }

  function onRecrop() {
    setPickId((n) => n + 1);
    setFile(null);
    resetResult();
  }

  async function onScan() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const r = await scan(file);
      setResult(r);
      setLatex(r.latex);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  async function onSolve() {
    const imagen = file ? await thumbnail(file, 640) : null;
    try {
      sessionStorage.setItem(
        "ejercicio",
        JSON.stringify({
          id: newId(),
          latex,
          enunciado_texto: result?.enunciado_texto ?? "",
          tipo: result?.tipo ?? "otro",
          imagen,
        }),
      );
    } catch {}
    router.push("/solve");
  }

  return (
    <main className="mx-auto w-full max-w-2xl p-6 flex flex-col gap-5">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Escanear ejercicio</h1>
        <Link href="/historial" className="text-sm text-blue-600">
          Historial
        </Link>
      </div>

      <div className="flex flex-wrap gap-3">
        <label className={PICK_BTN}>
          📷 Hacer foto
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => onPick(e.target)}
            className="sr-only"
          />
        </label>
        <label className={PICK_BTN}>
          🖼️ Elegir imagen
          <input type="file" accept="image/*" onChange={(e) => onPick(e.target)} className="sr-only" />
        </label>
        <button type="button" onClick={onWrite} className={PICK_BTN}>
          ✍️ Escribir ejercicio
        </button>
      </div>

      {raw && !file && <CropEditor key={pickId} file={raw} onDone={onCropped} onUseOriginal={onCropped} />}

      {file && preview && (
        <div className="flex flex-col gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="Ejercicio" className="max-h-72 self-start rounded-lg border border-black/10 object-contain" />
          <button type="button" onClick={onRecrop} className="self-start text-sm text-blue-600">
            Volver a recortar
          </button>
        </div>
      )}

      {file && (
        <button
          onClick={onScan}
          disabled={loading}
          className="self-start rounded-lg bg-blue-600 px-4 py-3 text-white disabled:opacity-50"
        >
          {loading ? "Leyendo…" : "Leer ejercicio"}
        </button>
      )}

      {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {result && (
        <section className="flex flex-col gap-3">
          {manual && (
            <div className="flex flex-col gap-2">
              <label className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-medium">Tipo de ejercicio</span>
                <select
                  value={result.tipo}
                  onChange={(e) => setResult({ ...result, tipo: e.target.value as Tipo })}
                  className="rounded-lg border border-black/20 bg-transparent px-2 py-1.5 dark:border-white/30"
                >
                  {TIPOS.map((t) => (
                    <option key={t.id} value={t.id} className="text-black">
                      {t.texto}
                    </option>
                  ))}
                </select>
              </label>
              <p className="text-sm opacity-70">
                Elige el tipo para que se verifique y se grafique. Escribe la fórmula en el editor o pulsa «Editar LaTeX en bruto».
              </p>
            </div>
          )}
          {!manual && result.confianza < LOW_CONFIDENCE && (
            <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
              Confianza baja ({Math.round(result.confianza * 100)} %). Revisa el LaTeX antes de resolver.
            </p>
          )}
          {!manual && (
            <p className="text-sm opacity-70">
              <RichText text={result.enunciado_texto} />
            </p>
          )}
          <LatexEditor value={latex} onChange={setLatex} />
          <div className="overflow-x-auto rounded-lg border border-black/10 p-4">
            <LatexView latex={latex} block />
          </div>
          <button
            onClick={onSolve}
            disabled={!latex.trim()}
            className="self-start rounded-lg bg-green-600 px-4 py-3 text-white disabled:opacity-50"
          >
            Resolver
          </button>
        </section>
      )}
    </main>
  );
}
