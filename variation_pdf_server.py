from __future__ import annotations

import base64
import io
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


APP_ROOT = Path(__file__).resolve().parent
SAMPLE_HEADER_IMAGE = APP_ROOT / "project files" / "variation_assets" / "image_0.jpg"

# Inter gives noticeably sharper, more professional PDF text than built-in Helvetica (Type 1).
FONT_TEXT = "Helvetica"
FONT_SEMI = "Helvetica-Bold"
FONT_BOLD = "Helvetica-Bold"


def _register_pdf_fonts() -> None:
    global FONT_TEXT, FONT_SEMI, FONT_BOLD
    d = APP_ROOT / "fonts"
    regular = d / "Inter-Regular.ttf"
    semi = d / "Inter-SemiBold.ttf"
    bold = d / "Inter-Bold.ttf"
    if regular.exists() and semi.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("ABSans", str(regular)))
        pdfmetrics.registerFont(TTFont("ABSans-SemiBold", str(semi)))
        pdfmetrics.registerFont(TTFont("ABSans-Bold", str(bold)))
        FONT_TEXT, FONT_SEMI, FONT_BOLD = "ABSans", "ABSans-SemiBold", "ABSans-Bold"


_register_pdf_fonts()


def _font(style: str) -> str:
    if style == "bold":
        return FONT_BOLD
    if style == "semibold":
        return FONT_SEMI
    return FONT_TEXT


app = Flask(__name__)
CORS(app)

PAGE_W, PAGE_H = A4
AB_BLUE = colors.HexColor("#31519D")
GRID = colors.HexColor("#D0D0D0")
TEXT = colors.HexColor("#1a1a1a")
TEXT_MUTED = colors.HexColor("#333333")
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


def _draw_text(
    c: canvas.Canvas,
    x: float,
    y: float,
    txt: str,
    size: float = 9,
    style: str = "regular",
    fill=None,
) -> None:
    fn = _font(style)
    c.setFont(fn, size)
    c.setFillColor(fill if fill is not None else TEXT)
    c.drawString(x, y, txt or "")


def _draw_wrapped(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    txt: str,
    size: float = 9,
    leading: float = 11.25,
) -> float:
    fn = FONT_TEXT
    c.setFont(fn, size)
    c.setFillColor(TEXT)
    words = (txt or "").split()
    line = []
    cursor_y = y
    for w in words:
        test = (" ".join(line + [w])).strip()
        if c.stringWidth(test, fn, size) <= width:
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


def _draw_money_right(
    c: canvas.Canvas,
    right_x: float,
    y: float,
    txt: str,
    size: float = 9,
    style: str = "regular",
    color=TEXT,
) -> None:
    fn = _font(style)
    c.setFont(fn, size)
    c.setFillColor(color)
    c.drawRightString(right_x, y, txt or "")


def _draw_center(
    c: canvas.Canvas,
    x_mid: float,
    y: float,
    txt: str,
    size: float = 9,
    style: str = "bold",
    color=colors.white,
) -> None:
    fn = _font(style)
    c.setFont(fn, size)
    c.setFillColor(color)
    width = c.stringWidth(txt or "", fn, size)
    c.drawString(x_mid - (width / 2.0), y, txt or "")


def _wrap_lines(c: canvas.Canvas, txt: str, width: float, size: float = 9, style: str = "regular"):
    font = _font(style)
    c.setFont(font, size)
    words = (txt or "").split()
    if not words:
        return [""]
    lines = []
    current = []
    for w in words:
        probe = (" ".join(current + [w])).strip()
        if c.stringWidth(probe, font, size) <= width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def _baseline_center_in_band(
    band_top: float,
    band_bottom: float,
    font_size: float,
    *,
    optical: float | None = None,
) -> float:
    """Vertical centre for body-style text baseline (top-origin coords)."""
    mid = (band_top + band_bottom) / 2.0
    k = optical if optical is not None else 0.38
    return mid - k * font_size


def _baseline_white_on_blue(band_top: float, band_bottom: float, font_size: float) -> float:
    """Baseline for centred white Inter bold on blue bars (tuned to PDF glyph bbox vs fill rect)."""
    mid = (band_top + band_bottom) / 2.0
    return mid + 0.22 * font_size


def _column_wrapped_height(c: canvas.Canvas, txt: str, col_width: float, size: float = 9, leading: float = 11.0, style: str = "regular") -> float:
    if not (txt or "").strip():
        return 2.0
    lines = _wrap_lines(c, txt or "", col_width, size, style=style)
    if not lines:
        return 2.0
    return size * 0.72 + (len(lines) - 1) * leading + size * 0.2


def _draw_wrapped_cell(
    c: canvas.Canvas,
    left: float,
    col_width: float,
    cell_top_from_page_top: float,
    txt: str,
    size: float = 9,
    leading: float = 11.0,
    style: str = "regular",
) -> float:
    """Draw wrapped text in a column; returns bottom edge (from page top, downward) after text."""
    if not (txt or "").strip():
        return cell_top_from_page_top + 3.0
    lines = _wrap_lines(c, txt or "", col_width, size, style=style)
    fn = _font(style)
    c.setFont(fn, size)
    c.setFillColor(TEXT)
    baseline = cell_top_from_page_top + size * 0.82
    y_pdf = _y(baseline)
    for ln in lines:
        c.drawString(left, y_pdf, ln)
        baseline += leading
        y_pdf = _y(baseline)
    return baseline + size * 0.15


def _draw_center_in_slice(
    c: canvas.Canvas,
    x_left: float,
    x_right: float,
    band_top: float,
    band_bottom: float,
    txt: str,
    size: float = 9,
    style: str = "bold",
    color=colors.white,
    *,
    white_on_blue_bar: bool = False,
) -> None:
    """Horizontally and vertically centred text in [x_left, x_right]. Use white_on_blue_bar for filled blue headers."""
    x_mid = (x_left + x_right) / 2.0
    if white_on_blue_bar:
        baseline = _baseline_white_on_blue(band_top, band_bottom, size)
    else:
        baseline = _baseline_center_in_band(band_top, band_bottom, size, optical=0.39)
    _draw_center(c, x_mid, _y(baseline), txt, size, style=style, color=color)


def _draw_blue_bar_title_wrapped(
    c: canvas.Canvas,
    band_top: float,
    txt: str,
    size: float = 9,
    side_pad: float = 10.0,
) -> float:
    """Centred wrapped title on blue bar; returns band_bottom (top-origin coords)."""
    inner_w = WIDTH - 2 * side_pad
    lines = _wrap_lines(c, txt, inner_w, size, style="bold")
    leading = size * 1.12
    text_block = len(lines) * leading + size * 0.35
    band_h = max(18.5, text_block + size * 0.85)
    band_bottom = band_top + band_h
    _draw_rect_top(c, LEFT, band_top, RIGHT, band_bottom, fill=AB_BLUE, stroke=1)
    pad_top = max(size * 0.55, (band_h - text_block) / 2.0 + size * 0.58)
    baseline0 = band_top + pad_top
    for i, ln in enumerate(lines):
        x_mid = (LEFT + RIGHT) / 2.0
        fn = FONT_BOLD
        c.setFont(fn, size)
        c.setFillColor(colors.white)
        w = c.stringWidth(ln, fn, size)
        c.drawString(x_mid - w / 2.0, _y(baseline0 + i * leading), ln)
    return band_bottom


@app.get("/health")
@app.get("/api/health")
def health() -> dict:
    sync = (os.environ.get("AB_VARIATION_SYNC_DIR") or "").strip()
    d = Path(sync).expanduser() if sync else None
    return {
        "ok": True,
        "sharepointSyncConfigured": bool(sync and d and d.is_dir()),
        "sharepointSyncPath": sync if sync else None,
    }


def _pa_auth_hint(status: int) -> str:
    if status in (401, 403):
        return (
            "Microsoft blocked this HTTP call (tenant security). Easiest fix: run the PDF server with "
            "AB_VARIATION_SYNC_DIR set to a Mac folder that syncs to SharePoint (OneDrive). "
            "Then use Generate Final PDF — files appear in SharePoint after sync. "
            "Alternatives: ask IT for a Flow URL that includes sig=, or a Bearer token (scope "
            "https://service.flow.microsoft.com/.default). "
            "For hosted use, set Vercel env vars POWER_AUTOMATE_TENANT_ID, POWER_AUTOMATE_CLIENT_ID, "
            "POWER_AUTOMATE_CLIENT_SECRET so the backend auto-fetches a token."
        )
    return ""


def _extract_microsoft_error_json(detail: str) -> str:
    """Pull human text from JSON error bodies (AAD / Power Platform)."""
    detail = (detail or "").strip()
    if not detail:
        return ""
    try:
        j = json.loads(detail)
        if isinstance(j, dict):
            for key in ("error_description", "message", "error", "detail"):
                v = j.get(key)
                if isinstance(v, str) and len(v.strip()) > 3:
                    return v.strip()[:900]
    except (json.JSONDecodeError, TypeError):
        pass
    return detail[:600]


def _resolve_bearer_token(explicit: str | None) -> str:
    raw = (explicit or os.environ.get("POWER_AUTOMATE_BEARER") or "").strip()
    if not raw:
        token = _fetch_flow_access_token_from_env()
        return f"Bearer {token}" if token else ""
    if raw.lower().startswith("bearer "):
        return raw
    return f"Bearer {raw}"


def _fetch_flow_access_token_from_env() -> str:
    """
    If app credentials are configured, fetch a Microsoft Entra access token for Power Automate.
    Required env vars:
      - POWER_AUTOMATE_TENANT_ID
      - POWER_AUTOMATE_CLIENT_ID
      - POWER_AUTOMATE_CLIENT_SECRET
    """
    tenant = (os.environ.get("POWER_AUTOMATE_TENANT_ID") or "").strip()
    client_id = (os.environ.get("POWER_AUTOMATE_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("POWER_AUTOMATE_CLIENT_SECRET") or "").strip()
    if not tenant or not client_id or not client_secret:
        return ""
    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    form = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "https://service.flow.microsoft.com/.default",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        token_url,
        data=form,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
            return str(body.get("access_token") or "")
    except Exception:
        return ""


def _post_power_automate_webhook(webhook: str, payload: dict, bearer_token: str = "") -> tuple[bool, dict]:
    """POST JSON to Power Automate. Returns (success, body_dict for client)."""
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json,*/*",
        "User-Agent": "ActionBuilders-VariationPDF/1.0",
    }
    auth = _resolve_bearer_token(bearer_token)
    if auth:
        headers["Authorization"] = auth
    req = urllib.request.Request(webhook, data=raw, method="POST", headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
            _ = resp.read()
            return True, {"ok": True, "upstreamStatus": getattr(resp, "status", 200) or 200}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:4000]
        hint = _pa_auth_hint(e.code)
        friendly = _extract_microsoft_error_json(detail) or (detail or str(e.reason))
        err_body: dict = {
            "ok": False,
            "upstreamStatus": e.code,
            "detail": friendly,
            "hint": hint,
        }
        if detail and detail.strip() != (friendly or "").strip():
            err_body["rawDetail"] = detail[:2000]
        return False, err_body
    except urllib.error.URLError as e:
        return False, {
            "ok": False,
            "error": str(getattr(e, "reason", e) or e),
            "hint": "Network error reaching Microsoft (VPN, proxy, or offline).",
        }


def _maybe_save_to_sync_folder(pdf_bytes: bytes, data: dict) -> str | None:
    """If AB_VARIATION_SYNC_DIR is set, copy PDF there. Returns path written or None."""
    sync = (os.environ.get("AB_VARIATION_SYNC_DIR") or "").strip()
    if not sync:
        return None
    try:
        d = Path(sync).expanduser().resolve()
        if not d.is_dir():
            return None
        proj = str(data.get("projectNumber") or data.get("ownerName") or "Contract")
        safe = "".join(ch if ch.isalnum() else "_" for ch in proj)[:80]
        out = d / f"Variation_{safe}.pdf"
        out.write_bytes(pdf_bytes)
        return str(out)
    except OSError:
        return None


@app.post("/api/variation/proxy-automation")
def proxy_automation():
    """POST JSON to Power Automate from the server (avoids browser CORS to powerplatform.com)."""
    data = request.get_json(silent=True) or {}
    webhook = (data.get("webhookUrl") or "").strip()
    payload = data.get("payload")
    bearer = (data.get("bearerToken") or "").strip()
    if not webhook or payload is None:
        return jsonify({"error": "webhookUrl and payload are required"}), 400
    if not webhook.lower().startswith("https://"):
        return jsonify({"error": "webhookUrl must be an https:// URL"}), 400
    ok, body = _post_power_automate_webhook(webhook, payload, bearer_token=bearer)
    status = 200 if ok else 502
    return jsonify(body), status


@app.post("/api/variation/pdf-and-flow")
def pdf_and_flow():
    """
    One call: build the variation PDF on the server, then POST it to Power Automate.
    Body: same JSON as /api/variation/pdf plus webhookUrl (required), optional bearerToken.
    Avoids huge base64 in the browser and applies the same Microsoft auth as the proxy.
    """
    data = request.get_json(silent=True) or {}
    webhook = (data.get("webhookUrl") or "").strip()
    bearer = (data.get("bearerToken") or "").strip()
    if not webhook:
        return jsonify({"error": "webhookUrl is required"}), 400
    var_payload = {k: v for k, v in data.items() if k not in ("webhookUrl", "bearerToken")}
    with app.test_client() as client:
        r = client.post("/api/variation/pdf", json=var_payload)
        if r.status_code != 200:
            return (
                jsonify(
                    {
                        "error": "PDF generation failed",
                        "detail": r.get_data(as_text=True)[:3000],
                    }
                ),
                400,
            )
        pdf_bytes = r.get_data()
    proj = str(var_payload.get("projectNumber") or var_payload.get("ownerName") or "Contract")
    safe = "".join(ch if ch.isalnum() else "_" for ch in proj)[:80]
    fname = f"Variation_{safe}.pdf"
    flow_payload = {
        "flowType": "variation_pdf_to_sharepoint",
        "sourceApp": "Action Builders Scope Builder",
        "pdfFileName": fname,
        "pdfMimeType": "application/pdf",
        "pdfContentBase64": base64.b64encode(pdf_bytes).decode("ascii"),
        "docusign": {
            "ownerName": var_payload.get("ownerSignName") or var_payload.get("ownerName"),
            "ownerEmail": var_payload.get("ownerEmail"),
            "builderRep": var_payload.get("builderRep"),
        },
        "sharepoint": {
            "projectNumber": var_payload.get("projectNumber"),
            "siteAddress": var_payload.get("siteAddress"),
            "suggestedFolderHint": var_payload.get("projectNumber") or fname.replace(".pdf", ""),
        },
        "variation": var_payload,
    }
    ok, body = _post_power_automate_webhook(webhook, flow_payload, bearer_token=bearer)
    body = dict(body)
    saved = _maybe_save_to_sync_folder(pdf_bytes, var_payload)
    if saved:
        body["pdfSavedTo"] = saved
    if not ok and saved:
        body["partialSuccess"] = True
        body["hint"] = (
            (body.get("hint") or "")
            + " Your PDF was still saved to the OneDrive/SharePoint sync folder (see pdfSavedTo). "
            "SharePoint will update after OneDrive syncs."
        ).strip()
    return jsonify(body), (200 if ok else 502)


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

    # Common column geometry
    col_details_r = 370.52
    col_add_r = 466.52
    col_credit_r = RIGHT
    line_h = 10.5
    # Align header labels with body text inset (not raw table edge).
    DETAILS_TX_LEFT = 47.5

    SPLIT_1 = 212.92
    SPLIT_2 = 383.32
    col_pad = 6.0
    col1_l = LEFT + col_pad
    col1_r = SPLIT_1 - col_pad
    col2_l = SPLIT_1 + col_pad
    col2_r = SPLIT_2 - col_pad
    col3_l = SPLIT_2 + col_pad
    col3_r = RIGHT - col_pad

    # Header image
    if SAMPLE_HEADER_IMAGE.exists():
        img = ImageReader(str(SAMPLE_HEADER_IMAGE))
        c.drawImage(img, 42.52, PAGE_H - 71.74, width=340.16, height=43.40, mask="auto")

    _draw_text(c, 45.4, _y(90.5), "Date", 9, style="semibold")
    _draw_text(c, 67.0, _y(90.5), _date(data.get("date", "")), 9)

    title_top = 106.0
    title_bottom = 138.0
    _draw_rect_top(c, LEFT, title_top, RIGHT, title_bottom, fill=AB_BLUE, stroke=1)
    title_baseline = _baseline_white_on_blue(title_top, title_bottom, 15.5)
    _draw_center(
        c,
        (LEFT + RIGHT) / 2.0,
        _y(title_baseline),
        "VARIATION TO CONTRACT",
        15.5,
        style="bold",
        color=colors.white,
    )

    # Header strip where BUILDER / OWNER / SITE ADDRESS are centred (must stay inside stroked rect).
    party_label_top = title_bottom + 14.0
    party_label_bottom = party_label_top + 13.5
    # Caps extend above the geometric band centre — pull outer border up so labels sit inside the table.
    party_table_top = party_label_top - 6.0
    inner_gap = 5.0
    row_gap_part = 7.0

    w1, w2, w3 = col1_r - col1_l, col2_r - col2_l, col3_r - col3_l
    party_rows = [
        ("Action Builders Hobart", owner_name or "", site_address or ""),
        ("116a Sandy Bay Road, Sandy Bay, 7005, TAS", "", str(data.get("projectNumber", "") or "")),
        ("info@actionbuilders.com.au", str(data.get("ownerPhone", "") or ""), ""),
        ("ABN: 17 063 265 707", str(data.get("ownerEmail", "") or ""), ""),
        ("LICENSE: CC7052", "", ""),
    ]
    cursor_est = party_label_bottom + inner_gap
    for t1, t2, t3 in party_rows:
        h1 = _column_wrapped_height(c, t1, w1, 9, 11.0, "regular")
        h2 = _column_wrapped_height(c, t2, w2, 9, 11.0, "regular")
        h3 = _column_wrapped_height(c, t3, w3, 9, 11.0, "regular")
        cursor_est += max(h1, h2, h3) + row_gap_part
    party_bottom = cursor_est + 12.0

    c.setStrokeColor(GRID)
    c.setLineWidth(0.75)
    _draw_rect_top(c, LEFT, party_table_top, RIGHT, party_bottom, fill=None, stroke=1)
    c.line(SPLIT_1, _y(party_table_top), SPLIT_1, _y(party_bottom))
    c.line(SPLIT_2, _y(party_table_top), SPLIT_2, _y(party_bottom))
    c.line(LEFT, _y(party_label_bottom), RIGHT, _y(party_label_bottom))

    _draw_center_in_slice(c, col1_l, col1_r, party_label_top, party_label_bottom, "BUILDER", 9, "semibold", TEXT)
    _draw_center_in_slice(c, col2_l, col2_r, party_label_top, party_label_bottom, "OWNER", 9, "semibold", TEXT)
    _draw_center_in_slice(c, col3_l, col3_r, party_label_top, party_label_bottom, "SITE ADDRESS", 8.5, "semibold", TEXT)

    cursor_party = party_label_bottom + inner_gap
    for t1, t2, t3 in party_rows:
        e1 = _draw_wrapped_cell(c, col1_l, col1_r - col1_l, cursor_party, t1)
        e2 = _draw_wrapped_cell(c, col2_l, col2_r - col2_l, cursor_party, t2)
        e3 = _draw_wrapped_cell(c, col3_l, col3_r - col3_l, cursor_party, t3)
        cursor_party = max(e1, e2, e3) + row_gap_part

    SECTION_GAP = 20.0
    reason_band_top = party_bottom + SECTION_GAP
    reason_band_bottom = _draw_blue_bar_title_wrapped(
        c,
        reason_band_top,
        "REASON FOR VARIATION (IF REQUESTED BY THE BUILDER)",
        8.5,
    )
    reason_body_text = data.get("reason", "") or ""
    reason_lines = _wrap_lines(c, reason_body_text, WIDTH - 18.0, 9, style="regular")
    reason_leading = 11.25
    reason_body_bottom = reason_band_bottom + 12.0 + max(14.0, len(reason_lines) * reason_leading + 10.0)
    _draw_rect_top(c, LEFT, reason_band_bottom, RIGHT, reason_body_bottom, fill=None, stroke=1)
    _draw_wrapped(c, 45.7, _y(reason_band_bottom + 9.0), WIDTH - 12.0, reason_body_text, 9, reason_leading)

    work_gap = 12.0
    work_header_top = reason_body_bottom + work_gap
    work_header_bottom = work_header_top + 17.65
    _draw_rect_top(c, LEFT, work_header_top, RIGHT, work_header_bottom, fill=AB_BLUE, stroke=1)
    details_hdr_mid = (DETAILS_TX_LEFT + col_details_r) / 2.0
    details_hdr_bl = _baseline_white_on_blue(work_header_top, work_header_bottom, 9)
    _draw_center(c, details_hdr_mid, _y(details_hdr_bl), "DETAILS OF WORK", 9, style="bold", color=colors.white)
    _draw_center_in_slice(
        c,
        col_details_r,
        col_add_r,
        work_header_top,
        work_header_bottom,
        "ADDITIONAL COST",
        9,
        "bold",
        colors.white,
        white_on_blue_bar=True,
    )
    _draw_center_in_slice(
        c,
        col_add_r,
        col_credit_r,
        work_header_top,
        work_header_bottom,
        "CREDIT DUE",
        9,
        "bold",
        colors.white,
        white_on_blue_bar=True,
    )

    current_top = work_header_bottom
    details_col_width = col_details_r - DETAILS_TX_LEFT - 6.0
    work_grid_top = work_header_bottom
    c.setStrokeColor(GRID)
    c.setLineWidth(0.4)

    # Draw all entered detail rows (fixes missing details issue).
    for row in lines:
        details = str(row.get("details", "") or "")
        wrapped = _wrap_lines(c, details, details_col_width, 9, style="regular")
        row_h = max(17.65, 10.0 + len(wrapped) * line_h)
        row_bottom = current_top + row_h

        _draw_rect_top(c, LEFT, current_top, RIGHT, row_bottom, fill=None, stroke=1)

        y_text = _y(current_top + 10.0)
        for ln in wrapped:
            _draw_text(c, DETAILS_TX_LEFT, y_text, ln, 9)
            y_text -= line_h

        money_y = current_top + row_h / 2.0 + 3.0
        _draw_money_right(c, col_add_r - 4.5, _y(money_y), _money(row.get("additionalCost", 0)), 9)
        _draw_money_right(c, col_credit_r - 4.5, _y(money_y), _money(row.get("creditDue", 0)), 9)
        current_top = row_bottom

    # Totals rows (amounts in Additional Cost only).
    subtotal = float(data.get("totals", {}).get("subtotal", 0))
    gst = float(data.get("totals", {}).get("gst", 0))
    total = float(data.get("totals", {}).get("total", 0))
    for label, amt in [("SUBTOTAL", subtotal), ("GST", gst), ("TOTAL", total)]:
        row_bottom = current_top + 17.65
        _draw_rect_top(c, LEFT, current_top, RIGHT, row_bottom, fill=None, stroke=1)
        total_row_mid = current_top + 17.65 / 2.0 + 3.2
        _draw_text(
            c,
            316.6,
            _y(total_row_mid),
            label,
            9,
            style="bold" if label == "TOTAL" else "semibold",
        )
        _draw_money_right(
            c,
            col_add_r - 4.5,
            _y(total_row_mid),
            _money(amt),
            9,
            style="bold" if label == "TOTAL" else "regular",
            color=TEXT,
        )
        current_top = row_bottom

    c.setStrokeColor(GRID)
    c.setLineWidth(0.45)
    c.line(col_details_r, _y(work_grid_top), col_details_r, _y(current_top))
    c.line(col_add_r, _y(work_grid_top), col_add_r, _y(current_top))

    # Extension / Payment
    ext_header_top = current_top + 6.0
    ext_header_bottom = ext_header_top + 17.65
    _draw_rect_top(c, LEFT, ext_header_top, RIGHT, ext_header_bottom, fill=AB_BLUE, stroke=1)
    _draw_center_in_slice(
        c, LEFT, 298.52, ext_header_top, ext_header_bottom, "EXTENSION OF TIME", 9, "bold", colors.white, white_on_blue_bar=True
    )
    _draw_center_in_slice(
        c, 298.52, RIGHT, ext_header_top, ext_header_bottom, "PAYMENT TERMS", 9, "bold", colors.white, white_on_blue_bar=True
    )

    ext_body_top = ext_header_bottom
    ext_copy = f"It is estimated the variation will extend the contract completion date by {int(data.get('extensionDays', 0))} Working Days"
    pay_copy = data.get("paymentTerms", "") or ""
    ext_n = len(_wrap_lines(c, ext_copy, 246.0, 9))
    pay_n = len(_wrap_lines(c, pay_copy, 246.0, 9))
    ext_body_bottom = ext_body_top + max(46.0, max(ext_n, pay_n) * 11.25 + 18.0)
    _draw_rect_top(c, LEFT, ext_body_top, RIGHT, ext_body_bottom, fill=None, stroke=1)
    c.line(298.52, _y(ext_body_top), 298.52, _y(ext_body_bottom))
    _draw_wrapped(
        c,
        45.7,
        _y(ext_body_top + 9.5),
        246.0,
        ext_copy,
        9,
        11.25,
    )
    _draw_wrapped(c, 301.0, _y(ext_body_top + 9.5), 246.0, pay_copy, 9, 11.25)

    # Signatures
    sig_header_top = ext_body_bottom
    sig_header_bottom = sig_header_top + 17.65
    _draw_rect_top(c, LEFT, sig_header_top, RIGHT, sig_header_bottom, fill=AB_BLUE, stroke=1)
    _draw_center_in_slice(
        c, LEFT, RIGHT, sig_header_top, sig_header_bottom, "SIGNATURES", 9, "bold", colors.white, white_on_blue_bar=True
    )

    sig_note_top = sig_header_bottom
    sig_note_bottom = sig_note_top + 17.65
    _draw_rect_top(c, LEFT, sig_note_top, RIGHT, sig_note_bottom, fill=None, stroke=1)
    _draw_wrapped(
        c,
        45.7,
        _y(sig_note_top + 9.5),
        WIDTH - 10.0,
        "This is to certify that the variation and extension of time detailed herein have this day been agreed/authorised by me/us:",
        8.5,
        10,
    )

    sig_rows = [("OWNERS NAME", "BUILDER REP"), ("SIGN:", "SIGN:"), ("DATE:", "DATE:")]
    sig_top = sig_note_bottom
    sig_bands = []
    for l_head, r_head in sig_rows:
        sig_bottom = sig_top + 34.0
        sig_bands.append((sig_top, sig_bottom, l_head, r_head))
        _draw_rect_top(c, LEFT, sig_top, 298.52, sig_bottom, fill=None, stroke=1)
        _draw_rect_top(c, 298.52, sig_top, RIGHT, sig_bottom, fill=None, stroke=1)
        _draw_text(c, 45.7, _y(sig_top + 10.5), l_head, 9, style="semibold")
        _draw_text(c, 301.0, _y(sig_top + 10.5), r_head, 9, style="semibold")
        sig_top = sig_bottom

    # Place values in the correct signature rows.
    # Row 0: names, Row 2: dates (row 1 intentionally blank for manual signatures).
    if len(sig_bands) >= 3:
        name_top, _, _, _ = sig_bands[0]
        date_top, _, _, _ = sig_bands[2]
        _draw_text(c, 45.7, _y(name_top + 23.0), data.get("ownerSignName") or owner_name)
        _draw_text(c, 301.0, _y(name_top + 23.0), data.get("builderRep", ""))
        _draw_text(c, 45.7, _y(date_top + 23.0), _date(data.get("ownerDate", "")))
        _draw_text(c, 301.0, _y(date_top + 23.0), _date(data.get("builderDate", "")))

    # Footer
    footer_top = min(sig_top + 20.0, 726.5)
    c.setStrokeColor(GRID)
    c.setLineWidth(0.4)
    c.line(LEFT, _y(footer_top), RIGHT, _y(footer_top))
    c.setFont(FONT_TEXT, 8.5)
    c.setFillColor(TEXT_MUTED)
    c.drawString(42.52, _y(footer_top + 7.5), "Action Builders Hobart")
    c.drawString(272.0, _y(footer_top + 7.5), "Page 1/1")
    c.drawString(460.0, _y(footer_top + 7.5), "Variation To Contract")

    c.showPage()
    c.save()
    packet.seek(0)
    pdf_bytes = packet.getvalue()
    packet = io.BytesIO(pdf_bytes)
    _maybe_save_to_sync_folder(pdf_bytes, data)
    return send_file(packet, mimetype="application/pdf", as_attachment=False, download_name="variation.pdf")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8787, debug=True)
