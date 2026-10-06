// Cortes y curvas de nivel de una malla z = f(x, y), calculados en el navegador (sin imports: los prueba
// `node --test` sin compilar, ver tests/). z[j][i] = f(x[i], y[j]); null = hueco (fuera del dominio).

export type Malla = { x: number[]; y: number[]; z: (number | null)[][]; z_range: [number, number] };
export type Segmento = [[number, number], [number, number]];

/** Posición de c entre las marcas de `ejes`: índice i y fracción t en [0, 1] (c se acota al rango). */
function bracket(ejes: number[], c: number): { i: number; t: number } {
  const n = ejes.length;
  if (c <= ejes[0]) return { i: 0, t: 0 };
  if (c >= ejes[n - 1]) return { i: n - 2, t: 1 };
  let i = 0;
  while (i < n - 2 && ejes[i + 1] < c) i++;
  const span = ejes[i + 1] - ejes[i];
  return { i, t: span === 0 ? 0 : (c - ejes[i]) / span };
}

/** Parte una lista de puntos (null = hueco) en tramos continuos de al menos 2 puntos. */
function tramos(puntos: ([number, number] | null)[]): [number, number][][] {
  const out: [number, number][][] = [];
  let actual: [number, number][] = [];
  for (const p of puntos) {
    if (p) actual.push(p);
    else {
      if (actual.length >= 2) out.push(actual);
      actual = [];
    }
  }
  if (actual.length >= 2) out.push(actual);
  return out;
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

/** Corte x = c: z en función de y. Interpola entre las dos columnas vecinas; un hueco en cualquiera corta la curva. */
export function cortePorX(g: Malla, c: number): [number, number][][] {
  const { i, t } = bracket(g.x, c);
  return tramos(
    g.y.map((y, j) => {
      const a = g.z[j][i], b = g.z[j][i + 1];
      if (a === null || b === null) return null;
      return [y, lerp(a, b, t)] as [number, number];
    }),
  );
}

/** Corte y = c: z en función de x. */
export function cortePorY(g: Malla, c: number): [number, number][][] {
  const { i: j, t } = bracket(g.y, c);
  return tramos(
    g.x.map((x, i) => {
      const a = g.z[j][i], b = g.z[j + 1][i];
      if (a === null || b === null) return null;
      return [x, lerp(a, b, t)] as [number, number];
    }),
  );
}

/**
 * Curvas de nivel z = L por marching squares con interpolación lineal. Devuelve segmentos sueltos en
 * coordenadas (x, y). Las celdas con algún hueco se saltan.
 */
export function curvasDeNivel(g: Malla, nivel: number): Segmento[] {
  const out: Segmento[] = [];
  for (let j = 0; j < g.y.length - 1; j++) {
    for (let i = 0; i < g.x.length - 1; i++) {
      const a = g.z[j][i], b = g.z[j][i + 1], c = g.z[j + 1][i + 1], d = g.z[j + 1][i];
      if (a === null || b === null || c === null || d === null) continue;
      const idx = (a >= nivel ? 1 : 0) | (b >= nivel ? 2 : 0) | (c >= nivel ? 4 : 0) | (d >= nivel ? 8 : 0);
      if (idx === 0 || idx === 15) continue;
      const x0 = g.x[i], x1 = g.x[i + 1], y0 = g.y[j], y1 = g.y[j + 1];
      const frac = (p: number, q: number) => (q === p ? 0.5 : (nivel - p) / (q - p));
      const E = {
        abajo: [lerp(x0, x1, frac(a, b)), y0] as [number, number],
        derecha: [x1, lerp(y0, y1, frac(b, c))] as [number, number],
        arriba: [lerp(x0, x1, frac(d, c)), y1] as [number, number],
        izquierda: [x0, lerp(y0, y1, frac(a, d))] as [number, number],
      };
      const seg = (p: keyof typeof E, q: keyof typeof E) => out.push([E[p], E[q]]);
      switch (idx) {
        case 1: case 14: seg("izquierda", "abajo"); break;
        case 2: case 13: seg("abajo", "derecha"); break;
        case 3: case 12: seg("izquierda", "derecha"); break;
        case 4: case 11: seg("derecha", "arriba"); break;
        case 6: case 9: seg("abajo", "arriba"); break;
        case 7: case 8: seg("izquierda", "arriba"); break;
        default: {
          // Silla (5 y 10): el centro decide qué esquinas quedan unidas.
          const centroAlto = (a + b + c + d) / 4 >= nivel;
          if ((idx === 5) === centroAlto) { seg("abajo", "derecha"); seg("izquierda", "arriba"); }
          else { seg("izquierda", "abajo"); seg("derecha", "arriba"); }
        }
      }
    }
  }
  return out;
}

/** Niveles "bonitos" estrictamente dentro de (min, max), unos `count` aproximadamente. */
export function nivelesBonitos(min: number, max: number, count = 9): number[] {
  const span = max - min;
  if (!(span > 0) || !Number.isFinite(span)) return [];
  const raw = span / count;
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const frac = raw / pow;
  const step = (frac < 1.5 ? 1 : frac < 3 ? 2 : frac < 7 ? 5 : 10) * pow;
  const out: number[] = [];
  for (let v = Math.ceil(min / step) * step; v < max && out.length < 40; v += step) {
    if (v > min) out.push(Math.abs(v) < step * 1e-9 ? 0 : Number(v.toPrecision(12)));
  }
  return out;
}
