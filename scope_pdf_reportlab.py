"""
PDF scope of work — visual match to Word template
`project files/New Project - Draft Scope of Work v1.dotx`
(font sizes from OOXML: 14pt header labels, 11pt body, 10pt scope items / NB-Reno body;
 Times-like fonts; A4, ~72pt margins per word/settings.xml).
"""
from __future__ import annotations

import io
import re
import zipfile
import base64
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4
# Word pgMar 1440 twips = 72 pt
MARGIN_X = 72.0
MARGIN_TOP = 122.0
MARGIN_BOT = 98.0
TEXT = colors.HexColor("#000000")

FN = "Times-Roman"
FB = "Times-Bold"
DOTX_TEMPLATE = Path(__file__).resolve().parent / "project files" / "New Project - Draft Scope of Work v1.dotx"


def _load_template_branding(dotx_path: Path = DOTX_TEMPLATE) -> dict[str, Any]:
    """
    Pull real company letterhead image and footer lines from .dotx package.
    Uses default header (header2.xml -> image2.png) and default footer (footer2.xml).
    """
    out: dict[str, Any] = {"header_image": None, "footer_lines": []}
    if not dotx_path.is_file():
        return out
    try:
        with zipfile.ZipFile(dotx_path, "r") as z:
            # Header image is linked in word/_rels/header2.xml.rels as rId1 -> media/image2.png
            rels_path = "word/_rels/header2.xml.rels"
            if rels_path in z.namelist():
                import xml.etree.ElementTree as ET

                rels = ET.fromstring(z.read(rels_path))
                target = None
                for rel in rels:
                    t = rel.attrib.get("Type", "")
                    if t.endswith("/image"):
                        target = rel.attrib.get("Target")
                        break
                if target:
                    if not target.startswith("word/"):
                        target = "word/" + target.lstrip("/")
                    if target in z.namelist():
                        out["header_image"] = z.read(target)

            # Footer copy in footer2.xml
            f_path = "word/footer2.xml"
            if f_path in z.namelist():
                import xml.etree.ElementTree as ET

                NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                root = ET.fromstring(z.read(f_path))
                lines = []
                for p in root.findall(".//w:p", NS):
                    txt = "".join(t.text or "" for t in p.findall(".//w:t", NS)).strip()
                    if txt:
                        lines.append(txt)
                out["footer_lines"] = lines
    except Exception:
        return out
    return out


def _wrap_lines(c: canvas.Canvas, text: str, font: str, size: float, max_w: float) -> list[str]:
    words = (text or "").replace("\r", "").split()
    if not words:
        return [""]
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        test = " ".join(cur + [w])
        if c.stringWidth(test, font, size) <= max_w:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def _y_from_top(y_down: float) -> float:
    return PAGE_H - y_down


def _data_url_to_bytes(data_url: str | None) -> bytes | None:
    if not data_url or not isinstance(data_url, str):
        return None
    if "," not in data_url:
        return None
    meta, payload = data_url.split(",", 1)
    if ";base64" not in meta:
        return None
    try:
        return base64.b64decode(payload)
    except Exception:
        return None


def _draw_image_fitted_page(c: canvas.Canvas, image_bytes: bytes, pad: float = 16.0) -> None:
    """Draw an uploaded form image centered and fitted to the page."""
    img = ImageReader(io.BytesIO(image_bytes))
    iw, ih = img.getSize()
    max_w = PAGE_W - 2 * pad
    max_h = PAGE_H - 2 * pad
    if iw <= 0 or ih <= 0:
        return
    scale = min(max_w / float(iw), max_h / float(ih))
    dw = iw * scale
    dh = ih * scale
    x = (PAGE_W - dw) / 2.0
    y = (PAGE_H - dh) / 2.0
    c.drawImage(img, x, y, width=dw, height=dh, mask="auto")


class _ScopeLayout:
    def __init__(self, c: canvas.Canvas, *, header_image=None, footer_lines: list[str] | None = None) -> None:
        self.c = c
        self.header_image = header_image
        self.footer_lines = footer_lines or []
        self.page_no = 1
        self.y = MARGIN_TOP
        self.max_w = PAGE_W - 2 * MARGIN_X
        self._draw_page_chrome()

    def _draw_page_chrome(self) -> None:
        """Draw company letterhead and footer on every page."""
        # Header image from template (default header2.xml)
        if self.header_image:
            try:
                img = ImageReader(io.BytesIO(self.header_image))
                iw, ih = img.getSize()
                # match template relation extent (roughly 320 x 64 pt)
                draw_w = 320.0
                draw_h = draw_w * (ih / float(iw)) if iw else 64.0
                top = 34.0
                self.c.drawImage(
                    img,
                    MARGIN_X,
                    _y_from_top(top + draw_h),
                    width=draw_w,
                    height=draw_h,
                    mask="auto",
                )
            except Exception:
                pass
        # Footer copy from template (footer2.xml), 10pt bold
        if self.footer_lines:
            self.c.setFillColor(TEXT)
            self.c.setFont(FB, 10)
            y = PAGE_H - (PAGE_H - 36.0)  # 36pt from bottom in top-origin math
            for ln in self.footer_lines:
                self.c.drawString(MARGIN_X, y, ln)
                y += 11.5

    def _need_page(self, extra: float) -> None:
        if self.y + extra > PAGE_H - MARGIN_BOT:
            self.c.showPage()
            self.page_no += 1
            self.y = MARGIN_TOP
            self._draw_page_chrome()

    def line(self, s: str, *, font: str = FN, size: float = 11, bold: bool = False, color=TEXT) -> None:
        f = FB if bold else font
        self._need_page(size * 1.4)
        self.c.setFont(f, size)
        self.c.setFillColor(color)
        self.c.drawString(MARGIN_X, _y_from_top(self.y + size * 0.85), s)
        self.y += size * 1.25

    def label_value(self, label: str, value: str, *, label_size: float = 14, value_size: float = 11) -> None:
        """Label bold, value on following lines (like Word label / indented block)."""
        self._need_page(label_size * 1.5)
        self.c.setFont(FB, label_size)
        self.c.setFillColor(TEXT)
        self.c.drawString(MARGIN_X, _y_from_top(self.y + label_size * 0.85), label)
        self.y += label_size * 1.05
        v = (value or "").strip() or " "
        indent = 18.0
        for ln in _wrap_lines(self.c, v, FN, value_size, self.max_w - indent):
            self._need_page(value_size * 1.2)
            self.c.setFont(FN, value_size)
            self.c.setFillColor(TEXT)
            self.c.drawString(MARGIN_X + indent, _y_from_top(self.y + value_size * 0.85), ln)
            self.y += value_size * 1.15
        self.y += 6

    def mixed_line(self, bold_part: str, normal_part: str, *, size: float = 11) -> None:
        """e.g. Assumed Finish Level: Medium–High"""
        self._need_page(size * 1.5)
        self.c.setFont(FB, size)
        self.c.setFillColor(TEXT)
        bw = self.c.stringWidth(bold_part, FB, size)
        self.c.drawString(MARGIN_X, _y_from_top(self.y + size * 0.85), bold_part)
        self.c.setFont(FN, size)
        rest = (normal_part or "").strip()
        if rest:
            self.c.drawString(MARGIN_X + bw, _y_from_top(self.y + size * 0.85), " " + rest)
        self.y += size * 1.35

    def paragraph_lead_body(
        self,
        lead_bold: str,
        body: str,
        *,
        size: float = 10,
    ) -> None:
        """New Build / Renovation: bold lead + 10pt body (template w:sz 20 = 10pt)."""
        body = (body or "").strip()
        self._need_page(size * 2)
        self.c.setFont(FB, size)
        self.c.setFillColor(TEXT)
        lead_w = self.c.stringWidth(lead_bold, FB, size)
        self.c.drawString(MARGIN_X, _y_from_top(self.y + size * 0.85), lead_bold)
        self.y += size * 1.1
        if body:
            indent = MARGIN_X
            for ln in _wrap_lines(self.c, body, FN, size, self.max_w - (indent - MARGIN_X)):
                self._need_page(size * 1.2)
                self.c.setFont(FN, size)
                self.c.drawString(indent, _y_from_top(self.y + size * 0.85), ln)
                self.y += size * 1.15
        self.y += 4

    def wrapped(self, text: str, *, font: str = FN, size: float = 10, indent: float = 0) -> None:
        text = (text or "").strip()
        if not text:
            return
        ix = MARGIN_X + indent
        for ln in _wrap_lines(self.c, text, font, size, self.max_w - indent):
            self._need_page(size * 1.2)
            self.c.setFont(font, size)
            self.c.setFillColor(TEXT)
            self.c.drawString(ix, _y_from_top(self.y + size * 0.85), ln)
            self.y += size * 1.12
        self.y += 2

    def spacer(self, pts: float = 8) -> None:
        self.y += pts

    def divider(self, *, pad_top: float = 8.0, pad_bottom: float = 10.0) -> None:
        """Horizontal separator line between major sections/cost centres."""
        self._need_page(pad_top + 2 + pad_bottom)
        self.y += pad_top
        y_pdf = _y_from_top(self.y)
        self.c.setStrokeColor(colors.HexColor("#666666"))
        self.c.setLineWidth(0.8)
        self.c.line(MARGIN_X, y_pdf, PAGE_W - MARGIN_X, y_pdf)
        self.y += pad_bottom

    def page_break(self) -> None:
        self.c.showPage()
        self.page_no += 1
        self.y = MARGIN_TOP
        self._draw_page_chrome()


def _date_display(value: str) -> str:
    if not value:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", value.strip())
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"
    return value


def build_scope_pdf(payload: dict[str, Any]) -> bytes:
    proj = payload.get("project") or {}
    centres = payload.get("costCentres") or []

    client = (proj.get("client") or "").strip()
    name = (proj.get("name") or "").strip()
    location = (proj.get("location") or "").strip()
    date = _date_display((proj.get("date") or "").strip())
    ref = (proj.get("num") or "").strip()
    finish = (proj.get("finishLevel") or "Medium–High").strip()
    design = (proj.get("designChar") or "—").strip()
    is_new_build = "new build" in str(proj.get("type") or "").lower()
    arch = (proj.get("archDrawings") or "").strip()
    struct = (proj.get("structDrawings") or "").strip()
    rooms = proj.get("selectedRooms") or []
    rooms_txt = ", ".join(str(x) for x in rooms) if rooms else "—"
    start_form_img = _data_url_to_bytes(proj.get("startFormImage"))
    ref_form_img = _data_url_to_bytes(proj.get("referenceFormImage"))

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    branding = _load_template_branding()

    # Optional exact form pages provided by user.
    # If present, place them as the opening pages so output can match sample sheets.
    used_form_pages = False
    if start_form_img:
        _draw_image_fitted_page(c, start_form_img, pad=10.0)
        c.showPage()
        used_form_pages = True
    if ref_form_img:
        _draw_image_fitted_page(c, ref_form_img, pad=10.0)
        c.showPage()
        used_form_pages = True

    L = _ScopeLayout(
        c,
        header_image=branding.get("header_image"),
        footer_lines=branding.get("footer_lines") or [],
    )
    if used_form_pages:
        # We already advanced pages above; keep numbering roughly in sync.
        L.page_no += 2 if (start_form_img and ref_form_img) else 1

    # --- Cover header (matches template paras 4–18) ---
    L.label_value("Prepared for:", client, label_size=14, value_size=11)
    L.label_value("Project:", name, label_size=14, value_size=11)
    L.label_value("Address:", location, label_size=14, value_size=11)
    L.spacer(6)
    L.line("Prepared by:\t\t\tAction Builders Pty Ltd", font=FN, size=11, bold=True)
    L.line("Address:\t\t\t116a Sandy Bay Road, Sandy Bay", font=FN, size=11, bold=True)
    L.spacer(4)
    L.label_value("Document Date:", date, label_size=11, value_size=11)
    L.spacer(10)

    # --- Reference documents (template ~16pt title, 11pt blocks) ---
    L.line("Reference Documents:", size=16, bold=True)
    L.spacer(4)
    L.line("Architectural Drawings", size=11, bold=True)
    arch_txt = arch or "Supplied by __________  Dated __________  Page Numbers __________"
    L.wrapped(arch_txt, size=11)
    L.line("BAL Rating TBA", size=11, bold=False)
    L.spacer(4)
    L.line("Structural Drawings", size=11, bold=True)
    struct_txt = struct or "Plans supplied by __________  Dated __________  Page Numbers __________"
    L.wrapped(struct_txt, size=11)
    for title, placeholder in [
        ("Civil Drawings", "Supplied by __________  Dated __________  Page Numbers __________"),
        ("Hydraulic Drawings", "Supplied by __________  Dated __________  Page Numbers __________"),
        ("Planning Permit", "Titles __________  Permit Number __________  Issue Date __________"),
        ("Plumbing Permit", "Council __________  Permit Number __________  Issue Date __________"),
        (
            "Certificate of Likely Compliance",
            "Issued by __________  Permit Number __________  Issue Date __________",
        ),
    ]:
        L.line(title, size=11, bold=True)
        L.wrapped(placeholder, size=11)
    L.spacer(14)

    # --- Cost centre scope banner (14pt bold, template para 65) ---
    L.line("Cost Centre Scope – Detailed Preliminary Draft", size=14, bold=True)
    L.spacer(6)
    L.mixed_line("Project: ", name or "—", size=11)
    L.mixed_line("Assumed Finish Level: ", finish, size=11)
    L.line("Design Characteristics (from plans):", size=11, bold=True)
    L.wrapped(design, size=10)
    L.mixed_line("Selected Rooms: ", rooms_txt, size=10)
    L.spacer(10)

    # First page reserved for project/reference information only.
    # Cost centres start from a fresh new page.
    if centres:
        L.page_break()

    # --- Each cost centre (template: bold CC name, NB/Reno 10pt, Assumptions, Scope items, lines 10pt) ---
    for i, block in enumerate(centres):
        cc_name = (block.get("name") or "").strip()
        if not cc_name:
            continue
        desc_nb = (block.get("descriptionNewBuild") or "").strip()
        desc_re = (block.get("descriptionRenovation") or "").strip()
        items = block.get("items") or []
        exclusions = block.get("exclusions") or []
        notes = block.get("notes") or []

        # Keep centre heading + opening labels together.
        L._need_page(64)
        L.line(cc_name, size=11, bold=True)
        L.spacer(2)
        if is_new_build:
            if desc_nb:
                L.paragraph_lead_body("New Build", desc_nb, size=10)
        else:
            if desc_re:
                L.paragraph_lead_body("Renovation", desc_re, size=10)
        L.line("Assumptions:", size=10, bold=True)
        L.spacer(2)
        L.line("Scope items:", size=10, bold=True)
        L.spacer(2)
        for it in items:
            line = (it.get("name") or "").strip()
            rooms_list = it.get("rooms") if isinstance(it.get("rooms"), list) else None
            if rooms_list:
                rooms_list = [str(r).strip() for r in rooms_list if str(r or "").strip()]
            room_label = ", ".join(rooms_list) if rooms_list else (it.get("room") or "").strip()
            qty = it.get("qty")
            prod = (it.get("productLine") or "").strip()
            if room_label:
                line += f" ({room_label})"
            if qty not in (None, "", 1, "1"):
                line += f" — Qty: {qty}"
            if prod:
                line += f" — {prod}"
            L.wrapped(line, size=10)

        if exclusions:
            L.spacer(6)
            L.line("Exclusions", size=11, bold=True)
            L.wrapped(
                "The following items will not be allowed for in our initial pricing model:",
                size=10,
            )
            for ex in exclusions:
                L.wrapped(f"• {ex}", size=10, indent=12)
        if notes:
            L.spacer(6)
            L.line("NOTES:", size=11, bold=True)
            for n in notes:
                L.wrapped(str(n), size=10, indent=8)
        # Strong visual separation between cost centres, while still allowing
        # next centre to use remaining space on the same page.
        last = i == (len(centres) - 1)
        if not last:
            L.divider(pad_top=10, pad_bottom=10)
        else:
            L.spacer(12)

    c.save()
    buf.seek(0)
    return buf.getvalue()
