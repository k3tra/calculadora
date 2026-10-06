"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import SolutionView from "@/components/SolutionView";
import StatementCard from "@/components/StatementCard";
import { solve, type Solution, type Tipo } from "@/lib/api";
import { addEntry } from "@/lib/history";

type Ejercicio = {
  id: string;
  latex: string;
  enunciado_texto: string;
  tipo?: Tipo;
  imagen: string | null;
  solution?: Solution; // ya resuelto: recargar no repite la llamada de pago
};

const inflight = new Map<string, Promise<Solution>>();

const subscribe = () => () => {};
function readStored(): string | null {
  try {
    return sessionStorage.getItem("ejercicio");
  } catch {
    return null;
  }
}

export default function SolvePage() {
  const raw = useSyncExternalStore(subscribe, readStored, () => null);
  const ejercicio = useMemo<Ejercicio | null>(() => (raw ? JSON.parse(raw) : null), [raw]);
  const [fetched, setFetched] = useState<Solution | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const solution = ejercicio?.solution ?? fetched;
  const needsSolving = !!ejercicio && !ejercicio.solution;

  useEffect(() => {
    if (!ejercicio || ejercicio.solution) return;
    let cancelled = false;
    // En desarrollo React monta los efectos dos veces: compartir la petición evita pagar dos llamadas.
    const key = String(ejercicio.id);
    let request = inflight.get(key);
    if (!request) {
      request = solve(ejercicio.latex, ejercicio.enunciado_texto, ejercicio.tipo);
      inflight.set(key, request);
      const clear = () => inflight.delete(key);
      request.then(clear, clear);
    }
    request
      .then((s) => {
        if (cancelled) return;
        setFetched(s);
        // La solución queda en sessionStorage (recargar no vuelve a llamar a la API) y en el historial.
        try {
          sessionStorage.setItem("ejercicio", JSON.stringify({ ...ejercicio, solution: s }));
        } catch {}
        addEntry({
          id: ejercicio.id,
          creado: Date.now(),
          latex: ejercicio.latex,
          enunciado_texto: ejercicio.enunciado_texto,
          tipo: ejercicio.tipo ?? "otro",
          imagen: ejercicio.imagen,
          solution: s,
        }).catch(() => {}); // si IndexedDB no está disponible, resolver sigue funcionando
      })
      .catch((e) => !cancelled && setApiError(e instanceof Error ? e.message : "Error desconocido"));
    return () => {
      cancelled = true;
    };
  }, [ejercicio]);

  const error = apiError ?? (raw === null ? "No hay ningún ejercicio que resolver." : null);

  return (
    <main className="mx-auto w-full max-w-2xl p-6 flex flex-col gap-5">
      <div className="flex justify-between text-sm text-blue-600">
        <Link href="/scan">← Otro ejercicio</Link>
        <Link href="/historial">Historial</Link>
      </div>
      <h1 className="text-2xl font-semibold">Resolución</h1>

      {ejercicio && <StatementCard latex={ejercicio.latex} imagen={ejercicio.imagen} />}

      {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {needsSolving && !solution && !error && <p className="text-sm opacity-70">Resolviendo…</p>}

      {ejercicio && solution && (
        <SolutionView latex={ejercicio.latex} enunciado_texto={ejercicio.enunciado_texto} solution={solution} />
      )}
    </main>
  );
}
