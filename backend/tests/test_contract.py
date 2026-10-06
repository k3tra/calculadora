"""El contrato backend <-> frontend: schemas.py y frontend/lib/api.ts deben describir los mismos campos."""

import re
import typing
from pathlib import Path

import pytest

from app import schemas

API_TS = Path(__file__).resolve().parents[2] / "frontend" / "lib" / "api.ts"


def ts_fields(name: str) -> set[str]:
    src = API_TS.read_text(encoding="utf-8")
    m = re.search(rf"export type {name} = \{{(.*?)\}};", src, re.S)
    assert m, f"api.ts no define 'export type {name}'"
    body = re.sub(r"//.*", "", m.group(1))  # los comentarios pueden contener ':'
    return set(re.findall(r"(\w+)\??\s*:", body))


@pytest.mark.parametrize("nombre", ["ScanResult", "Paso", "Verificacion", "Solution"])
def test_los_campos_coinciden(nombre):
    backend = set(getattr(schemas, nombre).model_fields)
    assert ts_fields(nombre) == backend, (
        f"{nombre}: solo en el backend {sorted(backend - ts_fields(nombre))}, "
        f"solo en el frontend {sorted(ts_fields(nombre) - backend)}"
    )


def test_los_tipos_de_ejercicio_coinciden():
    src = API_TS.read_text(encoding="utf-8")
    m = re.search(r"export type Tipo = ([^;]+);", src)
    assert m, "api.ts no define 'export type Tipo'"
    assert set(re.findall(r'"(\w+)"', m.group(1))) == set(typing.get_args(schemas.Tipo))


def test_los_estados_de_verificacion_coinciden():
    src = API_TS.read_text(encoding="utf-8")
    m = re.search(r"estado: ([^;]+);", src)
    assert m
    estados = set(re.findall(r'"(\w+)"', m.group(1)))
    assert estados == set(typing.get_args(schemas.Verificacion.model_fields["estado"].annotation))
