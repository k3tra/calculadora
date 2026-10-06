"use client";

import { useMemo, useState } from "react";
import type { Plot2D as Plot2DData, Plot3D } from "@/lib/api";
import { cortePorX, cortePorY } from "@/lib/plot/cuts";
import { formatTick } from "@/lib/plot/scale";
import ContourPlot from "./ContourPlot";
import Plot2D from "./Plot2D";
import Surface3D from "./Surface3D";

type Pestana = "superficie" | "niveles" | "x" | "y";

const PESTANAS: { id: Pestana; texto: string }[] = [
  { id: "superficie", texto: "Superficie" },
  { id: "niveles", texto: "Curvas de nivel" },
  { id: "x", texto: "Corte x = c" },
  { id: "y", texto: "Corte y = c" },
];

const PASOS = 200;

/** Superficie 3D con vistas derivadas de la misma malla: curvas de nivel y cortes x = c / y = c. */
export default function SurfacePanel({ plot }: { plot: Plot3D }) {
  const [tab, setTab] = useState<Pestana>("superficie");
  // Posición del deslizador en [0, 1]; una por eje para no perderla al cambiar de pestaña.
  const [pos, setPos] = useState({ x: 0.5, y: 0.5 });

  const [zmin, zmax] = plot.z_range;
  const rango = {
    x: [plot.x[0], plot.x[plot.x.length - 1]] as [number, number],
    y: [plot.y[0], plot.y[plot.y.length - 1]] as [number, number],
  };
  const eje = tab === "x" || tab === "y" ? tab : null;
  const c = eje ? rango[eje][0] + (rango[eje][1] - rango[eje][0]) * pos[eje] : 0;

  // El rango vertical es el de toda la superficie: así la curva se mueve sin que cambie la escala.
  const corte = useMemo<Plot2DData | null>(() => {
    if (!eje) return null;
    const pad = (zmax - zmin) * 0.05 || 1;
    const otro = eje === "x" ? "y" : "x";
    return {
      kind: "2d",
      variable: otro,
      x_range: rango[otro],
      y_range: [zmin - pad, zmax + pad],
      series: [
        {
          label: `z(${eje} = ${formatTick(c)}, ${otro})`,
          rol: "f",
          segmentos: eje === "x" ? cortePorX(plot, c) : cortePorY(plot, c),
        },
      ],
      puntos: [],
      area: null,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eje, c, plot, zmin, zmax]);

  return (
    <div className="flex flex-col gap-3">
      <div role="tablist" aria-label="Vista de la superficie" className="flex flex-wrap gap-2">
        {PESTANAS.map((p) => (
          <button
            key={p.id}
            type="button"
            role="tab"
            aria-selected={tab === p.id}
            onClick={() => setTab(p.id)}
            className={`rounded-lg border px-3 py-1.5 text-sm ${
              tab === p.id
                ? "border-blue-600 bg-blue-600 text-white dark:border-blue-400 dark:bg-blue-500"
                : "border-black/20 dark:border-white/30"
            }`}
          >
            {p.texto}
          </button>
        ))}
      </div>

      {tab === "superficie" && <Surface3D plot={plot} />}
      {tab === "niveles" && <ContourPlot plot={plot} />}
      {eje && corte && (
        <>
          <label className="flex flex-wrap items-center gap-3 text-sm">
            <span className="font-medium">
              {eje} = {formatTick(c)}
            </span>
            <input
              type="range"
              min={0}
              max={PASOS}
              value={Math.round(pos[eje] * PASOS)}
              onChange={(e) => setPos((p) => ({ ...p, [eje]: Number(e.target.value) / PASOS }))}
              aria-label={`Valor de ${eje} del corte`}
              className="min-w-40 flex-1"
            />
            <span className="opacity-70">
              de {formatTick(rango[eje][0])} a {formatTick(rango[eje][1])}
            </span>
          </label>
          {corte.series[0].segmentos.length === 0 ? (
            <p className="text-sm opacity-70">La función no está definida en este corte.</p>
          ) : (
            <Plot2D plot={corte} />
          )}
        </>
      )}
    </div>
  );
}
