"""
Generador de figuras científicas de estilo editorial académico (300 DPI, supermuestreo 2x)
para el informe del Tema 10. Paleta sobria UPCH (granate institucional, pizarra y carbón)
y notación matemática limpia sin sintaxis cruda tipo código.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

FONT_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_ITAL = "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

# Paleta editorial sobria (revista científica / identidad UPCH)
C_BG = (255, 255, 255)
C_INK = (26, 29, 36)
C_MUTED = (95, 104, 118)
C_GRID = (232, 236, 241)
C_AXIS = (55, 65, 81)

C_CRIMSON = (122, 28, 36)     # Granate UPCH sobrio
C_SLATE = (38, 63, 94)        # Azul petróleo oscuro
C_TEAL = (29, 116, 108)       # Verde pizarra elegante
C_AMBER = (176, 98, 22)       # Ocre académico
C_PLUM = (94, 67, 122)        # Ciruela apagado

C_TINT_SLATE = (243, 246, 250)
C_TINT_CRIMSON = (250, 242, 243)
C_TINT_TEAL = (240, 248, 247)
C_TINT_GRAY = (247, 248, 250)


def font(size: int, bold: bool = False, italic: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        path = FONT_MONO
    elif bold:
        path = FONT_BOLD
    elif italic:
        path = FONT_ITAL
    else:
        path = FONT_REG
    return ImageFont.truetype(path, size)


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    lines: Sequence[str],
    fnt: ImageFont.FreeTypeFont,
    fill=C_INK,
    line_gap: int = 8,
) -> None:
    x0, y0, x1, y1 = box
    widths, heights = [], []
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=fnt)
        widths.append(bb[2] - bb[0])
        heights.append(bb[3] - bb[1])
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    cur_y = y0 + (y1 - y0 - total_h) // 2
    for line, w, h in zip(lines, widths, heights):
        cur_x = x0 + (x1 - x0 - w) // 2
        draw.text((cur_x, cur_y), line, font=fnt, fill=fill)
        cur_y += h + line_gap


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    p0: Tuple[int, int],
    p1: Tuple[int, int],
    color=C_SLATE,
    width: int = 4,
    head: int = 16,
) -> None:
    draw.line([p0, p1], fill=color, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    left = (p1[0] - head * math.cos(ang - math.pi / 6), p1[1] - head * math.sin(ang - math.pi / 6))
    right = (p1[0] - head * math.cos(ang + math.pi / 6), p1[1] - head * math.sin(ang + math.pi / 6))
    draw.polygon([p1, left, right], fill=color)


def draw_power_label(
    draw: ImageDraw.ImageDraw,
    right_x: int,
    center_y: int,
    base: str,
    exp: str,
    size: int = 22,
    fill=C_INK,
) -> None:
    """Dibuja 10⁻², 10³, etc. con superíndice real alineado a la derecha en right_x."""
    fb = font(size)
    fe = font(int(size * 0.72))
    bb_b = draw.textbbox((0, 0), base, font=fb)
    bb_e = draw.textbbox((0, 0), exp, font=fe)
    bw, bh = bb_b[2] - bb_b[0], bb_b[3] - bb_b[1]
    ew, eh = bb_e[2] - bb_e[0], bb_e[3] - bb_e[1]
    total_w = bw + ew + 2
    x0 = right_x - total_w
    y_b = center_y - bh // 2
    draw.text((x0, y_b), base, font=fb, fill=fill)
    draw.text((x0 + bw + 2, y_b - eh // 3), exp, font=fe, fill=fill)


def make_fig1_architecture(out_path: Path) -> None:
    """Figura 1: Arquitectura modular con diseño sobrio tipo diagrama académico."""
    W, H = 2200, 1140
    img = Image.new("RGB", (W, H), C_BG)
    d = ImageDraw.Draw(img)

    draw_centered_text(
        d, (40, 26, W - 40, 86),
        ["Arquitectura del Contador Combinatorio con Funciones Generadoras"],
        font(38, bold=True), fill=C_INK,
    )
    draw_centered_text(
        d, (40, 84, W - 40, 128),
        ["Pipeline de modelado simbólico, álgebra exacta de series formales truncadas y verificación cruzada"],
        font(24, italic=True), fill=C_MUTED,
    )
    d.line([(160, 146), (W - 160, 146)], fill=C_GRID, width=3)

    stages = [
        (
            (70, 200, 520, 470),
            C_SLATE,
            "1. Especificación",
            "VariableConstraint · CLI",
            [
                "• Rangos acotados [l, u]",
                "• Paridad y múltiplos de paso d",
                "• Monedas con inventario finito",
                "• Particiones y códigos (FGE)",
            ],
        ),
        (
            (600, 200, 1070, 470),
            C_CRIMSON,
            "2. Traductor Simbólico",
            "combinatorics_engine.py",
            [
                "• FGO polinómica por factor",
                "• Forma racional compacta",
                "• FGE en anillos racionales Q[[x]]",
                "• Cocientes de recurrencias P/Q",
            ],
        ),
        (
            (1150, 200, 1650, 470),
            C_TEAL,
            "3. Motor de Series Formales",
            "formal_series.py",
            [
                "• Operador racional en O(mN)",
                "• NTT + CRT (3 primos) O(N log N)",
                "• Karatsuba y Cauchy exactos",
                "• Inversión formal 1 / Q(x)",
            ],
        ),
        (
            (1730, 200, 2130, 470),
            C_SLATE,
            "4. Extracción y Salida",
            "CountResult",
            [
                "• Coeficiente exacto [xⁿ] G(x)",
                "• Conteo etiquetado n! [xⁿ] A(x)",
                "• Distribución completa 0 … n",
                "• Expresión simbólica trazable",
            ],
        ),
    ]

    for (x0, y0, x1, y1), accent, header, sub, lines in stages:
        d.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=C_BG, outline=accent, width=4)
        d.rectangle([x0 + 2, y0 + 2, x1 - 2, y0 + 14], fill=accent)
        d.text((x0 + 24, y0 + 28), header, font=font(27, bold=True), fill=accent)
        d.text((x0 + 24, y0 + 66), sub, font=font(20, mono=True), fill=C_MUTED)
        d.line([(x0 + 20, y0 + 102), (x1 - 20, y0 + 102)], fill=C_GRID, width=2)
        cy = y0 + 120
        for ln in lines:
            d.text((x0 + 22, cy), ln, font=font(22), fill=C_INK)
            cy += 36

    draw_arrow(d, (522, 335), (596, 335), color=C_AXIS, width=4, head=18)
    draw_arrow(d, (1072, 335), (1146, 335), color=C_AXIS, width=4, head=18)
    draw_arrow(d, (1652, 335), (1726, 335), color=C_AXIS, width=4, head=18)

    # Bloque inferior izquierdo: Validación cruzada
    vx0, vy0, vx1, vy1 = 120, 625, 1300, 1000
    d.rounded_rectangle([vx0, vy0, vx1, vy1], radius=14, fill=C_TINT_GRAY, outline=C_AXIS, width=3)
    d.rectangle([vx0 + 2, vy0 + 2, vx1 - 2, vy0 + 12], fill=C_CRIMSON)
    d.text((vx0 + 26, vy0 + 26), "5. Validación Cruzada Independiente  (validators.py · tests/)", font=font(25, bold=True), fill=C_INK)
    d.line([(vx0 + 22, vy0 + 68), (vx1 - 22, vy0 + 68)], fill=C_GRID, width=2)

    oracles = [
        ("Fuerza Bruta", ["Enumeración exacta", "de tuplas válidas", "(N pequeño)"]),
        ("Prog. Dinámica", ["Tabla DP iterativa", "ajena al anillo", "de series"]),
        ("Fórmulas Cerradas", ["Estrellas y barras", "Inclusión-Exclusión", "Teorema de Euler"]),
        ("Pruebas Unitarias", ["11 casos automáticos", "casos límite y", "Ejercicios 9–14"]),
    ]
    ox = vx0 + 26
    ow = 266
    for title, desc in oracles:
        d.rounded_rectangle([ox, vy0 + 92, ox + ow, vy1 - 26], radius=10, fill=C_BG, outline=C_GRID, width=3)
        draw_centered_text(d, (ox + 8, vy0 + 106, ox + ow - 8, vy0 + 148), [title], font(23, bold=True), fill=C_SLATE)
        draw_centered_text(d, (ox + 8, vy0 + 152, ox + ow - 8, vy1 - 38), desc, font(20), fill=C_INK, line_gap=8)
        ox += ow + 20

    # Bloque inferior derecho: Benchmarks
    bx0, by0, bx1, by1 = 1380, 625, 2080, 1000
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=14, fill=C_TINT_GRAY, outline=C_AXIS, width=3)
    d.rectangle([bx0 + 2, by0 + 2, bx1 - 2, by0 + 12], fill=C_TEAL)
    d.text((bx0 + 26, by0 + 26), "6. Evaluación Empírica  (benchmarks.py)", font=font(25, bold=True), fill=C_INK)
    d.line([(bx0 + 22, by0 + 68), (bx1 - 22, by0 + 68)], fill=C_GRID, width=2)
    b_lines = [
        "• Medición de complejidad temporal real",
        "  (fuerza bruta, DP, Cauchy, Karatsuba, NTT)",
        "• Verificación de error nulo (exactitud 100 %)",
        "• Contraste asintótico con Hardy-Ramanujan",
        "• Registro reproducible en JSON y gráficas",
    ]
    cy = by0 + 96
    for bl in b_lines:
        d.text((bx0 + 28, cy), bl, font=font(22), fill=C_INK)
        cy += 48

    draw_arrow(d, (295, 472), (295, 620), color=C_AXIS, width=4, head=18)
    d.text((312, 530), "Entrada idéntica", font=font(21, italic=True), fill=C_MUTED)

    d.line([(1930, 472), (1930, 548), (940, 548)], fill=C_AXIS, width=4)
    draw_arrow(d, (940, 548), (940, 620), color=C_AXIS, width=4, head=18)
    draw_arrow(d, (1730, 548), (1730, 620), color=C_AXIS, width=4, head=18)
    d.text((1110, 512), "Verificación exacta: coeficiente FGO/FGE = Oráculo", font=font(21, italic=True), fill=C_SLATE)

    d.text(
        (70, H - 52),
        "Fuente: Elaboración propia. Implementación íntegra en Python 3.12 estándar sin dependencias externas.",
        font=font(20, italic=True), fill=C_MUTED,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W // 2, H // 2), Image.Resampling.LANCZOS).save(out_path, dpi=(300, 300))


def make_fig2_cluster_distribution(data: dict, out_path: Path) -> None:
    """Figura 2: Distribución de configuraciones del clúster de 5 servidores."""
    W, H = 2100, 1080
    img = Image.new("RGB", (W, H), C_BG)
    d = ImageDraw.Draw(img)

    info = data["exp3_cluster_distribution"]
    coeffs: List[int] = info["restricted_coeffs"]
    max_n = info["max_n"]
    peak_v = info["peak_value"]

    draw_centered_text(
        d, (40, 22, W - 40, 82),
        ["Distribución Exacta de Configuraciones Válidas: Clúster de 5 Servidores"],
        font(35, bold=True), fill=C_INK,
    )
    draw_centered_text(
        d, (40, 82, W - 40, 126),
        ["S₁ ∈ [1, 8],  S₂ par ∈ [0, 10],  S₃ impar ∈ [1, 9],  S₄ múltiplo de 3 ∈ [0, 12],  S₅ ∈ [2, 6]   |   Total G(1) = 6,000"],
        font(23, italic=True), fill=C_MUTED,
    )

    px0, py0, px1, py1 = 175, 170, W - 95, H - 165
    pw, ph = px1 - px0, py1 - py0
    ymax = 440

    for val in range(0, 401, 50):
        y = py1 - int(val / ymax * ph)
        d.line([(px0, y), (px1, y)], fill=C_GRID, width=2)
        lbl = str(val)
        bb = d.textbbox((0, 0), lbl, font=font(23))
        d.text((px0 - 18 - (bb[2] - bb[0]), y - (bb[3] - bb[1]) // 2), lbl, font=font(23), fill=C_INK)

    n_bars = max_n + 1
    slot_w = pw / n_bars
    bar_w = max(8, int(slot_w * 0.70))
    for k, c in enumerate(coeffs):
        cx = px0 + int((k + 0.5) * slot_w)
        bh = int(c / ymax * ph)
        x0, x1, y0 = cx - bar_w // 2, cx + bar_w // 2, py1 - bh
        color = C_CRIMSON if c == peak_v else C_SLATE
        if bh > 0:
            d.rectangle([x0, y0, x1, py1], fill=color)
        if k % 5 == 0 or k == max_n:
            lbl = str(k)
            bb = d.textbbox((0, 0), lbl, font=font(22))
            d.text((cx - (bb[2] - bb[0]) // 2, py1 + 14), lbl, font=font(22), fill=C_INK)
            d.line([(cx, py1), (cx, py1 + 7)], fill=C_AXIS, width=3)

    d.line([(px0, py0), (px0, py1), (px1, py1)], fill=C_AXIS, width=3)

    # Anotación del máximo simétrico (limpia, sin solapar barras)
    peak_x = px0 + int((24.5 + 0.5) * slot_w)
    peak_y = py1 - int(peak_v / ymax * ph)
    d.rounded_rectangle([peak_x + 215, py0 + 14, px1 - 15, py0 + 158], radius=10, fill=C_TINT_CRIMSON, outline=C_CRIMSON, width=2)
    d.text((peak_x + 238, py0 + 30), "Máximo simétrico (unimodal)", font=font(23, bold=True), fill=C_CRIMSON)
    d.text((peak_x + 238, py0 + 68), "n = 24 y n = 25: 339 formas", font=font(22), fill=C_INK)
    d.text((peak_x + 238, py0 + 104), "Soporte factible: n ∈ [4, 45]", font=font(22), fill=C_INK)
    draw_arrow(d, (peak_x + 215, py0 + 82), (peak_x + 18, peak_y - 2), color=C_CRIMSON, width=3, head=14)

    # Anotación desplazamiento mínimo
    z_x = px0 + int(2 * slot_w)
    d.rounded_rectangle([px0 + 28, py0 + 14, px0 + 505, py0 + 132], radius=10, fill=C_TINT_SLATE, outline=C_SLATE, width=2)
    d.text((px0 + 50, py0 + 30), "Desplazamiento mínimo (factor x⁴)", font=font(23, bold=True), fill=C_SLATE)
    d.text((px0 + 50, py0 + 70), "Para n < 4 no existen soluciones válidas", font=font(22), fill=C_INK)
    draw_arrow(d, (px0 + 140, py0 + 132), (z_x, py1 - 12), color=C_SLATE, width=3, head=14)

    draw_centered_text(d, (px0, py1 + 56, px1, py1 + 102), ["Carga total de tareas asignadas (n)"], font(25, bold=True), fill=C_INK)

    y_lbl_img = Image.new("RGBA", (620, 60), (255, 255, 255, 0))
    yd = ImageDraw.Draw(y_lbl_img)
    draw_centered_text(yd, (0, 0, 620, 60), ["Número exacto de configuraciones [xⁿ] G(x)"], font(25, bold=True), fill=C_INK)
    y_rot = y_lbl_img.rotate(90, expand=True)
    img.paste(y_rot, (28, py0 + (ph - 620) // 2), y_rot)

    d.text(
        (px0, H - 46),
        "Fuente: Resultados experimentales del motor formal_series.py contrastados al 100 % con DP y fuerza bruta.",
        font=font(20, italic=True), fill=C_MUTED,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W // 2, H // 2), Image.Resampling.LANCZOS).save(out_path, dpi=(300, 300))


def _plot_log_series(
    d: ImageDraw.ImageDraw,
    rect: Tuple[int, int, int, int],
    series_list: Sequence[Tuple[str, Sequence[Tuple[float, float]], Tuple[int, int, int], str]],
    x_ticks: Sequence[float],
    y_exps: Sequence[int],
    x_label: str,
    y_label: str,
    title: str,
    legend_pos: str = "top_left",
) -> None:
    px0, py0, px1, py1 = rect
    pw, ph = px1 - px0, py1 - py0
    draw_centered_text(d, (px0, py0 - 58, px1, py0 - 10), [title], font(26, bold=True), fill=C_INK)

    xmin, xmax = min(x_ticks), max(x_ticks)
    ymin_e, ymax_e = min(y_exps), max(y_exps)

    def map_x(v: float) -> int:
        t = (math.log10(v) - math.log10(xmin)) / (math.log10(xmax) - math.log10(xmin))
        return px0 + int(t * pw)

    def map_y(v: float) -> int:
        lv = math.log10(max(v, 10**ymin_e))
        t = (lv - ymin_e) / (ymax_e - ymin_e)
        return py1 - int(t * ph)

    for e in y_exps:
        y = map_y(10**e)
        d.line([(px0, y), (px1, y)], fill=C_GRID, width=2)
        if 0 <= e <= 2:
            lbl = str(int(10**e))
            bb = d.textbbox((0, 0), lbl, font=font(21))
            d.text((px0 - 14 - (bb[2] - bb[0]), y - (bb[3] - bb[1]) // 2), lbl, font=font(21), fill=C_INK)
        else:
            draw_power_label(d, px0 - 14, y, "10", str(e).replace("-", "−"), size=21, fill=C_INK)

    for xv in x_ticks:
        x = map_x(xv)
        d.line([(x, py0), (x, py1)], fill=C_GRID, width=2)
        lbl = str(int(xv))
        bb = d.textbbox((0, 0), lbl, font=font(21))
        d.text((x - (bb[2] - bb[0]) // 2, py1 + 12), lbl, font=font(21), fill=C_INK)

    d.line([(px0, py0), (px0, py1), (px1, py1)], fill=C_AXIS, width=3)

    for name, pts, col, marker in series_list:
        mapped = [(map_x(x), map_y(y)) for x, y in pts]
        if len(mapped) >= 2:
            d.line(mapped, fill=col, width=4)
        for mx, my in mapped:
            r = 7
            if marker == "circle":
                d.ellipse([mx - r, my - r, mx + r, my + r], fill=col, outline=C_BG, width=2)
            elif marker == "square":
                d.rectangle([mx - r, my - r, mx + r, my + r], fill=col, outline=C_BG, width=2)
            elif marker == "diamond":
                d.polygon([(mx, my - r - 2), (mx + r + 2, my), (mx, my + r + 2), (mx - r - 2, my)], fill=col, outline=C_BG)
            else:
                d.polygon([(mx, my - r - 2), (mx + r + 2, my + r), (mx - r - 2, my + r)], fill=col, outline=C_BG)

    lw = 370
    lh = 24 + len(series_list) * 34
    lx0, ly0 = (px1 - lw - 18, py1 - lh - 18) if legend_pos == "bottom_right" else (px0 + 20, py0 + 18)
    d.rounded_rectangle([lx0, ly0, lx0 + lw, ly0 + lh], radius=8, fill=C_BG, outline=C_GRID, width=2)
    cy = ly0 + 14
    for name, _, col, _ in series_list:
        d.line([(lx0 + 14, cy + 12), (lx0 + 50, cy + 12)], fill=col, width=4)
        d.ellipse([lx0 + 27, cy + 6, lx0 + 38, cy + 17], fill=col)
        d.text((lx0 + 62, cy), name, font=font(19, bold=True), fill=C_INK)
        cy += 34

    draw_centered_text(d, (px0, py1 + 48, px1, py1 + 90), [x_label], font(22, bold=True), fill=C_INK)
    d.text((px0 - 52, py0 - 28), y_label, font=font(20, italic=True), fill=C_MUTED)


def make_fig3_scalability(data: dict, out_path: Path) -> None:
    """Figura 3: Escalabilidad empírica en escala log-log."""
    W, H = 2200, 1060
    img = Image.new("RGB", (W, H), C_BG)
    d = ImageDraw.Draw(img)

    draw_centered_text(
        d, (40, 18, W - 40, 78),
        ["Análisis Empírico de Complejidad y Escalabilidad Temporal (Python 3.12)"],
        font(34, bold=True), fill=C_INK,
    )

    rows2 = data["exp2_scalability_methods"]
    _plot_log_series(
        d,
        rect=(135, 185, 1055, H - 150),
        series_list=[
            ("Fuerza bruta (N ≤ 34)", [(r["N"], r["brute_force_ms"]) for r in rows2 if r["brute_force_ms"] is not None], C_CRIMSON, "diamond"),
            ("Prog. Dinámica  O(m N u)", [(r["N"], r["dp_ms"]) for r in rows2], C_AMBER, "square"),
            ("FGO Clásica  O(m N²)", [(r["N"], r["ogf_schoolbook_ms"]) for r in rows2], C_PLUM, "triangle"),
            ("FGO NTT+CRT  O(m N log N)", [(r["N"], r["ogf_ntt_ms"]) for r in rows2], C_SLATE, "circle"),
            ("FGO Racional  O(m N)", [(r["N"], r["ogf_structured_ms"]) for r in rows2], C_TEAL, "circle"),
        ],
        x_ticks=[10, 20, 50, 100, 250, 500, 1000],
        y_exps=[-2, -1, 0, 1, 2],
        x_label="Suma objetivo N  (m = 6 variables, cota u = máx(6, N/3))",
        y_label="Tiempo (ms)",
        title="A) Conteo restringido: FGO frente a DP y Fuerza Bruta",
        legend_pos="bottom_right",
    )

    rows1 = data["exp1_series_multiplication"]
    _plot_log_series(
        d,
        rect=(1210, 185, W - 75, H - 150),
        series_list=[
            ("Cauchy clásica  O(N²)", [(r["N"], r["schoolbook_ms"]) for r in rows1], C_CRIMSON, "square"),
            ("NTT + CRT (3 primos)  O(N log N)", [(r["N"], r["ntt_ms"]) for r in rows1], C_SLATE, "circle"),
            ("Karatsuba  O(N¹·⁵⁸⁵)", [(r["N"], r["karatsuba_ms"]) for r in rows1], C_TEAL, "diamond"),
        ],
        x_ticks=[64, 128, 256, 512, 1024, 2048, 4096],
        y_exps=[-2, -1, 0, 1, 2, 3],
        x_label="Grado máximo de las series formales (N)",
        y_label="Tiempo (ms)",
        title="B) Multiplicación exacta de dos series densas en Z[[x]]",
        legend_pos="top_left",
    )

    d.text(
        (135, H - 44),
        "Fuente: Mediciones reproducibles registradas en results/benchmark_results.json (ambos paneles en escala logarítmica).",
        font=font(20, italic=True), fill=C_MUTED,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W // 2, H // 2), Image.Resampling.LANCZOS).save(out_path, dpi=(300, 300))


def make_fig4_partitions(data: dict, out_path: Path) -> None:
    """Figura 4: Particiones de Euler y aproximación de Hardy-Ramanujan."""
    W, H = 2100, 1040
    img = Image.new("RGB", (W, H), C_BG)
    d = ImageDraw.Draw(img)

    rows = [r for r in data["exp4_euler_partitions"] if r["n"] >= 1]
    draw_centered_text(
        d, (40, 20, W - 40, 80),
        ["Particiones de Enteros mediante Productos de Euler (n = 1 a 60)"],
        font(35, bold=True), fill=C_INK,
    )
    draw_centered_text(
        d, (40, 80, W - 40, 124),
        ["Verificación empírica exacta del Teorema de Euler y contraste con la fórmula asintótica de Hardy-Ramanujan"],
        font(23, italic=True), fill=C_MUTED,
    )

    px0, py0, px1, py1 = 175, 165, W - 90, H - 160
    pw, ph = px1 - px0, py1 - py0
    ymin_e, ymax_e = 0, 6

    def mx(n: float) -> int:
        return px0 + int((n - 1) / 59.0 * pw)

    def my(v: float) -> int:
        lv = math.log10(max(v, 1.0))
        return py1 - int((lv - ymin_e) / (ymax_e - ymin_e) * ph)

    for e in range(ymin_e, ymax_e + 1):
        y = my(10**e)
        d.line([(px0, y), (px1, y)], fill=C_GRID, width=2)
        draw_power_label(d, px0 - 16, y, "10", str(e), size=22, fill=C_INK)

    for xv in [1, 10, 20, 30, 40, 50, 60]:
        x = mx(xv)
        d.line([(x, py0), (x, py1)], fill=C_GRID, width=2)
        lbl = str(xv)
        bb = d.textbbox((0, 0), lbl, font=font(22))
        d.text((x - (bb[2] - bb[0]) // 2, py1 + 14), lbl, font=font(22), fill=C_INK)

    d.line([(px0, py0), (px0, py1), (px1, py1)], fill=C_AXIS, width=3)

    pts_p = [(mx(r["n"]), my(r["p_n"])) for r in rows]
    pts_hr = [(mx(r["n"]), my(r["hardy_ramanujan"])) for r in rows]
    pts_dist = [(mx(r["n"]), my(r["p_distinct"])) for r in rows]

    for i in range(0, len(pts_hr) - 1, 2):
        d.line([pts_hr[i], pts_hr[i + 1]], fill=C_AMBER, width=4)

    d.line(pts_p, fill=C_SLATE, width=5)
    d.line(pts_dist, fill=C_TEAL, width=5)

    for r in rows:
        if r["n"] % 5 == 0:
            x, y_d = mx(r["n"]), my(r["p_distinct"])
            d.ellipse([x - 7, y_d - 7, x + 7, y_d + 7], fill=C_CRIMSON, outline=C_BG, width=2)
            x, y_p = mx(r["n"]), my(r["p_n"])
            d.ellipse([x - 6, y_p - 6, x + 6, y_p + 6], fill=C_SLATE, outline=C_BG, width=2)

    lx0, ly0 = px0 + 30, py0 + 24
    d.rounded_rectangle([lx0, ly0, lx0 + 670, ly0 + 186], radius=10, fill=C_BG, outline=C_GRID, width=2)
    items = [
        ("p(n) exacto vía FGO de Euler", C_SLATE, False),
        ("Asintótica Hardy-Ramanujan (error 5.95 % en n = 60)", C_AMBER, True),
        ("Particiones en partes distintas  [curva continua]", C_TEAL, False),
        ("Particiones en partes impares  [puntos superpuestos]", C_CRIMSON, False),
    ]
    cy = ly0 + 18
    for txt, col, dashed in items:
        if dashed:
            d.line([(lx0 + 18, cy + 13), (lx0 + 34, cy + 13)], fill=col, width=4)
            d.line([(lx0 + 42, cy + 13), (lx0 + 58, cy + 13)], fill=col, width=4)
        else:
            d.line([(lx0 + 18, cy + 13), (lx0 + 58, cy + 13)], fill=col, width=5)
        d.text((lx0 + 74, cy), txt, font=font(21, bold=True), fill=C_INK)
        cy += 40

    r60 = rows[-1]
    bx0, by0 = px1 - 545, py1 - 182
    d.rounded_rectangle([bx0, by0, px1 - 24, py1 - 24], radius=10, fill=C_TINT_TEAL, outline=C_TEAL, width=2)
    d.text((bx0 + 22, by0 + 18), "Valores exactos en n = 60", font=font(22, bold=True), fill=C_TEAL)
    d.text((bx0 + 22, by0 + 56), f"p(60) = {r60['p_n']:,}   (HR: {r60['hardy_ramanujan']:,.0f})", font=font(21), fill=C_INK)
    d.text((bx0 + 22, by0 + 92), f"Distintas = Impares = {r60['p_distinct']:,}", font=font(21), fill=C_INK)
    d.text((bx0 + 22, by0 + 128), "Identidad verificada en 61 / 61 casos", font=font(20, italic=True), fill=C_SLATE)

    draw_centered_text(d, (px0, py1 + 56, px1, py1 + 100), ["Entero particionado (n)"], font(25, bold=True), fill=C_INK)

    y_lbl_img = Image.new("RGBA", (540, 60), (255, 255, 255, 0))
    yd = ImageDraw.Draw(y_lbl_img)
    draw_centered_text(yd, (0, 0, 540, 60), ["Número de particiones (escala logarítmica)"], font(25, bold=True), fill=C_INK)
    y_rot = y_lbl_img.rotate(90, expand=True)
    img.paste(y_rot, (28, py0 + (ph - 540) // 2), y_rot)

    d.text(
        (px0, H - 44),
        "Fuente: Cálculo exacto mediante formal_series.py sobre el anillo truncado de series formales.",
        font=font(20, italic=True), fill=C_MUTED,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.resize((W // 2, H // 2), Image.Resampling.LANCZOS).save(out_path, dpi=(300, 300))


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    data = json.loads((root / "results" / "benchmark_results.json").read_text(encoding="utf-8"))
    fig_dir = root / "docs" / "figures"

    make_fig1_architecture(fig_dir / "fig1_arquitectura.png")
    make_fig2_cluster_distribution(data, fig_dir / "fig2_distribucion_cluster.png")
    make_fig3_scalability(data, fig_dir / "fig3_escalabilidad.png")
    make_fig4_partitions(data, fig_dir / "fig4_particiones_euler.png")
    print(f"4 figuras editoriales generadas en {fig_dir}")


if __name__ == "__main__":
    main()
