"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import SolutionView from "@/components/SolutionView";
import StatementCard from "@/components/StatementCard";
import { getEntry, type HistoryEntry } from "@/lib/history";

// Ruta estática con ?id=…: así el service worker puede precachear la página y abrir ejercicios sin conexión.
function Detalle() {
  const id = useSearchParams().get("id") ?? "";
  // undefined = cargando, null = no existe
  const [entry, setEntry] = useState<HistoryEntry | null | undefined>(undefined);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getEntry(id)
      .then((e) => !cancelled && setEntry(e ?? null))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <main className="mx-auto w-full max-w-2xl p-6 flex flex-col gap-5">
      <Link href="/historial" className="text-sm text-blue-600">
        ← Historial
      </Link>
      <h1 className="text-2xl font-semibold">Resolución</h1>

      {failed && (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">No se pudo abrir el historial en este navegador.</p>
      )}
      {entry === undefined && !failed && <p className="text-sm opacity-70">Cargando…</p>}
      {entry === null && (
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Este ejercicio ya no está en el historial.</p>
      )}

      {entry && (
        <>
          <p className="text-xs opacity-60">{new Date(entry.creado).toLocaleString("es")}</p>
          <StatementCard latex={entry.latex} imagen={entry.imagen} />
          <SolutionView
            latex={entry.latex}
            enunciado_texto={entry.enunciado_texto}
            solution={entry.solution}
            tipo={entry.tipo}
          />
        </>
      )}
    </main>
  );
}

export default function HistorialDetallePage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm opacity-70">Cargando…</p>}>
      <Detalle />
    </Suspense>
  );
}
