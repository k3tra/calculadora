import { openDB, type DBSchema, type IDBPDatabase } from "idb";
import type { Solution, Tipo } from "./api";

/** Historial local (IndexedDB). Nunca sale del dispositivo: no hay ruta en el servidor. */
export type HistoryEntry = {
  id: string;
  creado: number; // ms desde epoch
  latex: string;
  enunciado_texto: string;
  tipo: Tipo;
  imagen: string | null; // miniatura JPEG como data URL
  solution: Solution;
};

export const MAX_ENTRIES = 100;

interface Schema extends DBSchema {
  historial: { key: string; value: HistoryEntry; indexes: { creado: number } };
}

let dbPromise: Promise<IDBPDatabase<Schema>> | null = null;

// Solo se abre bajo demanda (en el navegador): nunca durante el renderizado en servidor.
function db() {
  dbPromise ??= openDB<Schema>("ejercicios-latex", 1, {
    upgrade(d) {
      d.createObjectStore("historial", { keyPath: "id" }).createIndex("creado", "creado");
    },
  });
  return dbPromise;
}

/** crypto.randomUUID() no existe en contextos no seguros (http://IP-de-la-red-local); getRandomValues sí. */
export function newId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Guarda o reemplaza (idempotente por id) y borra las más antiguas si se pasa de MAX_ENTRIES. */
export async function addEntry(entry: HistoryEntry): Promise<void> {
  const tx = (await db()).transaction("historial", "readwrite");
  await tx.store.put(entry);
  let excess = (await tx.store.count()) - MAX_ENTRIES;
  let cursor = excess > 0 ? await tx.store.index("creado").openCursor() : null;
  while (cursor && excess-- > 0) {
    await cursor.delete();
    cursor = await cursor.continue();
  }
  await tx.done;
}

/** Más recientes primero. */
export async function listEntries(): Promise<HistoryEntry[]> {
  const all = await (await db()).getAllFromIndex("historial", "creado");
  return all.reverse();
}

export async function getEntry(id: string): Promise<HistoryEntry | undefined> {
  return (await db()).get("historial", id);
}

export async function deleteEntry(id: string): Promise<void> {
  await (await db()).delete("historial", id);
}

export async function clearAll(): Promise<void> {
  await (await db()).clear("historial");
}
