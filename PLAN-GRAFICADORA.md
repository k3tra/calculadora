# Plan: graficadora automática 2D/3D con cortes

Diseñado por un subagente Opus (2026-10-06) y revisado. Requisitos del usuario: la gráfica es **automática** (aparece sola en la solución), llega hasta **3 dimensiones** y permite **cortes en la tercera dimensión**. No llama nunca a la API de pago.
**Estado (2026-10-06, al apagar el PC):** fase 1 hecha y probada; fase 2 hecha y verificada en navegador; fase 3 con el código escrito y la silla `x²−y²` ya vista en pantalla, pero **con un problema abierto** (capturas de pantalla que agotan el tiempo, posible bucle de `ResizeObserver` en `Surface3D`) y sin pasar aún tests/lint/build completos; fases 4 y 5 sin empezar. Detalle y próximos pasos en `CLAUDE.md` (sección "Graficadora").

Ajustes sobre el plan original, ya decididos al implementar: rangos 2D por defecto [−5, 5] y, si casi nada es válido (`asin`, un disco…), se acerca la vista a la zona válida (en 2D y en 3D) en vez del "reintentar en [0, 10]"; `lambdify(..., "mpmath")` (no `["math", "mpmath"]`); el `motivo` de un `PlotNone` nunca lleva texto de excepciones.

## Decisiones
- **Qué se grafica:** el backend inspecciona `enunciado_sympy`/`resultado_sympy` (sin tocar `Tipo` ni `ScanResult`). Variables libres: `x` o `t` solo → 2D; exactamente `{x, y}` → 3D (`z` es el eje de altura, nunca entrada); cualquier otro caso (parámetros `a b c k n`, o `z`) → `none` (no aparece nada).
  - 2D por tipo: derivada → f y f′ (`sp.diff`, no la del LLM); integral indefinida → integrando y primitiva (solo si `diff(F) ≡ f`); definida → área sombreada [a, b]; ecuación → ambos lados + soluciones que cumplan |l−r|<1e-6; límite → f con punto hueco (a, L); otro → f.
  - 3D: superficie `z = f(x, y)` (de `Derivative(f,x)`, `Integral(f,(x,..),(y,..))` o una `f(x,y)` suelta).
- **Render:** 2D en SVG puro; **3D con proyección propia en Canvas 2D** (algoritmo del pintor sobre el campo de alturas, sin dependencias, ~10-15 KB), cargado con `next/dynamic` (`ssr: false`). Descartados (medidos con `npm view`): `three` (20 MB, ~170 KB gzip), `plotly.js-gl3d-dist-min` (~500 KB gzip), `@react-three/fiber` (peer `react <19.4`), `jsxgraph` (75 MB), `echarts-gl`. Plan B si la calidad no convence: three.js (solo núcleo + OrbitControls) tras el mismo `dynamic`.
- **Dónde se calcula:** muestreo en el backend (`backend/app/plot.py`) con `lambdify(..., "mpmath")` (sin numpy) dentro de `run_with_timeout` (proceso `spawn`, `safe_parse` DENTRO del hijo). **Curvas de nivel (marching squares) y cortes x=c / y=c en el FRONTEND** a partir de la malla ya descargada: latencia cero con el deslizador y ninguna carga en el servidor.
- **Límites:** `plot_limiter` (40/min, 2 simultáneas), expresión ≤ 500 caracteres y `count_ops ≤ 300`, timeout de proceso 6 s (corte interno a 3 s), respuesta ≤ 300 KB, malla n×n con 11 ≤ n ≤ 81, rangos finitos con |v| ≤ 1e6. `motivo` solo lleva textos propios, nunca excepciones ni rutas.
- La gráfica NO se guarda en el historial (se recalcula). Sin `enunciado_sympy` (entradas antiguas) no se pide.

## Fases
1. **Backend 2D:** `plot.py`, esquemas (`PlotRequest`, `Serie`, `Punto`, `Area`, `Plot2D`, `Plot3D`, `PlotNone`, unión discriminada `Plot`), `POST /api/plot`, limiter, tests y contrato.
2. **Frontend 2D automático:** `lib/api.ts`, `lib/plot/scale.ts`, `components/plot/{Plot2D,AutoPlot}.tsx`, integración en `SolutionView`/`solve`/`historial/detalle`.
3. **Superficie 3D:** `_sample_2d`, `lib/plot/project.ts`, `components/plot/Surface3D.tsx`, mock 3D (`MOCK_SOLUTION_3D`).
4. **Cortes:** `lib/plot/cuts.ts` (puro, con tests `node --test`), `components/plot/SurfacePanel.tsx` (pestañas Superficie / Curvas de nivel / Corte x=c / Corte y=c con deslizador).
5. **Página `/graficar`** (entrada libre `f(x)` o `z = f(x,y)`), enlaces, `sw.js` v3 + `PRECACHE`, retoque del prompt de `solver.py`.

## Trampas
Spawn en Windows (~1 s por petición: medirlo); `safe_parse` jamás en el proceso del servidor (`9**9**9`); `lambdify`+mpmath devuelve complejos en lugar de lanzar error (filtrar parte imaginaria); `ssr:false` solo en Client Components; los tests `.mjs` no importan alias `@/`; `touch-action: none` en el canvas 3D impide desplazar la página sobre él; escalar por `devicePixelRatio` (máx. 2); nunca cachear `/api/plot` en el service worker; sin `setState` síncrono en efectos; `ts_fields` de `test_contract.py` corta en el primer `};` → cada subtipo con nombre propio en `api.ts`.
**No hacer:** llamar a Claude desde la graficadora, guardar gráficas en el historial, añadir numpy/three/plotly sin pasar por el plan B, pedir al backend cada valor del deslizador, aceptar `z` como variable de entrada.
