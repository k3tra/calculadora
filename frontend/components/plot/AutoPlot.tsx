"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import Plot2D from "./Plot2D";
import { plot, type Plot, type Solution, type Tipo } from "@/lib/api";

// El código de la superficie 3D solo se descarga cuando hay un ejercicio de dos variables.
const Surface3D = dynamic(() => import("./Surface3D"), {
  ssr: false,
  loading: () => <p className="text-sm opacity-70">Cargando gráfica 3D…</p>,
});

// En desarrollo React monta los efectos dos veces: se comparte la petición en curso por clave.
const inflight = new Map<string, Promise<Plot>>();

type Props = { tipo: Tipo; solution: Solution };

/**
 * Gráfica automática bajo el resultado. Se pide aparte (no retrasa los pasos) y es opcional: si no hay
 * enunciado_sympy (entradas antiguas del historial), no se puede graficar, hay un error o no hay conexión,
 * no se muestra nada. No se guarda en el historial: recalcularla es gratis.
 */
export default function AutoPlot({ tipo, solution }: Props) {
  const enunciado = solution.enunciado_sympy ?? "";
  const resultado = solution.resultado_sympy ?? "";
  const key = JSON.stringify([tipo, enunciado, resultado]);
  const [state, setState] = useState<{ key: string; plot: Plot | null }>({ key: "", plot: null });

  useEffect(() => {
    if (!enunciado.trim()) return;
    let cancelled = false;
    let request = inflight.get(key);
    if (!request) {
      request = plot({ tipo, enunciado_sympy: enunciado, resultado_sympy: resultado });
      inflight.set(key, request);
      const clear = () => inflight.delete(key);
      request.then(clear, clear);
    }
    request
      .then((p) => !cancelled && setState({ key, plot: p }))
      .catch(() => !cancelled && setState({ key, plot: null }));
    return () => {
      cancelled = true;
    };
  }, [key, tipo, enunciado, resultado]);

  const current = state.key === key ? state.plot : null;
  if (!current || current.kind === "none") return null;
  if (current.kind === "2d") {
    return (
      <section className="rounded-lg border border-black/10 p-3 dark:border-white/15">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">Gráfica</h2>
        <Plot2D plot={current} />
      </section>
    );
  }
  return (
    <section className="rounded-lg border border-black/10 p-3 dark:border-white/15">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide">Superficie 3D</h2>
      <Surface3D plot={current} />
    </section>
  );
}
