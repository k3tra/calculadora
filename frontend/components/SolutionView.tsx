"use client";

import { useState } from "react";
import LatexView from "./LatexView";
import StepCard from "./StepCard";
import VerifyBadge from "./VerifyBadge";
import AutoPlot from "./plot/AutoPlot";
import { exportFile, saveBlob, type Solution, type Tipo } from "@/lib/api";

const BTN =
  "rounded-lg border border-black/20 px-4 py-2 text-sm disabled:opacity-50 dark:border-white/30";

type Props = { latex: string; enunciado_texto: string; solution: Solution; tipo?: Tipo };

/** Pasos, resultado con su verificación y los botones de copiar / descargar. */
export default function SolutionView({ latex, enunciado_texto, solution, tipo = "otro" }: Props) {
  const [copied, setCopied] = useState(false);
  const [exporting, setExporting] = useState<"tex" | "pdf" | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  async function download(kind: "tex" | "pdf") {
    setExporting(kind);
    setExportError(null);
    try {
      saveBlob(await exportFile(kind, { latex, enunciado_texto, solution }), `solucion.${kind}`);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "Error desconocido");
    } finally {
      setExporting(null);
    }
  }

  async function copy() {
    const tex = [latex, ...solution.pasos.map((p) => p.latex), solution.resultado_latex].join("\n\n");
    await navigator.clipboard.writeText(tex);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <>
      <div className="flex flex-col gap-3">
        {solution.pasos.map((p, i) => (
          <StepCard key={i} n={i + 1} paso={p} />
        ))}
      </div>
      <section className="rounded-lg bg-green-50 p-4 text-black">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">Resultado</h2>
        <div className="overflow-x-auto">
          <LatexView latex={solution.resultado_latex} block />
        </div>
        <div className="mt-3">
          <VerifyBadge verificacion={solution.verificacion} />
        </div>
      </section>
      <AutoPlot tipo={tipo} solution={solution} />
      <div className="flex flex-wrap gap-2">
        <button onClick={copy} className={BTN}>
          {copied ? "¡Copiado!" : "Copiar LaTeX"}
        </button>
        <button onClick={() => download("tex")} disabled={exporting !== null} className={BTN}>
          {exporting === "tex" ? "Generando…" : "Descargar .tex"}
        </button>
        <button onClick={() => download("pdf")} disabled={exporting !== null} className={BTN}>
          {exporting === "pdf" ? "Generando PDF…" : "Descargar PDF"}
        </button>
      </div>
      {exportError && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{exportError}</p>}
    </>
  );
}
