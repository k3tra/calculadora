# Ejercicios LaTeX

Escanea un ejercicio de matemáticas, pásalo a LaTeX y resuélvelo paso a paso. Diseño completo en [PLAN.md](PLAN.md).

## Arrancar

Backend (necesita `backend/.env` con `ANTHROPIC_API_KEY`, ver `.env.example`):

```
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --reload
```

Frontend:

```
cd frontend
npm install
npm run dev
```

Abre http://localhost:3000.
