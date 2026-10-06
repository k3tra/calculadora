import Link from "next/link";

export const metadata = { title: "Sin conexión" };

export default function OfflinePage() {
  return (
    <main className="mx-auto w-full max-w-2xl p-6 flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Sin conexión</h1>
      <p>
        Para leer y resolver ejercicios hace falta conexión con el servidor. Mientras tanto puedes revisar los
        ejercicios que ya habías resuelto.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link href="/historial" className="rounded-lg border border-black/20 px-4 py-3 dark:border-white/30">
          Ver historial
        </Link>
        <a href="/scan" className="rounded-lg border border-black/20 px-4 py-3 dark:border-white/30">
          Reintentar
        </a>
      </div>
    </main>
  );
}
