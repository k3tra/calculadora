# Guía paso a paso: cómo se construyó Ejercicios LaTeX

Esta guía cuenta **en qué orden se hizo todo, por qué se decidió así y cómo reproducirlo o continuarlo**. Está pensada para quien quiera rehacer el proyecto desde cero, entender sus decisiones o retomarlo meses después sin acordarse de nada.

El proyecto se construyó de forma iterativa con [Claude Code](https://claude.com/claude-code) (un agente de programación en la terminal), por fases pequeñas, probando cada una antes de pasar a la siguiente. Las notas internas de desarrollo están en [`CLAUDE.md`](../CLAUDE.md) y los diseños de cada parte en [`PLAN.md`](../PLAN.md), [`PLAN-FASE4.md`](../PLAN-FASE4.md) y [`PLAN-GRAFICADORA.md`](../PLAN-GRAFICADORA.md).

## Índice

0. [Qué se construye y con qué](#0-qué-se-construye-y-con-qué)
1. [Antes de empezar: cuentas, herramientas y gasto](#1-antes-de-empezar-cuentas-herramientas-y-gasto)
2. [Usar el proyecto ya hecho (5 minutos)](#2-usar-el-proyecto-ya-hecho-5-minutos)
3. [Reconstruirlo desde cero, fase por fase](#3-reconstruirlo-desde-cero-fase-por-fase)
4. [Seguridad: lo que no hay que olvidar](#4-seguridad-lo-que-no-hay-que-olvidar)
5. [Trampas y lecciones aprendidas](#5-trampas-y-lecciones-aprendidas)
6. [Medir la calidad y el coste](#6-medir-la-calidad-y-el-coste)
7. [Probar en el móvil e instalar la PWA](#7-probar-en-el-móvil-e-instalar-la-pwa)
8. [Lanzador con un clic (Windows)](#8-lanzador-con-un-clic-windows)
9. [Publicar en GitHub sin filtrar secretos](#9-publicar-en-github-sin-filtrar-secretos)
10. [Cómo trabajar con Claude Code en este proyecto](#10-cómo-trabajar-con-claude-code-en-este-proyecto)
11. [Mapa de ficheros](#11-mapa-de-ficheros)
12. [Ideas pendientes](#12-ideas-pendientes)

---

## 0. Qué se construye y con qué

Una app web para **escanear un ejercicio de matemáticas** (foto o imagen), pasarlo a **LaTeX**, **resolverlo paso a paso** y **graficarlo**.

```
[Navegador / móvil]  ──imagen──▶  [Backend FastAPI]
                                    ├─ Preprocesado de imagen (Pillow)
                                    ├─ Imagen → LaTeX (Claude con visión)
                                    ├─ Resolución paso a paso (Claude, salida JSON)
                                    ├─ Verificación (SymPy)
                                    ├─ Gráficas 2D/3D (SymPy + muestreo propio)
                                    └─ Exportación .tex / PDF (Tectonic)
                                 ◀──JSON──
[Renderizado con KaTeX, editor MathLive, gráficas en SVG/Canvas]
```

| Capa | Tecnología | Por qué |
|---|---|---|
| Frontend | Next.js 16 (App Router), React, TypeScript, Tailwind 4 | PWA instalable, un solo origen |
| Fórmulas | KaTeX (ver) y MathLive (editar) | KaTeX es rápido; MathLive da un editor visual |
| Backend | Python + FastAPI + Pydantic | Salida estructurada validada |
| Leer imagen | `claude-sonnet-5-5` | El modelo más barato que lee bien |
| Resolver | `claude-opus-5-5` con `effort: "high"` | El más fuerte, solo donde hace falta |
| Verificar | SymPy | No fiarse de un LLM para el resultado |
| PDF | Tectonic | Un solo binario, sin instalar TeX Live |
| Historial | IndexedDB en el navegador | Sin cuentas ni guardar fotos en servidor |

Resultados medidos (detalle en la sección 6): lectura correcta en 36 de 39 imágenes de prueba (92 %); más de 200 tests de backend y 11 de frontend, ninguno llama a la API de pago.

---

## 1. Antes de empezar: cuentas, herramientas y gasto

**Herramientas:** Python 3 (se probó con 3.14), Node.js 20+, Git. Opcional: Tectonic (PDF) y Windows para el lanzador `.exe`.

**Clave de API de Anthropic**
1. Crea una cuenta en <https://console.anthropic.com> y genera una clave (`sk-ant-…`).
2. **Antes de usarla, pon un límite de gasto mensual en la consola.** Es lo único que protege tu dinero de verdad; los límites del código (sección 4) son en memoria y se reinician con el servidor.
3. La clave solo debe vivir en `backend/.env` (ignorado por git). Nunca en el código, en un chat, en una captura ni en un log.

**Cuánto cuesta (orden de magnitud):** leer una imagen es una llamada a Sonnet (céntimos); resolver es una llamada a Opus con hasta 3 intentos (más caro). Las gráficas, la verificación, el historial y la exportación **no usan IA y son gratis**.

---

## 2. Usar el proyecto ya hecho (5 minutos)

```bash
git clone https://github.com/k3tra/calculadora.git
cd calculadora

# Backend
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt      # Linux/Mac: .venv/bin/python
cp .env.example .env                                         # escribe tu ANTHROPIC_API_KEY
.venv/Scripts/python -m uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs

# Frontend (otra terminal)
cd frontend
npm install
npm run dev                                                  # http://127.0.0.1:3000
```

**Probar sin gastar nada:** arranca el backend con `MOCK_LLM=1`. Devuelve siempre respuestas fijas (la derivada de x²·sen(x), o la superficie x²−y² si el LaTeX lleva una `y`). Sirve para probar toda la interfaz. Si la solución no tiene nada que ver con tu ejercicio, casi seguro estás en modo simulado.

**PDF:** descarga [Tectonic](https://tectonic-typesetting.github.io/) y déjalo en `backend/bin/tectonic/tectonic.exe` (o indica otra ruta en `TECTONIC_BIN`). La primera compilación baja paquetes LaTeX (~2 min); después tarda ~1 s.

**Tests:**
```bash
cd backend  && .venv/Scripts/python -m pytest -q
cd frontend && npm test && npm run lint && npm run build
```

---

## 3. Reconstruirlo desde cero, fase por fase

Cada fase tiene un **objetivo**, **qué se hizo** y **cómo saber que está hecha**. Haz la fase siguiente solo cuando la anterior pase su criterio.

### Fase 0: planificar antes de escribir código
- Se escribió `PLAN.md` con la arquitectura, los endpoints, la estructura de carpetas y las fases. Para planificar se usó el modelo más potente; para el resto, modelos más baratos (sección 10).
- **Decisión clave:** el modelo de lenguaje *propone* y un programa *comprueba*. Por eso el resultado pasa siempre por SymPy.

### Fase 1: MVP (subir imagen → LaTeX → pasos → KaTeX)
1. **Backend FastAPI** con tres rutas: `GET /api/health`, `POST /api/scan` (imagen) y `POST /api/solve` (JSON `{latex, enunciado_texto}`).
2. **Una sola función que habla con Claude** (`app/llm.py`, `parse_json`): usa salida estructurada (`client.beta.messages.parse(..., output_format=<modelo Pydantic>)` y se lee `parsed_output`) y traduce los errores de la API a códigos HTTP claros (429, 503, 502; una negativa del modelo → 422).
3. **Esquemas** (`app/schemas.py`): `ScanResult {enunciado_texto, latex, tipo, confianza}` y `Solution {pasos[{explicacion, latex}], resultado_latex, resultado_sympy, ...}`. El modelo solo genera el borrador; lo demás lo añade el backend.
4. **Preprocesado** (`app/preprocess.py`, Pillow): corrige la orientación EXIF, pasa a gris, sube el contraste y reduce a ~1500 px de ancho.
5. **Frontend Next.js:** `/scan` (subir y revisar el LaTeX) y `/solve` (resultados con KaTeX). El ejercicio pasa de una página a otra por `sessionStorage`.
6. **Prompts en español** que piden LaTeX compatible con KaTeX, sin `$` y con las fórmulas dentro del texto entre `$…$` (si no, el modelo mezcla `x^2` en texto plano con LaTeX).
- **Hecho cuando:** subes la foto de una derivada y ves los pasos renderizados.

### Fase 2: fiabilidad (verificar y editar)
1. **Verificador SymPy** (`app/verify.py`) por tipo de ejercicio: derivada, integral, ecuación, límite (otro tipo → "no verificable"). Se compara el resultado del modelo con el cálculo de SymPy en varios puntos de prueba, incluidos negativos y fraccionarios.
2. **Dos lecturas del enunciado:** el modelo lo transcribe a SymPy y además se interpreta el LaTeX con `parse_latex`. Si no coinciden → "no verificable". Nunca falsa seguridad ni falsa alarma.
3. **Reintentos:** hasta 2 más, pasando al modelo el motivo del fallo.
4. **Editor visual MathLive** (con conmutador a LaTeX en bruto) y vista previa en vivo.
- **Hecho cuando:** una derivada, una integral y una ecuación salen "Verificado", y una respuesta falsa deliberada sale "No verificado".

### Fase 3: exportar a .tex y PDF
1. Plantilla `backend/templates/solucion.tex` rellenada en una sola pasada.
2. `POST /api/export/tex` y `/api/export/pdf` (compila con Tectonic, `--untrusted`, límite de 2 compilaciones simultáneas y 180 s).
3. **Seguridad crítica:** el LaTeX viene de un LLM y del usuario y se compila en el servidor → ver sección 4.
- **Hecho cuando:** descargas `solucion.pdf` de una página con las tildes bien.

### Fase 4: experiencia móvil (cámara, recorte, historial, PWA)
Se diseñó primero en `PLAN-FASE4.md` y se entregó en este orden:
1. **Modo simulado** `MOCK_LLM` para probar sin API key.
2. **Proxy `/api/*`** en `next.config.ts` hacia el backend: el navegador habla solo con Next (mismo origen), sin CORS y sin contenido mixto bajo HTTPS. Se sube `proxyTimeout` a 300 s porque Opus puede tardar.
3. **Cámara:** un segundo `<input type="file" accept="image/*" capture="environment">`. Sin `getUserMedia` (exige HTTPS y da peor calidad).
4. **Recorte** con `react-image-crop` (rectángulo libre) y giro de 90°.
5. **Historial solo en el navegador** (IndexedDB con `idb`, máx. 100 entradas): sin cuentas, no se guardan fotos de deberes en ningún servidor.
6. **PWA:** `manifest.ts`, iconos, un **service worker escrito a mano** (~60 líneas) y página `/offline`.
7. **Endurecimiento antes de exponer nada** (sección 4).
- **Hecho cuando:** sin servidor, `/historial` y `/scan` cargan desde la caché; en Cache Storage no aparece nada de `/api/`.

### Fase 5: la graficadora (2D, 3D y cortes)
Pedido: automática, hasta 3 dimensiones y cortes en la tercera. Se diseñó en `PLAN-GRAFICADORA.md`:
1. **Backend** (`app/plot.py`, `POST /api/plot`): inspecciona las variables libres: `x` → curva 2D; `{x, y}` → superficie 3D; otra cosa → no se grafica. El muestreo corre en un **proceso aparte con tiempo límite** (la expresión viene de un LLM).
2. **2D en SVG puro** (`components/plot/Plot2D.tsx`): derivada → f y f′; integral → integrando y primitiva (o área sombreada); ecuación → ambos lados y soluciones; límite → punto hueco.
3. **3D con proyección propia en Canvas 2D** (`lib/plot/project.ts`, `Surface3D.tsx`): sin three.js ni plotly (pesan entre 170 KB y 500 KB comprimidos). Se giran arrastrando o con las flechas.
4. **Cortes y curvas de nivel en el navegador** (`lib/plot/cuts.ts`, `SurfacePanel.tsx`) a partir de la malla ya descargada: marching squares y deslizador sin pedir nada al servidor.
5. **Página `/graficar`** para funciones libres (escribes LaTeX y se grafica): gratis, sin IA.
- **Hecho cuando:** `x^2-y^2` muestra la silla, sus curvas de nivel y cortes con deslizador.

### Fase 6: escribir el ejercicio sin imagen
Botón "Escribir ejercicio" en `/scan`: abre el editor vacío con un selector de tipo (necesario para verificar y graficar) y no hace ninguna llamada de pago.

---

## 4. Seguridad: lo que no hay que olvidar

- **Clave de API:** solo en `backend/.env`. En el repo solo hay `.env.example` con la clave vacía. Antes de cualquier commit: `git add -n .` y comprobar que `.env` no aparece.
- **Límites de uso** (`app/limits.py`): cupo por minuto y concurrencia, globales (tras el proxy el backend siempre ve 127.0.0.1, así que no sirve limitar por IP): `/api/scan` 20/min y 4 simultáneas, `/api/solve` 10/min y 3, `/api/plot` 40/min y 2. Son en memoria: **no sustituyen al tope de gasto de la consola de Anthropic**.
- **Imágenes:** hasta 10 MB y solo PNG/JPEG/WebP; tope de 40 megapíxeles comprobado en la cabecera *antes* de decodificar.
- **No hay cuentas ni autenticación:** no expongas el backend a internet sin añadir un token de acceso.
- **Verificación segura:** `resultado_sympy` viene de un LLM. Nunca `eval`/`sympify` directo: se valida contra una lista blanca de nombres y el cálculo corre en un proceso aparte con tiempo límite (`9**9**9` se corta).
- **PDF (la parte más delicada):** el LaTeX se compila en el servidor. Pasa por una **lista blanca de comandos y entornos** (`ALLOWED_CMDS`/`ALLOWED_ENVS` en `app/export.py`). Se comprobó que `tectonic --untrusted` **no impide leer ficheros** (solo avisa), así que ese filtro es la única barrera. Un fallo real encontrado: `^^5c` (la barra invertida en TeX) atravesaba el filtro; ahora se rechaza `^^`. Hay un test que compila un PDF real intentando filtrar un fichero señuelo. Si despliegas, ejecuta Tectonic sin acceso a secretos.
- **Service worker:** nunca intercepta `/api/*` ni guarda imágenes del usuario ni respuestas que no sean del mismo origen.
- **El servidor de desarrollo solo escucha en `127.0.0.1`.** Exponerlo a la red local es una decisión tuya (`npm run dev:lan`).

---

## 5. Trampas y lecciones aprendidas

**Matemáticas y SymPy**
- `parse_latex` falla con `x^2(x-1)` o `x^2\sin(x)` y lee mal en silencio `\sin(x)(x+1)`: el código lo compensa insertando el producto explícito.
- `f(x) = …` da un árbol ambiguo (se quita el prefijo) y `e^{x}` se lee como la variable `e` (se sustituye por `E`).
- Los símbolos deben ser **reales**: con complejos, la derivada de `log|x|` queda como `re(x)` y toda integral con `ln|x|` salía "No verificado" aunque fuera correcta.
- Las integrales definidas se comparan **numéricamente**, no con forma cerrada.
- Con solo puntos de prueba positivos, `1` pasaba por derivada de `|x|`: hay que probar también negativos.
- `Limit` en SymPy es el límite por la derecha; el código define bilateral y laterales.

**Interfaz**
- "1/x^2-9" se lee como `(1/x²)−9`: el usuario debe revisar la fórmula renderizada antes de resolver.
- MathLive normaliza el LaTeX (`x^{2}` → `x^2`): el texto que llega al backend no es idéntico al devuelto por `/api/scan`.
- No uses URLs `blob:` para pasar la imagen entre páginas: se rompen al recargar. Se guarda una miniatura JPEG como data URL.
- `crypto.randomUUID()` no existe en contextos no seguros (`http://192.168.x.x`): usa `getRandomValues`.
- React monta los efectos dos veces en desarrollo: una llamada de pago dentro de un efecto debe compartirse por id o se paga doble.
- La regla de lint `react-hooks/set-state-in-effect` prohíbe `setState` síncrono en efectos: deriva el valor con `useMemo`.
- **Bucle de `ResizeObserver`:** un canvas con ancho fijo en píxeles cuya altura depende de ese ancho congelaba el navegador (la barra de desplazamiento cambiaba el ancho y volvía a disparar el observador). La solución: que la proporción la ponga el CSS (`aspect-ratio`) y el observador solo ajuste el bitmap.
- `react-image-crop`: `onComplete` solo se dispara al soltar; el botón "Usar recorte" depende de `onChange`.

**Service worker**
- Solo se pueden precachear páginas estáticas: por eso el detalle del historial es `/historial/detalle?id=…` y no una ruta dinámica `[id]`.
- Al cambiar el shell hay que subir `VERSION` en `public/sw.js` y añadir las páginas a `PRECACHE`.
- Se prueba con `next build && next start`, nunca con `next dev`. Para simular "sin conexión" basta parar el servidor.

**Herramientas**
- `multiprocessing` con `spawn` en Windows: al probar desde un script suelto hay que protegerlo con `if __name__ == "__main__":` o cada proceso hijo reejecuta el script.
- Next.js 16 cambia APIs respecto a versiones anteriores: lee la guía en `frontend/node_modules/next/dist/docs/` antes de usar una API nueva.
- **Antes de gastar dinero en una medición, prueba el script sin coste.** Una primera ejecución gastó 39 llamadas y no guardó nada porque el comparador falló justo después de cada lectura. Ahora cada lectura se guarda antes de compararla.

---

## 6. Medir la calidad y el coste

`backend/eval/` mide cuánto acierta la lectura de imágenes:

```bash
cd backend
PYTHONPATH=. .venv/Scripts/python -X utf8 eval/make_corpus.py      # genera 39 imágenes (gratis)
PYTHONPATH=. .venv/Scripts/python -X utf8 eval/run_eval.py         # 1 llamada de pago por imagen
```

- `corpus.py` define 39 ejercicios con su LaTeX correcto; `make_corpus.py` los compila con Tectonic, los rasteriza con PyMuPDF (`requirements-eval.txt`) y los degrada como una foto (giro, luz desigual, desenfoque, ruido, JPEG).
- `compare.py` decide si dos LaTeX son el mismo ejercicio (igual tras normalizar, equivalente con SymPy, distinto, o "revisar").
- **Resultado:** 36/39 (92 %). Limpias 13/13, foto 13/13, dura 10/13. Los fallos tuvieron confianza baja (0,40 y 0,35), así que el aviso "revisa el LaTeX" funciona. Tipo de ejercicio bien clasificado 39/39.
- **Límite:** el corpus es texto impreso degradado. **No incluye letra a mano ni fotos reales.** Para medirlo, deja fotos en `backend/eval/corpus_real/` (`NN.jpg` + `NN.txt` con el LaTeX correcto en la 1.ª línea y el tipo en la 2.ª) y usa `--dir eval/corpus_real`.

---

## 7. Probar en el móvil e instalar la PWA

**En la red local (sin instalar):**
```bash
cd frontend && npm run dev:lan        # escucha en 0.0.0.0
```
Abre `http://<IP-del-PC>:3000/scan` desde el móvil (misma Wi-Fi). El cortafuegos de Windows puede pedir permiso para `node.exe`, y si la Wi-Fi está en perfil "Público" puede bloquearlo. Es solo HTTP: la cámara con `capture` funciona, pero **instalar la PWA exige HTTPS**.

**Instalar la PWA (HTTPS con un túnel temporal):**
1. Pon antes el tope de gasto de la sección 1: el túnel expone la app a internet **sin contraseña**.
2. Descarga `cloudflared` del release oficial de GitHub de Cloudflare.
3. Compila y arranca en producción (el service worker solo se registra así): `npm run build && npm run start -- -H 127.0.0.1`, con el backend en marcha.
4. `cloudflared tunnel --url http://127.0.0.1:3000 --no-autoupdate` te da una URL `https://….trycloudflare.com`.
5. Ábrela en el móvil, navega un poco (para precachear) y usa "Instalar aplicación" (Chrome) o "Añadir a pantalla de inicio" (Safari).
6. **Cierra el túnel al terminar.** La URL cambia cada vez, así que la app instalada con ella dejará de abrir la parte online. Para uso diario hace falta un despliegue estable con token de acceso.

---

## 8. Lanzador con un clic (Windows)

`scripts/crear-exe.ps1` compila (con el `csc.exe` que trae Windows, sin instalar nada) un **`Ejercicios LaTeX.exe`** en el Escritorio. Al abrirlo:
1. Recompila la interfaz solo si el código es más nuevo que la última compilación.
2. Arranca el backend (API real) y el frontend en producción, solo en `127.0.0.1`.
3. Abre `http://127.0.0.1:3000/scan`.
4. Al pulsar Enter o cerrar la ventana, apaga todo.

Detalles que costó descubrir: el `finally` de PowerShell **no se ejecuta** si cierras la ventana a la fuerza, y los servidores quedaban huérfanos. Se arregló metiendo todo en un *job object* de Windows con `KILL_ON_JOB_CLOSE` (`scripts/Lanzador.cs`); así, si el `.exe` muere por lo que sea, Windows mata el árbol de procesos. `iniciar.ps1 -Prueba` arranca, comprueba y apaga sin dejar nada abierto. La ruta del proyecto queda fija dentro del `.exe`: si mueves la carpeta, vuelve a ejecutar `crear-exe.ps1`.

---

## 9. Publicar en GitHub sin filtrar secretos

Esto se hizo así (conviene repetirlo en cualquier proyecto con claves):

1. **Auditar el historial completo, no solo el último estado:**
   ```bash
   git log --all --name-only --format= | grep -E "(^|/)\.env($|\.local$)"      # .env nunca versionado
   git grep -nE "sk-ant-[A-Za-z0-9_-]{10,}" $(git rev-list --all)              # ninguna clave
   git grep -nE "tu-correo|192\.168\.|C:.Users" $(git rev-list --all)          # datos personales
   ```
2. **Hacer una copia aparte para publicar** y reescribir allí el historial, sin tocar tu repo de trabajo:
   ```bash
   git clone /ruta/al/repo publicar && cd publicar && git remote remove origin
   git filter-branch -f --prune-empty \
     --index-filter 'git rm -r -q --cached --ignore-unmatch carpeta-privada' \
     --env-filter 'export GIT_AUTHOR_EMAIL=ID+usuario@users.noreply.github.com GIT_COMMITTER_EMAIL=ID+usuario@users.noreply.github.com' \
     -- --all
   ```
   El ID numérico sale de `https://api.github.com/users/<usuario>`. Para quitar un dato de todo el historial (por ejemplo una IP) usa `--tree-filter` con `sed`.
3. **Borrar la copia de seguridad de `filter-branch`** (`refs/original/`), que conserva el historial antiguo con el correo real, y hacer `git reflog expire --expire=now --all && git gc --prune=now`.
4. **Repetir el escaneo solo sobre lo que se va a publicar** (`git rev-list main`).
5. Crear el repo en GitHub **vacío** (sin README, licencia ni `.gitignore`) y empujar **solo `main`** (`git push -u origin main`; nunca `--mirror` ni `--all`).
6. **Verificar desde fuera:** que `backend/.env` devuelva 404 en `raw.githubusercontent.com` y que `.env.example` tenga la clave vacía.

Qué queda fuera de git (`.gitignore`): `.env`, `.venv/`, `node_modules/`, `.next/`, `backend/bin/` (Tectonic y cloudflared), y las imágenes y resultados de la evaluación.

---

## 10. Cómo trabajar con Claude Code en este proyecto

Lo que funcionó:

- **Planificar primero, con el modelo más potente.** Cada fase grande (fase 4, graficadora) se diseñó en un documento `PLAN-*.md` antes de escribir código, con decisiones, pasos con criterio de "hecho", riesgos y qué no hacer.
- **Reparto de modelos:** planificar con Opus; tests y tareas repetitivas con Haiku; todo lo demás con Sonnet. Opus no se usa para otra cosa salvo petición expresa.
- **Un cambio pequeño cada vez y verificarlo de verdad:** tests, lint, build y, para la interfaz, abrirlo en el navegador. No se da una fase por buena sin ver el criterio de "hecho" cumplido.
- **Gasto bajo control:** todo lo que cuesta dinero (llamadas reales, descargar binarios, abrir el túnel a internet, subir a GitHub) se **confirma antes**. `MOCK_LLM=1` permite probar el flujo completo sin gastar.
- **Commits solo cuando se piden**, con mensaje en español escrito a un fichero (`git commit -F`) para evitar problemas de comillas en el shell.
- **`CLAUDE.md` como memoria del proyecto:** estado de cada fase, decisiones, trampas y comandos. Se actualiza al cerrar cada tarea, para poder retomar el trabajo sin contexto previo.
- **Dejar por escrito los fallos propios** (por ejemplo, la medición que gastó dinero sin guardar nada) para no repetirlos.

Cómo retomarlo: abre Claude Code en la carpeta, pídele que lea `CLAUDE.md` y los `PLAN-*.md`, y dile qué quieres hacer.

---

## 11. Mapa de ficheros

```
backend/
  app/main.py        rutas /api/health, scan, solve, export/tex, export/pdf, plot
  app/llm.py         única función que llama a Claude (parse_json) y traduce errores
  app/ocr.py         imagen → LaTeX            app/solver.py   pasos + reintentos
  app/verify.py      verificación SymPy         app/plot.py     muestreo 2D/3D
  app/export.py      LaTeX seguro + Tectonic    app/limits.py   límites de uso
  app/preprocess.py  Pillow                     app/schemas.py  contratos (Pydantic)
  app/mock.py        respuestas del modo simulado (MOCK_LLM=1)
  templates/solucion.tex    tests/    eval/ (medición de lectura)
frontend/
  app/scan  app/solve  app/graficar  app/historial  app/offline  app/manifest.ts
  components/        LatexView, LatexEditor/MathEditor, StepCard, SolutionView,
                     CropEditor, VerifyBadge, RegisterSW, plot/{Plot2D,Surface3D,SurfacePanel,ContourPlot,AutoPlot}
  lib/api.ts         cliente y tipos (reflejan schemas.py)   lib/history.ts  IndexedDB
  lib/plot/          scale, project, cuts       public/sw.js  service worker
  tests/             pruebas con node --test
scripts/             iniciar.ps1, Lanzador.cs, crear-exe.ps1
docs/GUIA.md         esta guía
```

**Contrato backend ↔ frontend:** `backend/tests/test_contract.py` compara los campos de `schemas.py` con los tipos de `frontend/lib/api.ts`. Si añades un campo a un lado, el test falla hasta que lo añadas al otro.

---

## 12. Ideas pendientes

- Medir la lectura con **fotos reales y letra a mano** (la parte difícil).
- **Despliegue estable:** token de acceso, tope diario en el servidor y tope mensual en la consola de Anthropic; ejecutar Tectonic en un contenedor o usuario sin acceso a secretos.
- Varios ejercicios por foto, modo "solo pistas" y cuentas de usuario (migrando el historial).
- Tests propios del frontend más allá de `lib/plot/cuts.ts`.
- Probar con la API real un ejercicio de dos variables, para confirmar que el modelo rellena bien `enunciado_sympy` usando solo `x` e `y`.
