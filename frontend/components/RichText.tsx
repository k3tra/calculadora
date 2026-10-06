import LatexView from "./LatexView";

/** Texto con matemáticas en línea entre $...$ (como el que devuelve el backend). */
export default function RichText({ text }: { text: string }) {
  // Si los $ no cuadran, se muestra tal cual en vez de renderizar a medias.
  if ((text.match(/\$/g)?.length ?? 0) % 2) return <>{text}</>;
  const parts = text.split(/\$([^$]+)\$/g); // los índices impares son fórmulas
  return (
    <>
      {parts.map((p, i) => (i % 2 ? <LatexView key={i} latex={p} /> : <span key={i}>{p}</span>))}
    </>
  );
}
