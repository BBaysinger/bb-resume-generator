#!/usr/bin/env python3
"""Normalize bullet list indentation inside a DOCX file."""

from __future__ import annotations

import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_MAP = {"w": W_NS}


def qn(tag: str) -> str:
    """Qualified XML name helper."""
    return f"{{{W_NS}}}{tag}"


def normalize_lists(docx_path: str | os.PathLike[str]) -> bool:
    docx_path = Path(docx_path)
    """Set bullet list indentation to zero left / 0.25in hanging."""
    with zipfile.ZipFile(docx_path, "r") as zin:
        try:
            numbering_xml = zin.read("word/numbering.xml")
        except KeyError:
            return False

    if b"xmlns:w=" not in numbering_xml:
        needle = b"<ns0:numbering "
        if needle in numbering_xml:
            numbering_xml = numbering_xml.replace(
                needle,
                needle + b'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ',
                1,
            )

    ET.register_namespace("w", W_NS)

    root = ET.fromstring(numbering_xml)
    changed = False

    for lvl in root.findall(".//w:lvl", NS_MAP):
        num_fmt = lvl.find("w:numFmt", NS_MAP)
        if num_fmt is None or num_fmt.get(qn("val")) != "bullet":
            continue

        ppr = lvl.find("w:pPr", NS_MAP)
        if ppr is None:
            ppr = ET.SubElement(lvl, qn("pPr"))

        ind = ppr.find("w:ind", NS_MAP)
        if ind is None:
            ind = ET.SubElement(ppr, qn("ind"))

        ind.set(qn("left"), "0")
        ind.set(qn("hanging"), "360")  # keep hanging indent for text alignment
        ind.set(qn("firstLine"), "0")
        changed = True

    if not changed:
        return False

    updated_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    tmp_path = docx_path.with_suffix(docx_path.suffix + ".tmp")
    with zipfile.ZipFile(docx_path, "r") as zin, zipfile.ZipFile(tmp_path, "w") as zout:
        for item in zin.infolist():
            data = updated_xml if item.filename == "word/numbering.xml" else zin.read(item.filename)
            zout.writestr(item, data)

    os.replace(tmp_path, docx_path)
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: normalize_docx_lists.py <path-to.docx>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"DOCX not found: {path}", file=sys.stderr)
        return 1

    if normalize_lists(path):
        print(f"Normalized bullet indentation in {path}")
    else:
        print("No bullet definitions were updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
