from __future__ import annotations

import html
import re
from typing import Any


def format_report(report: str, report_date: str) -> dict[str, str]:
    """
    Returns pre-rendered outputs for downstream delivery (email + Discord).
    """
    md_for_email = f"Report date: {report_date}\n\n{report}"
    return {
        "email_html": markdown_to_html(md_for_email),
        "discord_message": markdown_to_discord(report),
    }


def _extract_report_date(md: str) -> str:
    m = re.search(r"^Report date:\s*(.+)\s*$", md, flags=re.MULTILINE)
    if not m:
        return ""
    return m.group(1).strip()


_INLINE_TOKEN_RE = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)", flags=re.DOTALL)


def markdown_to_html(md: str) -> str:
    """
    Minimal markdown renderer for the council report.
    Inline styles only (no external CSS).
    """
    lines = md.replace("\r\n", "\n").split("\n")
    report_date = _extract_report_date(md)

    # Remove the report date line so it doesn't appear twice in the body.
    if report_date:
        cleaned_lines: list[str] = []
        skip_next_blank = False
        for ln in lines:
            if skip_next_blank and ln.strip() == "":
                skip_next_blank = False
                continue
            if re.match(r"^\s*Report date:\s*.+\s*$", ln):
                skip_next_blank = True
                continue
            cleaned_lines.append(ln)
        lines = cleaned_lines

    out: list[str] = []

    header_gradient = "linear-gradient(135deg,#0b2a6f 0%,#0a5bd3 55%,#1aa7ff 100%)"
    page_bg = "#f6f8fc"
    text_color = "#0f172a"

    out.append(
        "<!doctype html><html><body style=\"margin:0;padding:0;background:"
        + page_bg
        + ";font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;\">"
    )
    out.append(
        '<div style="max-width:760px;margin:0 auto;padding:24px 16px;">'
        + '<div style="padding:18px 18px;border-radius:14px;color:#ffffff;background:'
        + header_gradient
        + ';">'
        + '<div style="font-size:18px;font-weight:800;letter-spacing:0.2px;">Bloomberg Terminal</div>'
        + '<div style="font-size:13px;opacity:0.95;margin-top:6px;">Market Intelligence Report</div>'
        + (
            f'<div style="font-size:13px;opacity:0.95;margin-top:6px;">Report date: {html.escape(report_date)}</div>'
            if report_date
            else ""
        )
        + "</div>"
    )

    # Body content
    body_parts: list[str] = []
    paragraph_buf: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_buf
        if not paragraph_buf:
            return
        text = " ".join([p.strip() for p in paragraph_buf if p.strip() != ""]).strip()
        if text:
            body_parts.append(
                '<p style="margin:12px 0;color:'
                + text_color
                + ';line-height:1.6;font-size:14px;">'
                + _render_inline(text)
                + "</p>"
            )
        paragraph_buf = []

    def render_hr() -> str:
        return '<hr style="border:none;border-top:1px solid #dbe2f0;margin:14px 0;" />'

    def render_heading(level: int, content: str) -> str:
        size = {1: 20, 2: 16, 3: 14}.get(level, 14)
        margin_top = {1: 16, 2: 12, 3: 10}.get(level, 10)
        return (
            f'<h{level} style="margin:{margin_top}px 0 8px 0;color:#0b2a6f;font-size:{size}px;line-height:1.25;">'
            + _render_inline(content.strip())
            + f"</h{level}>"
        )

    def render_blockquote(callout_text: str) -> str:
        # Primary detection: blockquote syntax (requested).
        # Secondary fallback: keyword-based heuristics (still supported).
        lowered = callout_text.lower()
        is_integrity = any(
            kw in lowered
            for kw in (
                "data integrity",
                "missing data",
                "unavailable",
                "not available",
                "data not present",
                "null",
                "n/a",
                "warning",
            )
        )
        # Keep the amber callout styling for all blockquotes (primary detection).
        # Keyword detection only adds prominence inside the callout.
        border = "#d97706"
        bg = "#fef3c7"
        # render_blockquote may receive strings joined with "<br/>".
        # We must render inline on each segment and then re-join, otherwise "<br/>"
        # would be escaped as plain text.
        segments = callout_text.split("<br/>")
        rendered_segments = [_render_inline(seg) for seg in segments]
        callout_html = "<br/>".join(rendered_segments)
        label_html = (
            '<div style="font-weight:900;color:#9a3412;margin-bottom:6px;">DATA INTEGRITY WARNING</div>'
            if is_integrity
            else ""
        )
        return (
            '<div style="margin:14px 0;padding:12px 14px;border-radius:10px;border-left:6px solid '
            + border
            + ";background:"
            + bg
            + ';">'
            + label_html
            + '<div style="color:#111827;line-height:1.6;font-size:14px;">'
            + callout_html
            + "</div></div>"
        )

    def render_bullets(items: list[str]) -> str:
        lis = []
        for it in items:
            lis.append(
                '<li style="margin:6px 0;">'
                + _render_inline(it.strip())
                + "</li>"
            )
        return (
            '<ul style="margin:10px 0 14px 18px;padding:0;color:'
            + text_color
            + ';line-height:1.6;font-size:14px;">'
            + "".join(lis)
            + "</ul>"
        )

    def _parse_markdown_table(start: int) -> tuple[str, int]:
        # Expects:
        # 0: header row
        # 1: separator row
        header_line = lines[start].strip()
        sep_line = lines[start + 1].strip() if start + 1 < len(lines) else ""
        if "|" not in header_line or "|" not in sep_line:
            return "", start

        def split_row(row: str) -> list[str]:
            parts = [c.strip() for c in row.strip().strip("|").split("|")]
            return parts

        headers = split_row(header_line)

        rows: list[list[str]] = []
        idx = start + 2
        while idx < len(lines):
            ln = lines[idx].strip()
            if ln == "":
                break
            if "|" not in ln:
                break
            rows.append(split_row(ln))
            idx += 1

        # Render
        col_count = max(len(headers), max((len(r) for r in rows), default=0))
        # Normalize columns to col_count
        headers = (headers + [""] * col_count)[:col_count]
        norm_rows: list[list[str]] = []
        for r in rows:
            r2 = (r + [""] * col_count)[:col_count]
            norm_rows.append(r2)

        header_bg = "#0b3d91"
        header_fg = "#ffffff"
        row_even_bg = "#ffffff"
        row_odd_bg = "#f1f5f9"
        border = "#cbd5e1"

        table_parts: list[str] = []
        table_parts.append(
            '<table style="width:100%;border-collapse:collapse;margin:12px 0;font-size:14px;">'
        )
        table_parts.append("<thead>")
        table_parts.append(
            "<tr>"
            + "".join(
                f'<th style="border:1px solid {border};background:{header_bg};color:{header_fg};padding:8px;text-align:left;">'
                + _render_inline(h or "")
                + "</th>"
                for h in headers
            )
            + "</tr>"
        )
        table_parts.append("</thead><tbody>")

        for i, r in enumerate(norm_rows):
            bg = row_even_bg if i % 2 == 0 else row_odd_bg
            table_parts.append("<tr>")
            for cell in r:
                table_parts.append(
                    f'<td style="border:1px solid {border};background:{bg};padding:8px;vertical-align:top;">'
                    + _render_inline(cell or "")
                    + "</td>"
                )
            table_parts.append("</tr>")

        table_parts.append("</tbody></table>")
        return "".join(table_parts), idx

    def _render_inline(text: str) -> str:
        # Convert a small subset of markdown into HTML.
        # Everything else is escaped as plain text.
        out_inline: list[str] = []
        pos = 0
        for m in _INLINE_TOKEN_RE.finditer(text):
            if m.start() > pos:
                out_inline.append(html.escape(text[pos : m.start()]))

            token = m.group(0)
            if token.startswith("`"):
                inner = token[1:-1]
                out_inline.append(
                    '<code style="background:#eef2ff;border:1px solid #c7d2fe;padding:2px 6px;border-radius:8px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:12px;">'
                    + html.escape(inner)
                    + "</code>"
                )
            elif token.startswith("**"):
                inner = token[2:-2]
                out_inline.append(
                    '<strong style="font-weight:800;color:#0f172a;">' + html.escape(inner) + "</strong>"
                )
            elif token.startswith("*"):
                inner = token[1:-1]
                out_inline.append(
                    '<em style="font-style:italic;color:#0f172a;">' + html.escape(inner) + "</em>"
                )
            else:
                out_inline.append(html.escape(token))

            pos = m.end()

        if pos < len(text):
            out_inline.append(html.escape(text[pos:]))
        return "".join(out_inline)

    i = 0
    # Render loop with specialized parsing
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        if stripped == "":
            flush_paragraph()
            i += 1
            continue

        # Horizontal rules
        if re.match(r"^\s*(?:---+|\*\*\*+|___+)\s*$", raw):
            flush_paragraph()
            body_parts.append(render_hr())
            i += 1
            continue

        # Headings
        m = re.match(r"^\s*(#{1,3})\s+(.+)\s*$", raw)
        if m:
            flush_paragraph()
            level = len(m.group(1))
            body_parts.append(render_heading(level, m.group(2)))
            i += 1
            continue

        # Tables
        if (
            "|" in raw
            and i + 1 < len(lines)
            and "|" in lines[i + 1]
            and re.search(r"-{3,}", lines[i + 1])
        ):
            flush_paragraph()
            table_html, new_i = _parse_markdown_table(i)
            if table_html:
                body_parts.append(table_html)
                i = new_i
                continue

        # Blockquotes as amber callouts (primary)
        if re.match(r"^\s*>\s?.+", raw):
            flush_paragraph()
            q_lines: list[str] = []
            while i < len(lines) and re.match(r"^\s*>\s?.+", lines[i]):
                content = re.sub(r"^\s*>\s?", "", lines[i])
                q_lines.append(content.strip())
                i += 1
            body_parts.append(render_blockquote("<br/>".join(q_lines)))
            continue

        # Bullet lists
        if re.match(r"^\s*[-•]\s+.+", raw):
            flush_paragraph()
            items: list[str] = []
            while i < len(lines) and re.match(r"^\s*[-•]\s+.+", lines[i]):
                item = re.sub(r"^\s*[-•]\s+", "", lines[i]).strip()
                items.append(item)
                i += 1
            body_parts.append(render_bullets(items))
            continue

        # Default: paragraph line
        paragraph_buf.append(raw)
        i += 1

    flush_paragraph()

    out.append(
        '<div style="padding:18px 0px;">' + "".join(body_parts) + "</div>"
    )

    # Data integrity warnings fallback callout if report contains them but not as blockquotes.
    md_lower = md.lower()
    if any(kw in md_lower for kw in ("data integrity", "missing data", "unavailable", "not available", "null")):
        out.append(
            '<div style="margin-top:16px;padding:12px 14px;border-radius:10px;border-left:6px solid #ef4444;background:#fff1f2;">'
            '<div style="font-weight:800;color:#991b1b;margin-bottom:6px;">Data Integrity Warning</div>'
            '<div style="color:#111827;line-height:1.6;font-size:14px;">'
            "Some fields may be unavailable. Any missing values should be treated as null/unavailable."
            "</div></div>"
        )

    out.append("</div></body></html>")
    return "".join(out)


def markdown_to_discord(md: str) -> str:
    """
    Discord-friendly plain text:
    - Strips tables to plain text
    - Keeps bold as *text*
    - Keeps bullet points
    - Truncates to 1800 chars
    """
    lines = md.replace("\r\n", "\n").split("\n")
    rendered: list[str] = []

    def to_bold_discord(s: str) -> str:
        # **text** -> *text* (Discord italic)
        return re.sub(r"\*\*([^*]+)\*\*", r"*\1*", s)

    def to_plain_inline(s: str) -> str:
        s = s.replace("\t", " ")
        s = to_bold_discord(s)
        s = re.sub(r"`([^`]+)`", r"\1", s)  # keep inline code as plain text
        return s.strip()

    def is_table_at(idx: int) -> bool:
        if idx + 1 >= len(lines):
            return False
        return "|" in lines[idx] and "|" in lines[idx + 1] and re.search(r"-{3,}", lines[idx + 1]) is not None

    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if stripped == "":
            i += 1
            continue

        if is_table_at(i):
            # Convert table rows to text lines: "col1 | col2"
            header = [c.strip() for c in raw.strip().strip("|").split("|")]
            rendered.append(to_plain_inline(" | ".join([h for h in header if h != ""])))
            i += 2
            while i < len(lines):
                ln = lines[i].strip()
                if ln == "" or "|" not in ln:
                    break
                row = [c.strip() for c in ln.strip().strip("|").split("|")]
                rendered.append(to_plain_inline(" | ".join([c for c in row if c != ""])))
                i += 1
            continue

        # Blockquotes: strip the '>' prefix
        if raw.lstrip().startswith(">"):
            content = re.sub(r"^\s*>\s?", "", raw).strip()
            if content:
                rendered.append(to_plain_inline(content))
            i += 1
            continue

        # Bullet points
        if re.match(r"^\s*[-•]\s+.+", raw):
            item = re.sub(r"^\s*[-•]\s+", "", raw).strip()
            rendered.append("- " + to_plain_inline(item))
            i += 1
            continue

        # Headings: drop '#'
        m = re.match(r"^\s*#{1,3}\s+(.+)\s*$", raw)
        if m:
            rendered.append(to_plain_inline(m.group(1)))
            i += 1
            continue

        rendered.append(to_plain_inline(raw))
        i += 1

    msg = "\n".join([r for r in rendered if r != ""]).strip()
    if len(msg) > 1800:
        msg = msg[:1800].rstrip()

    suffix = "\n📝 Full report sent via email"
    # Ensure suffix fits (truncate the body again if needed).
    if len(msg) + len(suffix) > 1800:
        msg = msg[: 1800 - len(suffix)].rstrip()
    return msg + suffix

