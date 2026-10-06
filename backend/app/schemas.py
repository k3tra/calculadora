import math
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

Tipo = Literal["derivada", "integral", "ecuacion", "limite", "otro"]


class ScanResult(BaseModel):
    enunciado_texto: str = Field(description="Enunciado completo en texto, en el idioma original")
    latex: str = Field(description="Expresión matemática principal en LaTeX compatible con KaTeX")
    tipo: Tipo = Field(description="Tipo de ejercicio; 'otro' si no encaja en ninguno")
    confianza: float = Field(description="Confianza de la lectura entre 0 y 1")


class Paso(BaseModel):
    explicacion: str
    latex: str


class SolutionDraft(BaseModel):
    """Lo que genera el modelo."""

    pasos: list[Paso]
    resultado_latex: str
    resultado_sympy: str = Field(description="Resultado en sintaxis SymPy, vacío si no aplica")
    enunciado_sympy: str = Field(description="El enunciado en sintaxis SymPy (sin ambigüedades), vacío si no aplica")


class Verificacion(BaseModel):
    estado: Literal["verificado", "no_verificado", "no_verificable"]
    detalle: str = ""


class Solution(SolutionDraft):
    verificacion: Verificacion


class ExportRequest(BaseModel):
    latex: str = Field(min_length=1, max_length=5000)
    enunciado_texto: str = Field(default="", max_length=5000)
    pasos: list[Paso]
    resultado_latex: str = Field(min_length=1, max_length=5000)
    verificacion: Verificacion


class SolveRequest(BaseModel):
    latex: str = Field(min_length=1, max_length=5000)
    enunciado_texto: str = Field(default="", max_length=5000)
    tipo: Tipo = "otro"


# --- Graficadora (POST /api/plot): nunca llama a la API de pago -----------------------------------

_LIM = 1e6  # tope de |valor| de un rango pedido


def _check_range(lo, hi, nombre):
    if lo is None and hi is None:
        return
    if lo is None or hi is None:
        raise ValueError(f"{nombre}_min y {nombre}_max van juntos")
    if not (math.isfinite(lo) and math.isfinite(hi)) or abs(lo) > _LIM or abs(hi) > _LIM:
        raise ValueError(f"rango de {nombre} fuera de límites")
    if not lo < hi or hi - lo < 1e-6:
        raise ValueError(f"{nombre}_min debe ser menor que {nombre}_max")


class PlotRequest(BaseModel):
    tipo: Tipo = "otro"
    enunciado_sympy: str = Field(max_length=500)
    resultado_sympy: str = Field(default="", max_length=500)
    x_min: float | None = Field(default=None, allow_inf_nan=False)
    x_max: float | None = Field(default=None, allow_inf_nan=False)
    y_min: float | None = Field(default=None, allow_inf_nan=False)
    y_max: float | None = Field(default=None, allow_inf_nan=False)
    n: int = Field(default=41, ge=11, le=81)  # lado de la malla en 3D

    @model_validator(mode="after")
    def _rangos(self):
        _check_range(self.x_min, self.x_max, "x")
        _check_range(self.y_min, self.y_max, "y")
        return self


class Serie(BaseModel):
    label: str
    rol: Literal["f", "derivada", "primitiva", "izquierda", "derecha"]
    segmentos: list[list[tuple[float, float]]]  # tramos continuos: se cortan en asíntotas y huecos de dominio


class Punto(BaseModel):
    x: float
    y: float
    label: str
    hueco: bool = False


class Area(BaseModel):
    a: float
    b: float
    serie: int  # índice de la serie cuyo área bajo la curva se sombrea


class Plot2D(BaseModel):
    kind: Literal["2d"]
    variable: str
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    series: list[Serie]
    puntos: list[Punto]
    area: Area | None = None


class Plot3D(BaseModel):
    kind: Literal["3d"]
    label: str
    x: list[float]
    y: list[float]
    z: list[list[float | None]]  # z[j][i] = f(x[i], y[j]); null fuera del dominio real
    z_range: tuple[float, float]


class PlotNone(BaseModel):
    kind: Literal["none"]
    motivo: str = ""


Plot = Annotated[Plot2D | Plot3D | PlotNone, Field(discriminator="kind")]
