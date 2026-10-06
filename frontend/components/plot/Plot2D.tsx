"use client";

import { useId } from "react";
import type { Plot2D as Plot2DData, Serie } from "@/lib/api";
import { formatTick, linear, niceTicks } from "@/lib/plot/scale";

const W = 600;
const H = 340;
const M = { l: 48, r: 14, t: 12, b: 28 };

// Colores con contraste suficiente en claro y oscuro (currentColor hereda de estas clases).
const COLOR: Record<Serie["rol"], string> = {
  f: "text-blue-600 dark:text-blue-400",
  derivada: "text-red-600 dark:text-red-400",
  primitiva: "text-green-700 dark:text-green-400",
  izquierda: "text-blue-600 dark:text-blue-400",
  derecha: "text-orange-600 dark:text-orange-400",
};

export default function Plot2D({ plot }: { plot: Plot2DData }) {
  const clipId = useId();
  const [x0, x1] = plot.x_range;
  const [y0, y1] = plot.y_range;
  const sx = linear(x0, x1, M.l, W - M.r);
  const sy = linear(y0, y1, H - M.b, M.t);
  const xTicks = niceTicks(x0, x1, 8);
  const yTicks = niceTicks(y0, y1, 6);
  const etiqueta = `Gráfica de ${plot.series.map((s) => s.label).join(" y ")}, ${plot.variable} de ${formatTick(x0)} a ${formatTick(x1)}`;

  // Área bajo la curva entre a y b, un polígono por tramo continuo.
  const areaPolys: string[] = [];
  if (plot.area) {
    const { a, b, serie } = plot.area;
    const base = sy(Math.min(Math.max(0, y0), y1));
    for (const seg of plot.series[serie]?.segmentos ?? []) {
      const pts = seg.filter(([x]) => x >= a && x <= b);
      if (pts.length < 2) continue;
      const top = pts.map(([x, y]) => `${sx(x)},${sy(y)}`).join(" ");
      areaPolys.push(`${sx(pts[0][0])},${base} ${top} ${sx(pts[pts.length - 1][0])},${base}`);
    }
  }

  return (
    <figure className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={etiqueta} className="h-auto w-full">
        <defs>
          <clipPath id={clipId}>
            <rect x={M.l} y={M.t} width={W - M.l - M.r} height={H - M.t - M.b} />
          </clipPath>
        </defs>

        {/* Cuadrícula y marcas */}
        <g className="text-black/15 dark:text-white/20" stroke="currentColor" strokeWidth={1}>
          {xTicks.map((t) => (
            <line key={`gx${t}`} x1={sx(t)} x2={sx(t)} y1={M.t} y2={H - M.b} />
          ))}
          {yTicks.map((t) => (
            <line key={`gy${t}`} x1={M.l} x2={W - M.r} y1={sy(t)} y2={sy(t)} />
          ))}
        </g>
        <g fontSize={11} fill="currentColor" className="opacity-70">
          {xTicks.map((t) => (
            <text key={`tx${t}`} x={sx(t)} y={H - M.b + 15} textAnchor="middle">
              {formatTick(t)}
            </text>
          ))}
          {yTicks.map((t) => (
            <text key={`ty${t}`} x={M.l - 6} y={sy(t) + 4} textAnchor="end">
              {formatTick(t)}
            </text>
          ))}
        </g>

        {/* Ejes en x = 0 e y = 0 si caen dentro */}
        <g stroke="currentColor" strokeWidth={1.5} className="opacity-60">
          {y0 < 0 && y1 > 0 && <line x1={M.l} x2={W - M.r} y1={sy(0)} y2={sy(0)} />}
          {x0 < 0 && x1 > 0 && <line x1={sx(0)} x2={sx(0)} y1={M.t} y2={H - M.b} />}
        </g>
        <rect x={M.l} y={M.t} width={W - M.l - M.r} height={H - M.t - M.b} fill="none" stroke="currentColor" className="opacity-40" />

        <g clipPath={`url(#${clipId})`}>
          {areaPolys.map((p, i) => (
            <polygon key={`a${i}`} points={p} fill="currentColor" fillOpacity={0.25} className={COLOR[plot.series[plot.area!.serie].rol]} />
          ))}
          {plot.series.map((s, si) => (
            <g key={si} className={COLOR[s.rol]}>
              {s.segmentos.map((seg, i) => (
                <polyline
                  key={i}
                  points={seg.map(([x, y]) => `${sx(x)},${sy(y)}`).join(" ")}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinejoin="round"
                />
              ))}
            </g>
          ))}
        </g>

        {plot.puntos.map((p, i) => (
          <circle
            key={i}
            cx={sx(p.x)}
            cy={sy(p.y)}
            r={4.5}
            stroke="currentColor"
            strokeWidth={2}
            fill={p.hueco ? "var(--background)" : "currentColor"}
            className="text-black dark:text-white"
          >
            <title>{p.label}</title>
          </circle>
        ))}
      </svg>

      <figcaption className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {plot.series.map((s, i) => (
          <span key={i} className={`flex items-center gap-1.5 ${COLOR[s.rol]}`}>
            <span className="inline-block h-0.5 w-5 bg-current" />
            <span className="text-foreground">{s.label}</span>
          </span>
        ))}
        {plot.puntos.length > 0 && (
          <span className="opacity-70">
            {plot.puntos.map((p) => p.label).join(", ")}
          </span>
        )}
      </figcaption>
    </figure>
  );
}
