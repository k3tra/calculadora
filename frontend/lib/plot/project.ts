// Proyección 3D propia en Canvas 2D, sin dependencias (sin WebGL: no hay pérdida de contexto ni GPUs en lista
// negra, y el modo oscuro sale del color del texto). Una z = f(x, y) es un campo de alturas: dibujando las
// celdas de atrás adelante (algoritmo del pintor) no hace falta z-buffer.
// Solo sintaxis "borrable" (tipos): lo prueban `node --test` sin compilar (ver tests/).

export type Vec3 = [number, number, number];
export type View = { az: number; el: number }; // acimut y elevación, en radianes

export const DEFAULT_VIEW: View = { az: -0.75, el: 0.6 };
export const MIN_EL = 0.05;
export const MAX_EL = Math.PI / 2 - 0.05;

export type Grid = { x: number[]; y: number[]; z: (number | null)[][]; z_range: [number, number] };

export function clampView(v: View): View {
  return { az: v.az, el: Math.min(MAX_EL, Math.max(MIN_EL, v.el)) };
}

/**
 * Malla normalizada a la caja [-1, 1] × [-1, 1] × [-zScale, zScale]. z[j][i] = f(x[i], y[j]).
 * Los huecos (null) se conservan: la celda que toque uno no se dibuja.
 */
export function normalizeGrid(g: Grid, zScale = 0.8) {
  const mid = (a: number, b: number) => (a + b) / 2;
  const half = (a: number, b: number) => (b - a) / 2 || 1;
  const xs = g.x, ys = g.y;
  const xm = mid(xs[0], xs[xs.length - 1]), xh = half(xs[0], xs[xs.length - 1]);
  const ym = mid(ys[0], ys[ys.length - 1]), yh = half(ys[0], ys[ys.length - 1]);
  const zm = mid(g.z_range[0], g.z_range[1]), zh = half(g.z_range[0], g.z_range[1]);
  return {
    X: xs.map((v) => (v - xm) / xh),
    Y: ys.map((v) => (v - ym) / yh),
    Z: g.z.map((fila) => fila.map((v) => (v === null ? null : ((v - zm) / zh) * zScale))),
    zScale,
  };
}

export type Mesh = ReturnType<typeof normalizeGrid>;

/** Coordenadas de pantalla (u derecha, v arriba) y profundidad (mayor = más lejos) de un punto o vector. */
export function toView(p: Vec3, view: View): Vec3 {
  const [x, y, z] = p;
  const ca = Math.cos(view.az), sa = Math.sin(view.az);
  const x1 = x * ca - y * sa;
  const y1 = x * sa + y * ca;
  const ce = Math.cos(view.el), se = Math.sin(view.el);
  return [x1, z * ce + y1 * se, y1 * ce - z * se];
}

export type Cell = { i: number; j: number; depth: number };

/** Celdas completas (sin huecos en sus 4 esquinas), de la más lejana a la más cercana. */
export function orderedCells(mesh: Mesh, view: View): Cell[] {
  const { X, Y, Z } = mesh;
  const cells: Cell[] = [];
  for (let j = 0; j < Y.length - 1; j++) {
    for (let i = 0; i < X.length - 1; i++) {
      const a = Z[j][i], b = Z[j][i + 1], c = Z[j + 1][i + 1], d = Z[j + 1][i];
      if (a === null || b === null || c === null || d === null) continue;
      const cx = (X[i] + X[i + 1]) / 2, cy = (Y[j] + Y[j + 1]) / 2, cz = (a + b + c + d) / 4;
      cells.push({ i, j, depth: toView([cx, cy, cz], view)[2] });
    }
  }
  return cells.sort((p, q) => q.depth - p.depth);
}

// Rampa secuencial tipo "viridis" (perceptualmente uniforme, legible en claro y en oscuro).
const RAMP: Vec3[] = [
  [68, 1, 84],
  [59, 82, 139],
  [33, 145, 140],
  [94, 201, 98],
  [253, 231, 37],
];

export function rampColor(t: number): Vec3 {
  const k = Math.min(1, Math.max(0, t)) * (RAMP.length - 1);
  const i = Math.min(RAMP.length - 2, Math.floor(k));
  const f = k - i;
  const a = RAMP[i], b = RAMP[i + 1];
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}

/** Luz fija respecto a la cámara (arriba a la izquierda y desde el observador): u, v, profundidad. */
const LIGHT: Vec3 = (() => {
  const l: Vec3 = [-0.3, 0.5, -0.8];
  const n = Math.hypot(l[0], l[1], l[2]);
  return [l[0] / n, l[1] / n, l[2] / n];
})();

/** Intensidad Lambert (0,45–1) de una celda según su normal, ya en coordenadas de pantalla. */
export function shade(normal: Vec3): number {
  let [nu, nv, nd] = normal;
  const len = Math.hypot(nu, nv, nd) || 1;
  nu /= len; nv /= len; nd /= len;
  if (nd > 0) { nu = -nu; nv = -nv; nd = -nd; } // la cara visible mira al observador
  const dot = nu * LIGHT[0] + nv * LIGHT[1] + nd * LIGHT[2];
  return 0.45 + 0.55 * Math.max(0, dot);
}

export function cellNormal(mesh: Mesh, i: number, j: number, view: View): Vec3 {
  const { X, Y, Z } = mesh;
  const p00: Vec3 = [X[i], Y[j], Z[j][i] as number];
  const p10: Vec3 = [X[i + 1], Y[j], Z[j][i + 1] as number];
  const p01: Vec3 = [X[i], Y[j + 1], Z[j + 1][i] as number];
  const e1: Vec3 = [p10[0] - p00[0], p10[1] - p00[1], p10[2] - p00[2]];
  const e2: Vec3 = [p01[0] - p00[0], p01[1] - p00[1], p01[2] - p00[2]];
  const n: Vec3 = [
    e1[1] * e2[2] - e1[2] * e2[1],
    e1[2] * e2[0] - e1[0] * e2[2],
    e1[0] * e2[1] - e1[1] * e2[0],
  ];
  return toView(n, view); // rotación lineal: vale igual para vectores
}

export type Colors = { text: string; grid: string };

function fmt(v: number): string {
  if (v === 0) return "0";
  const a = Math.abs(v);
  return a >= 1e5 || a < 1e-3 ? v.toExponential(1).replace("e+", "e") : String(Number(v.toPrecision(4)));
}

/** Dibuja la superficie, el suelo con sus ejes y los rangos. `colors.text` es el color del texto de la página. */
export function renderSurface(
  ctx: CanvasRenderingContext2D,
  g: Grid,
  mesh: Mesh,
  view: View,
  w: number,
  h: number,
  colors: Colors,
) {
  ctx.clearRect(0, 0, w, h);
  const s = Math.min(w, h) * 0.33;
  const cx = w / 2, cy = h / 2 + h * 0.04;
  const sc = (p: Vec3): [number, number] => {
    const q = toView(p, view);
    return [cx + q[0] * s, cy - q[1] * s];
  };
  const zs = mesh.zScale;

  // Suelo y poste lejano (detrás de la superficie).
  const floor: Vec3[] = [[-1, -1, -zs], [1, -1, -zs], [1, 1, -zs], [-1, 1, -zs]];
  ctx.lineWidth = 1;
  ctx.strokeStyle = colors.grid;
  ctx.beginPath();
  floor.forEach((p, k) => {
    const [px, py] = sc(p);
    if (k === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  });
  ctx.closePath();
  ctx.stroke();
  const depths = floor.map((p) => toView(p, view)[2]);
  const far = depths.indexOf(Math.max(...depths));
  const near = depths.indexOf(Math.min(...depths));
  const [fx, fy, fz] = floor[far];
  ctx.beginPath();
  ctx.moveTo(...sc([fx, fy, fz]));
  ctx.lineTo(...sc([fx, fy, zs]));
  ctx.stroke();

  // Superficie, de atrás adelante.
  const [zmin, zmax] = g.z_range;
  for (const { i, j } of orderedCells(mesh, view)) {
    const { X, Y, Z } = mesh;
    const zc = ((Z[j][i] as number) + (Z[j][i + 1] as number) + (Z[j + 1][i + 1] as number) + (Z[j + 1][i] as number)) / 4;
    const t = (zc / zs + 1) / 2; // 0..1 según la altura
    const k = shade(cellNormal(mesh, i, j, view));
    const [r, gr, b] = rampColor(t);
    const fill = `rgb(${Math.round(r * k)},${Math.round(gr * k)},${Math.round(b * k)})`;
    ctx.beginPath();
    ctx.moveTo(...sc([X[i], Y[j], Z[j][i] as number]));
    ctx.lineTo(...sc([X[i + 1], Y[j], Z[j][i + 1] as number]));
    ctx.lineTo(...sc([X[i + 1], Y[j + 1], Z[j + 1][i + 1] as number]));
    ctx.lineTo(...sc([X[i], Y[j + 1], Z[j + 1][i] as number]));
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.strokeStyle = fill; // mismo color: tapa las costuras entre celdas
    ctx.lineWidth = 0.6;
    ctx.fill();
    ctx.stroke();
  }

  // Ejes: x e y en las dos aristas del suelo que salen de la esquina más cercana; z sobre el poste lejano.
  ctx.fillStyle = colors.text;
  ctx.font = "600 13px system-ui, sans-serif";
  ctx.textAlign = "center";
  const [nx, ny, nz] = floor[near];
  const dirX: Vec3 = [-Math.sign(nx), 0, 0], dirY: Vec3 = [0, -Math.sign(ny), 0];
  const [lx, ly] = sc([nx + dirX[0] * 2, ny, nz]);
  const [mx, my] = sc([nx, ny + dirY[1] * 2, nz]);
  ctx.beginPath();
  ctx.strokeStyle = colors.text;
  ctx.lineWidth = 1.5;
  ctx.moveTo(...sc([nx, ny, nz]));
  ctx.lineTo(lx, ly);
  ctx.moveTo(...sc([nx, ny, nz]));
  ctx.lineTo(mx, my);
  ctx.stroke();
  ctx.fillText("x", lx + (lx - sc([nx, ny, nz])[0]) * 0.12, ly + 14);
  ctx.fillText("y", mx + (mx - sc([nx, ny, nz])[0]) * 0.12, my + 14);
  const [zx, zy] = sc([fx, fy, zs]);
  ctx.fillText("z", zx, zy - 8);

  // Rangos de cada eje.
  ctx.font = "12px system-ui, sans-serif";
  ctx.textAlign = "left";
  ctx.globalAlpha = 0.8;
  const xr = `x ∈ [${fmt(g.x[0])}, ${fmt(g.x[g.x.length - 1])}]`;
  const yr = `y ∈ [${fmt(g.y[0])}, ${fmt(g.y[g.y.length - 1])}]`;
  const zr = `z ∈ [${fmt(zmin)}, ${fmt(zmax)}]`;
  ctx.fillText(`${xr}   ${yr}   ${zr}`, 8, h - 8);
  ctx.globalAlpha = 1;
}
