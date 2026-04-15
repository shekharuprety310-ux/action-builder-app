#!/usr/bin/env python3
"""Parse New Project - Draft Scope of Work v1.dotx and extract cost centres + items."""
import zipfile
import re
import json
import xml.etree.ElementTree as ET
from collections import OrderedDict

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}

path = "project files/New Project - Draft Scope of Work v1.dotx"


def paragraph_text(p):
    parts = []
    for t in p.findall(".//w:t", NS):
        if t.text:
            parts.append(t.text)
        if t.tail:
            parts.append(t.tail)
    return "".join(parts).strip()


def get_outline_level(p):
    ppr = p.find("w:pPr", NS)
    if ppr is None:
        return None
    outline = ppr.find("w:outlineLvl", NS)
    if outline is not None:
        val = outline.get(f"{{{NS['w']}}}val")
        if val is not None:
            try:
                return int(val)
            except ValueError:
                pass
    pstyle = ppr.find("w:pStyle", NS)
    if pstyle is not None:
        sid = pstyle.get(f"{{{NS['w']}}}val") or ""
        m = re.match(r"Heading\s*(\d+)", sid, re.I)
        if m:
            return int(m.group(1)) - 1
        if "Heading1" in sid or sid == "Heading1":
            return 0
        if "Heading2" in sid or sid == "Heading2":
            return 1
        if "Heading3" in sid or sid == "Heading3":
            return 2
    return None


def main():
    with zipfile.ZipFile(path, "r") as z:
        xml_bytes = z.read("word/document.xml")

    root = ET.fromstring(xml_bytes)
    body = root.find("w:body", NS)
    paragraphs = body.findall("w:p", NS)

    rows = []
    for p in paragraphs:
        txt = paragraph_text(p)
        if not txt:
            continue
        ol = get_outline_level(p)
        rows.append({"text": txt, "outline": ol})

    # Dump plain sequence for debugging
    with open("/tmp/dotx_paragraphs.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=0, ensure_ascii=False)

    # Find "Design Characteristics" (case-insensitive)
    start_idx = None
    for i, r in enumerate(rows):
        t = re.sub(r"\s+", " ", r["text"].lower())
        if "design characteristics" in t or "design characteristic" in t:
            start_idx = i
            break

    print("start_idx", start_idx, "total paragraphs", len(rows))
    if start_idx is not None:
        for j in range(start_idx, min(start_idx + 15, len(rows))):
            print(j, rows[j])

    # Find exclusions section
    ex_idx = None
    for i, r in enumerate(rows):
        t = r["text"].lower()
        if "exclusion" in t and len(t) < 80:
            ex_idx = i
            print("possible exclusion heading", i, r["text"][:80])


if __name__ == "__main__":
    main()
