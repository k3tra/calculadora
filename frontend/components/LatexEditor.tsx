"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

const MathEditor = dynamic(() => import("./MathEditor"), {
  ssr: false,
  loading: () => <p className="text-sm opacity-70">Cargando editor…</p>,
});

type Props = { value: string; onChange: (latex: string) => void };

export default function LatexEditor({ value, onChange }: Props) {
  const [raw, setRaw] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">LaTeX (puedes corregirlo)</span>
        <button type="button" onClick={() => setRaw((r) => !r)} className="text-xs text-blue-600">
          {raw ? "Editor visual" : "Editar LaTeX en bruto"}
        </button>
      </div>
      {raw ? (
        <textarea
          aria-label="LaTeX"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
          className="rounded-lg border border-black/20 bg-transparent p-2 font-mono text-sm dark:border-white/30"
        />
      ) : (
        <MathEditor value={value} onChange={onChange} />
      )}
    </div>
  );
}
