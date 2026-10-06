import type { Verificacion } from "@/lib/api";

const STYLES = {
  verificado: { icon: "✅", label: "Verificado", cls: "bg-green-100 text-green-900" },
  no_verificado: { icon: "⚠️", label: "No verificado", cls: "bg-amber-100 text-amber-900" },
  no_verificable: { icon: "ℹ️", label: "No verificable", cls: "bg-gray-100 text-gray-800" },
} as const;

export default function VerifyBadge({ verificacion }: { verificacion: Verificacion }) {
  const s = STYLES[verificacion.estado];
  return (
    <div className="flex flex-col gap-1">
      <span className={`self-start rounded-full px-3 py-1 text-sm font-medium ${s.cls}`}>
        {s.icon} {s.label}
      </span>
      {verificacion.detalle && <span className="text-xs opacity-70">{verificacion.detalle}</span>}
    </div>
  );
}
