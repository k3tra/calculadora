"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import LatexView from "@/components/LatexView";
import { clearAll, deleteEntry, listEntries, type HistoryEntry } from "@/lib/history";

const BTN = "rounded-lg border border-black/20 px-3 py-2 text-sm dark:border-white/30";

const ESTADO = {
  verificado: "✅ Verificado",
  no_verificado: "⚠️ No verificado",
  no_verificable: "ℹ️ No verificable",
} as const;

export default function HistorialPage() {
  const [entries, setEntries] = useState<HistoryEntry[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listEntries()
      .then((list) => !cancelled && setEntries(list))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  async function remove(id: string) {
    await deleteEntry(id);
    setEntries((prev) => prev?.filter((e) => e.id !== id) ?? null);
  }

  async function removeAll() {
    await clearAll();
    setEntries([]);
    setConfirmClear(false);
  }

  return (
    <main className="mx-auto w-full max-w-2xl p-6 flex flex-col gap-5">
      <Link href="/scan" className="text-sm text-blue-600">
        ← Escanear ejercicio
      </Link>
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Historial</h1>
        {entries && entries.length > 0 && !confirmClear && (
          <button type="button" onClick={() => setConfirmClear(true)} className="text-sm text-red-600">
            Borrar todo
          </button>
        )}
        {confirmClear && (
          <span className="flex items-center gap-2 text-sm">
            ¿Borrar todo el historial?
            <button type="button" onClick={removeAll} className={`${BTN} text-red-600`}>
              Sí, borrar
            </button>
            <button type="button" onClick={() => setConfirmClear(false)} className={BTN}>
              Cancelar
            </button>
          </span>
        )}
      </div>
      <p className="text-xs opacity-60">
        Se guarda solo en este navegador (no se sube a ningún servidor). Máximo 100 ejercicios.
      </p>

      {failed && (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          No se pudo abrir el historial en este navegador (¿modo privado?).
        </p>
      )}
      {!entries && !failed && <p className="text-sm opacity-70">Cargando…</p>}
      {entries && entries.length === 0 && <p className="text-sm opacity-70">Todavía no has resuelto ningún ejercicio.</p>}

      <ul className="flex flex-col gap-3">
        {entries?.map((e) => (
          <li
            key={e.id}
            className="flex items-center gap-3 rounded-lg border border-black/10 p-3 dark:border-white/15"
          >
            <Link href={`/historial/detalle?id=${encodeURIComponent(e.id)}`} className="flex min-w-0 flex-1 items-center gap-3">
              {e.imagen && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={e.imagen} alt="" className="h-14 w-20 shrink-0 rounded bg-white object-contain" />
              )}
              <span className="flex min-w-0 flex-col gap-1">
                <span className="overflow-x-auto">
                  <LatexView latex={e.latex} />
                </span>
                <span className="text-xs opacity-60">
                  {new Date(e.creado).toLocaleString("es")} · {ESTADO[e.solution.verificacion.estado]}
                </span>
              </span>
            </Link>
            <button type="button" onClick={() => remove(e.id)} aria-label="Borrar este ejercicio" className={BTN}>
              Borrar
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
