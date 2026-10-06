"""Corpus sintético para medir la lectura de imágenes: (id, categoría, tipo, enunciado en español, LaTeX correcto).

El LaTeX "verdad" es el que debería devolver `/api/scan` en el campo `latex` (sin el texto del enunciado).
Se renderiza con Tectonic y se degrada como una foto (ver make_corpus.py). Añadir casos aquí y volver a generar.
"""

# (categoria, tipo, texto, latex)
CASOS: list[tuple[str, str, str, str]] = [
    # --- derivadas ---
    ("derivada", "derivada", "Calcula la derivada de", r"f(x) = x^{2}\sin(x)"),
    ("derivada", "derivada", "Deriva", r"f(x) = \frac{x^{2}+1}{x-3}"),
    ("derivada", "derivada", "Calcula la derivada de", r"f(x) = e^{3x}\cos(2x)"),
    ("derivada", "derivada", "Deriva la función", r"f(x) = \ln(x^{2}+1)"),
    ("derivada", "derivada", "Calcula", r"\frac{d}{dx}\left(\sqrt{1+x^{2}}\right)"),
    ("derivada", "derivada", "Deriva", r"f(x) = \arctan(2x)"),
    ("derivada", "derivada", "Calcula la derivada de", r"f(x) = (3x^{2}-1)^{5}"),
    ("derivada", "derivada", "Deriva", r"f(x) = x^{x}"),
    # --- integrales ---
    ("integral", "integral", "Calcula la integral", r"\int x\,e^{x}\,dx"),
    ("integral", "integral", "Calcula", r"\int_{0}^{\pi} \sin^{2}(x)\,dx"),
    ("integral", "integral", "Resuelve", r"\int \frac{1}{x^{2}-9}\,dx"),
    ("integral", "integral", "Calcula", r"\int_{1}^{e} \ln(x)\,dx"),
    ("integral", "integral", "Calcula la integral impropia", r"\int_{1}^{\infty} \frac{1}{x^{2}}\,dx"),
    ("integral", "integral", "Resuelve", r"\int \frac{2x+3}{x^{2}+3x+5}\,dx"),
    ("integral", "integral", "Calcula", r"\int \sqrt{4-x^{2}}\,dx"),
    ("integral", "integral", "Calcula", r"\int_{-1}^{1} (x^{3}+2x)\,dx"),
    # --- ecuaciones ---
    ("ecuacion", "ecuacion", "Resuelve la ecuación", r"x^{2}-5x+6=0"),
    ("ecuacion", "ecuacion", "Resuelve", r"2x^{3}-3x^{2}-11x+6=0"),
    ("ecuacion", "ecuacion", "Resuelve", r"\sqrt{x+7}=x-5"),
    ("ecuacion", "ecuacion", "Resuelve", r"\frac{x+1}{x-2}=\frac{3}{x}"),
    ("ecuacion", "ecuacion", "Resuelve", r"e^{2x}-4e^{x}+3=0"),
    ("ecuacion", "ecuacion", "Resuelve", r"\ln(x)+\ln(x-3)=\ln(4)"),
    ("ecuacion", "ecuacion", "Resuelve", r"|2x-1|=7"),
    # --- límites ---
    ("limite", "limite", "Calcula el límite", r"\lim_{x\to 0}\frac{\sin(x)}{x}"),
    ("limite", "limite", "Calcula", r"\lim_{x\to\infty}\left(1+\frac{1}{x}\right)^{x}"),
    ("limite", "limite", "Calcula", r"\lim_{x\to 2}\frac{x^{2}-4}{x-2}"),
    ("limite", "limite", "Calcula", r"\lim_{x\to 0}\frac{1-\cos(x)}{x^{2}}"),
    ("limite", "limite", "Calcula", r"\lim_{x\to\infty}\frac{3x^{2}+1}{2x^{2}-x}"),
    ("limite", "limite", "Calcula", r"\lim_{x\to 0^{+}} x\ln(x)"),
    # --- expresiones con estructura difícil ---
    ("estructura", "otro", "Simplifica", r"\frac{\frac{1}{x}+\frac{1}{y}}{\frac{1}{x}-\frac{1}{y}}"),
    ("estructura", "otro", "Calcula", r"\sum_{k=1}^{n} k^{2}"),
    ("estructura", "otro", "Simplifica", r"\sqrt[3]{x^{5}}\cdot\sqrt{x}"),
    ("estructura", "otro", "Expande", r"(a+b)^{4}"),
    # --- dos variables ---
    ("dos_variables", "derivada", "Calcula la derivada parcial respecto de x", r"\frac{\partial}{\partial x}\left(x^{2}y+\sin(xy)\right)"),
    ("dos_variables", "otro", "Dibuja la superficie", r"z = x^{2}-y^{2}"),
    ("dos_variables", "otro", "Dibuja", r"z = \sin(x)\cos(y)"),
    ("dos_variables", "integral", "Calcula la integral doble", r"\int_{0}^{1}\int_{0}^{2} (x+y^{2})\,dy\,dx"),
    ("dos_variables", "derivada", "Calcula la derivada parcial respecto de y", r"f(x,y) = e^{xy}+\frac{x}{y}"),
    ("dos_variables", "otro", "Dibuja", r"z = \sqrt{9-x^{2}-y^{2}}"),
]
