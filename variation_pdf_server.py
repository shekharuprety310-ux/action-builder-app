from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


APP_ROOT = Path(__file__).resolve().parent
SAMPLE_HEADER_IMAGE = APP_ROOT / "project files" / "variation_assets" / "image_0.jpg"

app = Flask(__name__)
CORS(app)

PAGE_W, PAGE_H = A4
AB_BLUE = colors.HexColor("#31519D")
GRID = colors.HexColor("#D0D0D0")
LEFT = 42.52
RIGHT = 554.52
WIDTH = RIGHT - LEFT


def _money(value: float) -> str:
    v = float(value or 0.0)
    return f"${v:,.2f}" if v >= 0 else f"$-{abs(v):,.2f}"


def _date(value: str) -> str:
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%d-%m-%Y")
    except Exception:
        return value


def _draw_text(c: canvas.Canvas, x: float, y: float, txt: str, size: int = 9, bold: bool = False) -> None:
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.setFillColor(colors.black)
    c.drawString(x, y, txt or "")


def _draw_wrapped(c: canvas.Canvas, x: float, y: float, width: float, txt: str, size: int = 9, leading: float = 11) -> float:
    c.setFont("Helvetica", size)
    c.setFillColor(colors.black)
    words = (txt or "").split()
    line = []
    cursor_y = y
    for w in words:
        test = (" ".join(line + [w])).strip()
        if c.stringWidth(test, "Helvetica", size) <= width:
            line.append(w)
        else:
            if line:
                c.drawString(x, cursor_y, " ".join(line))
                cursor_y -= leading
            line = [w]
    if line:
        c.drawString(x, cursor_y, " ".join(line))
        cursor_y -= leading
    return cursor_y


def _y(top_from_pdf: float) -> float:
    # The sample geometry is measured from top edge. ReportLab uses bottom-left origin.
    return PAGE_H - top_from_pdf


def _draw_rect_top(c: canvas.Canvas, x0: float, top: float, x1: float, bottom: float, fill=None, stroke=1) -> None:
    y = _y(bottom)
    h = bottom - top
    if fill is not None:
        c.setFillColor(fill)
        c.rect(x0, y, x1 - x0, h, stroke=stroke, fill=1)
    else:
        c.rect(x0, y, x1 - x0, h, stroke=stroke, fill=0)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/variation/pdf")
def generate_variation_pdf():
    data = request.get_json(silent=True) or {}

    lines = data.get("lines") or []
    owner_name = data.get("ownerName", "")
    site_address = data.get("siteAddress", "")
    if not owner_name or not site_address or not lines:
        return jsonify({"error": "ownerName, siteAddress and lines are required"}), 400

    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)

    # Header image extracted from real sample PDF.
    if SAMPLE_HEADER_IMAGE.exists():
        img = ImageReader(str(SAMPLE_HEADER_IMAGE))
        c.drawImage(img, 42.52, PAGE_H - 71.74, width=340.16, height=43.40, mask="auto")

    # Date + title (calibrated near sample word coordinates).
    _draw_text(c, 45.4, _y(92.0), "Date", 9, True)
    _draw_text(c, 67.0, _y(92.0), _date(data.get("date", "")), 9, False)
    c.setFillColor(AB_BLUE)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(44.9, _y(121.0), "VARIATION TO CONTRACT")
    c.setFillColor(colors.black)

    # Top 3-column block.
    c.setStrokeColor(GRID)
    c.setLineWidth(0.8)
    c.rect(LEFT, _y(222.2), WIDTH, 77.63, stroke=1, fill=0)
    c.line(212.92, _y(144.57), 212.92, _y(222.2))
    c.line(383.32, _y(144.57), 383.32, _y(222.2))
    c.line(LEFT, _y(144.57), RIGHT, _y(144.57))

    _draw_text(c, 44.9, _y(136.0), "BUILDER", 9, True)
    _draw_text(c, 215.3, _y(136.0), "OWNER", 9, True)
    _draw_text(c, 385.7, _y(136.0), "SITE ADDRESS", 9, True)

    _draw_text(c, 44.9, _y(152.0), "Action Builders Hobart")
    _draw_text(c, 215.3, _y(152.0), owner_name)
    _draw_text(c, 385.7, _y(152.0), site_address)
    _draw_text(c, 44.9, _y(168.0), "116a Sandy Bay Road Sandy Bay")
    _draw_text(c, 385.7, _y(168.0), data.get("projectNumber", ""))
    _draw_text(c, 44.9, _y(184.0), "info@actionbuilders.com.au")
    _draw_text(c, 215.3, _y(184.0), data.get("ownerPhone", ""))
    _draw_text(c, 44.9, _y(200.0), "ABN: 17 063 265 707")
    _draw_text(c, 215.3, _y(200.0), data.get("ownerEmail", ""))
    _draw_text(c, 44.9, _y(216.0), "LICENSE: CC7052")

    # Reason header + body.
    _draw_rect_top(c, LEFT, 257.52, RIGHT, 275.17, fill=AB_BLUE, stroke=1)
    c.setFillColor(colors.white)
    _draw_text(c, 45.7, _y(264.6), "REASON FOR VARIATION (IF REQUESTED BY THE BUILDER)", 9, True)
    c.setFillColor(colors.black)
    _draw_rect_top(c, LEFT, 275.17, RIGHT, 311.47, fill=None, stroke=1)
    _draw_wrapped(c, 45.7, _y(291.0), WIDTH - 8.0, data.get("reason", ""), 9, 11)

    # Work table header (measured).
    _draw_rect_top(c, LEFT, 322.72, RIGHT, 340.37, fill=AB_BLUE, stroke=1)
    c.setStrokeColor(GRID)
    c.setLineWidth(0.4)
    c.line(370.52, _y(322.72), 370.52, _y(486.42))
    c.line(466.52, _y(322.72), 466.52, _y(486.42))
    c.setFillColor(colors.white)
    _draw_text(c, 45.7, _y(329.8), "DETAILS OF WORK", 9, True)
    _draw_text(c, 373.7, _y(329.8), "ADDITIONAL COST", 9, True)
    _draw_text(c, 469.7, _y(329.8), "CREDIT DUE", 9, True)
    c.setFillColor(colors.black)

    # Variable item rows in the space before totals.
    top_cursor = 340.37
    totals_header_top = 439.87
    details_limit = max(1, min(len(lines), 8))
    dynamic_height = max(14.0, (totals_header_top - top_cursor) / details_limit)
    for row in lines[:details_limit]:
        row_bottom = top_cursor + dynamic_height
        _draw_rect_top(c, LEFT, top_cursor, RIGHT, row_bottom, fill=None, stroke=1)
        c.line(370.52, _y(top_cursor), 370.52, _y(row_bottom))
        c.line(466.52, _y(top_cursor), 466.52, _y(row_bottom))
        _draw_wrapped(c, 45.7, _y(top_cursor + 10.0), 320.0, str(row.get("details", "")), 9, 10)
        _draw_text(c, 373.7, _y(top_cursor + 10.5), _money(row.get("additionalCost", 0)))
        _draw_text(c, 469.7, _y(top_cursor + 10.5), _money(row.get("creditDue", 0)))
        top_cursor = row_bottom

    # Fill remaining space if fewer rows.
    if top_cursor < totals_header_top:
        _draw_rect_top(c, LEFT, top_cursor, RIGHT, totals_header_top, fill=None, stroke=1)
        c.line(370.52, _y(top_cursor), 370.52, _y(totals_header_top))
        c.line(466.52, _y(top_cursor), 466.52, _y(totals_header_top))

    # Totals (exact-height blocks from sample).
    subtotal = float(data.get("totals", {}).get("subtotal", 0))
    gst = float(data.get("totals", {}).get("gst", 0))
    total = float(data.get("totals", {}).get("total", 0))
    total_rows = [
        ("SUBTOTAL", subtotal, 439.87, 457.52),
        ("GST", gst, 457.52, 486.42),
        ("TOTAL", total, 486.42, 504.07),
    ]
    for label, amt, t, b in total_rows:
        _draw_rect_top(c, LEFT, t, RIGHT, b, fill=AB_BLUE, stroke=1)
        c.setFillColor(colors.white)
        _draw_text(c, 414.0, _y(t + 10.5), label, 9, True)
        _draw_text(c, 469.7, _y(t + 10.5), _money(amt), 9, True)
        c.setFillColor(colors.black)

    # Extension + payment header.
    _draw_rect_top(c, LEFT, 504.07, RIGHT, 521.72, fill=AB_BLUE, stroke=1)
    c.setFillColor(colors.white)
    _draw_text(c, 45.7, _y(511.6), "EXTENSION OF TIME", 9, True)
    _draw_text(c, 301.0, _y(511.6), "PAYMENT TERMS", 9, True)
    c.setFillColor(colors.black)
    _draw_rect_top(c, LEFT, 521.72, RIGHT, 539.37, fill=None, stroke=1)
    c.line(298.52, _y(521.72), 298.52, _y(539.37))
    _draw_wrapped(
        c,
        45.7,
        _y(529.8),
        246.0,
        f"It is estimated the variation will extend the contract completion date by {int(data.get('extensionDays', 0))} Working Days",
        9,
        11,
    )
    _draw_wrapped(c, 301.0, _y(529.8), 246.0, data.get("paymentTerms", ""), 9, 11)

    # Signatures title and note.
    _draw_rect_top(c, LEFT, 539.37, RIGHT, 557.02, fill=AB_BLUE, stroke=1)
    c.setFillColor(colors.white)
    _draw_text(c, 45.7, _y(546.8), "SIGNATURES", 9, True)
    c.setFillColor(colors.black)
    _draw_rect_top(c, LEFT, 557.02, RIGHT, 579.37, fill=None, stroke=1)
    _draw_wrapped(
        c,
        45.7,
        _y(566.8),
        WIDTH - 10,
        "This is to certify that the variation and extension of time detailed herein have this day been agreed/authorised by me/us:",
        8.5,
        10,
    )

    # Signature grid rows exactly as sampled.
    sig_rows = [
        (579.37, 619.37, "OWNERS NAME", "BUILDER REP"),
        (619.37, 659.37, "SIGN:", "SIGN:"),
        (659.37, 699.37, "DATE:", "DATE:"),
    ]
    for t, b, l_head, r_head in sig_rows:
        _draw_rect_top(c, LEFT, t, 298.52, b, fill=AB_BLUE, stroke=1)
        _draw_rect_top(c, 298.52, t, RIGHT, b, fill=AB_BLUE, stroke=1)
        c.setFillColor(colors.white)
        _draw_text(c, 45.7, _y(t + 10.5), l_head, 9, True)
        _draw_text(c, 301.0, _y(t + 10.5), r_head, 9, True)
        c.setFillColor(colors.black)

    # Values in signature fields.
    _draw_text(c, 45.7, _y(607.0), data.get("ownerSignName") or owner_name)
    _draw_text(c, 301.0, _y(607.0), data.get("builderRep", ""))
    _draw_text(c, 45.7, _y(687.0), _date(data.get("ownerDate", "")))
    _draw_text(c, 301.0, _y(687.0), _date(data.get("builderDate", "")))

    # Footer line + labels.
    c.setStrokeColor(GRID)
    c.setLineWidth(0.4)
    c.line(LEFT, _y(726.5), RIGHT, _y(726.5))
    _draw_text(c, 42.52, _y(734.0), "Action Builders Hobart", 8, False)
    _draw_text(c, 272.0, _y(734.0), "Page 1/1", 8, False)
    _draw_text(c, 460.0, _y(734.0), "Variation To Contract", 8, False)

    c.showPage()
    c.save()
    packet.seek(0)
    return send_file(packet, mimetype="application/pdf", as_attachment=False, download_name="variation.pdf")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8787, debug=True)
