import LatexView from "./LatexView";

export default function StatementCard({ latex, imagen }: { latex: string; imagen: string | null }) {
  return (
    <section className="grid items-center gap-4 rounded-lg border border-black/10 p-4 dark:border-white/15 sm:grid-cols-2">
      {imagen && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imagen} alt="Ejercicio" className="max-h-40 w-full rounded object-contain" />
      )}
      <div className="min-w-0 overflow-x-auto">
        <LatexView latex={latex} block />
      </div>
    </section>
  );
}
