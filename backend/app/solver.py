import asyncio
import logging
import re

from .config import settings
from .llm import parse_json
from .mock import MOCK_SOLUTION, MOCK_SOLUTION_3D
from .schemas import Solution, SolutionDraft, SolveRequest
from .verify import verify

MAX_RETRIES = 2
# El logger de uvicorn: el del módulo no saldría por consola con la configuración por defecto.
log = logging.getLogger("uvicorn.error")

SYSTEM = (
    "Eres un profesor de matemáticas. Resuelve el ejercicio paso a paso, en español. "
    "Cada paso lleva una explicación breve y su fórmula en LaTeX compatible con KaTeX "
    "(sin delimitadores $ ni \\[ \\]). En la explicación, cualquier expresión matemática va entre $...$ "
    "en LaTeX (por ejemplo $u = x^2$), nunca como x^2 o sin(x) en texto plano. Termina con el resultado final en LaTeX y en sintaxis SymPy. "
    "resultado_sympy se usa para verificar tu respuesta con un programa, así que sigue este formato: "
    "usa ** para potencias y * explícito para productos; sin 'f(x) =' ni 'y =' delante, solo la expresión. "
    "Para derivada: la derivada. Para integral indefinida: una primitiva sin '+C'; para definida: el valor. "
    "Para ecuación: la lista de soluciones reales, por ejemplo [2, 3]. Para límite: el valor ('oo' para infinito). "
    "Déjalo vacío solo si el ejercicio no encaja en ninguno. "
    "enunciado_sympy es el ENUNCIADO del ejercicio transcrito a sintaxis SymPy, sin ambigüedades "
    "(** para potencias, * explícito en todos los productos, paréntesis completos), y sirve para comprobar tu "
    "resultado: derivada: la función a derivar (sin 'f(x) ='); integral: Integral(f, x) o, si es definida, "
    "Integral(f, (x, a, b)) con oo para infinito; ecuación: Eq(lado_izquierdo, lado_derecho); "
    "límite: Limit(f, x, a) para el límite bilateral (x→a), LimitPlus(f, x, a) para x→a⁺ y LimitMinus(f, x, a) "
    "para x→a⁻ (oo para infinito); si el límite bilateral no existe, pon nan en resultado_sympy. Transcríbelo fielmente del ejercicio dado, sin simplificarlo "
    "ni resolverlo. Déjalo vacío si no encaja en ninguno."
)


def _prompt(req: SolveRequest) -> str:
    text = f"Tipo: {req.tipo}\nEjercicio (LaTeX): {req.latex}"
    if req.enunciado_texto:
        text = f"Enunciado: {req.enunciado_texto}\n{text}"
    return text


async def solve(req: SolveRequest) -> Solution:
    if settings.mock_llm:
        # Una "y" suelta en el LaTeX (no dentro de un comando como \sqrt) simula un ejercicio de dos variables.
        return MOCK_SOLUTION_3D if re.search(r"(?<![A-Za-z\\])y(?![A-Za-z])", req.latex) else MOCK_SOLUTION
    base = _prompt(req)
    text = base
    for attempt in range(MAX_RETRIES + 1):
        draft = await parse_json(model=settings.solve_model, system=SYSTEM, content=text,
                                 output_format=SolutionDraft, effort="high")
        v = await asyncio.to_thread(verify, req.tipo, req.latex, draft)
        # Solo tipo, estado y motivo: sirve para diagnosticar verificaciones fallidas sin guardar el enunciado.
        log.info("verificacion tipo=%s intento=%d estado=%s detalle=%.200s", req.tipo, attempt + 1, v.estado, v.detalle)
        if v.estado != "no_verificado" or attempt == MAX_RETRIES:
            break
        text = (
            f"{base}\n\nUn intento anterior dio resultado_sympy = {draft.resultado_sympy!r}, "
            f"pero la verificación con SymPy falló: {v.detalle}. "
            "Revisa el razonamiento y devuelve una resolución corregida."
        )
    return Solution(**draft.model_dump(), verificacion=v)
