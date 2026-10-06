"use client";

import katex from "katex";
import "katex/dist/katex.min.css";
import { useMemo } from "react";

export default function LatexView({ latex, block = false }: { latex: string; block?: boolean }) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(latex, { displayMode: block, throwOnError: true });
    } catch {
      return null;
    }
  }, [latex, block]);

  if (html === null) {
    return <code className="text-sm text-red-600 break-all">{latex}</code>;
  }
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}
