"""Small, escaped HTML components and consistent native Streamlit tables."""
from html import escape
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st

from config import BANK_COLORS, STATUS_LABELS, YEAR


# Presentation-only vector artwork. No reference screenshot is rendered in the UI.
ICONS = {
    "bank": '<path d="m3 9 9-6 9 6H3Zm2 11h14M7 10v7m5-7v7m5-7v7M3 22h18"/>',
    "layers": '<path d="m3 8 9-5 9 5-9 5-9-5Zm0 5 9 5 9-5M3 18l9 5 9-5"/>',
    "bars": '<path d="M4 13h3v8H4Zm7-6h3v14h-3Zm7-5h3v19h-3Z"/>',
    "file": '<path d="M6 3h9l4 4v14H6V3Zm9 0v5h4M9 12h7m-7 4h7"/>',
    "trophy": '<path d="M7 3h10v7a5 5 0 0 1-10 0V3Zm0 2H3v3a4 4 0 0 0 4 4m10-7h4v3a4 4 0 0 1-4 4m-5 3v5m-4 2h8"/>',
    "star": '<path d="m12 2 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1 3-6Z"/>',
    "shield": '<path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4Zm-4 9 3 3 5-6"/>',
    "coins": '<ellipse cx="9" cy="6" rx="6" ry="3"/><path d="M3 6v5c0 2 4 3 6 3m-6-3v5c0 2 4 3 6 3m6-10v5m0 0c3-1 6 1 6 3s-3 3-6 3-5-1-5-3 2-3 5-3Z"/>',
    "screen": '<path d="M3 3h18v13H3V3Zm9 13v5m-5 0h10M6 7h12"/>',
    "bulb": '<path d="M8 17c0-4-4-5-4-9a8 8 0 0 1 16 0c0 4-4 5-4 9H8Zm1 3h6m-5 3h4M12 7v10"/>',
    "fingerprint": '<path d="M4 12a8 8 0 0 1 16 0m-13 8c3-3 1-6 2-9a3 3 0 0 1 6 1c0 4 0 7 3 9M3 17c2-2 2-3 2-5a7 7 0 0 1 14 0v4m-7-4c0 5-1 7-2 10"/>',
    "chip": '<path d="M5 5h14v14H5V5Zm4 4h6v6H9V9ZM8 2v3m8-3v3M8 19v3m8-3v3M2 8h3m-3 8h3m14-8h3m-3 8h3"/>',
}


def icon(name, tone="blue"):
    return (f'<span class="object-icon {safe(tone)}" aria-hidden="true"><svg viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">'
            + ICONS.get(name, ICONS["file"]) + '</svg></span>')


def bank_art(location):
    """Small original isometric banking object with decorative depth only."""
    prefix = "bank-" + location
    return f'''<svg class="bank-art" viewBox="0 0 340 210" aria-hidden="true">
      <defs><linearGradient id="{prefix}-roof" x2=".8" y2="1"><stop stop-color="#bcefff"/><stop offset=".48" stop-color="#6197ff"/><stop offset="1" stop-color="#1242bc"/></linearGradient>
      <linearGradient id="{prefix}-body" x2="1" y2="1"><stop stop-color="#eefaff"/><stop offset=".5" stop-color="#82baff"/><stop offset="1" stop-color="#265bd6"/></linearGradient></defs>
      <g fill="#4389ed" opacity=".17"><path d="M8 155V82l22-9v87ZM38 155V48l24-9v126ZM68 156V22l27-9v160ZM267 164V52l24-10v126ZM299 173V91l26-10v95Z"/></g>
      <path d="m64 171 122-42 111 46-125 32Z" fill="#2165ee" opacity=".15"/>
      <g stroke="#b7e8ff" stroke-width="1.4"><path d="m79 159 102-34 99 34-100 35Z" fill="url(#{prefix}-roof)"/>
      <path d="m85 150 95-31 91 31-92 31Z" fill="url(#{prefix}-body)"/>
      <path d="m112 86 72-23 64 24v64l-66 24-70-25Z" fill="#1e55c4"/>
      <path d="m112 86 70 20v69l-70-25Z" fill="url(#{prefix}-body)"/>
      <path d="m182 106 66-19v64l-66 24Z" fill="#356ada"/>
      <g fill="url(#{prefix}-body)"><path d="m121 99 12 4v49l-12-4Zm23 7 12 4v49l-12-4Zm23 7 12 4v49l-12-4ZM193 110l11-4v49l-11 4Zm22-7 11-4v49l-11 4Z"/></g>
      <path d="m95 89 86-65 83 61-83 27Z" fill="url(#{prefix}-roof)"/>
      <path d="m111 86 70-49 64 46-64 20Z" fill="#c5e5ff"/>
      <path d="m124 82 57-37 51 36-51 16Z" fill="#487ee4"/>
      <path d="m95 89 86 23 83-27v8l-83 28-86-25Z" fill="#88c5ff"/></g>
      <text x="181" y="81" text-anchor="middle" fill="white" font-family="system-ui" font-weight="700" font-size="13">BANK</text>
      <g fill="#33baf5"><path d="M46 101h9v30h-9Zm13-15h9v45h-9Zm13-17h9v62h-9Z"/><circle cx="284" cy="102" r="15" opacity=".7"/></g>
      <path d="m278 102 4 4 8-9" fill="none" stroke="white" stroke-width="2"/>
    </svg>'''


def text(value):
    return "N/A" if value is None or pd.isna(value) else str(value)


def safe(value):
    return escape(text(value), quote=True)


def number(value, digits=2):
    if value is None or pd.isna(value):
        return "N/A"
    try:
        rounded = Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
        return f"{rounded:,.{digits}f}".replace(",", " ").replace(".", ",")
    except (TypeError, ValueError, InvalidOperation):
        return text(value)


def valid_url(value):
    if value is None or pd.isna(value):
        return None
    try:
        url = str(value).strip()
        parsed = urlsplit(url)
        if parsed.scheme.lower() in ("http", "https") and parsed.hostname and not any(c.isspace() for c in url):
            return url
    except ValueError:
        pass
    return None


REVIEW_STATUSES = ("review", "provisional_review")


def status_badge(status, *, show_review=False):
    """Review metadata is displayed only when the sources view opts in."""
    status = text(status)
    if status in REVIEW_STATUSES and not show_review:
        return ""
    tone = "review" if status in REVIEW_STATUSES else "verified" if status in ("verified", "verified_supplement") else "neutral"
    return f'<span class="status {tone}">{safe(STATUS_LABELS.get(status, status))}</span>'


def html(content):
    st.markdown(content, unsafe_allow_html=True)


def panel(name):
    """A stable, named surface instead of styling generated Emotion classes."""
    return st.container(border=False, key="panel_" + name)


def page_header(title, subtitle, section):
    html(f'<header class="page-heading"><div class="heading-copy"><div class="page-context">Nghiên cứu của nhóm · {YEAR}</div>'
         f'<h1>{safe(title)}</h1><p>{safe(subtitle)}</p></div>'
         f'<div class="header-art">{bank_art("header")}</div><div class="year-card">{icon("file")}'
         f'<span>Năm đánh giá<strong>{YEAR}</strong></span></div></header>')


def section_header(title, note=None, symbol=None, tone="blue"):
    html(f'<div class="section-heading">{icon(symbol, tone) if symbol else ""}<div><h2>{safe(title)}</h2>'
         f'{"<p>" + safe(note) + "</p>" if note else ""}</div></div>')


def metrics(items):
    cards = []
    symbols = ("bank", "layers", "bars", "file", "trophy", "star")
    tones = ("blue", "violet", "teal", "violet", "gold", "blue")
    for index, (label, value, note) in enumerate(items):
        cards.append(f'<article class="metric-tile">{icon(symbols[index % 6], tones[index % 6])}<div>'
                     f'<div class="metric-value">{safe(value)}</div><div class="metric-label">{safe(label)}</div>'
                     f'<div class="metric-note">{safe(note)}</div></div></article>')
    html(f'<div class="metric-grid" style="--count:{len(items)}">' + "".join(cards) + '</div>')


def ranking_table(ranking):
    rows = []
    for record in ranking.sort_values("rank", kind="stable").to_dict("records"):
        ticker = record["ticker"]
        medal = {1: "gold", 2: "silver", 3: "bronze"}.get(record["rank"], "plain")
        rows.append(f'<tr><td><span class="rank-number {medal}">{safe(number(record["rank"], 0))}</span></td>'
                    f'<td><span class="bank-dot" style="--bank:{BANK_COLORS.get(ticker, "#345da3")}"></span><strong>{safe(record["bank"])}</strong></td>'
                    f'<td><span class="ticker" style="--bank:{BANK_COLORS.get(ticker, "#366b9c")}">{safe(ticker)}</span></td>'
                    f'<td class="numeric"><strong>{safe(number(record["total_score"]))}</strong></td></tr>')
    html('<div class="ranking-wrap"><table class="ranking-table"><thead><tr><th>Hạng</th><th>Ngân hàng</th>'
         '<th>Mã</th><th class="numeric">Tổng điểm</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')


def insight_cards(groups):
    cards = []
    for index, (_, part) in enumerate(groups.groupby("group", sort=False)):
        available = part.dropna(subset=["group_score_100"])
        if available.empty:
            names, score = "N/A", "N/A"
        else:
            best = available.group_score_100.max()
            leaders = available.loc[available.group_score_100.eq(best)]
            names = " · ".join(leaders.ticker)
            score = number(best)
        label = part.group_label.iloc[0]
        symbol = ("shield", "coins", "bars", "screen")[index % 4]
        cards.append(f'<article class="insight tone-{index}">{icon(symbol, ("teal", "gold", "violet", "blue")[index % 4])}'
                     f'<div><strong>{safe(names)} <b>{safe(score)}</b><small> / 100</small></strong>'
                     f'<p>Dẫn đầu: {safe(label)}</p></div></article>')
    html('<div class="insight-grid">' + "".join(cards) + '</div>')


def bank_summary(summary, strongest, weakest):
    ticker = summary["ticker"]
    html(f'<article class="bank-summary"><div class="bank-summary-title"><span class="ticker" '
         f'style="--bank:{BANK_COLORS.get(ticker, "#366b9c")}">{safe(ticker)}</span><strong>{safe(summary["bank"])}</strong></div>'
         f'<div class="bank-score">{safe(number(summary["total_score"]))}<small> / 100</small></div>'
         f'<p>Hạng {safe(number(summary["rank"], 0))}</p><dl><dt>Nhóm mạnh nhất</dt><dd>{safe(" · ".join(strongest) or "N/A")}</dd>'
         f'<dt>Nhóm thấp nhất</dt><dd>{safe(" · ".join(weakest) or "N/A")}</dd></dl></article>')


def digital_cards(record, labels):
    cards = []
    for code in ("D1", "D2", "D3"):
        value = record.get(f"{code}_score_0_3")
        symbol = {"D1": "fingerprint", "D2": "file", "D3": "chip"}[code]
        cards.append(f'<article class="digital-card">{icon(symbol, "teal" if code == "D2" else "violet")}<div><div class="digital-card-top"><span class="digital-token">{code}</span>'
                     f'{status_badge(record.get(code + "_status"))}</div><h2>{safe(labels[code])}</h2>'
                     f'<div class="digital-value">{safe(number(value, 0))}<span> / 3</span></div>'
                     '</div></article>')
    html('<div class="digital-grid">' + "".join(cards) + '</div>')


def evidence_card(record, bank=None):
    link = valid_url(record.get("source_url"))
    source_link = f'<a class="source-link" href="{escape(link, quote=True)}" target="_blank" rel="noopener noreferrer">Mở tài liệu nguồn ↗</a>' if link else '<span class="muted">URL: N/A</span>'
    html(f'<article class="evidence-card"><div class="evidence-top"><div><span class="evidence-code">{safe(record.get("indicator_code"))}</span>'
         f'<strong>{safe(bank) + " · " if bank else ""}{safe(record.get("indicator_name", record.get("indicator_code")))}</strong></div>{status_badge(record.get("status"))}</div>'
         f'<p class="evidence-text">{safe(record.get("evidence_text"))}</p><div class="evidence-meta">'
         f'<div><span>Điểm / Thời điểm</span><p>{safe(number(record.get("score_0_3"), 0))} / 3 · {safe(record.get("as_of"))}</p></div>'
         f'<div><span>Nguồn bằng chứng</span><p>{safe(record.get("source_description"))}</p></div>'
         f'<div><span>Loại nguồn / Trang</span><p>{safe(record.get("source_type"))} · {safe(record.get("page_or_section"))}</p></div></div>'
         f'<div class="evidence-footer">{source_link}</div></article>')


def bank_mini_cards(ranking, groups):
    cards = []
    for row in ranking.to_dict("records"):
        part = groups.loc[groups.ticker.eq(row["ticker"])] if groups is not None else None
        strongest = " · ".join(part.loc[part.group_score_100.eq(part.group_score_100.max()), "group_label"]) if part is not None else "N/A"
        color = BANK_COLORS.get(row["ticker"], "#345da3")
        cards.append(f'<article class="bank-mini" style="--bank:{color}"><div class="bank-mini-title">{icon("shield", "blue")}'
                     f'<div><strong>{safe(row["bank"])}</strong><span>{safe(row["ticker"])}</span></div></div>'
                     f'<div class="mini-score">{number(row["total_score"])}<small> / 100</small><span>Hạng {number(row["rank"], 0)}</span></div>'
                     f'<p>Mạnh nhất: {safe(strongest)}</p></article>')
    html(f'<div class="bank-mini-grid" style="--count:{len(cards)}">' + "".join(cards) + '</div>')


def analytical_summary(ranking, groups):
    for row in ranking.to_dict("records"):
        part = groups.loc[groups.ticker.eq(row["ticker"])]
        strong = part.loc[part.group_score_100.eq(part.group_score_100.max()), "group_label"].tolist()
        weak = part.loc[part.group_score_100.eq(part.group_score_100.min()), "group_label"].tolist()
        html(f'<div class="analysis-row"><span class="ticker" style="--bank:{BANK_COLORS.get(row["ticker"], "#345da3")}">{safe(row["ticker"])}</span>'
             f'<p><strong>{number(row["total_score"])} / 100</strong> · Hạng {number(row["rank"], 0)}<br>'
             f'Mạnh nhất: {safe(" · ".join(strong))}<br><span>Thấp nhất: {safe(" · ".join(weak))}</span></p></div>')


def methodology_steps(metadata):
    steps = (
        ("Dữ liệu đầu vào", "Chỉ tiêu tài chính và bằng chứng chuyển đổi số đã được nhóm tổng hợp."),
        ("Thống nhất chiều đánh giá", "Xác định chỉ tiêu cao hơn hoặc thấp hơn là tốt hơn."),
        ("Đánh giá D1–D3", "Điểm định tính theo bằng chứng, thang 0–3."),
        ("Chuẩn hóa & trọng số", "Chuẩn hóa chỉ tiêu và áp dụng trọng số trong mô hình hiện tại."),
        ("Tổng hợp & xếp hạng", "Kết quả đã xuất: điểm tiêu chí, điểm nhóm và thứ hạng ngân hàng."),
    )
    html('<ol class="method-steps">' + "".join(f'<li><strong>{safe(title)}</strong><p>{safe(note)}</p></li>' for title, note in steps) + '</ol>')
    if metadata:
        html(f'<div class="method-note">Phương pháp ghi trong lần chạy:<br><strong>{safe(metadata.get("method"))}</strong></div>')


def data_table(frame, labels=None, formats=None, links=(), height=None, key=None, *, show_review=False):
    display = frame.copy()
    if not show_review:
        # Hide review columns in presentation copies, including merged D1–D3 context.
        display = display.drop(columns=[column for column in display
                                       if (column == "status" or column.endswith("_status"))
                                       and display[column].isin(REVIEW_STATUSES).any()])
    if "status" in display:
        display["status"] = display.status.map(lambda value: STATUS_LABELS.get(text(value), text(value)))
    columns = {}
    for name in display.columns:
        label = (labels or {}).get(name, name)
        if name in links:
            display[name] = display[name].map(valid_url)
            columns[name] = st.column_config.LinkColumn(label, display_text="Mở nguồn ↗")
        elif name in (formats or {}):
            columns[name] = st.column_config.NumberColumn(label, format=formats[name])
        else:
            columns[name] = st.column_config.Column(label)
    options = dict(hide_index=True, width="stretch", column_config=columns, key=key, row_height=32)
    if height:
        options["height"] = height
    st.dataframe(display, **options)


def source_table(frame, labels, height):
    """Readable, wrapping provenance; full native data stays in the adjacent expander."""
    if frame.empty:
        st.info("Không có nguồn phù hợp với bộ lọc hiện tại.")
        return
    rows = []
    for record in frame.to_dict("records"):
        cells = []
        for column, value in record.items():
            if column == "source_url":
                url = valid_url(value)
                content = f'<a href="{safe(url)}" target="_blank" rel="noopener noreferrer" aria-label="Mở tài liệu nguồn">Mở ↗</a>' if url else '<span class="muted">N/A</span>'
            elif column == "status":
                content = status_badge(value, show_review=True)
            else:
                content = safe(number(value, 0) if column == "score_0_3" else value)
            cells.append(f'<td class="source-col-{safe(column)}">{content}</td>')
        rows.append('<tr>' + "".join(cells) + '</tr>')
    headers = "".join(f'<th scope="col">{safe(labels.get(column, column))}</th>' for column in frame.columns)
    html(f'<div class="source-scroll" style="--table-height:{height}px" tabindex="0" role="region" aria-label="Bảng nguồn dữ liệu có thể cuộn">'
         f'<table class="source-table"><thead><tr>{headers}</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>')
