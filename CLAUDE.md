# Ejercicios LaTeX

App para escanear un ejercicio de matemáticas (foto o imagen), pasarlo a LaTeX y resolverlo paso a paso. El diseño completo está en `PLAN.md`. `netsim/` es otro proyecto sin relación: no tocarlo.

## Estado
- **Fase 1 (MVP) hecha y probada con la API real:** subir imagen → LaTeX editable → pasos → KaTeX. Sin cuentas ni base de datos.
- **Fase 2 (fiabilidad) hecha:** verificación del resultado con SymPy (`backend/app/verify.py`), hasta 2 reintentos automáticos pasando el motivo del fallo al modelo, y editor visual MathLive. Probada con la API real en derivada, integral y ecuación (las 3 `verificado`).
- **Fase 3 (exportación) hecha:** `POST /api/export/tex` y `/api/export/pdf` (Tectonic), con botones "Descargar .tex" y "Descargar PDF" en `/solve`. Plantilla en `backend/templates/solucion.tex`. Probada con la resolución real de `x²·sen(x)`, también pulsando los botones en Chrome: se descargan `solucion.tex` y `solucion.pdf` (1 página, tildes correctas).
- **Flujo en el navegador probado** (Chrome, modo oscuro): subir imagen → leer → editar con MathLive → resolver → pasos, resultado "Verificado" y "Copiar LaTeX".
- **No probado con la API real:** límites ni ecuaciones no polinómicas (solo tests unitarios), ni el caso real de reintento tras una discrepancia de SymPy. El móvil tampoco.
- **Fase 4 (cámara, recorte, historial, PWA): en curso.** Plan y decisiones aprobadas en `PLAN-FASE4.md` (historial solo en el navegador, `react-image-crop`, túnel HTTPS temporal solo tras el límite de gasto).
  - **Hechos y probados en el navegador (pasos 0-3):** `MOCK_LLM`, proxy `/api/*` de Next al backend, botones "Hacer foto"/"Elegir imagen", recorte libre con giro. Medido: recorte 45 %×70 % de 1000×260 → 450×181 px.
  - **Hechos y probados en el navegador (pasos 4-7, historial):** `lib/history.ts` (IndexedDB vía `idb`, máx. 100), `components/SolutionView.tsx` y `StatementCard.tsx` extraídos de `/solve`, páginas `/historial` y `/historial/detalle?id=…` (ruta estática con query para poder precachearla; no usar una ruta dinámica `[id]`). Medido en el log del backend: 2 ejercicios → exactamente 2 POST a `/api/solve`; recargar `/solve` no repite la llamada.
  - **Sin probar:** acceso desde un móvil real (`npm run dev:lan`, IP LAN del PC `192.168.x.x` en Wi-Fi; el firewall de Windows puede pedir permiso para `node.exe`), la cámara real (`capture`) y el recorte con el dedo. **Decisión del usuario: el móvil se prueba al final**, junto con la PWA.
  - **Hecho (paso 9, endurecimiento):** `backend/app/limits.py` (`Limiter`: cupo por minuto + concurrencia, global y no por IP porque tras el proxy el backend siempre ve 127.0.0.1; 429 con `Retry-After`) en `/api/scan` (20/min, 4 simultáneas) y `/api/solve` (10/min, 3), y tope de 40 MP en `preprocess()` (413, se comprueba la cabecera antes de decodificar). Configurable por `.env`. Es en memoria: se reinicia con el servidor y no sustituye a un tope de gasto en la cuenta de Anthropic. Con esto ya se puede abrir el túnel (pidiendo confirmación).
  - **Hecho y probado (paso 8, PWA):** `app/manifest.ts`, iconos (`public/icons/`, `app/apple-icon.png`, una Σ blanca sobre azul generada con Pillow), `public/sw.js` a mano, `app/offline/page.tsx`, `components/RegisterSW.tsx`. Probado en Chrome sobre `next build && next start`: el SW se registra y controla la página, v2 sustituye a v1 y borra sus cachés, y **sin servidor** `/historial`, `/historial/detalle?id=…` y `/scan` cargan desde la caché y una ruta no visitada cae en `/offline`. La caché no contiene nada de `/api/`, `blob:`/`data:` ni RSC.
  - **Probado en un móvil real (por el usuario, 2026-10-06):** por la red local con `npm run dev:lan` (`http://192.168.x.x:3000/scan`, Wi-Fi en perfil Público con regla de firewall de `node.exe` ya existente): botones de cámara/recorte funcionan y una integral real (`1/(x²−9)`) se resolvió correctamente con la API de pago. No se anotó más detalle (orientación de la foto, recorte con el dedo, teclado de MathLive en móvil): si algo de eso falla, investigarlo.
  - **Pendiente (fase 4):** solo la instalación de la PWA en el móvil (exige HTTPS: túnel `cloudflared` sobre `next start`, ahora que el límite de gasto ya está; pedir confirmación antes de descargarlo y de exponer la app a internet).
  - **Trampa del modo simulado:** con `MOCK_LLM=1` la app devuelve SIEMPRE la derivada de x²·sen(x); si la solución no tiene nada que ver con el ejercicio, mirar primero si el backend está en modo simulado. Para arrancar en real: `uvicorn` sin `MOCK_LLM` (y `.env` con la clave).
  - **Lectura ambigua:** "1/x^2-9" se lee como `(1/x²)−9`; el usuario debe revisar la fórmula renderizada antes de resolver y corregir con el editor (`\frac{1}{x^{2}-9}`).
- **Pendiente (según `PLAN.md`):** fase 5 extras (varios ejercicios por foto, gráficas, modo pistas, cuentas).

## Estructura
- `backend/` — FastAPI (Python). Venv en `backend/.venv`.
  - `app/main.py` rutas `/api/health`, `/api/scan` (multipart `file`), `/api/solve` (JSON `{latex, enunciado_texto}`)
  - `app/llm.py` única función `parse_json` que llama a Claude y traduce errores de la API a HTTP (429/503/502, `refusal` → 422)
  - `app/ocr.py` imagen→LaTeX, `app/solver.py` pasos + bucle de reintentos, `app/preprocess.py` (Pillow), `app/schemas.py` (Pydantic), `app/config.py` (`.env`)
  - `app/verify.py` verificador SymPy por `tipo` (derivada, integral, ecuacion, limite; `otro` → no verificable)
  - `app/export.py` LaTeX seguro + compilación con Tectonic (`render_tex`, `sanitize_math`, `escape_text`, `compile_pdf`); `templates/solucion.tex`
  - `bin/tectonic/tectonic.exe` (0.17.0, descargado del release oficial de GitHub; **no está en git**, `bin/` está en `.gitignore`). Ruta configurable con `TECTONIC_BIN`
  - `tests/` (`test_api`, `test_verify`, `test_solver`, `test_export`): ninguno llama a la API real de Anthropic
- `frontend/` — Next.js 16 (App Router, TypeScript, Tailwind 4) + KaTeX.
  - `app/scan/page.tsx` subida y revisión del LaTeX; `app/solve/page.tsx` resultados; el ejercicio pasa de una a otra por `sessionStorage` (clave `ejercicio`)
  - `components/LatexView.tsx` (KaTeX), `components/StepCard.tsx`, `components/VerifyBadge.tsx`, `lib/api.ts` (cliente + tipos que reflejan `schemas.py`)
  - `components/LatexEditor.tsx` envuelve `MathEditor.tsx` (MathLive, cargado con `dynamic` y `ssr: false`) con un conmutador a textarea en bruto

## Comandos
```
# Backend (desde backend/)
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m uvicorn app.main:app --reload     # :8000, docs en /docs

# Frontend (desde frontend/)
npm run dev      # :3000
npm run build
npm run lint
```
Configuración: copiar `backend/.env.example` → `backend/.env` y poner `ANTHROPIC_API_KEY`; opcionalmente `frontend/.env.local` desde `.env.local.example`.

## Decisiones y convenciones
- **Modelos:** `claude-sonnet-5-5` lee la imagen y `claude-opus-5-5` resuelve (con `effort: "high"`; el valor por defecto de Opus 5.5 es `medium`). Se cambian por `.env` (`OCR_MODEL`, `SOLVE_MODEL`).
- **Salida estructurada:** `client.beta.messages.parse(..., output_format=<modelo Pydantic>)` y se lee `parsed_output`. Está con `betas=["server-side-fallback-2026-07-01"]` y `fallbacks="default"`.
- **Forma de las respuestas:** `ScanResult {enunciado_texto, latex, tipo, confianza}` (`tipo` es un Literal: derivada/integral/ecuacion/limite/otro) y `Solution = SolutionDraft {pasos[{explicacion, latex}], resultado_latex, resultado_sympy} + verificacion {estado, detalle}`. El modelo solo genera `SolutionDraft`; `verificacion` la añade el backend. Si se cambian, actualizar a la vez `backend/app/schemas.py` y `frontend/lib/api.ts`.
- **Formato de `resultado_sympy`** (lo fija el prompt de `solver.py`): solo la expresión, sin `f(x)=`; derivada → la derivada; integral → primitiva sin `+C` (o el valor si es definida); ecuación → lista de soluciones reales `[2, 3]`; límite → el valor.
- **Seguridad de la verificación:** `resultado_sympy` viene de un LLM. Nunca `sympify`/`eval` directo: `safe_parse` valida contra lista blanca de nombres y evalúa sin builtins, y el cálculo corre en un proceso aparte con timeout de 15 s (`run_with_timeout`, usa `spawn`).
- **Matemáticas dentro de texto:** `explicacion` y `enunciado_texto` llevan las expresiones entre `$...$` (lo pide el prompt de `ocr.py` y `solver.py`). El frontend las renderiza con `components/RichText.tsx` y el PDF con `render_rich_text` (cada fórmula pasa por `sanitize_math`; si es inválida o los `$` no cuadran, queda como texto literal). Sin esto, el modelo mezcla `x^2` en texto plano con LaTeX y los exponentes salen inconsistentes. Los prompts reducen el problema pero no lo garantizan.
- **Seguridad del PDF:** el LaTeX viene de un LLM y del usuario y se compila en el servidor. Las fórmulas pasan por una lista blanca de comandos y entornos (`ALLOWED_CMDS`/`ALLOWED_ENVS` en `export.py`; rechaza `\input`, `\write`, `\def`, `\[`, `%`, `$`...), el texto normal se escapa con `escape_text`, la plantilla se rellena en una sola pasada y Tectonic corre con `--untrusted`. Si una fórmula legítima falla con "comando no permitido", se añade a la lista blanca, no se relaja el filtro.
- **Tectonic:** la primera compilación descarga paquetes LaTeX de internet (~2 min); después quedan en caché y tarda ~1 s. Límite de 2 compilaciones simultáneas y 180 s.
- **Modelos de los subagentes (preferencia del usuario):** planificación → subagente `opus` (p. ej. el agente `Plan`); tests y tareas repetitivas → subagentes `haiku`; todo lo demás → Sonnet. No usar Opus para otra cosa que planificar salvo petición expresa. Pasar siempre `model` explícito al lanzar un subagente.
- **Cómo se obtiene el enunciado a verificar (`verify._problem`):** el modelo transcribe el enunciado a SymPy en `enunciado_sympy` (`Integral(f, (x, a, b))`, `Eq(l, r)`, `Limit(f, x, a)`, o la función para derivadas) y además se interpreta el LaTeX con `parse_latex`. Si las dos lecturas están disponibles **deben coincidir**; si no, `no_verificable` (nunca falsa seguridad ni falsa alarma). Si el LaTeX no se puede leer, se usa solo la transcripción del modelo y el `detalle` lo avisa.
- **Variables reales:** los símbolos de SymPy son `real=True` (`_SYMS` y los del LaTeX). Con variables complejas `d/dx log(Abs(x))` queda como `Derivative(re(x), x)` y toda integral con `ln|x|` salía "No verificado" aunque fuera correcta.
- **Integrales definidas** (también impropias, con `oo`) se comparan **numéricamente** (`_valor_numerico`/`_close`), no con forma cerrada simbólica (SymPy da expresiones con `gamma` imposibles de comparar).
- **Trampas de `parse_latex` (lark)** que `_normalize_latex` compensa: no admite `\ ` (barra-espacio); falla con una potencia seguida de paréntesis o función (`x^2(x-1)`, `x^2\sin(x)`, `e^{x}(x+1)`) y **lee mal en silencio** `\sin(x)(x+1)` como `sin(x·(x+1))`. Los límites `\int_{a}^{b}` no se tocan. `x(x-1)` y `f(x)` dan un árbol ambiguo (se rechaza).
- **Diagnóstico:** `solver.solve` registra en el log de uvicorn una línea `verificacion tipo=… intento=… estado=… detalle=…` (sin el enunciado). Si un usuario reporta un "No verificado/verificable", mirar ahí y reproducir con `check()` (la verificación es local, no gasta API).
- **Importante:** para reproducir con un script suelto, ejecutar con `PYTHONPATH=.` desde `backend/` y `python -X utf8` (no `-I`: ignora `PYTHONPATH` y `PYTHONIOENCODING`).
- **`parse_latex` (SymPy, backend `lark`):** `f(x) = ...` da un árbol ambiguo, por eso `verify.py` quita el prefijo; y lee `e^{x}` como variable `e`, por eso se sustituye por `E`.
- El LaTeX debe ser compatible con KaTeX y sin delimitadores `$`.
- Límites de seguridad: imágenes de hasta 10 MB y solo PNG/JPEG/WebP; CORS solo `http://localhost:3000`; la API key solo vive en `backend/.env`.
- Textos de la interfaz y mensajes de error en español.
- **Next.js 16:** su API cambia respecto a versiones anteriores. Antes de usar una API de Next, leer la guía correspondiente en `frontend/node_modules/next/dist/docs/` (lo indica `frontend/AGENTS.md`).
- **Imagen entre `/scan` y `/solve`:** se guarda en `sessionStorage` como miniatura JPEG data URL (`frontend/lib/thumbnail.ts`). No usar `blob:` URLs: se rompen al salir de la página o recargar.
- **MathLive** normaliza el LaTeX (`x^{2}` → `x^2`, quita espacios), así que el texto que llega al backend no es idéntico al que devolvió `/api/scan`. Se importa `mathlive/fonts.css` y `MathfieldElement.fontsDirectory = null` para que las fuentes no den 404.
- **Modo simulado:** `MOCK_LLM=1` (variable de entorno al arrancar uvicorn, ver `backend/app/mock.py`) hace que `/api/scan` y `/api/solve` devuelvan respuestas fijas: sirve para probar el flujo de la interfaz sin API key ni coste.
- **Proxy de API:** el frontend llama a `/api/*` en su propio origen y `next.config.ts` lo reenvía a `BACKEND_URL` (por defecto `http://127.0.0.1:8000`) con `experimental.proxyTimeout` de 300 s. `NEXT_PUBLIC_API_URL` solo se usa para apuntar a otro backend.
- **`react-image-crop`:** `onComplete` solo se dispara al soltar el puntero; el botón "Usar recorte" depende de `onChange` (la selección en vivo), no de `onComplete`.
- **Probar en el navegador con las herramientas de Chrome:** la acción `type` no llega al `<math-field>`; usar `key` (tecla a tecla) o `javascript_tool`. Un clic por `ref` justo tras `file_upload` puede no registrarse; repetirlo por coordenadas.
- **Tests y limitadores:** los `Limiter` son globales; `backend/tests/conftest.py` los resetea antes de cada test (fixture autouse). Un test nuevo que dependa de un límite debe ajustarlo con `monkeypatch.setattr(scan_limiter, "per_minute", N)`.
- **Service worker (`frontend/public/sw.js`):** reglas de privacidad que no se relajan: nunca interceptar `/api/*`, nunca guardar imágenes del usuario ni respuestas no `basic`/redirigidas/`no-store`. Al cambiar el shell (nuevas páginas estáticas o rutas) hay que subir `VERSION` y añadir la página a `PRECACHE`: solo se guardan como navegación las páginas cargadas completas (la navegación interna de Next usa payloads RSC, que no se cachean), por eso las páginas estáticas se precachean. Se registra solo en producción (`RegisterSW`); en desarrollo se des-registra. Si queda un SW viejo en el navegador: DevTools → Application → Unregister.
- **Probar el SW:** `next build && next start` (no `next dev`); borrar `.next` si `next build` falla por tipos de rutas ya eliminadas. Para simular "sin conexión" basta parar `next start`: lo que cargue sale de la caché del SW.
- **Ids sin `crypto.randomUUID()`:** no existe en contextos no seguros (`http://192.168.x.x`), usar `newId()` de `lib/history.ts` (`getRandomValues`).
- **Doble efecto en desarrollo:** React monta los efectos dos veces; en `/solve` la petición a `/api/solve` se comparte por id (`inflight`) para no pagar dos llamadas. Cualquier otro efecto que dispare una llamada de pago debe hacer lo mismo.
- **React lint estricto** (`react-hooks/set-state-in-effect`): no llamar a `setState` de forma síncrona dentro de un `useEffect`. Derivar el valor con `useMemo` o `useSyncExternalStore`.
- Entorno: Windows 11. En el shell Bash, los bloques grandes con heredoc pueden fallar por el entrecomillado; para crear archivos conviene usar la herramienta Write.
- **Git:** un único repositorio en la raíz `hh/` (rama `main`). El `.git` que creó `create-next-app` dentro de `frontend/` (solo tenía su commit inicial) se retiró para no anidar repositorios. Incluye también `netsim/` (otro proyecto del usuario, no relacionado: no tocarlo). Historial: `53e7d72` (netsim, aparte) y `87b8fbe` (la app, fases 1-4). Sin remoto configurado (no se ha subido a ningún sitio). **Hacer commits solo cuando el usuario lo pida**, con mensaje en español; los mensajes se escriben a un fichero y se usa `git commit -F` (evita problemas de comillas en el shell). Antes de cualquier commit: comprobar con `git add -n .` que `backend/.env` (clave de la API) no aparece; está ignorado y no debe versionarse nunca. Las plantillas `backend/.env.example` y `frontend/.env.local.example` sí se versionan (`frontend/.gitignore` tiene una excepción para esta última).
- `backend/requirements.txt` no fija versiones (solo nombres): si se quiere un entorno reproducible, congelarlo con `pip freeze` o fijar versiones.
