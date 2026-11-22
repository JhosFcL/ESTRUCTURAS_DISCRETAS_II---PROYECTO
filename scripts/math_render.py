"""
Motor de tipografía matemática (600 DPI) con fuentes Computer Modern (MathJax OpenType).

Genera fórmulas matemáticas en PNG transparente de ultra-alta definición con:
- Fracciones verticales reales (numerador / barra horizontal / denominador).
- Operadores grandes (∑, ∏) con límites apilados arriba y abajo.
- Coeficientes binomiales con paréntesis altos curvos.
- Superíndices, subíndices y sub-superíndices simultáneos.
- Raíces cuadradas con vínculo horizontal.
- Paréntesis y corchetes autoajustables a la altura del contenido.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

from PIL import Image, ImageDraw, ImageFont

MATHJAX_DIR = Path("/usr/share/fonts/opentype/mathjax")
F_MAIN = str(MATHJAX_DIR / "MathJax_Main-Regular.otf")
F_MAIN_BOLD = str(MATHJAX_DIR / "MathJax_Main-Bold.otf")
F_ITALIC = str(MATHJAX_DIR / "MathJax_Math-Italic.otf")
F_AMS = str(MATHJAX_DIR / "MathJax_AMS-Regular.otf")
F_SIZE1 = str(MATHJAX_DIR / "MathJax_Size1-Regular.otf")
F_SIZE2 = str(MATHJAX_DIR / "MathJax_Size2-Regular.otf")
F_SIZE3 = str(MATHJAX_DIR / "MathJax_Size3-Regular.otf")
F_SIZE4 = str(MATHJAX_DIR / "MathJax_Size4-Regular.otf")

INK = (22, 24, 28, 255)


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, max(10, int(round(size))))


@dataclass
class Box:
    """Caja tipográfica con imagen RGBA, ancho, alto y posición vertical del eje matemático (axis)."""
    img: Image.Image
    axis: int  # distancia desde la parte superior hasta la línea del eje matemático (signo '=' / barra fracción)

    @property
    def w(self) -> int:
        return self.img.width

    @property
    def h(self) -> int:
        return self.img.height


class Node:
    def render(self, size: int) -> Box:
        raise NotImplementedError


def _render_glyph(text: str, font_path: str, size: int, pad_x: int = 2, axis_ratio: float = 0.54) -> Box:
    fnt = _font(font_path, size)
    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    dr = ImageDraw.Draw(dummy)
    # Medir con ancla 'ls' (left baseline) para alinear correctamente las líneas base
    bbox = dr.textbbox((0, 0), text, font=fnt, anchor="ls")
    x0, y0, x1, y1 = bbox
    # Usar referencia de altura de 'x' para definir el eje matemático de la fuente
    xb = dr.textbbox((0, 0), "x", font=fnt, anchor="ls")
    x_mid_above_base = -(xb[1] + xb[3]) / 2.0  # positivo sobre la línea base
    w = max(1, (x1 - x0) + 2 * pad_x + 4)
    h = max(1, (y1 - y0) + 6)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base_y = -y0 + 3
    d.text((pad_x - x0 + 2, base_y), text, font=fnt, fill=INK, anchor="ls")
    axis = int(round(base_y - x_mid_above_base))
    return Box(img=img, axis=axis)


class Rm(Node):
    """Texto romano recto (números, funciones cosh, sen, palabras cortas, signos)."""
    def __init__(self, text: str, bold: bool = False) -> None:
        self.text = text
        self.bold = bold

    def render(self, size: int) -> Box:
        return _render_glyph(self.text, F_MAIN_BOLD if self.bold else F_MAIN, size, pad_x=2)


class Var(Node):
    """Variables matemáticas en cursiva Computer Modern."""
    def __init__(self, text: str) -> None:
        self.text = text

    def render(self, size: int) -> Box:
        return _render_glyph(self.text, F_ITALIC, size, pad_x=3)


class Bb(Node):
    """Blackboard bold (Z, Q, R) con MathJax_AMS."""
    def __init__(self, text: str) -> None:
        self.text = text

    def render(self, size: int) -> Box:
        return _render_glyph(self.text, F_AMS, size, pad_x=2)


class Op(Node):
    """Operador binario o de relación con espaciado matemático limpio."""
    def __init__(self, symbol: str, pad: float = 0.24) -> None:
        self.symbol = symbol
        self.pad = pad

    def render(self, size: int) -> Box:
        b = _render_glyph(self.symbol, F_MAIN, size, pad_x=max(2, int(size * self.pad)))
        # Centrar el eje exactamente en el centro vertical del símbolo para '=', '+', '−', '⋅'
        if self.symbol in ("=", "+", "−", "⋅", "·", "∼", "≤", "≥", "≠", "∈", "→", "⇒"):
            b.axis = b.h // 2
        return b


class Space(Node):
    def __init__(self, em: float = 0.25) -> None:
        self.em = em

    def render(self, size: int) -> Box:
        w = max(2, int(round(size * self.em)))
        return Box(Image.new("RGBA", (w, 4), (0, 0, 0, 0)), axis=2)


class Row(Node):
    """Concatenación horizontal alineada por el eje matemático."""
    def __init__(self, *items: Node, gap: int = 0) -> None:
        self.items = list(items)
        self.gap = gap

    def render(self, size: int) -> Box:
        boxes = [it.render(size) for it in self.items]
        if not boxes:
            return Box(Image.new("RGBA", (1, 1), (0, 0, 0, 0)), axis=0)
        max_above = max(b.axis for b in boxes)
        max_below = max(b.h - b.axis for b in boxes)
        total_w = sum(b.w for b in boxes) + self.gap * max(0, len(boxes) - 1)
        total_h = max(1, max_above + max_below)
        img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        cx = 0
        for b in boxes:
            y = max_above - b.axis
            img.alpha_composite(b.img, (cx, y))
            cx += b.w + self.gap
        return Box(img=img, axis=max_above)


class Script(Node):
    """Base con superíndice y/o subíndice."""
    def __init__(self, base: Node, sub: Optional[Node] = None, sup: Optional[Node] = None) -> None:
        self.base = base
        self.sub = sub
        self.sup = sup

    def render(self, size: int) -> Box:
        b = self.base.render(size)
        sub_sz = max(14, int(round(size * 0.68)))
        sb = self.sub.render(sub_sz) if self.sub else None
        sp = self.sup.render(sub_sz) if self.sup else None

        script_w = max(sb.w if sb else 0, sp.w if sp else 0)
        shift_sup = int(round(size * 0.34))
        shift_sub = int(round(size * 0.30))

        # Coordenadas relativas al eje matemático de base (y=0 en el eje)
        top = -b.axis
        bot = b.h - b.axis
        if sp:
            sup_top = -shift_sup - sp.axis
            top = min(top, sup_top)
        if sb:
            sub_bot = shift_sub + (sb.h - sb.axis)
            bot = max(bot, sub_bot)

        total_h = max(1, int(round(bot - top)))
        axis = int(round(-top))
        total_w = b.w + script_w + (2 if script_w else 0)
        img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        img.alpha_composite(b.img, (0, axis - b.axis))
        if sp:
            img.alpha_composite(sp.img, (b.w + 1, axis - shift_sup - sp.axis))
        if sb:
            img.alpha_composite(sb.img, (b.w + 1, axis + shift_sub - sb.axis))
        return Box(img=img, axis=axis)


class Frac(Node):
    """Fracción vertical real con barra horizontal centrada en el eje matemático."""
    def __init__(self, num: Node, den: Node, scale: float = 0.90) -> None:
        self.num = num
        self.den = den
        self.scale = scale

    def render(self, size: int) -> Box:
        inner_sz = max(16, int(round(size * self.scale)))
        nb = self.num.render(inner_sz)
        db = self.den.render(inner_sz)
        rule_h = max(2, int(round(size * 0.055)))
        gap = max(5, int(round(size * 0.14)))
        pad_x = max(8, int(round(size * 0.16)))
        bar_w = max(nb.w, db.w) + 2 * pad_x
        total_w = bar_w + 6
        total_h = nb.h + gap + rule_h + gap + db.h
        img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        img.alpha_composite(nb.img, ((total_w - nb.w) // 2, 0))
        bar_y = nb.h + gap
        d.rectangle([3, bar_y, total_w - 4, bar_y + rule_h - 1], fill=INK)
        img.alpha_composite(db.img, ((total_w - db.w) // 2, bar_y + rule_h + gap))
        return Box(img=img, axis=bar_y + rule_h // 2)


def _draw_paren(height: int, side: str, size: int) -> Image.Image:
    """Dibuja paréntesis curvos elegantes (usando MathJax_Size1..4 o curva bezier limpia)."""
    # Elegir fuente Size según altura
    candidates = [(F_MAIN, size), (F_SIZE1, size), (F_SIZE2, size), (F_SIZE3, size), (F_SIZE4, size)]
    ch = "(" if side == "left" else ")"
    best_box = None
    for fp, sz in candidates:
        b = _render_glyph(ch, fp, sz, pad_x=2)
        best_box = b
        if b.h >= height * 0.92:
            break
    assert best_box is not None
    if best_box.h < height * 0.90:
        # Escalar verticalmente suavemente manteniendo grosor armónico
        new_w = max(best_box.w, int(round(best_box.w * (height / best_box.h) ** 0.35)))
        return best_box.img.resize((new_w, height), Image.Resampling.LANCZOS)
    return best_box.img


class Paren(Node):
    """Paréntesis o corchetes autoajustables a la altura del contenido."""
    def __init__(self, inner: Node, left: str = "(", right: str = ")") -> None:
        self.inner = inner
        self.left = left
        self.right = right

    def render(self, size: int) -> Box:
        ib = self.inner.render(size)
        target_h = int(round(ib.h * 1.06))
        if self.left == "(" and self.right == ")":
            l_img = _draw_paren(target_h, "left", size)
            r_img = _draw_paren(target_h, "right", size)
        else:
            # Corchetes vectoriales nítidos
            bw = max(10, int(round(size * 0.24)))
            lw = max(2, int(round(size * 0.055)))
            l_img = Image.new("RGBA", (bw, target_h), (0, 0, 0, 0))
            dl = ImageDraw.Draw(l_img)
            dl.rectangle([2, 0, 2 + lw, target_h - 1], fill=INK)
            dl.rectangle([2, 0, bw - 2, lw], fill=INK)
            dl.rectangle([2, target_h - 1 - lw, bw - 2, target_h - 1], fill=INK)

            r_img = Image.new("RGBA", (bw, target_h), (0, 0, 0, 0))
            dr = ImageDraw.Draw(r_img)
            dr.rectangle([bw - 2 - lw, 0, bw - 2, target_h - 1], fill=INK)
            dr.rectangle([2, 0, bw - 2, lw], fill=INK)
            dr.rectangle([2, target_h - 1 - lw, bw - 2, target_h - 1], fill=INK)

        pad = max(2, int(round(size * 0.06)))
        total_w = l_img.width + pad + ib.w + pad + r_img.width
        max_above = max(ib.axis, l_img.height // 2)
        max_below = max(ib.h - ib.axis, l_img.height - l_img.height // 2)
        total_h = max_above + max_below
        img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        img.alpha_composite(l_img, (0, max_above - l_img.height // 2))
        img.alpha_composite(ib.img, (l_img.width + pad, max_above - ib.axis))
        img.alpha_composite(r_img, (l_img.width + pad + ib.w + pad, max_above - r_img.height // 2))
        return Box(img=img, axis=max_above)


class Binom(Node):
    """Coeficiente binomial apilado con paréntesis altos: (n \\ k)."""
    def __init__(self, top: Node, bottom: Node) -> None:
        self.top = top
        self.bottom = bottom

    def render(self, size: int) -> Box:
        inner_sz = max(16, int(round(size * 0.85)))
        tb = self.top.render(inner_sz)
        bb = self.bottom.render(inner_sz)
        gap = max(8, int(round(size * 0.20)))
        w = max(tb.w, bb.w) + 6
        h = tb.h + gap + bb.h
        inner_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        inner_img.alpha_composite(tb.img, ((w - tb.w) // 2, 0))
        inner_img.alpha_composite(bb.img, ((w - bb.w) // 2, tb.h + gap))
        inner_box = Box(img=inner_img, axis=h // 2)

        l_img = _draw_paren(int(round(h * 1.10)), "left", size)
        r_img = _draw_paren(int(round(h * 1.10)), "right", size)
        total_h = max(h, l_img.height)
        total_w = l_img.width + w + r_img.width
        img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        img.alpha_composite(l_img, (0, (total_h - l_img.height) // 2))
        img.alpha_composite(inner_box.img, (l_img.width, (total_h - h) // 2))
        img.alpha_composite(r_img, (l_img.width + w, (total_h - r_img.height) // 2))
        return Box(img=img, axis=total_h // 2)


class BigOp(Node):
    """Operador grande (∑ o ∏) con límites inferior y superior apilados arriba y abajo."""
    def __init__(self, symbol: str, lower: Optional[Node] = None, upper: Optional[Node] = None) -> None:
        self.symbol = symbol  # "∑" o "∏"
        self.lower = lower
        self.upper = upper

    def render(self, size: int) -> Box:
        op_box = _render_glyph(self.symbol, F_SIZE2, int(round(size * 1.05)), pad_x=4)
        lim_sz = max(14, int(round(size * 0.65)))
        ub = self.upper.render(lim_sz) if self.upper else None
        lb = self.lower.render(lim_sz) if self.lower else None
        gap = max(4, int(round(size * 0.10)))

        w = max(op_box.w, ub.w if ub else 0, lb.w if lb else 0) + 6
        top_h = (ub.h + gap) if ub else 0
        bot_h = (lb.h + gap) if lb else 0
        total_h = top_h + op_box.h + bot_h
        img = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
        if ub:
            img.alpha_composite(ub.img, ((w - ub.w) // 2, 0))
        img.alpha_composite(op_box.img, ((w - op_box.w) // 2, top_h))
        if lb:
            img.alpha_composite(lb.img, ((w - lb.w) // 2, top_h + op_box.h + gap))
        return Box(img=img, axis=top_h + op_box.h // 2)


class Sqrt(Node):
    """Raíz cuadrada vectorial nítida con barra superior (vínculo)."""
    def __init__(self, inner: Node) -> None:
        self.inner = inner

    def render(self, size: int) -> Box:
        ib = self.inner.render(size)
        lw = max(2, int(round(size * 0.055)))
        hook_w = max(18, int(round(size * 0.42)))
        top_pad = max(6, int(round(size * 0.14)))
        total_w = hook_w + ib.w + 8
        total_h = ib.h + top_pad + lw + 2
        img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        # Trazar radical limpio
        y_top = lw + 1
        y_bot = total_h - 3
        y_mid = int(round(total_h * 0.58))
        d.line([(2, y_mid), (hook_w * 0.28, y_mid - lw), (hook_w * 0.55, y_bot)], fill=INK, width=lw + 1)
        d.line([(hook_w * 0.55, y_bot), (hook_w, y_top), (total_w - 3, y_top)], fill=INK, width=lw)

        img.alpha_composite(ib.img, (hook_w + 3, top_pad + lw))
        return Box(img=img, axis=top_pad + lw + ib.axis)


def render_equation_png(node: Node, out_path: Path, size: int = 86, pad: int = 10) -> Tuple[int, int]:
    """Renderiza un nodo matemático a PNG transparente a 600 DPI y retorna (w, h) en píxeles."""
    box = node.render(size)
    out = Image.new("RGBA", (box.w + 2 * pad, box.h + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(box.img, (pad, pad))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path, dpi=(600, 600))
    return out.size


# =============================================================================
# Definición de todas las ecuaciones del informe (desplegadas y de tablas)
# =============================================================================
def build_all_equations(eq_dir: Path) -> dict:
    """Genera todas las imágenes de ecuaciones en alta resolución (600 DPI)."""
    eq_dir.mkdir(parents=True, exist_ok=True)
    specs = {
        # Ecuación (1): Definición FGO
        "eq1_fgo": Row(
            Var("G"), Paren(Var("x")), Op("="),
            Script(Var("a"), sub=Rm("0")), Op("+"),
            Script(Var("a"), sub=Rm("1")), Var("x"), Op("+"),
            Script(Var("a"), sub=Rm("2")), Script(Var("x"), sup=Rm("2")), Op("+"),
            Rm("⋯"), Op("+"),
            Script(Var("a"), sub=Var("k")), Script(Var("x"), sup=Var("k")), Op("+"),
            Rm("⋯"), Op("="),
            BigOp("∑", lower=Row(Var("k"), Op("=", 0.12), Rm("0")), upper=Rm("∞")),
            Space(0.10),
            Script(Var("a"), sub=Var("k")), Script(Var("x"), sup=Var("k")),
        ),
        # Ecuación (2): Suma formal
        "eq2_sum": Row(
            Paren(Row(Var("f"), Op("+"), Var("g"))), Paren(Var("x")), Op("="),
            BigOp("∑", lower=Row(Var("k"), Op("=", 0.12), Rm("0")), upper=Rm("∞")),
            Space(0.08),
            Paren(Row(Script(Var("a"), sub=Var("k")), Op("+"), Script(Var("b"), sub=Var("k")))),
            Script(Var("x"), sup=Var("k")),
        ),
        # Ecuación (3): Producto de Cauchy
        "eq3_cauchy": Row(
            Paren(Row(Var("f"), Op("⋅", 0.14), Var("g"))), Paren(Var("x")), Op("="),
            BigOp("∑", lower=Row(Var("k"), Op("=", 0.12), Rm("0")), upper=Rm("∞")),
            Space(0.06),
            Paren(Row(
                BigOp("∑", lower=Row(Var("j"), Op("=", 0.12), Rm("0")), upper=Var("k")),
                Space(0.08),
                Script(Var("a"), sub=Var("j")),
                Script(Var("b"), sub=Row(Var("k"), Op("−", 0.08), Var("j"))),
            )),
            Script(Var("x"), sup=Var("k")),
        ),
        # Ecuación (4): Serie geométrica formal e inversión
        "eq4_geom": Row(
            Frac(Rm("1"), Row(Rm("1"), Op("−", 0.14), Var("c"), Script(Var("x"), sup=Var("r")))),
            Op("="),
            BigOp("∑", lower=Row(Var("m"), Op("=", 0.12), Rm("0")), upper=Rm("∞")),
            Space(0.08),
            Script(Var("c"), sup=Var("m")),
            Script(Var("x"), sup=Row(Var("m"), Var("r"))),
            Space(0.50),
            Rm(","), Space(0.45),
            Script(Var("b"), sub=Var("k")), Op("="),
            Op("−", 0.08),
            Frac(Rm("1"), Script(Var("a"), sub=Rm("0"))),
            Space(0.08),
            BigOp("∑", lower=Row(Var("j"), Op("=", 0.12), Rm("1")), upper=Var("k")),
            Space(0.06),
            Script(Var("a"), sub=Var("j")),
            Script(Var("b"), sub=Row(Var("k"), Op("−", 0.08), Var("j"))),
        ),
        # Ecuación (5): Teorema del binomio negativo
        "eq5_negbinom": Row(
            Frac(Rm("1"), Script(Paren(Row(Rm("1"), Op("−", 0.14), Var("x"))), sup=Var("n"))),
            Op("="),
            BigOp("∑", lower=Row(Var("k"), Op("=", 0.12), Rm("0")), upper=Rm("∞")),
            Space(0.08),
            Binom(Row(Var("n"), Op("+", 0.12), Var("k"), Op("−", 0.12), Rm("1")), Var("k")),
            Space(0.08),
            Script(Var("x"), sup=Var("k")),
        ),
        # Ecuación (6): Principio multiplicativo con restricciones
        "eq6_mult": Row(
            Script(Var("a"), sub=Var("n")), Op("="),
            Paren(Script(Var("x"), sup=Var("n")), left="[", right="]"),
            Space(0.10),
            BigOp("∏", lower=Row(Var("i"), Op("=", 0.12), Rm("1")), upper=Var("m")),
            Space(0.06),
            Paren(Row(
                BigOp("∑", lower=Row(Var("c"), Op("∈", 0.10), Script(Var("S"), sub=Var("i")))),
                Space(0.08),
                Script(Var("x"), sup=Var("c")),
            )),
            Op("="),
            Paren(Script(Var("x"), sup=Var("n")), left="[", right="]"),
            Space(0.10),
            BigOp("∏", lower=Row(Var("i"), Op("=", 0.12), Rm("1")), upper=Var("m")),
            Space(0.08),
            Frac(
                Row(
                    Script(Var("x"), sup=Script(Var("l"), sub=Var("i"))),
                    Paren(Row(
                        Rm("1"), Op("−", 0.12),
                        Script(Var("x"), sup=Row(Paren(Row(Script(Var("q"), sub=Var("i")), Op("+", 0.08), Rm("1"))), Script(Var("d"), sub=Var("i")))),
                    )),
                ),
                Row(Rm("1"), Op("−", 0.12), Script(Var("x"), sup=Script(Var("d"), sub=Var("i")))),
            ),
        ),
        # Ecuación (7): Teorema de particiones de Euler
        "eq7_euler": Row(
            Var("D"), Paren(Var("x")), Op("="),
            BigOp("∏", lower=Row(Var("k"), Op("=", 0.12), Rm("1")), upper=Rm("∞")),
            Space(0.06),
            Paren(Row(Rm("1"), Op("+", 0.14), Script(Var("x"), sup=Var("k")))),
            Op("="),
            BigOp("∏", lower=Row(Var("k"), Op("=", 0.12), Rm("1")), upper=Rm("∞")),
            Space(0.08),
            Frac(
                Row(Rm("1"), Op("−", 0.12), Script(Var("x"), sup=Row(Rm("2"), Var("k")))),
                Row(Rm("1"), Op("−", 0.12), Script(Var("x"), sup=Var("k"))),
            ),
            Op("="),
            BigOp("∏", lower=Row(Var("j"), Op("=", 0.12), Rm("1")), upper=Rm("∞")),
            Space(0.08),
            Frac(
                Rm("1"),
                Row(Rm("1"), Op("−", 0.12), Script(Var("x"), sup=Row(Rm("2"), Var("j"), Op("−", 0.08), Rm("1")))),
            ),
            Op("="), Var("O"), Paren(Var("x")),
        ),
        # Ecuación (8): FGE y producto etiquetado
        "eq8_egf": Row(
            Var("A"), Paren(Var("x")), Op("="),
            BigOp("∑", lower=Row(Var("n"), Op("=", 0.12), Rm("0")), upper=Rm("∞")),
            Space(0.08),
            Script(Var("a"), sub=Var("n")),
            Space(0.06),
            Frac(Script(Var("x"), sup=Var("n")), Row(Var("n"), Rm("!"))),
            Space(0.55),
            Rm("⇒"), Space(0.45),
            Script(Var("a"), sub=Var("n")), Op("="),
            Var("n"), Rm("!"), Space(0.08),
            Paren(Script(Var("x"), sup=Var("n")), left="[", right="]"),
            Space(0.08),
            BigOp("∏", lower=Row(Var("i"), Op("=", 0.12), Rm("1")), upper=Var("m")),
            Space(0.06),
            Paren(Row(
                BigOp("∑", lower=Row(Var("c"), Op("∈", 0.10), Script(Var("S"), sub=Var("i")))),
                Space(0.08),
                Frac(Script(Var("x"), sup=Var("c")), Row(Var("c"), Rm("!"))),
            )),
        ),
        # Ecuación (9): Fórmula asintótica de Hardy-Ramanujan
        "eq9_hr": Row(
            Var("p"), Paren(Var("n")), Op("∼"),
            Frac(Rm("1"), Row(Rm("4"), Var("n"), Sqrt(Rm("3")))),
            Space(0.14),
            Rm("exp"),
            Paren(Row(Var("π"), Space(0.06), Sqrt(Frac(Row(Rm("2"), Var("n")), Rm("3"))))),
        ),
        # Ecuación (10): Inclusión-Exclusión (oráculo analítico del Experimento 2)
        "eq10_ie": Row(
            Script(Var("a"), sub=Var("N")), Op("="),
            BigOp("∑", lower=Row(Var("j"), Op("=", 0.12), Rm("0")), upper=Var("m")),
            Space(0.08),
            Script(Paren(Row(Op("−", 0.04), Rm("1"))), sup=Var("j")),
            Space(0.06),
            Binom(Var("m"), Var("j")),
            Space(0.06),
            Binom(
                Row(Var("N"), Op("−", 0.10), Var("j"), Paren(Row(Var("u"), Op("+", 0.08), Rm("1"))), Op("+", 0.10), Var("m"), Op("−", 0.10), Rm("1")),
                Row(Var("m"), Op("−", 0.10), Rm("1")),
            ),
        ),
        # --- Fórmulas compactas para Tabla 1 ---
        "t1_1": Script(Paren(Row(Rm("1"), Op("+", 0.12), Var("x"))), sup=Var("n")),
        "t1_2": Frac(Row(Rm("1"), Op("−", 0.12), Script(Var("x"), sup=Row(Var("n"), Op("+", 0.08), Rm("1")))), Row(Rm("1"), Op("−", 0.12), Var("x"))),
        "t1_3": Frac(Rm("1"), Row(Rm("1"), Op("−", 0.12), Script(Var("x"), sup=Var("r")))),
        "t1_4": Frac(Rm("1"), Script(Paren(Row(Rm("1"), Op("−", 0.12), Var("x"))), sup=Var("n"))),
        "t1_5": Frac(Rm("1"), Row(Rm("1"), Op("−", 0.12), Var("a"), Var("x"))),
        "t1_6": Row(Script(Var("e"), sup=Var("x")), Op("="), BigOp("∑", lower=Row(Var("k"), Op("=", 0.10), Rm("0")), upper=Rm("∞")), Space(0.06), Frac(Script(Var("x"), sup=Var("k")), Row(Var("k"), Rm("!")))),
        "t1_7": Row(Rm("cosh"), Paren(Var("x")), Op("="), Frac(Row(Script(Var("e"), sup=Var("x")), Op("+", 0.12), Script(Var("e"), sup=Row(Op("−", 0.04), Var("x")))), Rm("2"))),
        # Coeficientes Tabla 1
        "t1_c1": Binom(Var("n"), Var("k")),
        "t1_c4": Binom(Row(Var("n"), Op("+", 0.10), Var("k"), Op("−", 0.10), Rm("1")), Var("k")),
        # --- Fórmulas compactas para Tabla 3 ---
        "t3_euro": Row(BigOp("∏", lower=Row(Var("d"), Op("∈", 0.08), Var("D"))), Space(0.06), Frac(Rm("1"), Row(Rm("1"), Op("−", 0.10), Script(Var("x"), sup=Var("d"))))),
        "t3_lim": Row(BigOp("∏", lower=Var("i")), Space(0.06), Frac(Row(Rm("1"), Op("−", 0.10), Script(Var("x"), sup=Row(Script(Var("d"), sub=Var("i")), Paren(Row(Script(Var("q"), sub=Var("i")), Op("+", 0.06), Rm("1")))))), Row(Rm("1"), Op("−", 0.10), Script(Var("x"), sup=Script(Var("d"), sub=Var("i")))))),
        "t3_ej12": Row(Var("G"), Paren(Var("x")), Op("="), Frac(Row(Rm("1"), Op("+", 0.10), Var("x")), Row(Paren(Row(Rm("1"), Op("−", 0.10), Var("x"))), Paren(Row(Rm("1"), Op("−", 0.10), Rm("3"), Var("x")))))),
        "t3_ej13": Row(Var("G"), Paren(Var("x")), Op("="), Frac(Rm("1"), Row(Rm("1"), Op("−", 0.10), Rm("4"), Var("x")))),
        "t3_ej14": Row(Var("G"), Paren(Var("x")), Op("="), Frac(Rm("6"), Row(Rm("1"), Op("−", 0.10), Rm("5"), Var("x"), Op("+", 0.10), Rm("6"), Script(Var("x"), sup=Rm("2"))))),
    }

    sizes = {}
    for name, node in specs.items():
        sz = 72 if name.startswith(("t1_", "t3_")) else 84
        w, h = render_equation_png(node, eq_dir / f"{name}.png", size=sz, pad=10)
        sizes[name] = (w, h)
    return sizes


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    out = root / "docs" / "equations"
    res = build_all_equations(out)
    print(f"Generadas {len(res)} ecuaciones tipográficas en {out}")
