"use client";

import { useId, useMemo } from "react";
import type { Plot3D } from "@/lib/api";
import { curvasDeNivel, nivelesBonitos } from "@/lib/plot/cuts";
import { rampColor } from "@/lib/plot/project";
import { formatTick, linear, niceTicks } from "@/lib/plot/scale";

const W = 600;
const H = 400;
const M = { l: 48, r: 14, t: 12, b: 28 };

/** Curvas de nivel z = constante en el plano xy, con el mismo color que la superficie en esa altura. */
export default function ContourPlot({ plot }: { plot: Plot3D }) {
  const clipId = useId();
  const x0 = plot.x[0], x1 = plot.x[plot.x.length - 1];
  const y0 = plot.y[0], y1 = plot.y[plot.y.length - 1];
  const [zmin, zmax] = plot.z_range;
  const sx = linear(x0, x1, M.l, W - M.r);
  const sy = linear(y0, y1, H - M.b, M.t);
  const niveles = useMemo(() => nivelesBonitos(zmin, zmax, 9), [zmin, zmax]);
  const curvas = useMemo(
    () => niveles.map((nivel) => ({ nivel, segs: curvasDeNivel(plot, nivel) })),
    [niveles, plot],
  );
  const xTicks = niceTicks(x0, x1, 8);
  const yTicks = niceTicks(y0, y1, 6);

  return (
    <figure className="flex flex-col gap-2">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Curvas de nivel de f(x, y): ${niveles.length} niveles de z entre ${formatTick(zmin)} y ${formatTick(zmax)}`}
        className="h-auto w-full"
      >
        <defs>
          <clipPath id={clipId}>
            <rect x={M.l} y={M.t} width={W - M.l - M.r} height={H - M.t - M.b} />
          </clipPath>
        </defs>
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
          <text x={W - M.r} y={H - 4} textAnchor="end">x</text>
          <text x={4} y={M.t + 8}>y</text>
        </g>
        <rect x={M.l} y={M.t} width={W - M.l - M.r} height={H - M.t - M.b} fill="none" stroke="currentColor" className="opacity-40" />
        <g clipPath={`url(#${clipId})`} strokeWidth={2} strokeLinecap="round">
          {curvas.map(({ nivel, segs }) => {
            const [r, g, b] = rampColor((nivel - zmin) / (zmax - zmin || 1));
            return (
              <g key={nivel} stroke={`rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})`}>
                {segs.map(([[ax, ay], [bx, by]], i) => (
                  <line key={i} x1={sx(ax)} y1={sy(ay)} x2={sx(bx)} y2={sy(by)} />
                ))}
              </g>
            );
          })}
        </g>
      </svg>
      <figcaption className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        <span className="opacity-70">Cada curva une los puntos con el mismo valor de z.</span>
        {niveles.map((n) => {
          const [r, g, b] = rampColor((n - zmin) / (zmax - zmin || 1));
          return (
            <span key={n} className="flex items-center gap-1">
              <span className="inline-block h-0.5 w-4" style={{ background: `rgb(${Math.round(r)},${Math.round(g)},${Math.round(b)})` }} />
              z = {formatTick(n)}
            </span>
          );
        })}
      </figcaption>
    </figure>
  );
}
