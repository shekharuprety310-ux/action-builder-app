#!/usr/bin/env python3
"""Build DOTX_COST_CENTRES + template defaults from New Project - Draft Scope of Work v1.dotx"""
import json
import re
import zipfile
import xml.etree.ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
DOTX = "project files/New Project - Draft Scope of Work v1.dotx"


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
    return None


def read_rows():
    with zipfile.ZipFile(DOTX, "r") as z:
        xml_bytes = z.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    body = root.find("w:body", NS)
    rows = []
    for p in body.findall("w:p", NS):
        txt = paragraph_text(p)
        if not txt:
            continue
        rows.append(txt.strip())
    return rows


def is_subheading(line: str) -> bool:
    s = line.strip()
    if len(s) < 3:
        return False
    if s.upper().startswith("NOTE:"):
        return False
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 3:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio >= 0.85 and s.upper() == s:
        return True
    return False


def line_to_item(line: str):
    if is_subheading(line):
        return {
            "name": line.strip(),
            "type": "Subheading",
            "category": "General",
            "room": None,
        }
    return {
        "name": line.strip(),
        "type": "Service",
        "category": "General",
        "room": None,
    }


def extract_scope_centres(rows):
    si_list = [i for i, t in enumerate(rows) if t == "Scope items:"]
    centres = []

    def cost_centre_name_before_scope(si):
        j = si - 1
        while j >= 0 and not rows[j].startswith("Assumptions:"):
            j -= 1
        if j < 0:
            raise RuntimeError(f"Could not find Assumptions before Scope items at index {si}")
        k = j - 1
        while k >= 0 and rows[k].upper().startswith("NOTE:"):
            k -= 1
        if k >= 2 and rows[k].startswith("Renovation"):
            return rows[k - 2]
        if j >= 3:
            return rows[j - 3]
        raise RuntimeError(f"Could not resolve cost centre name before Scope items at index {si}")

    for idx, si in enumerate(si_list):
        cc = cost_centre_name_before_scope(si)

        items_raw = []
        k = si + 1
        while k < len(rows):
            if rows[k] in ("Exclusions", "NOTES:") or (
                rows[k].lower() == "exclusions" and len(rows[k]) < 20
            ):
                break
            if k + 1 < len(rows) and rows[k + 1].startswith("New Build"):
                break
            items_raw.append(rows[k])
            k += 1

        items = [line_to_item(x) for x in items_raw if x.strip()]
        cats = sorted({i["category"] for i in items if i["type"] != "Subheading"})
        if not cats:
            cats = ["General"]
        centres.append({"name": cc, "items": items, "categories": cats})
    return centres


def extract_template_defaults(rows):
    ex_start = None
    for i, t in enumerate(rows):
        if t == "Exclusions":
            ex_start = i
            break
    exclusions = []
    notes = []
    if ex_start is not None:
        k = ex_start + 1
        if k < len(rows) and "following items" in rows[k].lower():
            k += 1
        while k < len(rows):
            line = rows[k]
            if line == "NOTES:" or line.startswith("NOTES:"):
                break
            if line.upper().startswith("NOTE:"):
                exclusions.append(line)
                k += 1
                continue
            if line.strip():
                exclusions.append(line)
            k += 1
        if k < len(rows) and rows[k].startswith("NOTES:"):
            k += 1
            while k < len(rows):
                line = rows[k]
                if line.startswith("SELECTION ITEMS:") or line.startswith("DESIGN CLARIFICATION"):
                    break
                if line.strip():
                    notes.append(line)
                k += 1
    return exclusions, notes


def normalise_exclusions_for_js(lines):
    out = []
    for i, text in enumerate(lines):
        label = text.split(".")[0][:40] if text else f"Item {i+1}"
        if len(label) < 3:
            label = re.split(r"[.:]", text)[0][:28] or "Exclusion"
        out.append({"label": label.strip(), "text": text.strip()})
    return out


def main():
    rows = read_rows()
    centres = extract_scope_centres(rows)
    ex_lines, note_lines = extract_template_defaults(rows)

    counts = {}
    cc_obj = {}
    for c in centres:
        base = c["name"]
        counts[base] = counts.get(base, 0) + 1
        cnt = counts[base]
        name = base if cnt == 1 else f"{base} ({cnt})"
        cc_obj[name] = {"items": c["items"], "categories": c["categories"]}

    ex_js = normalise_exclusions_for_js(ex_lines)

    payload = {
        "cost_centres": cc_obj,
        "default_exclusions": ex_js,
        "default_notes": note_lines,
        "meta": {
            "source": DOTX,
            "cost_centre_count": len(cc_obj),
            "scope_items_markers": len([i for i, t in enumerate(rows) if t == "Scope items:"]),
        },
    }

    with open("cost_centres_dotx.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Emit JS: assign to globals used by index.html
    def esc(s):
        return json.dumps(s, ensure_ascii=False)

    lines_out = [
        "// Auto-generated by build_dotx_dataset.py — do not edit by hand.",
        "const DOTX_COST_CENTRES = " + json.dumps(cc_obj, indent=2, ensure_ascii=False) + ";",
        "const DOTX_DEFAULT_EXCLUSIONS = " + json.dumps(ex_js, indent=2, ensure_ascii=False) + ";",
        "const DOTX_DEFAULT_NOTES = " + json.dumps(note_lines, indent=2, ensure_ascii=False) + ";",
    ]
    with open("cost_centres_dotx.js", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")

    print("Wrote cost_centres_dotx.json and cost_centres_dotx.js")
    print("Meta:", payload["meta"])
    print("Cost centres:", list(cc_obj.keys()))


if __name__ == "__main__":
    main()
