import LatexView from "./LatexView";
import RichText from "./RichText";
import type { Paso } from "@/lib/api";

export default function StepCard({ n, paso }: { n: number; paso: Paso }) {
  return (
    <details open className="rounded-lg border border-black/10 dark:border-white/15 p-4">
      <summary className="cursor-pointer font-medium">
        {n}. <RichText text={paso.explicacion} />
      </summary>
      <div className="mt-3 overflow-x-auto">
        <LatexView latex={paso.latex} block />
      </div>
    </details>
  );
}
