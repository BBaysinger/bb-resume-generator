#!/usr/bin/env python3
"""Apply consistent typography and page setup to a DOCX.

Goal: make DOCX output visually align with converter CSS defaults.

This script intentionally focuses on global/structural formatting that Word
represents well:
- Page margins
- Default font family, size, color
- Default paragraph spacing + line spacing
- Heading 1/2/3 sizes + spacing + color
- Hyperlink color + no-underline

It does not attempt to replicate CSS-only behaviors like pseudo-elements
(e.g., `li::before`) or complex selector-based styling.
"""

from __future__ import annotations

import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_MAP = {"w": W_NS}


def qn(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def _ensure(parent: ET.Element, child_tag: str) -> ET.Element:
    child = parent.find(f"w:{child_tag}", NS_MAP)
    if child is None:
        child = ET.SubElement(parent, qn(child_tag))
    return child


def _ensure_under(parent: ET.Element, path_tags: list[str]) -> ET.Element:
    node = parent
    for tag in path_tags:
        node = _ensure(node, tag)
    return node


def _set_rfonts(rpr: ET.Element, font_name: str) -> None:
    rfonts = _ensure(rpr, "rFonts")
    # Set all common script slots.
    rfonts.set(qn("ascii"), font_name)
    rfonts.set(qn("hAnsi"), font_name)
    rfonts.set(qn("eastAsia"), font_name)
    rfonts.set(qn("cs"), font_name)


def _set_font_size_half_points(rpr: ET.Element, half_points: int) -> None:
    sz = _ensure(rpr, "sz")
    sz.set(qn("val"), str(half_points))
    sz_cs = _ensure(rpr, "szCs")
    sz_cs.set(qn("val"), str(half_points))


def _set_color_hex(rpr: ET.Element, hex_rgb: str) -> None:
    color = _ensure(rpr, "color")
    color.set(qn("val"), hex_rgb.upper())


def _set_paragraph_spacing(
    ppr: ET.Element,
    *,
    before_twips: int | None = None,
    after_twips: int | None = None,
    line_240ths: int | None = None,
) -> None:
    spacing = _ensure(ppr, "spacing")

    if before_twips is not None:
        spacing.set(qn("before"), str(before_twips))

    if after_twips is not None:
        spacing.set(qn("after"), str(after_twips))

    if line_240ths is not None:
        # Use auto line spacing, in 240ths of a line.
        spacing.set(qn("lineRule"), "auto")
        spacing.set(qn("line"), str(line_240ths))


def _update_style(
    styles_root: ET.Element,
    *,
    style_id: str,
    font_name: str | None = None,
    font_size_half_points: int | None = None,
    color_hex: str | None = None,
    bold: bool | None = None,
    underline: str | None = None,
    spacing_before_twips: int | None = None,
    spacing_after_twips: int | None = None,
    line_240ths: int | None = None,
) -> bool:
    style = styles_root.find(f".//w:style[@w:styleId='{style_id}']", NS_MAP)
    if style is None:
        return False

    rpr = _ensure(style, "rPr")
    ppr = _ensure(style, "pPr")

    if font_name:
        _set_rfonts(rpr, font_name)

    if font_size_half_points is not None:
        _set_font_size_half_points(rpr, font_size_half_points)

    if color_hex:
        _set_color_hex(rpr, color_hex)

    if bold is not None:
        b = rpr.find("w:b", NS_MAP)
        if bold:
            if b is None:
                b = ET.SubElement(rpr, qn("b"))
            b.set(qn("val"), "1")
        else:
            if b is not None:
                rpr.remove(b)

    if underline is not None:
        u = _ensure(rpr, "u")
        u.set(qn("val"), underline)

    if any(v is not None for v in [spacing_before_twips, spacing_after_twips, line_240ths]):
        _set_paragraph_spacing(
            ppr,
            before_twips=spacing_before_twips,
            after_twips=spacing_after_twips,
            line_240ths=line_240ths,
        )

    return True


def _update_doc_defaults(styles_root: ET.Element, *, font_name: str, body_half_points: int, body_color: str) -> None:
    # docDefaults/rPrDefault/rPr
    rpr = _ensure_under(styles_root, ["docDefaults", "rPrDefault", "rPr"])
    _set_rfonts(rpr, font_name)
    _set_font_size_half_points(rpr, body_half_points)
    _set_color_hex(rpr, body_color)

    # docDefaults/pPrDefault/pPr
    ppr = _ensure_under(styles_root, ["docDefaults", "pPrDefault", "pPr"])
    # paragraph margin 4pt top/bottom => 80 twips
    _set_paragraph_spacing(ppr, before_twips=80, after_twips=80, line_240ths=324)  # 1.35 * 240


def _update_page_margins(document_root: ET.Element, *, margin_twips: int) -> bool:
    changed = False
    for sect in document_root.findall(".//w:sectPr", NS_MAP):
        pg_mar = sect.find("w:pgMar", NS_MAP)
        if pg_mar is None:
            pg_mar = ET.SubElement(sect, qn("pgMar"))

        for side in ["top", "right", "bottom", "left"]:
            old = pg_mar.get(qn(side))
            new_val = str(margin_twips)
            if old != new_val:
                pg_mar.set(qn(side), new_val)
                changed = True

    return changed


def normalize_styles(docx_path: str | os.PathLike[str]) -> bool:
    docx_path = Path(docx_path)

    with zipfile.ZipFile(docx_path, "r") as zin:
        styles_xml = zin.read("word/styles.xml")
        document_xml = zin.read("word/document.xml")

    ET.register_namespace("w", W_NS)

    styles_root = ET.fromstring(styles_xml)
    document_root = ET.fromstring(document_xml)

    # DOCX font choice
    #
    # The converter CSS uses an Inter-first font stack, but DOCX output is often
    # opened on machines without Inter installed. In that case Word may fall back
    # to an unexpected serif font.
    #
    # Use a broadly-available sans-serif as the default to keep output consistent.
    font_name = "Arial"
    body_color = "111111"
    heading_color = "87AD26"

    # Sizes are in half-points for docx (8pt => 16)
    body_sz = 16
    h1_sz = 37  # 18.5pt
    h2_sz = 24  # 12pt
    h3_sz = 19  # 9.5pt

    # CSS margins: resume.css uses 0.6in
    margin_twips = 864

    _update_doc_defaults(styles_root, font_name=font_name, body_half_points=body_sz, body_color=body_color)

    changed = False

    # Base paragraph style
    changed |= _update_style(
        styles_root,
        style_id="Normal",
        font_name=font_name,
        font_size_half_points=body_sz,
        color_hex=body_color,
        spacing_before_twips=80,
        spacing_after_twips=80,
        line_240ths=324,
    )

    # Headings
    changed |= _update_style(
        styles_root,
        style_id="Heading1",
        font_name=font_name,
        font_size_half_points=h1_sz,
        color_hex=heading_color,
        bold=True,
        spacing_after_twips=160,  # 8pt
        line_240ths=288,  # 1.2 * 240
    )

    changed |= _update_style(
        styles_root,
        style_id="Heading2",
        font_name=font_name,
        font_size_half_points=h2_sz,
        color_hex=heading_color,
        bold=True,
        spacing_before_twips=120,
        spacing_after_twips=120,
        line_240ths=288,
    )

    changed |= _update_style(
        styles_root,
        style_id="Heading3",
        font_name=font_name,
        font_size_half_points=h3_sz,
        color_hex=heading_color,
        bold=True,
        spacing_before_twips=160,
        spacing_after_twips=80,
        line_240ths=288,
    )

    # Hyperlinks: match CSS (green, no underline)
    changed |= _update_style(
        styles_root,
        style_id="Hyperlink",
        color_hex=heading_color,
        underline="none",
    )

    # Page margins
    changed |= _update_page_margins(document_root, margin_twips=margin_twips)

    if not changed:
        return False

    updated_styles = ET.tostring(styles_root, encoding="utf-8", xml_declaration=True)
    updated_document = ET.tostring(document_root, encoding="utf-8", xml_declaration=True)

    tmp_path = docx_path.with_suffix(docx_path.suffix + ".tmp")
    with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(tmp_path, "w") as zout:
        for item in zin.infolist():
            if item.filename == "word/styles.xml":
                zout.writestr(item, updated_styles)
            elif item.filename == "word/document.xml":
                zout.writestr(item, updated_document)
            else:
                zout.writestr(item, zin.read(item.filename))

    os.replace(tmp_path, docx_path)
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: normalize_docx_styles.py <path-to.docx>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"DOCX not found: {path}", file=sys.stderr)
        return 1

    if normalize_styles(path):
        print(f"Applied styles to {path}")
    else:
        print("No style changes were applied")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
