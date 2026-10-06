import test from "node:test";
import assert from "node:assert/strict";
import { cortePorX, cortePorY, curvasDeNivel, nivelesBonitos, type Malla } from "../lib/plot/cuts.ts";

// z = x² − y² en [-2, 2]² con 5 puntos por eje (paso 1).
const eje = [-2, -1, 0, 1, 2];
const silla: Malla = {
  x: eje,
  y: eje,
  z: eje.map((y) => eje.map((x) => x * x - y * y)),
  z_range: [-4, 4],
};

test("corte x = c en un nodo devuelve z(c, y) exacta", () => {
  const [tramo] = cortePorX(silla, 1);
  assert.deepEqual(tramo, eje.map((y) => [y, 1 - y * y]));
});

test("corte y = c entre nodos interpola linealmente", () => {
  const [tramo] = cortePorY(silla, 0.5); // entre y=0 (z=x²) y y=1 (z=x²−1)
  assert.deepEqual(tramo.map(([, z]) => z), eje.map((x) => x * x - 0.5));
});

test("c fuera del rango se acota al borde", () => {
  assert.deepEqual(cortePorX(silla, 99), cortePorX(silla, 2));
  assert.deepEqual(cortePorY(silla, -99), cortePorY(silla, -2));
});

test("un hueco parte la curva en tramos", () => {
  const z = silla.z.map((f) => f.slice());
  z[2][2] = null; // y = 0, x = 0
  const tramos = cortePorX({ ...silla, z }, 0);
  assert.equal(tramos.length, 2);
  assert.deepEqual(tramos.map((t) => t.length), [2, 2]);
});

test("los tramos de un solo punto se descartan", () => {
  const z = silla.z.map((f) => f.slice());
  z[1][2] = null;
  z[3][2] = null; // deja el punto y=0 aislado
  assert.deepEqual(cortePorX({ ...silla, z }, 0).map((t) => t.length), []);
});

test("curva de nivel z = 0 de la silla: dos rectas y = ±x; todos los puntos cumplen x² = y²", () => {
  const segs = curvasDeNivel(silla, 0.0001);
  assert.ok(segs.length > 0);
  for (const [[x1, y1], [x2, y2]] of segs) {
    // Con z lineal por celda no es exacta; el error debe ser pequeño.
    assert.ok(Math.abs(x1 * x1 - y1 * y1) < 0.6 && Math.abs(x2 * x2 - y2 * y2) < 0.6);
  }
});

test("nivel fuera del rango no da segmentos", () => {
  assert.equal(curvasDeNivel(silla, 100).length, 0);
  assert.equal(curvasDeNivel(silla, -100).length, 0);
});

test("plano z = x: la curva de nivel c es la recta vertical x = c (exacta)", () => {
  const plano: Malla = { x: eje, y: eje, z: eje.map(() => eje.slice()), z_range: [-2, 2] };
  const segs = curvasDeNivel(plano, 0.5);
  assert.equal(segs.length, 4);
  for (const [[x1], [x2]] of segs) {
    assert.ok(Math.abs(x1 - 0.5) < 1e-12 && Math.abs(x2 - 0.5) < 1e-12);
  }
});

test("una celda con hueco se salta", () => {
  const plano: Malla = { x: eje, y: eje, z: eje.map(() => eje.slice()), z_range: [-2, 2] };
  plano.z[0][0] = null;
  assert.equal(curvasDeNivel(plano, 0.5).length, 4); // x = 0.5 cruza las columnas 2-3; el hueco está en la 0
  plano.z[0][2] = null;
  assert.equal(curvasDeNivel(plano, 0.5).length, 3);
});

test("silla de una celda: el centro decide la conexión", () => {
  const m: Malla = { x: [0, 1], y: [0, 1], z: [[1, 0], [0, 1]], z_range: [0, 1] }; // a y c altos
  assert.equal(curvasDeNivel(m, 0.5).length, 2);
});

test("nivelesBonitos queda estrictamente dentro y es creciente", () => {
  const n = nivelesBonitos(-4, 4, 8);
  assert.deepEqual(n, [-3, -2, -1, 0, 1, 2, 3]);
  assert.deepEqual(nivelesBonitos(1, 1), []);
  assert.ok(nivelesBonitos(0, 10).every((v) => v > 0 && v < 10));
});
