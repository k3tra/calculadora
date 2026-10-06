"use client";

import { MathfieldElement } from "mathlive";
import "mathlive/fonts.css";
import { useEffect, useRef } from "react";

// Las fuentes las resuelve el bundler con fonts.css, MathLive no debe buscarlas.
MathfieldElement.fontsDirectory = null;

type Props = { value: string; onChange: (latex: string) => void };

export default function MathEditor({ value, onChange }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const field = useRef<MathfieldElement | null>(null);
  const latest = useRef({ value, onChange });

  useEffect(() => {
    latest.current = { value, onChange };
  });

  useEffect(() => {
    const mf = new MathfieldElement();
    mf.value = latest.current.value;
    mf.style.fontSize = "1.25rem";
    mf.style.width = "100%";
    mf.addEventListener("input", () => latest.current.onChange(mf.getValue("latex")));
    host.current?.append(mf);
    field.current = mf;
    return () => {
      mf.remove();
      field.current = null;
    };
  }, []);

  useEffect(() => {
    const mf = field.current;
    if (mf && mf.getValue("latex") !== value) mf.setValue(value);
  }, [value]);

  return <div ref={host} className="rounded-lg border border-black/20 p-2 dark:border-white/30" />;
}
