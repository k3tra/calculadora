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
    enunciado_sympy="x**2*sin(x)",
    verificacion=Verificacion(estado="no_verificable", detalle="Respuesta simulada (MOCK_LLM)"),
)

# Con MOCK_LLM=1 y una "y" suelta en el LaTeX (p. ej. x^2 - y^2) se devuelve una función de dos variables,
# para probar las superficies 3D y sus cortes sin gastar API.
MOCK_SOLUTION_3D = Solution(
    pasos=[
        Paso(explicacion="La función depende de dos variables: su gráfica es una superficie $z = f(x, y)$.",
             latex=r"z = x^{2} - y^{2}"),
        Paso(explicacion="Es una silla de montar: sube en la dirección de $x$ y baja en la de $y$.",
             latex=r"\frac{\partial z}{\partial x} = 2x, \quad \frac{\partial z}{\partial y} = -2y"),
    ],
    resultado_latex=r"z = x^{2} - y^{2}",
    resultado_sympy="x**2 - y**2",
    enunciado_sympy="x**2 - y**2",
    verificacion=Verificacion(estado="no_verificable", detalle="Respuesta simulada (MOCK_LLM)"),
)
