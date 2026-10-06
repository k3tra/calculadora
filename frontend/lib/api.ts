// Vacío = mismo origen: Next reenvía /api/* al backend (ver next.config.ts).
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export type Tipo = "derivada" | "integral" | "ecuacion" | "limite" | "otro";

export type ScanResult = {
  enunciado_texto: string;
  latex: string;
  tipo: Tipo;
  confianza: number;
};

export type Paso = { explicacion: string; latex: string };

export type Verificacion = {
  estado: "verificado" | "no_verificado" | "no_verificable";
  detalle: string;
};

export type Solution = {
  pasos: Paso[];
  resultado_latex: string;
  resultado_sympy: string;
  // Opcional: las entradas del historial guardadas antes de añadirlo no lo tienen.
  enunciado_sympy?: string;
  verificacion: Verificacion;
};

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new Error("No se pudo conectar con el servidor");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Error ${res.status}`);
  }
  return res.json();
}

export function scan(file: File): Promise<ScanResult> {
  const form = new FormData();
  form.append("file", file);
  return request<ScanResult>("/api/scan", { method: "POST", body: form });
}

export function solve(latex: string, enunciado_texto = "", tipo: Tipo = "otro"): Promise<Solution> {
  return request<Solution>("/api/solve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ latex, enunciado_texto, tipo }),
  });
}

export type ExportPayload = {
  latex: string;
  enunciado_texto: string;
  solution: Solution;
};

export async function exportFile(kind: "tex" | "pdf", p: ExportPayload): Promise<Blob> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/export/${kind}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        latex: p.latex,
        enunciado_texto: p.enunciado_texto,
        pasos: p.solution.pasos,
        resultado_latex: p.solution.resultado_latex,
        verificacion: p.solution.verificacion,
      }),
    });
  } catch {
    throw new Error("No se pudo conectar con el servidor");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `Error ${res.status}`);
  }
  return res.blob();
}

export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// --- Graficadora (POST /api/plot): no llama a la API de pago ---------------------------------------
// Cada subtipo con su propio nombre y sin objetos anidados: backend/tests/test_contract.py los lee con una regex.

export type PlotRequest = {
  tipo: Tipo;
  enunciado_sympy?: string;
  enunciado_latex?: string;
  resultado_sympy?: string;
  x_min?: number | null;
  x_max?: number | null;
  y_min?: number | null;
  y_max?: number | null;
  n?: number;
};

export type Serie = {
  label: string;
  rol: "f" | "derivada" | "primitiva" | "izquierda" | "derecha";
  segmentos: [number, number][][];
};

export type Punto = { x: number; y: number; label: string; hueco: boolean };

export type Area = { a: number; b: number; serie: number };

export type Plot2D = {
  kind: "2d";
  variable: string;
  x_range: [number, number];
  y_range: [number, number];
  series: Serie[];
  puntos: Punto[];
  area: Area | null;
};

export type Plot3D = {
  kind: "3d";
  label: string;
  x: number[];
  y: number[];
  z: (number | null)[][];
  z_range: [number, number];
};

export type PlotNone = { kind: "none"; motivo: string };

export type Plot = Plot2D | Plot3D | PlotNone;

export function plot(req: PlotRequest): Promise<Plot> {
  return request<Plot>("/api/plot", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}
