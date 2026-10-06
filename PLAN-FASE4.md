# Plan fase 4: UX móvil (cámara, recorte, historial, PWA)

Diseñado por un subagente Opus y revisado contra el código. Decisiones del usuario (2026-10-06) marcadas con ✔.
Estado: **pasos 0-9 implementados y probados en escritorio** (cámara/recorte, historial, PWA, límite de gasto). Pendiente solo la prueba en un móvil real y el túnel HTTPS. Estado detallado en `CLAUDE.md`.
Desviación respecto a este plan: la ruta de detalle es `/historial/detalle?id=…` (estática, precacheable) y no `/historial/[id]`, porque el service worker solo puede precachear páginas estáticas y sin ella abrir un ejercicio sin conexión caía en `/offline`.

## Decisiones
- ✔ **Historial solo en el navegador (IndexedDB)**, no SQLite ni `GET /api/history` como decía `PLAN.md`. Sin cuentas, un id de dispositivo en servidor equivale a una contraseña, y no se guardan fotos de deberes en el servidor. Entrada: `{id: crypto.randomUUID(), creado, latex, enunciado_texto, tipo, imagen (miniatura 320 px ≈ 20 KB), solution}`; máximo 100, se borran las más antiguas. La fase 5 (cuentas) podrá migrarlo.
- **Cámara:** segundo `<input type="file" accept="image/*" capture="environment">` ("Hacer foto"), junto al selector actual. Sin `getUserMedia` (exige HTTPS, peor calidad).
- ✔ **Recorte con `react-image-crop`** (rectángulo libre con asas), no `react-easy-crop` (proporción fija). Girar 90° a mano. Flujo: elegir/fotografiar → `createImageBitmap(file, {imageOrientation: "from-image"})` reducido a ≤2000 px → `CropEditor` → "Usar recorte"/"Omitir" → `cropToFile()` (canvas → JPEG 0.9) → `setFile`. `scan(file)` y `thumbnail()` no cambian; el recodificado a JPEG resuelve HEIC, EXIF y el límite de 10 MB.
- **PWA con service worker escrito a mano** (`public/sw.js`, ~60 líneas, sin Serwist). `app/manifest.ts` (`MetadataRoute.Manifest`), iconos 192/512/maskable. Caché: instala `/offline` e iconos; navegaciones red→caché→`/offline`; `/_next/static/*` caché primero. **Solo se guardan GET del mismo origen, `res.ok && type==="basic"`, fuera de `/api/` y sin RSC.** Registro solo en producción. `Cache-Control: no-cache` para `/sw.js`.
- ✔ **Túnel HTTPS temporal** (`cloudflared tunnel --url http://localhost:3000` sobre `next start`) para probar la PWA en el móvil, **solo con el límite de gasto (paso 9) activo**. Es una descarga externa y una exposición a internet: **volver a pedir confirmación en ese momento**.
- ✔ **Sin caché de `/api/solve` por ahora.** Guardar la solución en historial/`sessionStorage` evita el gasto frecuente (recargar `/solve` hoy repite la llamada a Opus). La caché por hash de imagen casi no acertaría (el recorte cambia los bytes).

## Pasos (cada uno con criterio de "hecho")
0. **`MOCK_LLM`** (`backend/app/config.py`): si está activo, `ocr.image_to_latex` y `solver.solve` devuelven datos fijos. Hecho: flujo completo sin API key + test pytest.
1. **Móvil por red local:** en `frontend/next.config.ts`, `rewrites()` de `/api/:path*` a `http://127.0.0.1:8000/api/:path*` y `allowedDevOrigins` con la IP local; `API_URL` pasa a `""` por defecto en `lib/api.ts` (mismo origen, sin CORS); script `dev:lan` (`next dev -H 0.0.0.0`). Hecho: `/scan` funciona desde el móvil en `http://192.168.x.x:3000`. Ojo al timeout del proxy (solve con Opus puede pasar de 30 s; plan B: `NEXT_PUBLIC_API_URL=http://IP:8000`, uvicorn `--host 0.0.0.0` e IP en `CORS_ORIGINS`) y al firewall de Windows.
2. **Cámara:** segundo `<input>` en `app/scan/page.tsx`, botones grandes. Hecho: abre la cámara trasera en Android e iOS.
3. **Recorte:** `lib/crop.ts` (`loadBitmap`, `cropToFile`), `components/CropEditor.tsx`, estado `raw` vs `file` en `scan/page.tsx` (recortar de nuevo reinicia `result` y `latex`). Hecho: foto de 12 MP girada sale recortada y derecha, JPEG <2 MB.
4. **`lib/history.ts`** (dependencia `idb`): `addEntry`, `listEntries`, `getEntry`, `deleteEntry`, `clearAll`, recorte a 100.
5. **Extraer `components/SolutionView.tsx`** de `app/solve/page.tsx` (pasos, resultado, `VerifyBadge`, copiar, .tex, PDF).
6. **Guardar al resolver:** `onSolve` genera `id`; `/solve` hace `put(id)` (idempotente) al llegar la solución y la guarda en `sessionStorage`; al recargar usa la guardada. Hecho: recargar no hace nuevo POST (pestaña Network).
7. **Páginas:** `app/historial/page.tsx` (lista con miniatura, LaTeX, fecha; borrar y "Borrar todo") y `app/historial/[id]/page.tsx` (`useParams` + `getEntry` + `SolutionView`). Enlaces desde `app/page.tsx` y `/scan`. Regla de lint `set-state-in-effect`: actualizar estado dentro del `.then`.
8. **PWA:** `app/manifest.ts`, iconos (`public/icons/`, `app/apple-icon.png`), `public/sw.js`, `app/offline/page.tsx`, `components/RegisterSW.tsx` en `app/layout.tsx`, `viewport.themeColor`. Hecho: Lighthouse instalable; en Cache Storage no aparece nada de `/api/`.
9. **Endurecimiento (obligatorio antes del túnel):** en `preprocess()`, comprobar `width*height` (≤ ~40 MP) antes de decodificar → 413; semáforo global y cupo por minuto en `/api/scan` y `/api/solve` (mismo patrón que `pdf_max_concurrent`). Con `rewrites` el backend ve siempre 127.0.0.1, así que no sirve un límite por IP.

## Orden de entrega
1. Pasos 0-3 (cámara + recorte). 2. Pasos 4-7 (historial). 3. Paso 8 (PWA). 4. Paso 9 (endurecimiento) **antes** de usar el túnel.

## API, dependencias y pruebas
- Sin cambios en `schemas.py` ni en los tipos de `lib/api.ts`. `HistoryEntry` es solo del frontend (reutiliza `Solution` y `Tipo`).
- Frontend: `react-image-crop`, `idb`. Backend: ninguna.
- pytest (sin coste): rechazo por demasiados píxeles (413), límite de peticiones (429), respuestas `MOCK_LLM` válidas contra `ScanResult`/`Solution`. Frontend: lint + build; `lib/crop.ts` y `lib/history.ts` como funciones puras.
- Manual con `MOCK_LLM=1`: recorte (giro, recortar dos veces, omitir), historial (recargar sin POST, borrar, >100 entradas), SW sobre `next build && next start` (DevTools → Offline: `/historial` sigue y `/scan` avisa).
- Móvil: la cámara con `capture` funciona por HTTP en la red local; instalación y SW exigen HTTPS (túnel). `--experimental-https` solo vale para localhost. **Una sola pasada con la API real al final** (foto de móvil → resolver).

## Riesgos
iOS: límite de canvas ~16 Mpx (reducir antes de recortar), sin `beforeinstallprompt` (instalación manual), Safari puede borrar IndexedDB tras 7 días sin instalar (pedir `navigator.storage.persist()`). SW en desarrollo: registrar solo en producción. MathLive: el teclado virtual puede quedar tapado en modo standalone. Next 16: usar `MetadataRoute.Manifest` y `viewport` (no `metadata.themeColor`); leer la guía en `frontend/node_modules/next/dist/docs/` antes de usar cada API.
