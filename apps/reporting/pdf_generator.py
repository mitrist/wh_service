"""PDF report using ReportLab (Cyrillic requires a TTF; Helvetica has no Cyrillic glyphs)."""

from __future__ import annotations

import io
import logging
import os
from typing import Any, Dict, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)


def build_audit_pdf_bytes(session_meta: Dict[str, Any], summary: Dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    api = summary.get("api") or {}
    engine = summary.get("engine") or {}
    report = summary.get("full_report") or api.get("full_report") or engine.get("full_report") or {}
    fonts = _ensure_fonts()
    styles = _build_styles(fonts)

    header = report.get("header") or {}
    overall = report.get("overall_index") or {
        "score_percent": int(api.get("total_score") or 0),
        "zone_label": str(api.get("grade") or ""),
        "description": "",
        "formula_note": "",
    }
    criteria = (report.get("criteria") or {}).get("rows") or []
    if not criteria:
        criteria = [{"emoji": "", "title": k, "score_percent": v, "measured": ""} for k, v in (api.get("category_scores") or {}).items()]
    top_points = report.get("top_loss_points") or []
    bench = (report.get("market_benchmarks") or {}).get("rows") or []
    loss_map = report.get("loss_map") or {}
    quick = report.get("quick_wins") or {}
    next_steps = report.get("next_steps") or {}

    story = []
    story.append(Paragraph("Отчёт по самоаудиту склада", styles["title"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"<b>Компания:</b> {_safe_text(header.get('company') or session_meta.get('company', ''))}", styles["normal"]))
    story.append(Paragraph(f"<b>Дата:</b> {_safe_text(header.get('date', ''))}", styles["normal"]))
    story.append(Spacer(1, 2 * mm))
    for d in header.get("disclaimer", []):
        story.append(Paragraph(f"<b>Внимание:</b> {_safe_text(d)}", styles["small"]))
    story.append(_section_divider())

    story.append(Paragraph("1. Общий индекс здоровья склада", styles["h2"]))
    story.append(Paragraph(f"{overall.get('score_percent', '')}% — {_safe_text(overall.get('zone_label', ''))}", styles["normal"]))
    story.append(Paragraph(_safe_text(overall.get("description", "")), styles["normal"]))
    story.append(Paragraph(_safe_text(overall.get("formula_note", "")), styles["small"]))
    story.append(_section_divider())

    story.append(Paragraph("2. Показатели по 4 критериям", styles["h2"]))
    criteria_rows = [["Критерий", "Балл", "Что измерялось"]]
    for row in criteria:
        criteria_rows.append([
            _safe_text(f"{_short_icon(row.get('emoji'))} {row.get('title', '')}"),
            f"{row.get('score_percent', 0)}%",
            _safe_text(row.get("measured", "")),
        ])
    story.append(_styled_table(criteria_rows, [52 * mm, 20 * mm, 102 * mm], fonts, header=True))
    story.append(_section_divider())

    story.append(Paragraph("3. Три главные точки потерь", styles["h2"]))
    for p in top_points:
        story.append(Paragraph(f"{_severity_bullet(p.get('severity_zone'))} <b>Проблема {p.get('rank')}.</b> {_safe_text(p.get('title', ''))}", styles["normal"]))
        story.append(Paragraph(f"<b>Ваш ответ:</b> {_safe_text(p.get('selected_answer', ''))}", styles["small"]))
        story.append(Paragraph(f"<b>Норма рынка:</b> {_safe_text(p.get('market_norm', ''))}", styles["small"]))
        story.append(Paragraph(f"<b>Разрыв:</b> {_safe_text(p.get('gap', ''))}", styles["small"]))
        story.append(Paragraph(f"<b>Почему это дорого:</b> {_safe_text(p.get('why_costly', ''))}", styles["small"]))
        for chk in p.get("check_now") or []:
            story.append(Paragraph(f"• {_safe_text(chk)}", styles["small"]))
        story.append(Paragraph(f"<b>Быстрое решение:</b> {_safe_text(p.get('quick_solution', ''))}", styles["small"]))
        story.append(Spacer(1, 1.5 * mm))
    story.append(_section_divider())

    story.append(Paragraph("4. Где вы относительно рынка", styles["h2"]))
    bench_rows = [["Показатель", "Слабый", "Средний", "Хорошо", "Ваш результат"]]
    for b in bench:
        bench_rows.append([
            _safe_text(b.get("title", "")),
            _safe_text(b.get("weak", "")),
            _safe_text(b.get("average", "")),
            _safe_text(b.get("good", "")),
            _safe_text(_bench_result_text(b.get("your_result"))),
        ])
    story.append(_styled_table(bench_rows, [43 * mm, 31 * mm, 31 * mm, 31 * mm, 37 * mm], fonts, header=True))
    story.append(Paragraph(_safe_text((report.get("market_benchmarks") or {}).get("note", "")), styles["small"]))
    story.append(_section_divider())

    loss_items = loss_map.get("items") or []
    if loss_items:
        story.append(Paragraph("5. Где обычно прячутся деньги — карта потерь", styles["h2"]))
        for item in loss_items:
            story.append(Paragraph(f"• <b>{_safe_text(item.get('title', ''))}</b> — {_safe_text(item.get('description', ''))}", styles["small"]))
        story.append(Paragraph(_safe_text(loss_map.get("note", "")), styles["small"]))
        story.append(_section_divider())

    story.append(Paragraph("6. Быстрые победы", styles["h2"]))
    story.append(Paragraph(f"<b>Ваш ответ:</b> {_safe_text(quick.get('from_q20', '') or '—')}", styles["small"]))
    story.append(Paragraph(f"• {_safe_text(quick.get('personal_recommendation', ''))}", styles["small"]))
    story.append(Paragraph(f"• {_safe_text(quick.get('yellow_zone_tip', ''))}", styles["small"]))
    story.append(Paragraph(f"• {_safe_text(quick.get('universal_tip', ''))}", styles["small"]))
    story.append(_section_divider())

    paths = next_steps.get("paths") or []
    if paths:
        story.append(Paragraph("7. Что дальше — три честных пути", styles["h2"]))
        highlight = next_steps.get("highlight")
        for p in paths:
            prefix = "►" if p.get("code") == highlight else "•"
            story.append(Paragraph(f"{prefix} <b>{_safe_text(p.get('title', ''))}</b> — {_safe_text(p.get('description', ''))}", styles["small"]))

    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f"ID сессии: {_safe_text(session_meta.get('id'))}", styles["muted"]))

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    doc.build(story)
    return buf.getvalue()


def build_wms_checklist_pdf_bytes(
    session_id: Optional[str],
    status_by_item: Optional[Dict[int, Any]],
) -> bytes:
    """PDF чек-листа WMS: статусы опциональны (пустой словарь = шаблон)."""
    from apps.frontend.wms_checklist_data import WMS_CHECKLIST_ITEMS, count_ready_answers, resolve_wms_band

    buf = io.BytesIO()
    fonts = _ensure_fonts()
    styles = _build_styles(fonts)
    st = status_by_item or {}
    story: list[Any] = []

    story.append(Paragraph("Чек-лист готовности склада к внедрению WMS", styles["title"]))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            _safe_text(
                "WMS — дорогостоящий инструмент. Половина внедрений проваливается не из-за ПО, а потому что склад "
                "был не готов. Оцените готовность до переговоров с интегратором.",
            ),
            styles["small"],
        ),
    )
    story.append(Spacer(1, 3 * mm))
    story.append(_section_divider())

    status_label = {
        "ready": "Готово",
        "in_progress": "В процессе",
        "not_ready": "Не готово",
    }

    wms_table_hdr = ParagraphStyle(
        "wmsTableHdr",
        parent=styles["small"],
        fontName=fonts["bold"],
        fontSize=8.5,
        leading=10,
        spaceBefore=0,
        spaceAfter=0,
    )
    wms_table_cell = ParagraphStyle(
        "wmsTableCell",
        parent=styles["small"],
        fontName=fonts["regular"],
        fontSize=8.5,
        leading=10.5,
        spaceBefore=0,
        spaceAfter=0,
    )

    for item in WMS_CHECKLIST_ITEMS:
        story.append(Paragraph(f"{item.number}. {_safe_text(item.title)}", styles["h2"]))
        story.append(Paragraph(_safe_text(item.subtitle), styles["normal"]))
        rows = [
            [
                Paragraph(escape("Готово к WMS"), wms_table_hdr),
                Paragraph(escape("Ещё не готово"), wms_table_hdr),
            ],
            [
                Paragraph(escape(_safe_text(item.ready_text)), wms_table_cell),
                Paragraph(escape(_safe_text(item.not_ready_text)), wms_table_cell),
            ],
        ]
        wms_tbl = Table(rows, colWidths=[85 * mm, 85 * mm])
        wms_tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#aab4c2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                ],
            ),
        )
        story.append(wms_tbl)
        if item.warning:
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph(f"<b>Внимание:</b> {_safe_text(item.warning)}", styles["small"]))
        if item.tip:
            story.append(Paragraph(f"<b>Совет:</b> {_safe_text(item.tip)}", styles["small"]))
        st_val = st.get(item.number) if st else None
        if st:
            label = status_label.get(st_val, "—")
            story.append(Paragraph(f"<b>Ваш статус по пункту:</b> {_safe_text(label)}", styles["normal"]))
        story.append(Spacer(1, 2 * mm))
        story.append(_section_divider())

    all_filled = bool(st) and all(st.get(n) not in (None, "") for n in range(1, 11))
    score = count_ready_answers(st) if all_filled else None
    story.append(Paragraph("Итоговая шкала (по числу «Готово»)", styles["h2"]))
    for sample, label in (
        (0, "0–3"),
        (4, "4–6"),
        (7, "7–8"),
        (9, "9–10"),
    ):
        b = resolve_wms_band(sample)
        story.append(Paragraph(f"<b>{label} баллов — {_safe_text(b['title'])}</b>", styles["normal"]))
        story.append(Paragraph(_safe_text(b["body"]), styles["small"]))
        story.append(Spacer(1, 1 * mm))

    if all_filled and score is not None:
        band = resolve_wms_band(score)
        story.append(Spacer(1, 2 * mm))
        story.append(
            Paragraph(
                f"<b>Ваш результат:</b> «Готово» = {score} из 10. {_safe_text(band['title'])}.",
                styles["normal"],
            ),
        )
        story.append(Paragraph(_safe_text(band["body"]), styles["small"]))

    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            _safe_text(
                "Пройти самоаудит склада можно на сайте сервиса. Чек-лист — инструмент самооценки; "
                "точная готовность определяется при выездном аудите.",
            ),
            styles["muted"],
        ),
    )
    if session_id:
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"ID сессии: {_safe_text(session_id)}", styles["muted"]))

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    doc.build(story)
    return buf.getvalue()


def _build_styles(fonts: Dict[str, str]) -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Heading1"], fontName=fonts["bold"], fontSize=18, leading=22),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=fonts["bold"], fontSize=11.5, leading=14, spaceBefore=1.5 * mm, spaceAfter=1 * mm),
        "normal": ParagraphStyle("normal", parent=base["BodyText"], fontName=fonts["regular"], fontSize=10, leading=12.5, spaceAfter=0.7 * mm),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName=fonts["regular"], fontSize=9, leading=11.2, spaceAfter=0.6 * mm),
        "muted": ParagraphStyle(
            "muted",
            parent=base["BodyText"],
            fontName=fonts["regular"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#93a1b2"),
            spaceAfter=0,
        ),
    }


def _styled_table(data: list[list[str]], col_widths: list[float], fonts: Dict[str, str], *, header: bool) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style = TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#aab4c2")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("FONTNAME", (0, 0), (-1, -1), fonts["regular"]),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ],
    )
    if header:
        style.add("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7"))
        style.add("FONTNAME", (0, 0), (-1, 0), fonts["bold"])
    table.setStyle(style)
    return table


def _section_divider() -> Table:
    t = Table([[""]], colWidths=[174 * mm], rowHeights=[0.8 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#d5dbe4")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ],
        ),
    )
    return Table([[t], [Spacer(1, 1.8 * mm)]], colWidths=[174 * mm])


def _ensure_fonts() -> Dict[str, str]:
    """Pick a Unicode TTF. On Linux VMs, try DejaVu/Liberation before Windows paths."""
    regular = "Helvetica"
    bold = "Helvetica-Bold"

    here = os.path.dirname(os.path.abspath(__file__))
    bundled = (
        os.path.join(here, "fonts", "DejaVuSans.ttf"),
        os.path.join(here, "fonts", "DejaVuSans-Bold.ttf"),
    )

    candidates: list[tuple[str, str]] = [
        bundled,
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ),
        (
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        ),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf"),
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ]

    for reg_path, bold_path in candidates:
        if not (os.path.isfile(reg_path) and os.path.isfile(bold_path)):
            continue
        try:
            if "AppTextRegular" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("AppTextRegular", reg_path))
            if "AppTextBold" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("AppTextBold", bold_path))
            regular, bold = "AppTextRegular", "AppTextBold"
            logger.info("pdf_generator: using fonts %s / %s", reg_path, bold_path)
            break
        except Exception:
            logger.exception("pdf_generator: failed to register font pair %s %s", reg_path, bold_path)

    if regular == "Helvetica":
        logger.warning(
            "pdf_generator: Helvetica has no Cyrillic glyphs — PDF text will be unreadable. "
            "On Ubuntu/Debian run: sudo apt install -y fonts-dejavu-core "
            "or place DejaVuSans.ttf and DejaVuSans-Bold.ttf under apps/reporting/fonts/."
        )

    return {"regular": regular, "bold": bold}


def _severity_bullet(zone: Any) -> str:
    z = str(zone or "").lower()
    if z == "red":
        return "●"
    if z == "orange":
        return "◐"
    if z == "yellow":
        return "○"
    if z == "green":
        return "◌"
    return "•"


def _short_icon(icon: Any) -> str:
    v = str(icon or "")
    mapping = {"🎯": "Точность", "⚡": "Скорость", "📦": "Ёмкость", "🧠": "Управляемость"}
    return mapping.get(v, "")


def _bench_result_text(v: Any) -> str:
    s = str(v or "")
    if "🔴" in s:
        return "Критично"
    if "🟠" in s:
        return "Системные проблемы"
    if "🟡" in s:
        return "Есть резервы"
    if "🟢" in s:
        return "Норма"
    return s


def _safe_text(text: Any) -> str:
    out = str(text or "")
    for src in ["🟢", "🟡", "🟠", "🔴", "🎯", "⚡", "📦", "🧠"]:
        out = out.replace(src, "")
    return out.strip()
