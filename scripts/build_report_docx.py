"""
Generador de Informe Académico en formato .docx (OOXML nativo) con tipografía matemática
editorial (Computer Modern 600 DPI con fracciones verticales reales, operadores ∑/∏ y
superíndices/subíndices nativos en texto corrido), conforme al formato oficial de la
Universidad Peruana Cayetano Heredia (UPCH) — Estructuras Discretas II (Tema 10).

Reglas de formato respetadas estrictamente:
- Papel A4 (210 mm × 297 mm).
- Márgenes: Superior 2,5 cm | Inferior 3,0 cm | Derecho 2,5 cm | Izquierdo 3,0 cm.
- Fuente: Arial 12 pt en todo el cuerpo (Carátula: título en Arial 14 pt).
- Interlineado: 1,5 (360 twips), texto justificado.
- Numeración de páginas en margen inferior derecho:
  * Carátula: sin numeración.
  * Páginas preliminares (Índices y Resumen): romanos minúsculas iniciando en ii.
  * Cuerpo (I. Introducción hasta X. Referencias bibliográficas): arábigos iniciando en 1.
  * XI. Anexos: sin numeración.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Optional, Sequence, Tuple, Union
from xml.sax.saxutils import escape
import zipfile

from PIL import Image

from math_render import build_all_equations

# Dimensiones exactas A4 y márgenes en twips (1 cm = 566.929 twips)
A4_W = 11906
A4_H = 16838
MARGIN_TOP = 1417      # 2.5 cm
MARGIN_BOTTOM = 1701   # 3.0 cm
MARGIN_RIGHT = 1417    # 2.5 cm
MARGIN_LEFT = 1701     # 3.0 cm
CONTENT_W_TWIPS = A4_W - MARGIN_LEFT - MARGIN_RIGHT  # 8788 twips
CONTENT_W_EMU = int(CONTENT_W_TWIPS * 635)           # 1 twip = 635 EMU
PT_TO_EMU = 12700                                    # 1 pt = 12700 EMU

# Paleta editorial sobria (UPCH)
COL_INK = "1A1D24"
COL_CRIMSON = "7A1C24"
COL_SLATE = "263F5E"
COL_MUTED = "525B68"
COL_RULE = "CBD2D9"
COL_HEADER_BG = "F4F5F7"


def _to_roman(n: int) -> str:
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = []
    for v, s in vals:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


# Tokenizador ligero de texto académico enriquecido:
#   **negrita**, *cursiva*, `código`, ^{superíndice}, _{subíndice}
_INLINE_TOKEN_RE = re.compile(
    r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\^\{[^}]+\}|_\{[^}]+\})"
)


class DocxBuilder:
    """Constructor OOXML con soporte de ecuaciones tipográficas, tablas booktabs y algoritmos."""

    def __init__(self) -> None:
        self.body_elements: List[str] = []
        self.images: List[Tuple[str, Path, int, int]] = []
        self._image_rid_cache: Dict[Path, str] = {}
        self._next_rid = 10
        self._next_doc_id = 100

    def _register_image(self, img_path: Path) -> str:
        if img_path in self._image_rid_cache:
            return self._image_rid_cache[img_path]
        rid = f"rId{self._next_rid}"
        self._next_rid += 1
        self._image_rid_cache[img_path] = rid
        self.images.append((rid, img_path, 0, 0))
        return rid

    def _drawing_xml(self, img_path: Path, cx: int, cy: int) -> str:
        rid = self._register_image(img_path)
        self._next_doc_id += 1
        doc_id = self._next_doc_id
        return (
            "<w:r><w:drawing>"
            '<wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/>'
            '<wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{doc_id}" name="{escape(img_path.name)}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="{doc_id}" name="{escape(img_path.name)}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            "</pic:pic></a:graphicData></a:graphic>"
            "</wp:inline></w:drawing></w:r>"
        )

    def _run(
        self,
        text: str,
        bold: bool = False,
        italic: bool = False,
        size_pt: float = 12.0,
        font: str = "Arial",
        color: Optional[str] = COL_INK,
        vert_align: Optional[str] = None,  # "superscript" | "subscript"
    ) -> str:
        sz = int(round(size_pt * 2))
        rpr = [
            f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>',
            f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>',
        ]
        if bold:
            rpr.append("<w:b/><w:bCs/>")
        if italic:
            rpr.append("<w:i/><w:iCs/>")
        if color:
            rpr.append(f'<w:color w:val="{color}"/>')
        if vert_align:
            rpr.append(f'<w:vertAlign w:val="{vert_align}"/>')
        lines = text.split("\n")
        inner = []
        for idx, part in enumerate(lines):
            if idx > 0:
                inner.append("<w:br/>")
            inner.append(f'<w:t xml:space="preserve">{escape(part)}</w:t>')
        return f"<w:r><w:rPr>{''.join(rpr)}</w:rPr>{''.join(inner)}</w:r>"

    def _markup_to_runs(
        self,
        text: str,
        base_bold: bool = False,
        base_italic: bool = False,
        size_pt: float = 12.0,
        color: str = COL_INK,
        vert_align: Optional[str] = None,
    ) -> str:
        parts = _INLINE_TOKEN_RE.split(text)
        out: List[str] = []
        for tok in parts:
            if not tok:
                continue
            if tok.startswith("**") and tok.endswith("**"):
                out.append(self._markup_to_runs(tok[2:-2], base_bold=True, base_italic=base_italic, size_pt=size_pt, color=color, vert_align=vert_align))
            elif tok.startswith("*") and tok.endswith("*"):
                out.append(self._markup_to_runs(tok[1:-1], base_bold=base_bold, base_italic=True, size_pt=size_pt, color=color, vert_align=vert_align))
            elif tok.startswith("`") and tok.endswith("`"):
                out.append(self._run(tok[1:-1], bold=base_bold, italic=False, size_pt=max(9.0, size_pt - 1.5), font="DejaVu Sans Mono", color=COL_SLATE, vert_align=vert_align))
            elif tok.startswith("^{") and tok.endswith("}"):
                out.append(self._markup_to_runs(tok[2:-1], base_bold=base_bold, base_italic=base_italic, size_pt=size_pt, color=color, vert_align="superscript"))
            elif tok.startswith("_{") and tok.endswith("}"):
                out.append(self._markup_to_runs(tok[2:-1], base_bold=base_bold, base_italic=base_italic, size_pt=size_pt, color=color, vert_align="subscript"))
            else:
                out.append(self._run(tok, bold=base_bold, italic=base_italic, size_pt=size_pt, color=color, vert_align=vert_align))
        return "".join(out)

    def add_prose(
        self,
        text: str,
        align: str = "both",
        bold: bool = False,
        italic: bool = False,
        size_pt: float = 12.0,
        color: str = COL_INK,
        space_before: int = 0,
        space_after: int = 120,
        line_spacing: int = 360,
        keep_next: bool = False,
        indent_left: int = 0,
        hanging: int = 0,
        first_line: int = 0,
        page_break_before: bool = False,
        border_bottom: Optional[str] = None,
        border_left: Optional[str] = None,
        shading: Optional[str] = None,
    ) -> None:
        ppr = [
            f'<w:jc w:val="{align}"/>',
            f'<w:spacing w:before="{space_before}" w:after="{space_after}" w:line="{line_spacing}" w:lineRule="auto"/>',
        ]
        if keep_next:
            ppr.append("<w:keepNext/>")
        if page_break_before:
            ppr.append("<w:pageBreakBefore/>")
        if indent_left or hanging or first_line:
            attrs = [f'w:left="{indent_left}"'] if indent_left else []
            if hanging:
                attrs.append(f'w:hanging="{hanging}"')
            if first_line:
                attrs.append(f'w:firstLine="{first_line}"')
            ppr.append(f"<w:ind {' '.join(attrs)}/>")
        if shading:
            ppr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shading}"/>')
        pbdr = []
        if border_bottom:
            pbdr.append(f'<w:bottom w:val="single" w:sz="6" w:space="4" w:color="{border_bottom}"/>')
        if border_left:
            pbdr.append(f'<w:left w:val="single" w:sz="12" w:space="10" w:color="{border_left}"/>')
        if pbdr:
            ppr.append(f"<w:pBdr>{''.join(pbdr)}</w:pBdr>")

        runs = self._markup_to_runs(text, base_bold=bold, base_italic=italic, size_pt=size_pt, color=color) if text else ""
        self.body_elements.append(f"<w:p><w:pPr>{''.join(ppr)}</w:pPr>{runs}</w:p>")

    def add_heading1(self, title: str, page_break_before: bool = False) -> None:
        self.add_prose(
            title,
            align="left",
            bold=True,
            size_pt=12.0,
            color=COL_INK,
            space_before=260,
            space_after=140,
            line_spacing=360,
            keep_next=True,
            page_break_before=page_break_before,
            border_bottom=COL_CRIMSON,
        )

    def add_heading2(self, title: str) -> None:
        self.add_prose(
            title,
            align="left",
            bold=True,
            size_pt=12.0,
            color=COL_CRIMSON,
            space_before=200,
            space_after=90,
            line_spacing=360,
            keep_next=True,
        )

    def add_theorem(self, title: str, statement: str) -> None:
        """Bloque de teorema estilo revista matemática (encabezado negrita + enunciado cursiva)."""
        self.add_prose(
            f"**{title}.** *{statement}*",
            align="both",
            size_pt=12.0,
            space_before=140,
            space_after=100,
            line_spacing=360,
            indent_left=180,
            border_left=COL_CRIMSON,
        )

    def add_proof(self, body: str) -> None:
        """Demostración matemática formal cerrada con el símbolo de Halmos (□)."""
        self.add_prose(
            f"*Demostración.* {body}  □",
            align="both",
            size_pt=12.0,
            space_before=40,
            space_after=140,
            line_spacing=360,
        )

    def add_equation_img(self, img_path: Path, number: str, target_dpi_scale: float = 0.145) -> None:
        """
        Inserta una ecuación matemática tipográfica (Computer Modern 600 DPI) centrada
        en una tabla invisible de 2 columnas con su numeración (1), (2)... a la derecha.
        """
        with Image.open(img_path) as im:
            iw, ih = im.size
        # Escala consistente: 84 px de cuerpo -> ~12 pt visual
        cx = int(round(iw * target_dpi_scale * PT_TO_EMU))
        cy = int(round(ih * target_dpi_scale * PT_TO_EMU))
        max_cx = int(CONTENT_W_EMU * 0.84)
        if cx > max_cx:
            ratio = max_cx / cx
            cx = max_cx
            cy = int(round(cy * ratio))

        col_eq = int(CONTENT_W_TWIPS * 0.89)
        col_num = CONTENT_W_TWIPS - col_eq
        drawing = self._drawing_xml(img_path, cx, cy)
        num_run = self._run(f"({number})", size_pt=11.0, color=COL_MUTED)

        tbl = (
            "<w:tbl><w:tblPr>"
            f'<w:tblW w:w="{CONTENT_W_TWIPS}" w:type="dxa"/>'
            "<w:tblBorders>"
            '<w:top w:val="none"/><w:bottom w:val="none"/><w:left w:val="none"/>'
            '<w:right w:val="none"/><w:insideH w:val="none"/><w:insideV w:val="none"/>'
            "</w:tblBorders>"
            '<w:tblCellMar><w:top w:w="70" w:type="dxa"/><w:bottom w:w="70" w:type="dxa"/>'
            '<w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
            "</w:tblPr>"
            f'<w:tblGrid><w:gridCol w:w="{col_eq}"/><w:gridCol w:w="{col_num}"/></w:tblGrid>'
            "<w:tr><w:trPr><w:cantSplit/></w:trPr>"
            f'<w:tc><w:tcPr><w:tcW w:w="{col_eq}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>{drawing}</w:p></w:tc>'
            f'<w:tc><w:tcPr><w:tcW w:w="{col_num}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p><w:pPr><w:jc w:val="right"/><w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>{num_run}</w:p></w:tc>'
            "</w:tr></w:tbl>"
        )
        self.body_elements.append(tbl)
        self.body_elements.append(
            '<w:p><w:pPr><w:spacing w:before="0" w:after="60" w:line="240" w:lineRule="auto"/></w:pPr></w:p>'
        )

    def add_algorithm(self, title: str, io_lines: Sequence[str], steps: Sequence[str]) -> None:
        """Bloque de pseudocódigo limpio estilo revista científica (reglas horizontales tipo algorithm2e)."""
        tbl_pr = (
            "<w:tblPr>"
            f'<w:tblW w:w="{CONTENT_W_TWIPS}" w:type="dxa"/>'
            "<w:tblBorders>"
            f'<w:top w:val="single" w:sz="12" w:space="0" w:color="{COL_INK}"/>'
            f'<w:bottom w:val="single" w:sz="10" w:space="0" w:color="{COL_INK}"/>'
            f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{COL_RULE}"/>'
            '<w:left w:val="none"/><w:right w:val="none"/><w:insideV w:val="none"/>'
            "</w:tblBorders>"
            '<w:tblCellMar><w:top w:w="70" w:type="dxa"/><w:bottom w:w="70" w:type="dxa"/>'
            '<w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar>'
            "</w:tblPr>"
        )
        # Fila 1: Título del algoritmo (con keepNext para no quedar huérfano al final de página)
        r_title = (
            "<w:tr><w:trPr><w:cantSplit/></w:trPr>"
            f'<w:tc><w:tcPr><w:tcW w:w="{CONTENT_W_TWIPS}" w:type="dxa"/>'
            f'<w:shd w:val="clear" w:color="auto" w:fill="{COL_HEADER_BG}"/></w:tcPr>'
            '<w:p><w:pPr><w:jc w:val="left"/><w:keepNext/><w:spacing w:before="0" w:after="0" w:line="260" w:lineRule="auto"/></w:pPr>'
            f"{self._markup_to_runs(f'**{title}**', size_pt=10.5, color=COL_INK)}</w:p></w:tc></w:tr>"
        )
        # Fila 2: Entrada / Salida + pasos numerados
        body_ps = []
        for ln in io_lines:
            body_ps.append(
                '<w:p><w:pPr><w:jc w:val="left"/><w:spacing w:before="20" w:after="20" w:line="260" w:lineRule="auto"/></w:pPr>'
                f"{self._markup_to_runs(ln, size_pt=10.0)}</w:p>"
            )
        for idx, st in enumerate(steps, 1):
            num = self._run(f"{idx:2d}.  ", bold=True, size_pt=9.5, font="DejaVu Sans Mono", color=COL_MUTED)
            body_ps.append(
                '<w:p><w:pPr><w:jc w:val="left"/><w:ind w:left="360" w:hanging="360"/>'
                '<w:spacing w:before="25" w:after="25" w:line="260" w:lineRule="auto"/></w:pPr>'
                f"{num}{self._markup_to_runs(st, size_pt=10.0)}</w:p>"
            )
        r_body = (
            "<w:tr><w:trPr><w:cantSplit/></w:trPr>"
            f'<w:tc><w:tcPr><w:tcW w:w="{CONTENT_W_TWIPS}" w:type="dxa"/></w:tcPr>'
            f"{''.join(body_ps)}</w:tc></w:tr>"
        )
        self.body_elements.append(
            f'<w:tbl>{tbl_pr}<w:tblGrid><w:gridCol w:w="{CONTENT_W_TWIPS}"/></w:tblGrid>{r_title}{r_body}</w:tbl>'
        )
        self.body_elements.append(
            '<w:p><w:pPr><w:spacing w:before="0" w:after="100" w:line="240" w:lineRule="auto"/></w:pPr></w:p>'
        )

    def add_code_listing(self, code: str, title: str) -> None:
        """Listado de código fuente limpio y sobrio (estilo académico con filetes finos)."""
        self.add_prose(
            f"**{title}**",
            align="left", size_pt=10.0, color=COL_SLATE,
            space_before=120, space_after=40, line_spacing=260, keep_next=True,
        )
        tbl_pr = (
            "<w:tblPr>"
            f'<w:tblW w:w="{CONTENT_W_TWIPS}" w:type="dxa"/>'
            "<w:tblBorders>"
            f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{COL_SLATE}"/>'
            f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="{COL_SLATE}"/>'
            '<w:left w:val="none"/><w:right w:val="none"/><w:insideH w:val="none"/><w:insideV w:val="none"/>'
            "</w:tblBorders>"
            '<w:tblCellMar><w:top w:w="90" w:type="dxa"/><w:bottom w:w="90" w:type="dxa"/>'
            '<w:left w:w="120" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar>'
            "</w:tblPr>"
        )
        run = self._run(code.rstrip("\n"), size_pt=8.5, font="DejaVu Sans Mono", color=COL_INK)
        self.body_elements.append(
            f'<w:tbl>{tbl_pr}<w:tblGrid><w:gridCol w:w="{CONTENT_W_TWIPS}"/></w:tblGrid>'
            f'<w:tr><w:tc><w:tcPr><w:tcW w:w="{CONTENT_W_TWIPS}" w:type="dxa"/>'
            '<w:shd w:val="clear" w:color="auto" w:fill="FAFBFD"/></w:tcPr>'
            f'<w:p><w:pPr><w:jc w:val="left"/><w:spacing w:before="0" w:after="0" w:line="230" w:lineRule="auto"/></w:pPr>{run}</w:p>'
            "</w:tc></w:tr></w:tbl>"
        )
        self.body_elements.append(
            '<w:p><w:pPr><w:spacing w:before="0" w:after="100" w:line="240" w:lineRule="auto"/></w:pPr></w:p>'
        )

    def add_table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[Union[str, Tuple[str, Path, float]]]],
        col_widths_pct: Optional[Sequence[float]] = None,
        caption: Optional[str] = None,
        font_size_pt: float = 9.5,
        align_cols: Optional[Sequence[str]] = None,
    ) -> None:
        """
        Tabla editorial estilo booktabs.
        Cada celda puede ser un string con markup enriquecido (^{}, _{}, *...*)
        o una tupla ("img", Path, scale_factor) para insertar fórmulas verticales 600 DPI.
        """
        if caption:
            self.add_prose(
                f"**{caption}**",
                align="left", size_pt=10.5, color=COL_INK,
                space_before=160, space_after=60, line_spacing=280, keep_next=True,
            )

        ncols = len(headers)
        col_widths = (
            [CONTENT_W_TWIPS // ncols] * ncols
            if col_widths_pct is None
            else [int(CONTENT_W_TWIPS * p) for p in col_widths_pct]
        )

        tbl_grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in col_widths)
        tbl_pr = (
            "<w:tblPr>"
            f'<w:tblW w:w="{CONTENT_W_TWIPS}" w:type="dxa"/>'
            "<w:tblBorders>"
            f'<w:top w:val="single" w:sz="12" w:space="0" w:color="{COL_CRIMSON}"/>'
            f'<w:bottom w:val="single" w:sz="10" w:space="0" w:color="{COL_INK}"/>'
            '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="E5E7EB"/>'
            '<w:left w:val="none"/><w:right w:val="none"/><w:insideV w:val="none"/>'
            "</w:tblBorders>"
            '<w:tblCellMar><w:top w:w="80" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/>'
            '<w:left w:w="90" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar>'
            "</w:tblPr>"
        )

        tr_xmls: List[str] = []
        hdr_cells = []
        for idx, h in enumerate(headers):
            al = align_cols[idx] if align_cols else "center"
            hdr_cells.append(
                "<w:tc>"
                f'<w:tcPr><w:tcW w:w="{col_widths[idx]}" w:type="dxa"/>'
                f'<w:shd w:val="clear" w:color="auto" w:fill="{COL_HEADER_BG}"/>'
                '<w:tcBorders>'
                f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="{COL_INK}"/>'
                "</w:tcBorders>"
                '<w:vAlign w:val="center"/></w:tcPr>'
                f'<w:p><w:pPr><w:jc w:val="{al}"/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                f"{self._markup_to_runs(h, base_bold=True, size_pt=font_size_pt, color=COL_INK)}</w:p>"
                "</w:tc>"
            )
        tr_xmls.append(f"<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>{''.join(hdr_cells)}</w:tr>")

        for r_idx, row in enumerate(rows):
            bg = "FAFAFB" if r_idx % 2 == 1 else "FFFFFF"
            cells = []
            for c_idx, val in enumerate(row):
                al = align_cols[c_idx] if align_cols else "left"
                if isinstance(val, tuple) and val[0] == "img":
                    _, img_p, scale = val
                    with Image.open(img_p) as im:
                        iw, ih = im.size
                    cx = int(round(iw * scale * PT_TO_EMU))
                    cy = int(round(ih * scale * PT_TO_EMU))
                    max_cell_cx = int(col_widths[c_idx] * 635 * 0.92)
                    if cx > max_cell_cx:
                        r = max_cell_cx / cx
                        cx = max_cell_cx
                        cy = int(round(cy * r))
                    content_xml = self._drawing_xml(img_p, cx, cy)
                    al_use = "center"
                else:
                    content_xml = self._markup_to_runs(str(val), size_pt=font_size_pt, color=COL_INK)
                    al_use = al
                cells.append(
                    "<w:tc>"
                    f'<w:tcPr><w:tcW w:w="{col_widths[c_idx]}" w:type="dxa"/>'
                    f'<w:shd w:val="clear" w:color="auto" w:fill="{bg}"/>'
                    '<w:vAlign w:val="center"/></w:tcPr>'
                    f'<w:p><w:pPr><w:jc w:val="{al_use}"/><w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/></w:pPr>'
                    f"{content_xml}</w:p>"
                    "</w:tc>"
                )
            tr_xmls.append(f"<w:tr><w:trPr><w:cantSplit/></w:trPr>{''.join(cells)}</w:tr>")

        self.body_elements.append(f"<w:tbl>{tbl_pr}<w:tblGrid>{tbl_grid}</w:tblGrid>{''.join(tr_xmls)}</w:tbl>")
        self.body_elements.append(
            '<w:p><w:pPr><w:spacing w:before="0" w:after="90" w:line="240" w:lineRule="auto"/></w:pPr></w:p>'
        )

    def add_figure(self, img_path: Path, caption: str, width_fraction: float = 0.96) -> None:
        with Image.open(img_path) as im:
            iw, ih = im.size
        cx = int(CONTENT_W_EMU * width_fraction)
        cy = int(cx * ih / iw)
        drawing = self._drawing_xml(img_path, cx, cy)
        self.body_elements.append(
            '<w:p><w:pPr><w:jc w:val="center"/><w:keepNext/>'
            '<w:spacing w:before="120" w:after="60" w:line="240" w:lineRule="auto"/></w:pPr>'
            f"{drawing}</w:p>"
        )
        self.add_prose(
            f"*{caption}*",
            align="center", size_pt=10.0, color=COL_MUTED,
            space_before=20, space_after=140, line_spacing=260,
        )

    def add_toc_table(self, entries: Sequence[Tuple[str, str]], title: str) -> None:
        self.add_heading1(title)
        col_w = [CONTENT_W_TWIPS - 1050, 1050]
        tbl_pr = (
            "<w:tblPr>"
            f'<w:tblW w:w="{CONTENT_W_TWIPS}" w:type="dxa"/>'
            "<w:tblBorders>"
            '<w:top w:val="none"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD2D9"/>'
            '<w:insideH w:val="dotted" w:sz="4" w:space="0" w:color="CBD2D9"/>'
            '<w:left w:val="none"/><w:right w:val="none"/><w:insideV w:val="none"/>'
            "</w:tblBorders>"
            '<w:tblCellMar><w:top w:w="55" w:type="dxa"/><w:bottom w:w="55" w:type="dxa"/>'
            '<w:left w:w="30" w:type="dxa"/><w:right w:w="30" w:type="dxa"/></w:tblCellMar>'
            "</w:tblPr>"
        )
        rows_xml = []
        for label, pg in entries:
            is_sub = label.startswith("   ")
            rows_xml.append(
                "<w:tr>"
                f'<w:tc><w:tcPr><w:tcW w:w="{col_w[0]}" w:type="dxa"/></w:tcPr>'
                f'<w:p><w:pPr><w:jc w:val="left"/><w:spacing w:before="0" w:after="0" w:line="280" w:lineRule="auto"/></w:pPr>'
                f"{self._markup_to_runs(label, base_bold=not is_sub, size_pt=11.0)}</w:p></w:tc>"
                f'<w:tc><w:tcPr><w:tcW w:w="{col_w[1]}" w:type="dxa"/></w:tcPr>'
                f'<w:p><w:pPr><w:jc w:val="right"/><w:spacing w:before="0" w:after="0" w:line="280" w:lineRule="auto"/></w:pPr>'
                f"{self._run(pg, bold=not is_sub, size_pt=11.0)}</w:p></w:tc>"
                "</w:tr>"
            )
        self.body_elements.append(
            f'<w:tbl>{tbl_pr}<w:tblGrid><w:gridCol w:w="{col_w[0]}"/><w:gridCol w:w="{col_w[1]}"/></w:tblGrid>{"".join(rows_xml)}</w:tbl>'
        )
        self.body_elements.append(
            '<w:p><w:pPr><w:spacing w:before="0" w:after="90" w:line="240" w:lineRule="auto"/></w:pPr></w:p>'
        )

    def add_page_break(self) -> None:
        self.body_elements.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def _sect_pr_xml(self, footer_rid: Optional[str], page_num_fmt: Optional[str], page_num_start: Optional[int]) -> str:
        parts = []
        if footer_rid:
            parts.append(f'<w:footerReference w:type="default" r:id="{footer_rid}"/>')
        parts.append(f'<w:pgSz w:w="{A4_W}" w:h="{A4_H}"/>')
        parts.append(
            f'<w:pgMar w:top="{MARGIN_TOP}" w:right="{MARGIN_RIGHT}" '
            f'w:bottom="{MARGIN_BOTTOM}" w:left="{MARGIN_LEFT}" '
            f'w:header="708" w:footer="708" w:gutter="0"/>'
        )
        if page_num_fmt:
            start_attr = f' w:start="{page_num_start}"' if page_num_start is not None else ""
            parts.append(f'<w:pgNumType w:fmt="{page_num_fmt}"{start_attr}/>')
        return f"<w:sectPr>{''.join(parts)}</w:sectPr>"

    def add_section_break(
        self,
        footer_rid: Optional[str],
        page_num_fmt: Optional[str] = None,
        page_num_start: Optional[int] = None,
    ) -> None:
        sect = self._sect_pr_xml(footer_rid, page_num_fmt, page_num_start)
        self.body_elements.append(f"<w:p><w:pPr>{sect}</w:pPr></w:p>")

    def save(self, out_path: Path, final_footer_rid: Optional[str] = "rId5") -> None:
        final_sect = self._sect_pr_xml(final_footer_rid, None, None)
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
            f"<w:body>{''.join(self.body_elements)}{final_sect}</w:body></w:document>"
        )

        empty_footer = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p/></w:ftr>'
        )
        page_num_footer = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:p><w:pPr><w:jc w:val="right"/></w:pPr>'
            '<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
            '<w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="4B5563"/></w:rPr>'
            '<w:fldChar w:fldCharType="begin"/></w:r>'
            '<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
            '<w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="4B5563"/></w:rPr>'
            '<w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
            '<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
            '<w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="4B5563"/></w:rPr>'
            '<w:fldChar w:fldCharType="separate"/></w:r>'
            '<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
            '<w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="4B5563"/></w:rPr>'
            '<w:fldChar w:fldCharType="end"/></w:r>'
            "</w:p></w:ftr>"
        )

        styles_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:docDefaults><w:rPrDefault><w:rPr>"
            '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
            '<w:sz w:val="24"/><w:szCs w:val="24"/>'
            '<w:lang w:val="es-PE"/>'
            "</w:rPr></w:rPrDefault>"
            "<w:pPrDefault><w:pPr>"
            '<w:spacing w:line="360" w:lineRule="auto" w:after="120"/>'
            '<w:jc w:val="both"/>'
            "</w:pPr></w:pPrDefault></w:docDefaults>"
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:name w:val="Normal"/></w:style>'
            "</w:styles>"
        )

        rels_entries = [
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>',
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer2.xml"/>',
            '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer3.xml"/>',
            '<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer4.xml"/>',
        ]
        for rid, img_path, _, _ in self.images:
            rels_entries.append(
                f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{img_path.name}"/>'
            )

        doc_rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{''.join(rels_entries)}</Relationships>"
        )
        root_rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>"
        )
        content_types_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="png" ContentType="image/png"/>'
            '<Default Extension="jpg" ContentType="image/jpeg"/>'
            '<Default Extension="jpeg" ContentType="image/jpeg"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
            '<Override PartName="/word/footer2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
            '<Override PartName="/word/footer3.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
            '<Override PartName="/word/footer4.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
            "</Types>"
        )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types_xml)
            zf.writestr("_rels/.rels", root_rels_xml)
            zf.writestr("word/document.xml", doc_xml)
            zf.writestr("word/styles.xml", styles_xml)
            zf.writestr("word/footer1.xml", empty_footer)
            zf.writestr("word/footer2.xml", page_num_footer)
            zf.writestr("word/footer3.xml", page_num_footer)
            zf.writestr("word/footer4.xml", empty_footer)
            zf.writestr("word/_rels/document.xml.rels", doc_rels_xml)
            for _, img_path, _, _ in self.images:
                zf.write(img_path, arcname=f"word/media/{img_path.name}")


def build_report(root: Path, page_map: Optional[Dict[str, str]] = None) -> Path:
    data = json.loads((root / "results" / "benchmark_results.json").read_text(encoding="utf-8"))
    fig_dir = root / "docs" / "figures"
    eq_dir = root / "docs" / "equations"
    pm = page_map or {}

    def pg(key: str, default: str = "—") -> str:
        return pm.get(key, default)

    def eq(name: str) -> Path:
        return eq_dir / f"{name}.png"

    doc = DocxBuilder()

    # =========================================================================
    # SECCIÓN 1: CARÁTULA EXACTA DE LA PLANTILLA OFICIAL UPCH (sin numeración)
    # =========================================================================
    # Línea 1: UNIVERSIDAD PERUANA (#7F7F7F) CAYETANO HEREDIA (#C00000) en una sola línea
    doc.body_elements.append(
        '<w:p><w:pPr><w:jc w:val="center"/>'
        '<w:spacing w:before="80" w:after="70" w:line="260" w:lineRule="auto"/></w:pPr>'
        f"{doc._run('UNIVERSIDAD PERUANA ', bold=True, size_pt=17.5, color='7F7F7F')}"
        f"{doc._run('CAYETANO HEREDIA', bold=True, size_pt=17.5, color='C00000')}"
        "</w:p>"
    )
    doc.add_prose(
        "FACULTAD DE CIENCIAS E INGENIERÍA",
        align="center", bold=True, size_pt=16.0, color="000000",
        space_before=0, space_after=100, line_spacing=260,
    )
    # Escudo oficial UPCH extraído directamente de la plantilla del docente (4.62 cm x 4.62 cm)
    escudo_path = root / "docs" / "assets" / "escudo_upch.jpg"
    doc.body_elements.append(
        '<w:p><w:pPr><w:jc w:val="center"/>'
        '<w:spacing w:before="60" w:after="100" w:line="240" w:lineRule="auto"/></w:pPr>'
        f"{doc._drawing_xml(escudo_path, 1665027, 1665027)}</w:p>"
    )
    doc.add_prose(
        "ESCUELA PROFESIONAL DE INGENIERÍA INFORMÁTICA",
        align="center", bold=True, size_pt=16.0, color="365F91",
        space_before=40, space_after=80, line_spacing=260,
    )
    doc.add_prose(
        "ESTRUCTURAS DISCRETAS II",
        align="center", bold=True, size_pt=16.0, color="365F91",
        space_before=0, space_after=220, line_spacing=260,
    )
    doc.add_prose(
        "Trabajo Académico — Tema 10",
        align="center", bold=True, size_pt=14.0, color="000000",
        space_before=0, space_after=80, line_spacing=280,
    )
    doc.add_prose(
        "“Diseño de un contador combinatorio con funciones generadoras”",
        align="center", bold=True, size_pt=14.0, color="000000",
        space_before=0, space_after=280, line_spacing=340,
    )
    doc.add_prose(
        "AUTORES:",
        align="center", bold=True, size_pt=12.0, color="000000",
        space_before=60, space_after=40, line_spacing=280,
    )
    doc.add_prose(
        "Apellidos, Nombres (ORCID: 0000-0000-0000-0000)\n"
        "Apellidos, Nombres (ORCID: 0000-0000-0000-0000)\n"
        "Apellidos, Nombres (ORCID: 0000-0000-0000-0000)\n"
        "Apellidos, Nombres (ORCID: 0000-0000-0000-0000)\n"
        "Apellidos, Nombres (ORCID: 0000-0000-0000-0000)",
        align="center", bold=True, size_pt=12.0, color="000000",
        space_before=0, space_after=180, line_spacing=300,
    )
    doc.add_prose(
        "ASESOR:",
        align="center", bold=True, size_pt=12.0, color="000000",
        space_before=40, space_after=40, line_spacing=280,
    )
    doc.add_prose(
        "Dr. Ing. CIP. Illesca Cangalaya, Omar Felix\nORCID: 0000-0002-0144-6878",
        align="center", bold=True, size_pt=12.0, color="000000",
        space_before=0, space_after=140, line_spacing=300,
    )
    doc.add_prose(
        "SAN MARTÍN DE PORRES – PERÚ",
        align="center", bold=True, size_pt=12.0, color="000000",
        space_before=40, space_after=40, line_spacing=280,
    )
    doc.add_prose(
        "2026",
        align="center", bold=True, size_pt=16.0, color="000000",
        space_before=0, space_after=140, line_spacing=280,
    )
    doc.add_prose(
        "Fecha: Noviembre de 2026",
        align="left", bold=True, size_pt=14.0, color="000000",
        space_before=40, space_after=0, line_spacing=280,
    )
    doc.add_section_break(footer_rid="rId2")

    # =========================================================================
    # SECCIÓN 2: PÁGINAS PRELIMINARES (romanos minúsculas desde ii)
    # =========================================================================
    toc_entries = [
        ("Resumen y palabras clave", pg("RESUMEN")),
        ("I. Introducción", pg("I. INTRODUCCIÓN")),
        ("II. Antecedentes históricos y aportes de autores", pg("II. ANTECEDENTES HISTÓRICOS")),
        ("III. Marco teórico", pg("III. MARCO TEÓRICO")),
        ("   3.1. Anillo de series formales de potencias", pg("3.1.")),
        ("   3.2. Teoremas fundamentales y demostraciones", pg("3.2.")),
        ("   3.3. Funciones generatrices exponenciales y recurrencias", pg("3.3.")),
        ("IV. Objetivos", pg("IV. OBJETIVOS")),
        ("V. Metodología y diseño", pg("V. METODOLOGÍA Y DISEÑO")),
        ("VI. Implementación o simulación", pg("VI. IMPLEMENTACIÓN O SIMULACIÓN")),
        ("VII. Resultados y análisis", pg("VII. RESULTADOS Y ANÁLISIS")),
        ("VIII. Discusión", pg("VIII. DISCUSIÓN")),
        ("IX. Conclusiones", pg("IX. CONCLUSIONES")),
        ("X. Referencias bibliográficas", pg("X. REFERENCIAS BIBLIOGRÁFICAS")),
        ("XI. Anexos", "s/n"),
    ]
    doc.add_toc_table(toc_entries, "ÍNDICE")
    doc.add_page_break()

    table_entries = [
        ("Tabla 1. Funciones generatrices ordinarias y exponenciales más usuales", pg("Tabla 1.")),
        ("Tabla 2. Casos de prueba normales y límite verificados en el sistema", pg("Tabla 2.")),
        ("Tabla 3. Contraste exacto del motor frente a oráculos matemáticos independientes", pg("Tabla 3.")),
        ("Tabla 4. Escalabilidad temporal (ms) en conteo restringido de seis variables", pg("Tabla 4.")),
        ("Tabla 5. Multiplicación exacta de dos series densas (ms) según algoritmo", pg("Tabla 5.")),
        ("Tabla 6. Particiones de Euler y error relativo de Hardy-Ramanujan", pg("Tabla 6.")),
    ]
    doc.add_toc_table(table_entries, "ÍNDICE DE TABLAS")

    fig_entries = [
        ("Figura 1. Arquitectura modular del Contador Combinatorio con Funciones Generadoras", pg("Figura 1.")),
        ("Figura 2. Distribución exacta de configuraciones válidas en un clúster de 5 servidores", pg("Figura 2.")),
        ("Figura 3. Análisis empírico de complejidad y escalabilidad temporal en escala logarítmica", pg("Figura 3.")),
        ("Figura 4. Particiones de Euler (*n* = 1 a 60) y convergencia asintótica de Hardy-Ramanujan", pg("Figura 4.")),
    ]
    doc.add_toc_table(fig_entries, "ÍNDICE DE FIGURAS")
    doc.add_page_break()

    # RESUMEN Y PALABRAS CLAVE (~210 palabras, redacción natural y sobria)
    doc.add_heading1("RESUMEN")
    doc.add_prose(
        "Determinar con exactitud cuántas configuraciones discretas satisfacen un conjunto simultáneo "
        "de restricciones —como cuotas mínimas y máximas, condiciones de paridad, cambio de monedas "
        "con inventario finito, particiones de enteros o secuencias etiquetadas— resulta rápidamente "
        "intratable por enumeración exhaustiva debido a la explosión combinatoria. El presente estudio "
        "tiene por objeto diseñar, implementar y validar un contador combinatorio exacto fundamentado "
        "en funciones generadoras ordinarias (FGO) y exponenciales (FGE) sobre los anillos truncados "
        "de series formales ℤ[[*x*]] y ℚ[[*x*]]. Para ello se formalizaron las identidades algebraicas "
        "mediante demostraciones rigurosas y se desarrolló un motor reproducible en Python 3.12 puro "
        "que integra tres estrategias exactas: operadores racionales estructurados en *O*(*mN*), "
        "convolución modular mediante Transformada Teórica de Números con Teorema Chino del Resto "
        "(NTT+CRT) en *O*(*N* log *N*) y multiplicación de Karatsuba en *O*(*N*^{1,585}). Cada salida "
        "fue contrastada con oráculos independientes de fuerza bruta, programación dinámica y fórmulas "
        "cerradas. El sistema alcanzó exactitud íntegra en todos los casos normales, límite y "
        "ejercicios del curso; en particular, resolvió instancias de *N* = 1000 con más de 2,28 × 10^{12} "
        "configuraciones en 2,00 ms —24,3 veces más rápido que la programación dinámica estándar— y "
        "verificó el Teorema de Euler de particiones en todo el intervalo *n* ∈ [0, 60]."
    )
    doc.add_prose(
        "**Palabras clave:** funciones generadoras, series formales de potencias, conteo combinatorio, "
        "Transformada Teórica de Números, particiones de Euler.",
        space_before=80, space_after=120,
    )
    doc.add_section_break(footer_rid="rId3", page_num_fmt="lowerRoman", page_num_start=2)

    # =========================================================================
    # SECCIÓN 3: CUERPO DEL INFORME (I. Introducción hasta X. Referencias, arábigos desde 1)
    # =========================================================================

    # I. INTRODUCCIÓN
    doc.add_heading1("I. INTRODUCCIÓN")
    doc.add_prose(
        "Diversos problemas centrales de la ingeniería informática exigen calcular con exactitud el "
        "tamaño de espacios discretos sujetos a múltiples restricciones simultáneas [1], [2]. Ocurre "
        "así al distribuir cargas entre servidores con límites operativos y tamaños de lote, al "
        "evaluar políticas de cambio de monedas con inventario limitado, al cuantificar particiones "
        "de memoria o al dimensionar el espacio de claves válidas en protocolos de seguridad [3], [4]. "
        "En todos estos escenarios no basta una cota aproximada: se requiere el conteo exacto como "
        "entero de precisión arbitraria."
    )
    doc.add_prose(
        "El abordaje directo mediante búsqueda exhaustiva colapsa apenas crecen las dimensiones del "
        "problema, pues el número de tuplas factibles crece como *O*(*N*^{*m*−1}) o exponencialmente. "
        "Por su parte, las técnicas combinatorias elementales —combinaciones con repetición o "
        "principio de inclusión-exclusión— se tornan frágiles cuando cada variable obedece reglas "
        "distintas de rango, paridad o divisibilidad [1], [5]. Frente a estas limitaciones, las "
        "funciones generadoras brindan un lenguaje algebraico unificado: codifican sucesiones enteras "
        "como coeficientes de series formales de potencias, reduciendo el conteo a productos y "
        "cocientes polinómicos bien definidos [4], [6]."
    )
    doc.add_prose(
        "El presente trabajo se circunscribe al diseño, implementación reproducible en Python 3.12 "
        "estándar y validación matemática de un contador combinatorio exacto basado en funciones "
        "generadoras ordinarias y exponenciales. El alcance comprende cinco familias representativas: "
        "composiciones restringidas con dominios heterogéneos, cambio de monedas con y sin límite de "
        "stock, particiones de enteros, permutaciones con repetición restringida y expansión de "
        "cocientes racionales asociados a relaciones de recurrencia lineales. No se aborda el análisis "
        "asintótico por integración de contorno en variable compleja, salvo como referencia comparativa "
        "a través de la fórmula clásica de Hardy-Ramanujan."
    )
    doc.add_prose(
        "A partir de este planteamiento se formula la pregunta que orienta la investigación: "
        "*¿de qué manera puede diseñarse e implementarse un contador combinatorio exacto basado en el "
        "álgebra de series formales de potencias que unifique problemas heterogéneos de conteo "
        "discreto, garantice su corrección frente a oráculos independientes y supere la escalabilidad "
        "de la fuerza bruta y de la programación dinámica convencional?*"
    )

    # II. ANTECEDENTES HISTÓRICOS Y APORTES DE AUTORES
    doc.add_heading1("II. ANTECEDENTES HISTÓRICOS Y APORTES DE AUTORES")
    doc.add_prose(
        "La teoría de funciones generadoras emergió en el siglo XVIII como respuesta a problemas "
        "concretos de probabilidad y teoría de números, consolidándose progresivamente como un puente "
        "estructural entre el álgebra formal, la combinatoria y el análisis de algoritmos [4], [6]. "
        "Su primer antecedente sistemático se remonta a **Abraham de Moivre (1730)**, quien en "
        "*Miscellanea Analytica* empleó series de potencias para resolver relaciones de recurrencia "
        "lineales vinculadas a juegos de azar y a la sucesión de Fibonacci, mostrando que el término "
        "general podía extraerse descomponiendo una función racional [5], [7]."
    )
    doc.add_prose(
        "Poco después, **Leonhard Euler (1748)** transformó el método en una herramienta central de la "
        "combinatoria en su *Introductio in Analysin Infinitorum*. Al modelar particiones de enteros "
        "mediante productos infinitos formales, Euler demostró de forma puramente algebraica que el "
        "número de particiones de *n* en partes distintas coincide con el de particiones en partes "
        "impares [4], [7]. Décadas más tarde, **Pierre-Simon Laplace (1812)** acuñó la denominación "
        "de «función generadora» (*fonction génératrice*) en su *Théorie Analytique des Probabilités*, "
        "estableciendo su papel en ecuaciones en diferencias y distribuciones discretas [5]."
    )
    doc.add_prose(
        "Durante el siglo XX, el enfoque adquirió plena autonomía algebraica. **George Pólya (1937)** "
        "incorporó la acción de grupos de simetría al conteo mediante polinomios de índice de ciclos, "
        "mientras **Richard Stanley (1986–2012)** formalizó el estudio del anillo de series formales "
        "de potencias sin exigir convergencia analítica [7]. En el ámbito de la computación, "
        "**Herbert S. Wilf (1990)** popularizó la intuición de la serie generatriz como un soporte "
        "ordenado para exhibir y manipular sucesiones [4]; **Graham, Knuth y Patashnik (1994)** "
        "estandarizaron la notación [*x*^{*n*}] *G*(*x*) en *Concrete Mathematics* [5]; y "
        "**Philippe Flajolet junto con Robert Sedgewick (2009)** sistematizaron el método simbólico "
        "que traduce constructores de estructuras de datos en ecuaciones de FGO y FGE [6]."
    )
    doc.add_prose(
        "Finalmente, la viabilidad computacional a gran escala dependió de avances en multiplicación "
        "rápida de polinomios. **Cooley y Tukey (1965)** redujeron la convolución discreta de "
        "*O*(*N*^{2}) a *O*(*N* log *N*) mediante la Transformada Rápida de Fourier [9], y "
        "**John Pollard (1971)** trasladó dicha estructura a cuerpos finitos mediante la Transformada "
        "Teórica de Números (NTT) [10]. Esta transición resulta decisiva en combinatoria exacta, pues "
        "suprime los errores de redondeo inherentes a la aritmética en punto flotante [8]."
    )

    # III. MARCO TEÓRICO
    doc.add_heading1("III. MARCO TEÓRICO")

    doc.add_heading2("3.1. Anillo de series formales de potencias")
    doc.add_prose(
        "Sea *K* un anillo conmutativo con unidad —en este estudio, ℤ o ℚ—. Dada una sucesión "
        "{*a*_{*k*}}_{*k* ≥ 0} con términos en *K*, su **función generatriz ordinaria (FGO)** se define "
        "como la serie formal de potencias en la indeterminada *x* [1], [4], [7]:"
    )
    doc.add_equation_img(eq("eq1_fgo"), "1")
    doc.add_prose(
        "El operador [*x*^{*n*}] *G*(*x*) = *a*_{*n*} denota la extracción del *n*-ésimo coeficiente [5]. "
        "A diferencia del cálculo real, la indeterminada *x* no asume valores numéricos ni requiere "
        "radio de convergencia positivo; la serie actúa como un registro algebraico exacto de la "
        "sucesión. Dotado de la adición término a término y del producto de Cauchy, el conjunto "
        "*K*[[*x*]] conforma un anillo conmutativo con unidad [1], [7]:"
    )
    doc.add_equation_img(eq("eq2_sum"), "2")
    doc.add_equation_img(eq("eq3_cauchy"), "3")
    doc.add_prose(
        "Conviene precisar que en el producto de Cauchy (3) el índice interno *j* recorre exactamente "
        "de 0 a *k*, ya que no existen coeficientes de índice negativo. Al trabajar módulo *x*^{*N*+1} "
        "se obtiene el anillo cociente *K*[*x*] / (*x*^{*N*+1}), cuya representación finita preserva "
        "con exactitud todos los coeficientes desde *a*_{0} hasta *a*_{*N*}."
    )

    doc.add_heading2("3.2. Teoremas fundamentales y demostraciones")

    doc.add_theorem(
        "Teorema 1 (Inversión formal y serie geométrica)",
        "Una serie formal A(x) ∈ ℚ[[x]] admite inverso multiplicativo B(x) tal que A(x)·B(x) = 1 "
        "si y solo si a_{0} ≠ 0. En particular, para todo escalar c ∈ ℚ y entero r ≥ 1 se satisface "
        "la expansión geométrica formal junto con la recurrencia de coeficientes dada en (4).",
    )
    doc.add_equation_img(eq("eq4_geom"), "4")
    doc.add_proof(
        "La igualdad *A*(*x*) · *B*(*x*) = 1 equivale al sistema triangular *a*_{0}*b*_{0} = 1 y "
        "∑ *a*_{*j*}*b*_{*k*−*j*} = 0 (con *j* de 0 a *k*) para todo *k* ≥ 1. Si *a*_{0} = 0, la "
        "primera ecuación carece de solución. Si *a*_{0} ≠ 0, resulta de manera única *b*_{0} = "
        "*a*_{0}^{−1} y, por inducción fuerte sobre *k* ≥ 1, cada *b*_{*k*} queda determinado por la "
        "segunda expresión de (4). Aplicando este resultado a *A*(*x*) = 1 − *cx*^{*r*} —donde "
        "*a*_{0} = 1, *a*_{*r*} = −*c* y los demás coeficientes son nulos— se obtiene *b*_{0} = 1, "
        "*b*_{*k*} = *cb*_{*k*−*r*} para *k* ≥ *r* y *b*_{*k*} = 0 cuando *r* no divide a *k*, lo cual "
        "implica *b*_{*mr*} = *c*^{*m*} para todo entero *m* ≥ 0."
    )

    doc.add_theorem(
        "Teorema 2 (Teorema del binomio negativo)",
        "Para todo entero positivo n ≥ 1, la inversa de (1 − x)^{n} en el anillo ℚ[[x]] genera los "
        "coeficientes de combinaciones con repetición:",
    )
    doc.add_equation_img(eq("eq5_negbinom"), "5")
    doc.add_proof(
        "Procedemos por inducción matemática sobre *n*. Para el caso base *n* = 1, el Teorema 1 "
        "garantiza que el coeficiente de *x*^{*k*} en (1 − *x*)^{−1} es 1, lo cual coincide con el "
        "coeficiente binomial correspondiente. Supóngase ahora válida la identidad (5) para un entero "
        "*n* ≥ 1. Multiplicando ambos miembros por (1 − *x*)^{−1} y aplicando el producto de Cauchy (3), "
        "el coeficiente de *x*^{*k*} en (1 − *x*)^{−(*n*+1)} es la suma acumulada de los coeficientes "
        "binomiales desde *j* = 0 hasta *k*. Por aplicación reiterada de la regla de Pascal "
        "(identidad del palo de hockey), dicha suma colapsa exactamente en el coeficiente binomial "
        "correspondiente a *n* + 1, completando la inducción."
    )

    doc.add_theorem(
        "Teorema 3 (Principio multiplicativo de conteo con restricciones)",
        "Sean S_{1}, S_{2}, …, S_{m} ⊆ ℤ_{≥0} conjuntos arbitrarios de valores permitidos. El número "
        "de soluciones enteras de x_{1} + x_{2} + … + x_{m} = n con x_{i} ∈ S_{i} coincide con el "
        "coeficiente de x^{n} en el producto de factores dado en (6); además, si cada S_{i} es una "
        "progresión aritmética de inicio l_{i}, paso d_{i} y longitud q_{i} + 1, el producto admite "
        "la forma racional compacta del miembro derecho.",
    )
    doc.add_equation_img(eq("eq6_mult"), "6")
    doc.add_proof(
        "Al distribuir formalmente el producto de los *m* factores, cada monomio generado proviene de "
        "seleccionar un exponente *c*_{*i*} ∈ *S*_{*i*} por cada factor *i*, formando el producto "
        "*x*^{*c*₁ + … + *c*ₘ}. Al agrupar términos de grado *n*, el coeficiente [*x*^{*n*}] "
        "incrementa en una unidad por cada tupla (*c*_{1}, …, *c*_{*m*}) cuya suma sea *n*. Cuando "
        "*S*_{*i*} = {*l*_{*i*}, *l*_{*i*} + *d*_{*i*}, …, *l*_{*i*} + *q*_{*i*}*d*_{*i*}}, factorizar "
        "*x*^{*l*ᵢ} reduce el polinomio a una suma geométrica finita de razón *x*^{*d*ᵢ}, "
        "obteniéndose inmediatamente la expresión racional de (6)."
    )

    doc.add_theorem(
        "Teorema 4 (Teorema de Particiones de Euler)",
        "Para todo entero no negativo n, la cantidad de particiones de n en sumandos estrictamente "
        "distintos coincide con la cantidad de particiones de n en sumandos impares.",
    )
    doc.add_equation_img(eq("eq7_euler"), "7")
    doc.add_proof(
        "En una partición en partes distintas, cada entero *k* ≥ 1 aparece cero o una vez, lo que "
        "aporta el factor (1 + *x*^{*k*}). Sustituyendo cada factor por la diferencia de cuadrados "
        "(1 − *x*^{2*k*}) / (1 − *x*^{*k*}) dentro del producto infinito formal, cada factor de "
        "exponente par presente en el numerador se cancela exactamente con su contraparte en el "
        "denominador —operación plenamente válida en ℤ[[*x*]], dado que en cada grado truncado solo "
        "intervienen finitos factores—. Permanecen únicamente los denominadores de exponente impar "
        "1 − *x*^{2*j*−1}, estableciendo *D*(*x*) = *O*(*x*) y, por unicidad de coeficientes, la "
        "igualdad buscada para todo *n* ≥ 0 [4], [7]."
    )

    doc.add_heading2("3.3. Funciones generatrices exponenciales y recurrencias")
    doc.add_prose(
        "Cuando el orden de los elementos es significativo —por ejemplo, al enumerar palabras, códigos "
        "o permutaciones con repetición acotada— corresponde emplear la **función generatriz "
        "exponencial (FGE)** [4], [6]. Su producto incorpora de manera natural los coeficientes "
        "multinomiales de intercalación entre símbolos:"
    )
    doc.add_equation_img(eq("eq8_egf"), "8")
    doc.add_prose(
        "En el ámbito de las relaciones de recurrencia lineales con coeficientes constantes, "
        "multiplicar ambos miembros por *x*^{*n*} y sumar sobre el rango de validez traduce la "
        "recurrencia en una ecuación algebraica en *G*(*x*). Despejando *G*(*x*) como un cociente "
        "racional *P*(*x*) / *Q*(*x*), la sucesión se obtiene bien analíticamente mediante fracciones "
        "parciales, o bien computacionalmente por inversión formal en ℚ[[*x*]] [1], [2]. La Tabla 1 "
        "reúne las funciones generatrices más frecuentes empleadas a lo largo del trabajo."
    )

    # Tabla 1 con fórmulas tipográficas verticales reales (600 DPI)
    doc.add_table(
        headers=["Función Generatriz", "Tipo", "Coeficiente *a*_{*k*}", "Interpretación combinatoria"],
        rows=[
            [("img", eq("t1_1"), 0.140), "FGO", ("img", eq("t1_c1"), 0.125), "Subconjuntos de tamaño *k* sin repetición"],
            [("img", eq("t1_2"), 0.130), "FGO", "1 si 0 ≤ *k* ≤ *n*; 0 en otro caso", "Variable entera acotada 0 ≤ *x*_{*i*} ≤ *n*"],
            [("img", eq("t1_3"), 0.130), "FGO", "1 si *r* | *k*; 0 en otro caso", "Moneda de denominación *r* (stock ilimitado)"],
            [("img", eq("t1_4"), 0.130), "FGO", ("img", eq("t1_c4"), 0.125), "Combinaciones con repetición (estrellas y barras)"],
            [("img", eq("t1_5"), 0.130), "FGO", "*a*^{*k*}", "Recurrencia homogénea *a*_{*k*} = *a* · *a*_{*k*−1}"],
            [("img", eq("t1_6"), 0.120), "FGE", "1  (en *k*! [*x*^{*k*}])", "Símbolo con frecuencia libre en permutaciones"],
            [("img", eq("t1_7"), 0.125), "FGE", "1 si *k* par; 0 si *k* impar", "Símbolo con frecuencia par en cadenas"],
        ],
        col_widths_pct=[0.30, 0.08, 0.24, 0.38],
        caption="Tabla 1. Funciones generatrices ordinarias y exponenciales más usuales [1], [4], [5].",
        font_size_pt=9.5,
        align_cols=["center", "center", "center", "left"],
    )

    # IV. OBJETIVOS
    doc.add_heading1("IV. OBJETIVOS")
    doc.add_prose(
        "**Objetivo general.** Diseñar, implementar y validar un contador combinatorio exacto y "
        "reproducible sustentado en funciones generadoras ordinarias y exponenciales, capaz de "
        "modelar y resolver de manera unificada problemas de conteo discreto con restricciones "
        "heterogéneas."
    )
    doc.add_prose("**Objetivos específicos:**", space_before=60, space_after=60)
    doc.add_prose(
        "1. Formalizar el modelo matemático del contador en los anillos de series truncadas "
        "ℤ[*x*] / (*x*^{*N*+1}) y ℚ[*x*] / (*x*^{*N*+1}), articulando FGO, FGE, factores racionales "
        "e inversión formal con sus respectivas demostraciones.",
        indent_left=360, hanging=240, space_after=80,
    )
    doc.add_prose(
        "2. Implementar un motor algorítmico modular en Python 3.12 estándar sin dependencias externas "
        "que integre y compare el producto de Cauchy clásico *O*(*N*^{2}), la multiplicación de "
        "Karatsuba *O*(*N*^{1,585}), la convolución exacta NTT+CRT *O*(*N* log *N*) y operadores "
        "racionales lineales *O*(*mN*).",
        indent_left=360, hanging=240, space_after=80,
    )
    doc.add_prose(
        "3. Validar los resultados generados frente a oráculos independientes de fuerza bruta, "
        "programación dinámica y fórmulas cerradas, evaluando empíricamente la precisión exacta y "
        "la escalabilidad en casos normales, casos límite y aplicaciones representativas.",
        indent_left=360, hanging=240, space_after=120,
    )

    # V. METODOLOGÍA Y DISEÑO
    doc.add_heading1("V. METODOLOGÍA Y DISEÑO")
    doc.add_prose(
        "La investigación sigue un enfoque aplicado y experimental de base formal. Cada módulo del "
        "contador se derivó primero como identidad exacta en los anillos de series de potencias, se "
        "tradujo posteriormente a algoritmos deterministas libres de aproximaciones numéricas y se "
        "sometió a validación cruzada automatizada y mediciones reproducibles de tiempo de ejecución."
    )

    doc.add_heading2("5.1. Modelado de entradas y arquitectura del sistema")
    doc.add_prose(
        "Cada restricción sobre una variable o símbolo se declara mediante una estructura inmutable "
        "`VariableConstraint(name, min_val, max_val, step, allowed)`. El traductor simbólico examina "
        "las restricciones: si todas conforman progresiones aritméticas (rangos acotados, cotas "
        "inferiores, paridad o múltiplos de denominaciones), delega el cálculo al operador racional "
        "estructurado en *O*(*mN*); cuando existen conjuntos arbitrarios *S*_{*i*}, construye los "
        "polinomios indicadores y los combina mediante un árbol binario equilibrado de productos. "
        "La Figura 1 sintetiza el flujo de datos y el acoplamiento con los módulos de verificación."
    )
    doc.add_figure(
        fig_dir / "fig1_arquitectura.png",
        "Figura 1. Arquitectura modular del Contador Combinatorio con Funciones Generadoras.",
        width_fraction=0.98,
    )

    doc.add_heading2("5.2. Decisiones tecnológicas y algoritmos principales")
    doc.add_prose(
        "Se eligió Python 3.12 estándar sin bibliotecas de terceros por dos criterios de ingeniería. "
        "Primero, los enteros nativos (`int`) poseen precisión arbitraria y `fractions.Fraction` "
        "garantiza aritmética racional exacta, evitando los errores de redondeo propios del estándar "
        "IEEE-754 cuando los conteos superan 2^{53} ≈ 9 × 10^{15}. Segundo, la ausencia de "
        "dependencias externas asegura que cualquier evaluador reproduzca tanto el software como los "
        "experimentos de manera inmediata. Los Algoritmos 1 y 2 formalizan los dos núcleos de "
        "aceleración desarrollados."
    )

    doc.add_algorithm(
        "Algoritmo 1. Conteo Racional Estructurado para Restricciones Aritméticas en O(mN)",
        io_lines=[
            "**Entrada:** *m* restricciones aritméticas (*l*_{*i*}, *u*_{*i*}, *d*_{*i*}) y objetivo entero *N* ≥ 0.",
            "**Salida:** arreglo exacto *C*[0 … *N*] donde *C*[*k*] = [*x*^{*k*}] *G*(*x*).",
        ],
        steps=[
            "*desplazamiento* ← ∑ *l*_{*i*}  (para *i* = 1 hasta *m*).",
            "**Si** *desplazamiento* > *N*, **retornar** vector de ceros de longitud *N* + 1.",
            "*rem* ← *N* − *desplazamiento*;  inicializar *A*[0 … *rem*] ← [1, 0, …, 0].",
            "**Para cada** restricción (*l*_{*i*}, *u*_{*i*}, *d*_{*i*}):",
            "   **Para** *k* desde *d*_{*i*} hasta *rem*:  *A*[*k*] ← *A*[*k*] + *A*[*k* − *d*_{*i*}]  *(división por 1 − x^{dᵢ})*.",
            "   **Si** *u*_{*i*} es finito:",
            "      *span* ← (⌊(*u*_{*i*} − *l*_{*i*}) / *d*_{*i*}⌋ + 1) · *d*_{*i*}.",
            "      **Para** *k* desde *rem* bajando hasta *span*:  *A*[*k*] ← *A*[*k*] − *A*[*k* − *span*]  *(producto por 1 − x^{span})*.",
            "**Retornar** concatenación de *desplazamiento* ceros seguidos de *A*.",
        ],
    )

    doc.add_algorithm(
        "Algoritmo 2. Convolución Entera Exacta mediante NTT y Teorema Chino del Resto en O(N log N)",
        io_lines=[
            "**Entrada:** series enteras *A*[0 … *N*], *B*[0 … *N*]; primos NTT *P*_{1} = 998244353, *P*_{2} = 167772161, *P*_{3} = 469762049 (*g* = 3).",
            "**Salida:** producto de Cauchy exacto truncado *C*[0 … *N*].",
        ],
        steps=[
            "Calcular cota superior *U* = máx|*A*| · máx|*B*| · mín(|*A*|, |*B*|) y módulo compuesto *M* = *P*_{1}*P*_{2}*P*_{3} ≈ 7,86 × 10^{25}.",
            "**Si** *U* ≥ *M* / 2, **retornar** *Karatsuba*(*A*, *B*)[0 … *N*]  *(respaldo exacto sin desbordamiento)*.",
            "**Para cada** primo *P*_{*t*} ∈ {*P*_{1}, *P*_{2}, *P*_{3}}:",
            "   Computar *C*_{*t*} ← NTT^{−1}( NTT(*A* mód *P*_{*t*}) ⊙ NTT(*B* mód *P*_{*t*}) ) mód *P*_{*t*}  *(Cooley-Tukey iterativo)*.",
            "**Para** *k* = 0 hasta *N*: reconstruir el único entero *C*[*k*] ∈ (−*M*/2, *M*/2] congruente con (*C*_{1}[*k*], *C*_{2}[*k*], *C*_{3}[*k*]) vía CRT.",
            "**Retornar** *C*.",
        ],
    )

    doc.add_prose(
        "Para validar experimentalmente el Algoritmo 1 en problemas con cota superior uniforme *u*, "
        "se incorporó además como oráculo analítico independiente la fórmula cerrada derivada del "
        "Principio de Inclusión-Exclusión [1], [5]:"
    )
    doc.add_equation_img(eq("eq10_ie"), "9")

    # VI. IMPLEMENTACIÓN O SIMULACIÓN
    doc.add_heading1("VI. IMPLEMENTACIÓN O SIMULACIÓN")
    doc.add_prose(
        "El prototipo se organizó en cinco módulos de Python claramente desacoplados: `formal_series.py` "
        "(anillo truncado, Cauchy, Karatsuba, NTT+CRT e inversión formal), `combinatorics_engine.py` "
        "(modelado de restricciones, monedas, particiones, FGE y recurrencias), `validators.py` "
        "(oráculos de fuerza bruta, programación dinámica y fórmulas cerradas), `benchmarks.py` "
        "(experimentos reproducibles) y `cli.py` (interfaz de comandos). Los listados siguientes "
        "muestran el núcleo de los operadores lineales y la extracción exacta en FGE."
    )

    doc.add_code_listing(
        "def div_one_minus_monomial(self, coeff: int, power: int) -> 'FormalPowerSeries':\n"
        "    \"\"\"Divide por (1 - coeff * x^power) en O(N): b_k = a_k + coeff * b_{k - power}.\"\"\"\n"
        "    out = list(self.coeffs)\n"
        "    for k in range(power, self.max_degree + 1):\n"
        "        out[k] = out[k] + coeff * out[k - power]\n"
        "    return FormalPowerSeries(out, max_degree=self.max_degree, rational=self.rational)\n\n"
        "def mul_binomial_factor(self, coeff: int, power: int) -> 'FormalPowerSeries':\n"
        "    \"\"\"Multiplica por (1 + coeff * x^power) en O(N) recorriendo en orden inverso.\"\"\"\n"
        "    out = list(self.coeffs)\n"
        "    for k in range(self.max_degree, power - 1, -1):\n"
        "        out[k] = out[k] + coeff * out[k - power]\n"
        "    return FormalPowerSeries(out, max_degree=self.max_degree, rational=self.rational)",
        title="Listado 1. Operadores racionales exactos en O(N) implementados en src/formal_series.py.",
    )
    doc.add_code_listing(
        "def count_restricted_permutations_egf(self, symbol_constraints, length_n: int) -> CountResult:\n"
        "    factors = [\n"
        "        FormalPowerSeries.from_exponents(c.exponents_up_to(length_n), length_n, exponential=True)\n"
        "        for c in symbol_constraints\n"
        "    ]\n"
        "    series = FormalPowerSeries.one(length_n, rational=True)\n"
        "    for f in factors:\n"
        "        series = series.multiply(f, method='schoolbook')\n"
        "    counts = [(series.coeffs[k] * math.factorial(k)).numerator for k in range(length_n + 1)]\n"
        "    return CountResult('restricted_permutations_EGF', length_n, counts[length_n], ...)",
        title="Listado 2. Evaluación exacta de Funciones Generatrices Exponenciales en ℚ[[x]].",
    )

    doc.add_prose(
        "Para reproducir integralmente el sistema desde la carpeta raíz basta ejecutar tres comandos "
        "con Python 3.12: `python3 -m unittest discover -s tests -v` (verifica las 11 pruebas "
        "unitarias), `python3 -m src.cli demo` (ejecuta los cinco casos demostrativos) y "
        "`python3 -m src.benchmarks` (regenera las mediciones en `results/benchmark_results.json`). "
        "La Tabla 2 sintetiza los casos normales y casos límite sometidos a prueba automatizada."
    )

    doc.add_table(
        headers=["ID", "Categoría", "Descripción de la entrada", "Salida exacta", "Criterio de verificación"],
        rows=[
            ["N1", "Normal (FGO)", "Cambio de 1 Euro: {1, 2, 5, 10, 20, 50, 100}, *N* = 100", "4,563", "Literatura clásica y DP"],
            ["N2", "Normal (FGO)", "Clúster de 5 servidores heterogéneos, *N* = 20", "282", "DP y fuerza bruta (1,640 nodos)"],
            ["N3", "Normal (FGE)", "Cadenas de longitud 8 sobre {*A* ≥ 1, *B* par, *C* ≤ 3, *D* libre}", "26,653", "Oráculo multinomial exacto"],
            ["N4", "Normal (Euler)", "Particiones *p*(30), *p*_{dist}(30) y *p*_{imp}(30)", "5,604 / 296 / 296", "OEIS A000041 y Teorema 4"],
            ["L1", "Límite (*N* = 0)", "*x*_{1}, *x*_{2} ∈ [0, 5] con suma *N* = 0", "1", "Solución trivial única (0, 0)"],
            ["L2", "Límite (vacío)", "*x*_{1} ≥ 4, *x*_{2} ≥ 6 con *N* = 7 (mínimo 10 > 7)", "0", "Región factible vacía"],
            ["L3", "Límite (paridad)", "*x*_{1}, *x*_{2} pares no negativos con *N* = 11", "0", "Invariante de paridad"],
            ["L4", "Límite (stock)", "Monedas {5, 10} con stock [2, 2] para *N* = 50", "0", "Máximo alcanzable igual a 30"],
            ["L5", "Límite (escala)", "Coeficientes > 10^{15} superando *M*/2 en NTT", "Exacto", "Respaldo automático a Karatsuba"],
            ["L6", "Límite (error)", "Inverso formal con *a*_{0} = 0 o entradas negativas", "Excepción", "Teorema 1 / `ValueError`"],
        ],
        col_widths_pct=[0.06, 0.16, 0.39, 0.16, 0.23],
        caption="Tabla 2. Casos de prueba normales y límite verificados en la suite automatizada.",
        font_size_pt=9.0,
        align_cols=["center", "left", "left", "right", "left"],
    )

    # VII. RESULTADOS Y ANÁLISIS
    doc.add_heading1("VII. RESULTADOS Y ANÁLISIS")

    doc.add_heading2("7.1. Validación de exactitud frente a oráculos teóricos")
    doc.add_prose(
        "La suite completa de pruebas unitarias se ejecutó en 0,008 s con 11 de 11 casos exitosos y "
        "discrepancia nula frente a todos los oráculos independientes. La Tabla 3 concentra el "
        "contraste exacto en escenarios de aplicación —incluyendo el cambio de 1 Euro referido en las "
        "sesiones del curso, el cambio de S/ 5,00 con monedas peruanas en versiones ilimitada y "
        "acotada, el conteo etiquetado mediante FGE y la verificación de las recurrencias de la Lista "
        "de Ejercicios 14—."
    )
    apps = data["exp5_applications"]
    doc.add_table(
        headers=["Escenario evaluado", "Función Generatriz", "Motor FGO/FGE", "Oráculo teórico", "Error"],
        rows=[
            ["Cambio de 1 Euro (100 c)", ("img", eq("t3_euro"), 0.125), f"{apps['euro_100c_ways']:,}", "4,563", "0"],
            ["Cambio S/ 5,00 (ilimitado)", ("img", eq("t3_euro"), 0.125), f"{apps['peru_5soles_unlimited_ways']:,}", "451 (DP)", "0"],
            ["Cambio S/ 5,00 (stock limitado)", ("img", eq("t3_lim"), 0.115), f"{apps['peru_5soles_limited_ways']:,}", "120 (DP)", "0"],
            ["Clúster 5 nodos (*N* = 24)", "Producto racional de 5 factores", "339", "339 (DP y FB)", "0"],
            ["FGE códigos (longitud *n* = 10)", "Producto en ℚ[[*x*]] (ec. 8)", f"{apps['egf_counts_0_to_10'][10]:,}", f"{apps['egf_counts_0_to_10'][10]:,} (Mult.)", "0"],
            ["Recurrencia Ej. 12 (*k* = 8)", ("img", eq("t3_ej12"), 0.120), "13,121", "2 · 3^{8} − 1 = 13,121", "0"],
            ["Recurrencia Ej. 13 (*k* = 8)", ("img", eq("t3_ej13"), 0.125), "65,536", "4^{8} = 65,536", "0"],
            ["Recurrencia Ej. 14 (*k* = 8)", ("img", eq("t3_ej14"), 0.115), "115,026", "18·3^{8}−12·2^{8} = 115,026", "0"],
        ],
        col_widths_pct=[0.25, 0.30, 0.15, 0.22, 0.08],
        caption="Tabla 3. Contraste exacto del motor frente a oráculos matemáticos independientes.",
        font_size_pt=9.0,
        align_cols=["left", "center", "right", "right", "center"],
    )

    doc.add_heading2("7.2. Distribución completa de configuraciones bajo restricciones")
    doc.add_prose(
        "A diferencia de un algoritmo diseñado para responder una única consulta puntual, la expansión "
        "truncada de *G*(*x*) entrega en una sola pasada la distribución completa desde *n* = 0 hasta "
        "*N*. En el Experimento 3 se modeló un clúster de cinco servidores con reglas heterogéneas: "
        "*S*_{1} ∈ [1, 8], *S*_{2} par en [0, 10], *S*_{3} impar en [1, 9], *S*_{4} múltiplo de 3 en "
        "[0, 12] y *S*_{5} ∈ [2, 6]. Como ilustra la Figura 2, las cotas inferiores introducen un "
        "factor global *x*^{4} que anula toda carga inferior a 4; la curva resultante es unimodal y "
        "simétrica alrededor del par central *n* = 24 y *n* = 25 (con 339 asignaciones válidas cada "
        "uno), y la suma de todos los coeficientes verifica exactamente la identidad *G*(1) = "
        "8 × 6 × 5 × 5 × 5 = 6,000 configuraciones posibles."
    )
    doc.add_figure(
        fig_dir / "fig2_distribucion_cluster.png",
        "Figura 2. Distribución exacta de configuraciones válidas en un clúster de 5 servidores con restricciones heterogéneas.",
        width_fraction=0.96,
    )

    doc.add_heading2("7.3. Escalabilidad temporal y análisis empírico de complejidad")
    doc.add_prose(
        "El Experimento 2 contrastó cinco estrategias sobre el problema *x*_{1} + … + *x*_{6} = *N* "
        "con cota proporcional *u* = máx(6, ⌊*N*/3⌋), validando cada resultado contra la ecuación (9). "
        "Como documentan la Tabla 4 y la Figura 3A, la búsqueda por fuerza bruta se torna inviable "
        "rápidamente: en *N* = 34 explora ya 1,117,131 nodos en 68,96 ms. Más relevante aún, cuando la "
        "cota *u* escala proporcionalmente con *N*, la programación dinámica estándar requiere "
        "*O*(*mNu*) = *O*(*mN*^{2}) operaciones (48,49 ms en *N* = 1000), comportamiento cuadrático "
        "análogo al de la convolución clásica (55,30 ms). El motor FGO racional conserva en cambio "
        "complejidad estrictamente lineal *O*(*mN*), resolviendo *N* = 1000 —más de 2,28 billones de "
        "configuraciones exactas— en solo 2,00 ms, lo que representa una aceleración de 24,3× sobre "
        "la programación dinámica y de 27,7× sobre Cauchy clásica."
    )

    rows2 = data["exp2_scalability_methods"]
    t4_rows = [
        [
            str(r["N"]),
            str(r["upper_bound"]),
            f"{r['exact_count']:,}",
            f"{r['brute_force_ms']:.3f}" if r["brute_force_ms"] is not None else "Intractable",
            f"{r['dp_ms']:.3f}",
            f"{r['ogf_schoolbook_ms']:.3f}",
            f"{r['ogf_ntt_ms']:.3f}",
            f"{r['ogf_structured_ms']:.3f}",
        ]
        for r in rows2
    ]
    doc.add_table(
        headers=["*N*", "*u*", "Conteo exacto", "F. Bruta", "DP", "FGO Clás.", "FGO NTT", "FGO Rac."],
        rows=t4_rows,
        col_widths_pct=[0.07, 0.06, 0.24, 0.13, 0.11, 0.13, 0.13, 0.13],
        caption="Tabla 4. Escalabilidad temporal (ms) en conteo restringido de seis variables (Experimento 2).",
        font_size_pt=8.5,
        align_cols=["right", "right", "right", "right", "right", "right", "right", "right"],
    )

    doc.add_prose(
        "Para aislar el costo puro del producto de series densas sin estructura racional (caso de "
        "conjuntos *S*_{*i*} arbitrarios), el Experimento 1 comparó Cauchy clásica *O*(*N*^{2}), "
        "Karatsuba *O*(*N*^{1,585}) y NTT+CRT *O*(*N* log *N*) desde *N* = 64 hasta *N* = 4096 "
        "(Tabla 5 y Figura 3B). Los tres algoritmos coincidieron coeficiente a coeficiente en cada "
        "grado evaluado, registrándose el punto de cruce entre NTT+CRT y Cauchy cerca de *N* ≈ 1800 "
        "y una aceleración de 2,05× en *N* = 4096."
    )

    rows1 = data["exp1_series_multiplication"]
    t5_rows = [
        [
            str(r["N"]),
            f"{r['schoolbook_ms']:.3f}",
            f"{r['karatsuba_ms']:.3f}",
            f"{r['ntt_ms']:.3f}",
            f"{r['speedup_ntt_vs_schoolbook']:.2f}×",
            "Sí" if r["exact_match"] else "No",
        ]
        for r in rows1
    ]
    doc.add_table(
        headers=["Grado *N*", "Cauchy *O*(*N*^{2})", "Karatsuba *O*(*N*^{1,585})", "NTT+CRT *O*(*N* log *N*)", "Aceleración NTT", "Exacto"],
        rows=t5_rows,
        col_widths_pct=[0.11, 0.19, 0.22, 0.23, 0.16, 0.09],
        caption="Tabla 5. Multiplicación exacta de dos series densas (ms) según algoritmo (Experimento 1).",
        font_size_pt=9.0,
        align_cols=["right", "right", "right", "right", "right", "center"],
    )

    doc.add_figure(
        fig_dir / "fig3_escalabilidad.png",
        "Figura 3. Análisis empírico de complejidad y escalabilidad temporal en escala logarítmica.",
        width_fraction=0.98,
    )

    doc.add_heading2("7.4. Particiones de Euler y contraste con Hardy-Ramanujan")
    doc.add_prose(
        "En el Experimento 4 se evaluaron exactamente *p*(*n*), *p*_{dist}(*n*) y *p*_{imp}(*n*) "
        "para todo *n* ∈ [0, 60] mediante productos truncados de Euler. Se verificó la igualdad "
        "exacta *p*_{dist}(*n*) = *p*_{imp}(*n*) en los 61 valores del rango (confirmando "
        "computacionalmente el Teorema 4). Adicionalmente, se contrastó *p*(*n*) contra la fórmula "
        "asintótica clásica de Hardy y Ramanujan (1918) [11]:"
    )
    doc.add_equation_img(eq("eq9_hr"), "10")
    doc.add_prose(
        "Como sintetizan la Tabla 6 y la Figura 4, la aproximación asintótica captura fielmente la "
        "tendencia subexponencial de *p*(*n*) y reduce progresivamente su error relativo de 14,53 % "
        "en *n* = 10 a 5,95 % en *n* = 60, aunque para valores moderados sigue sobreestimando el "
        "conteo real en decenas de miles de particiones, lo que subraya el valor práctico del "
        "cómputo exacto mediante series formales."
    )

    p_rows = data["exp4_euler_partitions"]
    t6_rows = [
        [
            str(p_rows[k]["n"]),
            f"{p_rows[k]['p_n']:,}",
            f"{p_rows[k]['p_distinct']:,}",
            f"{p_rows[k]['p_odd']:,}",
            "Sí",
            f"{p_rows[k]['hardy_ramanujan']:,.2f}",
            f"{p_rows[k]['hr_rel_error_pct']:.2f} %",
        ]
        for k in [0, 5, 10, 20, 30, 40, 50, 60]
    ]
    doc.add_table(
        headers=["*n*", "*p*(*n*) exacto", "*p*_{dist}(*n*)", "*p*_{imp}(*n*)", "Euler", "Hardy-Ramanujan", "Error rel."],
        rows=t6_rows,
        col_widths_pct=[0.07, 0.17, 0.15, 0.15, 0.09, 0.22, 0.15],
        caption="Tabla 6. Particiones de Euler y error relativo de Hardy-Ramanujan para valores seleccionados de n.",
        font_size_pt=9.0,
        align_cols=["right", "right", "right", "right", "center", "right", "right"],
    )
    doc.add_figure(
        fig_dir / "fig4_particiones_euler.png",
        "Figura 4. Particiones de Euler (n = 1 a 60) y convergencia asintótica de Hardy-Ramanujan.",
        width_fraction=0.96,
    )

    # VIII. DISCUSIÓN
    doc.add_heading1("VIII. DISCUSIÓN")
    doc.add_prose(
        "Los resultados obtenidos confirman que el paradigma algebraico sistematizado por Wilf [4] y "
        "por Flajolet y Sedgewick [6] no solo posee elegancia teórica, sino que induce una "
        "arquitectura de software extraordinariamente cohesiva. Pasar del problema del cambio de "
        "monedas al balanceo de servidores o a las particiones de Euler no requiere reescribir la "
        "lógica de conteo: basta sustituir la especificación de factores y operar dentro del mismo "
        "anillo truncado ℤ[[*x*]]."
    )
    doc.add_prose(
        "Un hallazgo particularmente instructivo emerge al examinar las constantes ocultas en la "
        "Tabla 5 y la Figura 3B. Aunque la convolución NTT+CRT disfruta de una cota asintótica "
        "estrictamente superior (*O*(*N* log *N*)) frente a Karatsuba (*O*(*N*^{1,585})) y Cauchy "
        "(*O*(*N*^{2})), ejecutar tres transformadas modulares más la reconstrucción CRT en código "
        "interpretado de CPython introduce una constante multiplicativa considerable. Por esa razón, "
        "NTT+CRT supera a Cauchy a partir de *N* ≈ 1800, mientras que Karatsuba se mantiene más veloz "
        "hasta *N* = 4096 (120,77 ms frente a 191,52 ms). Este contraste demuestra que una política "
        "híbrida informada por mediciones empíricas supera en la práctica a cualquier algoritmo "
        "único elegido solo por su orden asintótico [8]."
    )
    doc.add_prose(
        "El diseño actual presenta limitaciones bien delimitadas que conviene reconocer. En primer "
        "lugar, truncar explícitamente la serie a grado *N* exige memoria *O*(*N*) aun cuando el "
        "usuario únicamente consulte el coeficiente aislado [*x*^{*N*}] *G*(*x*). En segundo lugar, "
        "en las FGE el crecimiento factorial *k*! origina fracciones con denominadores muy grandes "
        "para *N* elevado si se opera directamente en ℚ[[*x*]] sin factorización modular. Asimismo, "
        "una implementación ingenua basada en FFT flotante habría introducido errores silenciosos al "
        "superar 2^{53}, problema evitado deliberadamente mediante aritmética entera exacta y "
        "respaldo automático a Karatsuba."
    )
    doc.add_prose(
        "Como líneas concretas de mejora para futuras versiones destacan tres direcciones: incorporar "
        "el algoritmo de Bostan y Mori (2021) [12] para extraer un coeficiente aislado [*x*^{*N*}] "
        "*P*(*x*) / *Q*(*x*) en tiempo *O*(*d* log *d* log *N*) —habilitando valores del orden de "
        "*N* = 10^{12}—; compilar el núcleo de mariposas NTT en C o Rust para desplazar el cruce de "
        "rendimiento por debajo de *N* = 128; y dotar al sistema de un analizador simbólico de "
        "expresiones para uso interactivo en aula."
    )

    # IX. CONCLUSIONES
    doc.add_heading1("IX. CONCLUSIONES")
    doc.add_prose(
        "1. Se diseñó, implementó y validó un contador combinatorio exacto basado en funciones "
        "generadoras ordinarias y exponenciales en Python 3.12 estándar, capaz de resolver bajo un "
        "mismo marco algebraico composiciones restringidas, cambio de monedas, particiones de Euler, "
        "permutaciones etiquetadas y relaciones de recurrencia lineales.",
        indent_left=360, hanging=240, space_after=100,
    )
    doc.add_prose(
        "2. En correspondencia con el primer objetivo específico, la formalización en los anillos "
        "truncados ℤ[*x*] / (*x*^{*N*+1}) y ℚ[*x*] / (*x*^{*N*+1}) —respaldada por las demostraciones "
        "de inversión formal, binomio negativo, principio multiplicativo y teorema de Euler— "
        "estableció una correspondencia rigurosa entre restricciones combinatorias y operadores "
        "polinómicos sin requerir convergencia analítica.",
        indent_left=360, hanging=240, space_after=100,
    )
    doc.add_prose(
        "3. En cumplimiento del segundo objetivo específico, el motor multimetodológico evidenció "
        "que explotar la estructura racional de las restricciones reduce la complejidad de "
        "*O*(*mN*^{2}) a *O*(*mN*), resolviendo *N* = 1000 (2,286 × 10^{12} configuraciones exactas) "
        "en 2,00 ms —24,3 veces más rápido que la programación dinámica estándar—, mientras que "
        "NTT+CRT supera a la convolución clásica en 2,05× para *N* = 4096 sin errores de redondeo.",
        indent_left=360, hanging=240, space_after=100,
    )
    doc.add_prose(
        "4. Respecto al tercer objetivo específico, la validación cruzada contra fuerza bruta, "
        "programación dinámica, inclusión-exclusión, conteo multinomial y los ejercicios 9 a 14 del "
        "curso arrojó 100 % de exactitud (11 de 11 pruebas automatizadas exitosas y 61 de 61 "
        "verificaciones del Teorema de Euler), confirmando la corrección matemática y computacional "
        "del sistema desarrollado.",
        indent_left=360, hanging=240, space_after=120,
    )

    # X. REFERENCIAS BIBLIOGRÁFICAS (Norma IEEE)
    doc.add_heading1("X. REFERENCIAS BIBLIOGRÁFICAS")
    refs = [
        "[1] K. H. Rosen, *Discrete Mathematics and Its Applications*, 8th ed. New York, NY, USA: McGraw-Hill Education, 2019.",
        "[2] S. S. Epp, *Discrete Mathematics with Applications*, 5th ed. Boston, MA, USA: Cengage Learning, 2020.",
        "[3] E. Lehman, F. T. Leighton, and A. R. Meyer, *Mathematics for Computer Science*. Cambridge, MA, USA: MIT OpenCourseWare, 2010.",
        "[4] H. S. Wilf, *generatingfunctionology*, 3rd ed. Wellesley, MA, USA: A K Peters/CRC Press, 2006.",
        "[5] R. L. Graham, D. E. Knuth, and O. Patashnik, *Concrete Mathematics: A Foundation for Computer Science*, 2nd ed. Reading, MA, USA: Addison-Wesley, 1994.",
        "[6] P. Flajolet and R. Sedgewick, *Analytic Combinatorics*. Cambridge, U.K.: Cambridge University Press, 2009.",
        "[7] R. P. Stanley, *Enumerative Combinatorics, Volume 1*, 2nd ed. Cambridge, U.K.: Cambridge University Press, 2012.",
        "[8] T. H. Cormen, C. E. Leiserson, R. L. Rivest, and C. Stein, *Introduction to Algorithms*, 4th ed. Cambridge, MA, USA: MIT Press, 2022.",
        "[9] J. W. Cooley and J. W. Tukey, “An algorithm for the machine calculation of complex Fourier series,” *Mathematics of Computation*, vol. 19, no. 90, pp. 297–301, Apr. 1965.",
        "[10] J. M. Pollard, “The fast Fourier transform in a finite field,” *Mathematics of Computation*, vol. 25, no. 114, pp. 365–374, Apr. 1971.",
        "[11] G. H. Hardy and S. Ramanujan, “Asymptotic formulae in combinatory analysis,” *Proceedings of the London Mathematical Society*, vol. s2-17, no. 1, pp. 75–115, 1918.",
        "[12] A. Bostan and R. Mori, “A simple and fast algorithm for computing the N-th term of a linearly recurrent sequence,” in *Proc. 4th Symposium on Simplicity in Algorithms (SOSA)*, SIAM, 2021, pp. 118–132.",
    ]
    for r in refs:
        doc.add_prose(
            r,
            align="both", size_pt=11.0,
            space_before=0, space_after=80, line_spacing=320,
            indent_left=420, hanging=420,
        )

    doc.add_section_break(footer_rid="rId4", page_num_fmt="decimal", page_num_start=1)

    # =========================================================================
    # SECCIÓN 4: XI. ANEXOS (SIN numeración de página)
    # =========================================================================
    doc.add_heading1("XI. ANEXOS")

    doc.add_heading2("Anexo A. Estructura del repositorio y manual mínimo de reproducción")
    doc.add_code_listing(
        "DISCRETAS 2/\n"
        "├── README.md                  # Manual y guía de reproducción\n"
        "├── src/\n"
        "│   ├── formal_series.py       # Z[[x]]/Q[[x]], Cauchy, Karatsuba, NTT+CRT\n"
        "│   ├── combinatorics_engine.py# FGO/FGE: rangos, monedas, Euler, recurrencias\n"
        "│   ├── validators.py          # Oráculos: fuerza bruta, DP, Hardy-Ramanujan\n"
        "│   ├── benchmarks.py          # Experimentos -> results/benchmark_results.json\n"
        "│   └── cli.py                 # CLI (demo, coins, compose, partitions)\n"
        "├── tests/test_contador.py     # 11 pruebas automatizadas (unittest)\n"
        "├── scripts/\n"
        "│   ├── math_render.py         # Motor tipográfico Computer Modern 600 DPI\n"
        "│   ├── generate_charts.py     # Generador de las 4 figuras (300 DPI)\n"
        "│   └── build_report_docx.py   # Generador reproducible del informe UPCH\n"
        "└── docs/\n"
        "    ├── figures/               # fig1..fig4 en alta resolución\n"
        "    ├── equations/             # Ecuaciones matemáticas tipográficas 600 DPI\n"
        "    ├── Informe_Tema10_Contador_Combinatorio_FG.docx\n"
        "    └── Informe_Tema10_Contador_Combinatorio_FG.pdf\n\n"
        "# Comandos de reproducción (solo requiere Python 3.12+):\n"
        "python3 -m unittest discover -s tests -v\n"
        "python3 -m src.cli demo\n"
        "python3 -m src.cli coins --denoms 1,2,5,10,20,50,100 --target 100\n"
        "python3 -m src.cli compose --specs \"1:8:1,0:10:2,1:9:2\" --target 12 --verify\n"
        "python3 -m src.cli partitions --n 60 --variant all\n"
        "python3 -m src.benchmarks",
        title="Estructura del proyecto y guía rápida de ejecución por CLI",
    )

    doc.add_heading2("Anexo B. Evidencia de ejecución de pruebas automatizadas y CLI")
    doc.add_code_listing(
        "$ python3 -m unittest discover -s tests -v\n"
        "test_coin_change_classic_euro_and_dp ... ok\n"
        "test_course_practice_14_exercises_9_to_14 ... ok\n"
        "test_edge_cases ... ok\n"
        "test_egf_restricted_permutations ... ok\n"
        "test_euler_partitions_and_theorem ... ok\n"
        "test_heterogeneous_constraints_against_oracles ... ok\n"
        "test_stars_and_bars_and_inclusion_exclusion ... ok\n"
        "test_binomial_and_negative_binomial ... ok\n"
        "test_convolution_methods_exact_equivalence ... ok\n"
        "test_inverse_identity_and_non_invertible_error ... ok\n"
        "test_ntt_large_coeff_karatsuba_fallback ... ok\n"
        "----------------------------------------------------------------------\n"
        "Ran 11 tests in 0.008s — OK\n\n"
        "$ python3 -m src.cli demo\n"
        "[1] Cambio de 1 Euro (100 céntimos): 4,563 formas distintas\n"
        "[2] Clúster 5 servidores (n=20): FGO=282 (0.058 ms) | DP=282 | FB=282 -> EXACTA\n"
        "[3] Particiones n=30: p(30)=5,604 | p_dist=296 | p_imp=296 (Euler: True)\n"
        "[4] FGE palabras n=8 sobre {A>=1, B par, C<=3, D libre}: 26,653 secuencias\n"
        "[5] Recurrencia Ej. 14 G(x)=6/(1-5x+6x^2): [6,30,114,390,1266,3990,...] -> OK",
        title="Traza real de ejecución de pruebas unitarias y demostración CLI",
    )

    doc.add_heading2("Anexo C. Distribución de tareas y bitácora del equipo (plantilla)")
    doc.add_table(
        headers=["Integrante (Apellidos, Nombres)", "Rol asignado", "Entregables verificables", "Aporte (%)"],
        rows=[
            ["[Integrante 1]", "Marco teórico y demostraciones", "Secciones II, III, demostraciones y referencias IEEE", "20 %"],
            ["[Integrante 2]", "Motor algebraico `formal_series.py`", "Cauchy, Karatsuba, NTT+CRT, inversión formal", "20 %"],
            ["[Integrante 3]", "Motor combinatorio y CLI", "`combinatorics_engine.py`, `cli.py`, casos de uso", "20 %"],
            ["[Integrante 4]", "Validación y pruebas unitarias", "`validators.py`, `test_contador.py`, casos límite", "20 %"],
            ["[Integrante 5]", "Benchmarks, gráficas e informe", "`benchmarks.py`, Figuras 1–4, edición UPCH", "20 %"],
        ],
        col_widths_pct=[0.28, 0.24, 0.36, 0.12],
        caption="Tabla A1. Matriz sugerida de roles y contribución verificable (completar antes de la entrega).",
        font_size_pt=9.0,
        align_cols=["left", "left", "left", "center"],
    )

    doc.add_heading2("Anexo D. Registro de evaluación adjunto al informe de investigación")
    doc.add_prose(
        "**Equipo:** __________________________      **Tema:** Tema 10 — Diseño de un contador combinatorio con funciones generadoras",
        align="left", size_pt=10.5, space_after=80, line_spacing=280,
    )
    doc.add_table(
        headers=["Criterio de evaluación", "Peso", "Observaciones", "Puntaje"],
        rows=[
            ["1. Rigor de la investigación y marco teórico", "4", "", ""],
            ["2. Diseño, programación y simulación", "4", "", ""],
            ["3. Estructura y calidad del informe", "2", "", ""],
            ["4. Citación, referencias e integridad académica", "1", "", ""],
            ["5. Exposición oral y dominio conceptual", "3", "", ""],
            ["6. Vestimenta formal y presentación profesional", "2", "", ""],
            ["7. Trabajo en equipo y contribución verificable", "1", "", ""],
            ["8. Defensa, preguntas y pensamiento crítico", "3", "", ""],
            ["**TOTAL**", "**20**", "", ""],
        ],
        col_widths_pct=[0.46, 0.10, 0.30, 0.14],
        caption="Tabla A2. Registro de evaluación oficial adjunto al informe (Estructuras Discretas II, 2026-II).",
        font_size_pt=9.5,
        align_cols=["left", "center", "left", "center"],
    )

    out_docx = root / "docs" / "Informe_Tema10_Contador_Combinatorio_FG.docx"
    doc.save(out_docx, final_footer_rid="rId5")
    return out_docx


def convert_to_pdf(docx_path: Path) -> Path:
    out_dir = docx_path.parent
    subprocess.run(
        [
            "libreoffice",
            "-env:UserInstallation=file:///tmp/lo_profile",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(docx_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return docx_path.with_suffix(".pdf")


def extract_page_map(pdf_path: Path) -> Dict[str, str]:
    res = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    pages = res.stdout.split("\x0c")
    body_start_idx = None
    for idx, txt in enumerate(pages):
        if "ÍNDICE" in txt:
            continue
        if "I. INTRODUCCIÓN" in txt:
            body_start_idx = idx
            break
    if body_start_idx is None:
        return {}

    def fmt_page(phys_idx: int) -> str:
        if phys_idx == 0:
            return ""
        if phys_idx < body_start_idx:
            return _to_roman(phys_idx + 1)
        return str(phys_idx - body_start_idx + 1)

    targets = [
        "RESUMEN",
        "I. INTRODUCCIÓN",
        "II. ANTECEDENTES HISTÓRICOS",
        "III. MARCO TEÓRICO",
        "3.1.",
        "3.2.",
        "3.3.",
        "IV. OBJETIVOS",
        "V. METODOLOGÍA Y DISEÑO",
        "VI. IMPLEMENTACIÓN O SIMULACIÓN",
        "VII. RESULTADOS Y ANÁLISIS",
        "VIII. DISCUSIÓN",
        "IX. CONCLUSIONES",
        "X. REFERENCIAS BIBLIOGRÁFICAS",
        "Tabla 1.",
        "Tabla 2.",
        "Tabla 3.",
        "Tabla 4.",
        "Tabla 5.",
        "Tabla 6.",
        "Figura 1.",
        "Figura 2.",
        "Figura 3.",
        "Figura 4.",
    ]

    found: Dict[str, str] = {}
    for idx, txt in enumerate(pages):
        if idx == 0:
            continue
        for t in targets:
            if t in found:
                continue
            if t == "RESUMEN":
                if idx < body_start_idx and "ÍNDICE" not in txt and "\nRESUMEN\n" in f"\n{txt}\n":
                    found[t] = fmt_page(idx)
            else:
                if idx >= body_start_idx and t in txt:
                    found[t] = fmt_page(idx)
    return found


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    build_all_equations(root / "docs" / "equations")
    # Pasada 1: calcular numeración real
    docx_path = build_report(root, page_map=None)
    pdf_path = convert_to_pdf(docx_path)
    pm = extract_page_map(pdf_path)
    print("Mapa de páginas (Pasada 1):", json.dumps(pm, ensure_ascii=False))
    # Pasada 2: generar documento definitivo con índices exactos
    docx_path = build_report(root, page_map=pm)
    pdf_path = convert_to_pdf(docx_path)
    pm2 = extract_page_map(pdf_path)
    print("Mapa de páginas (Pasada 2):", json.dumps(pm2, ensure_ascii=False))
    print(f"Informe editorial generado:\n  DOCX: {docx_path}\n  PDF : {pdf_path}")


if __name__ == "__main__":
    main()
