# Plan: app para escanear ejercicios y resolverlos en LaTeX

## 1. Qué hace la app

1. El usuario saca una foto o sube una imagen del ejercicio, impreso o a mano.
2. La app reconoce el enunciado y lo pasa a **LaTeX**.
3. El usuario revisa el LaTeX con una vista previa y lo corrige si hace falta.
4. La app genera la **resolución paso a paso**, con cada paso en LaTeX y una explicación.
5. Un sistema de álgebra simbólica (CAS) **verifica** el resultado.
6. La app muestra el enunciado, los pasos y el resultado final, y permite exportar a `.tex` o PDF.

## 2. Arquitectura

```
[Frontend web/móvil] ──imagen──▶ [API backend]
                                    ├─ Preprocesado de imagen (OpenCV/Pillow)
                                    ├─ Imagen → LaTeX (modelo de visión)
                                    ├─ Resolución paso a paso (LLM, salida JSON)
                                    ├─ Verificación (SymPy)
                                    └─ Exportación (.tex / PDF con Tectonic)
                                 ◀──JSON con pasos──
[Renderizado KaTeX]
```

## 3. Tecnologías

| Capa | Opción recomendada | Alternativas |
|---|---|---|
| Frontend | Next.js + React como PWA | React Native/Expo |
| Renderizar fórmulas | KaTeX | MathJax |
| Editor de LaTeX | MathLive o CodeMirror con vista previa | — |
| Backend | Python + FastAPI | Node + microservicio de verificación |
| Imagen → LaTeX | Claude con visión (`claude-sonnet-5-5`) | Mathpix, pix2tex |
| Resolución | Claude (`claude-opus-5-5` para problemas difíciles, `claude-sonnet-5-5` para el resto) | — |
| Verificación | SymPy | — |
| PDF | Tectonic | pdflatex |
| Base de datos | SQLite, después Postgres | — |
| Almacenamiento de imágenes | Disco local, después S3 o R2 | — |

## 4. Flujo de datos

### a) Captura y preprocesado
- Recorte manual en el frontend (`react-easy-crop`).
- En el backend: corrección de perspectiva, escala de grises, más contraste y redimensionado a unos 1500 px de ancho.

### b) Imagen → LaTeX
Salida estructurada:
```json
{
  "enunciado_texto": "Calcula la derivada de...",
  "latex": "f(x) = \\frac{x^2+1}{\\sin x}",
  "tipo": "derivada",
  "confianza": 0.92
}
```
Si la confianza sale baja, la app pide revisión al usuario.

### c) Resolución paso a paso
```json
{
  "pasos": [
    { "explicacion": "Aplicamos la regla del cociente", "latex": "f'(x)=\\frac{u'v-uv'}{v^2}" }
  ],
  "resultado_latex": "f'(x)=\\frac{2x\\sin x-(x^2+1)\\cos x}{\\sin^2 x}",
  "resultado_sympy": "(2*x*sin(x)-(x**2+1)*cos(x))/sin(x)**2"
}
```

### d) Verificación con SymPy
- Se resuelve con SymPy, convirtiendo el LaTeX con `sympy.parsing.latex.parse_latex`.
- Se compara `simplify(resultado_llm - resultado_sympy) == 0`.
- Si coinciden: "✅ Verificado". Si no: se reintenta pasando el error al modelo y, si sigue fallando, se muestra "⚠️ No verificado".

### e) Presentación
- Tarjeta del enunciado: la imagen original al lado del LaTeX renderizado.
- Pasos numerados y desplegables, con explicación y fórmula.
- Resultado final destacado, con la etiqueta de verificación.
- Botones para copiar el LaTeX, descargar el `.tex` y descargar el PDF.

## 5. Endpoints

| Método | Ruta | Función |
|---|---|---|
| POST | `/api/scan` | Recibe la imagen y devuelve el LaTeX del enunciado |
| POST | `/api/solve` | Recibe el LaTeX y devuelve los pasos y el resultado verificado |
| POST | `/api/export/pdf` | Recibe la resolución y devuelve el PDF |
| GET | `/api/history` | Devuelve los ejercicios guardados |

## 6. Estructura

```
hh/
├── frontend/          # Next.js
│   ├── app/scan/      # cámara + recorte
│   ├── app/solve/     # vista de resultados
│   └── components/    # LatexView, StepCard, LatexEditor
├── backend/           # FastAPI
│   ├── app/main.py
│   ├── app/ocr.py         # imagen → LaTeX
│   ├── app/solver.py      # pasos con LLM
│   ├── app/verify.py      # SymPy
│   ├── app/export.py      # plantilla .tex + Tectonic
│   └── templates/solucion.tex
└── docker-compose.yml
```

## 7. Fases

1. **MVP:** subir imagen → LaTeX → pasos → renderizado con KaTeX. Sin cuentas de usuario.
2. **Fiabilidad:** editor de LaTeX, verificación con SymPy, reintentos automáticos.
3. **Exportación:** plantilla LaTeX y PDF con Tectonic.
4. **UX móvil:** PWA, cámara, recorte, historial.
5. **Extras:** varios ejercicios por foto, gráficas, modo "solo pistas", cuentas.

## 8. Riesgos

- Errores al leer la imagen: la revisión y edición del LaTeX es obligatoria antes de resolver.
- Errores del modelo en un paso: verificación con SymPy y reintento; si SymPy no cubre el problema, se marca como "no verificable".
- LaTeX que KaTeX no renderiza: MathJax como alternativa, o pedir solo comandos compatibles con KaTeX.
- Costes: el modelo más barato para leer la imagen, el más potente solo para resolver; caché por hash de la imagen.
- Seguridad: la API key va solo en el backend (`.env`), con límite de tamaño de imagen y límite de peticiones.

## 9. Pruebas

- Un conjunto de unas 50 imágenes de ejercicios reales, cada una con su LaTeX y su resultado correctos.
- Un script que mida el porcentaje de LaTeX bien reconocido y el porcentaje de resultados verificados.
