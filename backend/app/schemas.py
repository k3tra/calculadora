from typing import Literal

from pydantic import BaseModel, Field

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
