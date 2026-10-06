"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Plot3D } from "@/lib/api";
import { clampView, DEFAULT_VIEW, normalizeGrid, renderSurface, type View } from "@/lib/plot/project";

const BTN = "rounded-lg border border-black/20 px-3 py-1.5 text-sm dark:border-white/30";

/** Superficie z = f(x, y) con rotación por arrastre (ratón o dedo) o con las flechas del teclado. */
export default function Surface3D({ plot }: { plot: Plot3D }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drag = useRef<{ x: number; y: number } | null>(null);
  const [view, setView] = useState<View>(DEFAULT_VIEW);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [scheme, setScheme] = useState(0); // cambia al alternar claro/oscuro para redibujar
  const mesh = useMemo(() => normalizeGrid(plot), [plot]);

  // Tamaño según el ancho disponible (4:3). El observador avisa también al empezar.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas?.parentElement) return;
    const ro = new ResizeObserver(([entry]) => {
      const w = Math.floor(entry.contentRect.width);
      const h = Math.floor(w * 0.75);
      setSize((p) => (p.w === w && p.h === h ? p : { w, h }));
    });
    ro.observe(canvas.parentElement);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const on = () => setScheme((n) => n + 1);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx || size.w === 0) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1); // nítido, pero sin pasarse en móviles
    canvas.width = size.w * dpr;
    canvas.height = size.h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const text = getComputedStyle(canvas).color;
    renderSurface(ctx, plot, mesh, view, size.w, size.h, { text, grid: "rgba(128,128,128,0.55)" });
  }, [plot, mesh, view, size, scheme]);

  const rotar = (daz: number, del: number) => setView((v) => clampView({ az: v.az + daz, el: v.el + del }));

  const etiqueta =
    `Superficie 3D de f(x, y): x de ${plot.x[0]} a ${plot.x[plot.x.length - 1]}, ` +
    `y de ${plot.y[0]} a ${plot.y[plot.y.length - 1]}, z de ${plot.z_range[0]} a ${plot.z_range[1]}. ` +
    "Arrastra para girarla o usa las flechas del teclado.";

  return (
    <figure className="flex flex-col gap-2">
      {/* La proporción la fija el CSS: el tamaño del lienzo ya no realimenta al observador. */}
      <div className="relative w-full" style={{ aspectRatio: "4 / 3" }}>
        <canvas
          ref={canvasRef}
          role="img"
          aria-label={etiqueta}
          tabIndex={0}
          style={{ touchAction: "none" }}
          className="absolute inset-0 h-full w-full cursor-grab rounded-lg border border-black/10 focus:outline-2 focus:outline-blue-500 active:cursor-grabbing dark:border-white/15"
          onPointerDown={(e) => {
            e.currentTarget.setPointerCapture(e.pointerId);
            drag.current = { x: e.clientX, y: e.clientY };
          }}
          onPointerMove={(e) => {
            if (!drag.current) return;
            rotar((e.clientX - drag.current.x) * 0.01, (e.clientY - drag.current.y) * 0.01);
            drag.current = { x: e.clientX, y: e.clientY };
          }}
          onPointerUp={() => (drag.current = null)}
          onPointerCancel={() => (drag.current = null)}
          onKeyDown={(e) => {
            const paso = 0.1;
            if (e.key === "ArrowLeft") rotar(-paso, 0);
            else if (e.key === "ArrowRight") rotar(paso, 0);
            else if (e.key === "ArrowUp") rotar(0, -paso);
            else if (e.key === "ArrowDown") rotar(0, paso);
            else return;
            e.preventDefault();
          }}
        />
      </div>
      <figcaption className="flex flex-wrap items-center gap-3 text-sm">
        <button type="button" onClick={() => setView(DEFAULT_VIEW)} className={BTN}>
          Restablecer vista
        </button>
        <span className="opacity-70">Arrastra para girar la superficie.</span>
      </figcaption>
    </figure>
  );
}
