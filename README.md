# Ejercicios LaTeX

Escanea un ejercicio de matemáticas (foto o imagen), pásalo a LaTeX, resuélvelo paso a paso y grafícalo. Diseño completo en [PLAN.md](PLAN.md); notas de desarrollo en [CLAUDE.md](CLAUDE.md).

- **Leer:** imagen → LaTeX editable (editor visual MathLive o LaTeX en bruto), con recorte y giro. También se puede escribir el ejercicio sin imagen.
- **Resolver:** pasos explicados en español con KaTeX. El resultado se **verifica con SymPy** (derivadas, integrales, ecuaciones, límites) y, si no cuadra, se reintenta hasta 2 veces.
- **Graficar (gratis, sin IA):** curvas 2D automáticas bajo cada solución y superficies 3D `z = f(x, y)` con curvas de nivel y cortes `x = c` / `y = c`. Página `/graficar` para funciones libres.
- **Exportar:** `.tex` y PDF (Tectonic).
- **PWA:** historial local en el navegador (IndexedDB), instalable y con soporte sin conexión.

Stack: FastAPI + Claude (Anthropic) en el backend; Next.js 16, React, Tailwind y KaTeX en el frontend.

## Requisitos

- Python 3 (probado con 3.14), Node.js 20+ y una clave de la API de Anthropic (**cada lectura y cada resolución se cobra**).
- Opcional: [Tectonic](https://tectonic-typesetting.github.io/) para exportar PDF (`backend/bin/tectonic/tectonic.exe`, o la ruta en `TECTONIC_BIN`).

## Arrancar

```
# Backend (desde backend/)
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env            # y escribe tu ANTHROPIC_API_KEY (nunca se sube a git)
.venv/Scripts/python -m uvicorn app.main:app --reload     # :8000

# Frontend (desde frontend/)
npm install
npm run dev                     # :3000, solo en 127.0.0.1
```

Abre http://127.0.0.1:3000. Sin clave y sin gasto, el backend puede arrancar en modo simulado (`MOCK_LLM=1`): devuelve siempre respuestas fijas, útil para probar la interfaz.

En Windows, `scripts/crear-exe.ps1` genera un `Ejercicios LaTeX.exe` en el Escritorio que levanta backend y frontend y abre el navegador (usa la API real).

## Pruebas

```
cd backend  && .venv/Scripts/python -m pytest -q     # ninguna llama a la API real
cd frontend && npm test && npm run lint && npm run build
```

`backend/eval/` mide la calidad de lectura (imagen → LaTeX) sobre un corpus sintético; **usa la API de pago** (ver el docstring de `run_eval.py`).

## Seguridad y costes

- La clave solo vive en `backend/.env` (ignorado por git). Hay límites por minuto y de concurrencia en `/api/scan`, `/api/solve` y `/api/plot`, pero son en memoria y globales: **no sustituyen a un tope de gasto en tu cuenta de Anthropic**.
- No hay cuentas ni autenticación: no expongas el backend a internet sin añadir un token de acceso.
- El LaTeX que genera el modelo se compila en el servidor para el PDF: pasa por una lista blanca (ver `backend/app/export.py`); si se despliega, ejecuta Tectonic sin acceso a secretos.

## Licencia

MIT, ver [LICENSE](LICENSE).
