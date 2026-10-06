"""Respuestas fijas para probar el flujo completo sin llamar a la API de Anthropic (MOCK_LLM=1)."""

from .schemas import Paso, ScanResult, Solution, Verificacion

MOCK_SCAN = ScanResult(
    enunciado_texto="Calcula la derivada de $f(x) = x^2 \\sin(x)$",
    latex=r"f(x) = x^{2} \cdot \sin(x)",
    tipo="derivada",
    confianza=0.95,
)

MOCK_SOLUTION = Solution(
    pasos=[
        Paso(explicacion="Es un producto de dos funciones, $u = x^2$ y $v = \\sin(x)$: regla del producto.",
             latex=r"(u \cdot v)' = u' \cdot v + u \cdot v'"),
        Paso(explicacion="Derivamos cada factor: $u' = 2x$ y $v' = \\cos(x)$.",
             latex=r"u' = 2x, \quad v' = \cos(x)"),
        Paso(explicacion="Sustituimos en la regla del producto.",
             latex=r"f'(x) = 2x \sin(x) + x^{2} \cos(x)"),
    ],
    resultado_latex=r"f'(x) = 2x\sin(x) + x^{2}\cos(x)",
    resultado_sympy="2*x*sin(x) + x**2*cos(x)",
    verificacion=Verificacion(estado="no_verificable", detalle="Respuesta simulada (MOCK_LLM)"),
)
