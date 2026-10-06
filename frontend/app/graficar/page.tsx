"use client";

import Link from "next/link";
import { useState } from "react";
import { PlotView } from "@/components/plot/AutoPlot";
import LatexEditor from "@/components/LatexEditor";
import { plot, type Plot } from "@/lib/api";

const EJEMPLOS = [
  { texto: "sen(x)/x", latex: String.raw`\frac{\sin(x)}{x}` },
  { texto: "x³ − 3x", latex: "x^3-3x" },
  { texto: "z = x² − y²", latex: "z=x^2-y^2" },
  { texto: "sen(x)·cos(y)", latex: String.raw`\sin(x)\cos(y)` },
];

export default function GraficarPage() {
  const [latex, setLatex] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Plot | null>(null);

  async function onPlot() {
    setLoading(true);
    setError(null);
    try {
      setResult(await plot({ tipo: "otro", enunciado_latex: latex }));
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-5 p-6">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Graficar una función</h1>
        <Link href="/scan" className="text-sm text-blue-600">
          Escanear
        </Link>
      </div>
      <p className="text-sm opacity-70">
        Escribe f(x) para una curva, o una expresión en x e y (también «z = …») para una superficie 3D con cortes. Es
        gratis: no usa inteligencia artificial.
      </p>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="opacity-70">Ejemplos:</span>
        {EJEMPLOS.map((e) => (
          <button
            key={e.latex}
            type="button"
            onClick={() => setLatex(e.latex)}
            className="rounded-lg border border-black/20 px-2 py-1 dark:border-white/30"
          >
            {e.texto}
          </button>
        ))}
      </div>
      <LatexEditor value={latex} onChange={setLatex} />
      <button
        onClick={onPlot}
        disabled={!latex.trim() || loading}
        className="self-start rounded-lg bg-blue-600 px-4 py-3 text-white disabled:opacity-50"
      >
        {loading ? "Calculando…" : "Graficar"}
      </button>
      {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {result?.kind === "none" && <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">{result.motivo}</p>}
      {result && <PlotView plot={result} />}
    </main>
  );
}
