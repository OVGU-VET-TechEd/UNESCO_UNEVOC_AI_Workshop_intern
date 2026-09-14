#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common.py — shared building blocks for both Part 3 variants.

Both `semi_agent.py` (fixed pipeline, human in the loop) and `agent.py` (control
loop, agent decides) import from this file, so the ONLY difference between the
two demos is control flow. That is the point of the exercise.

Read the section headers to find what you need:

    1. Model access        — the only code that talks to a language model
    2. PDF -> Markdown     — the required ingestion step
    3. Table extraction    — pulls numbers back out of the Markdown
    4. Chart               — a static PNG, embedded, no internet needed
    5. HTML report         — one self-contained file, no CDN, no external CSS
    6. PDF report          — optional; produced only if reportlab is installed

Nothing in this file calls the internet. The only network destination anywhere in
Part 3 is http://127.0.0.1:11434 , the local Ollama server.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from typing import Any

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
TIMEOUT_SECONDS = 300


# ===========================================================================
# 1. MODEL ACCESS — the only part of Part 3 that is "the AI"
# ===========================================================================

def call_ollama(model: str, prompt: str, num_predict: int = 220,
                temperature: float = 0.2) -> str:
    """Send one prompt to the local model. Returns the reply text.

    Everything else in this package is harness. This function is the model call.
    """
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8")).get("response", "").strip()


def list_models() -> list[str]:
    """Which models are installed here? REST API first, `ollama list` as fallback."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=10) as response:
            names = [m["name"] for m in
                     json.loads(response.read().decode("utf-8")).get("models", [])]
        if names:
            return sorted(names)
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError):
        pass
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True,
                                text=True, timeout=20, check=False)
        return sorted(line.split()[0]
                      for line in result.stdout.strip().splitlines()[1:] if line.strip())
    except (OSError, subprocess.SubprocessError):
        return []


def require_model(model: str) -> None:
    """Fail early with a useful message rather than deep inside a loop."""
    available = list_models()
    if not available:
        print(f"Warning: cannot reach Ollama at {OLLAMA_URL} to list models. Trying anyway.")
        return
    if model not in available:
        raise SystemExit(
            f"Model '{model}' is not installed here.\n"
            f"Installed: {', '.join(available)}\n"
            f"Pull it first:  ollama pull {model}"
        )


# ===========================================================================
# 2. PDF -> MARKDOWN — the ingestion step, required for both variants
# ===========================================================================
# Why this is not optional: everything downstream (chunking, retrieval,
# summarisation, table extraction) inherits the quality of this step. A PDF is a
# layout format, not a text format. Feeding raw PDF bytes or badly ordered text
# to a model produces confident nonsense.
#
# What we do:  text  -> Markdown paragraphs
#              tables -> Markdown pipe tables
#              images -> a NOTE with the caption if one is nearby.
# What we do NOT do: OCR of figures. If a number only exists inside a picture,
# it does not enter the dataset, and the report says so.

CAPTION_PATTERN = re.compile(
    r"^\s*((figure|fig\.?|abbildung|abb\.?|table|tabelle|chart)\s*\d*[.:]?\s*.*)$",
    re.IGNORECASE,
)


def _table_to_markdown(table: list[list[Any]]) -> str:
    """Turn a pdfplumber table (list of rows) into a Markdown pipe table."""
    rows = [[(cell if cell is not None else "").replace("\n", " ").strip()
             for cell in row] for row in table if row]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    header, body = rows[0], rows[1:]
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(["---"] * width) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in body]
    return "\n".join(lines)


def pdf_to_markdown(pdf_path: str) -> str:
    """Convert one PDF into clean Markdown. Returns the Markdown as a string."""
    try:
        import pdfplumber
    except ImportError as error:  # pragma: no cover - environment problem
        raise SystemExit(
            "pdfplumber is not installed. Run:  pip install -r requirements.txt"
        ) from error

    name = os.path.basename(pdf_path)
    parts: list[str] = [f"# {os.path.splitext(name)[0].replace('_', ' ')}", "",
                        f"*Converted from `{name}`. Figures are noted, not OCR'd.*", ""]

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            parts.append(f"## Page {page_number}")
            parts.append("")

            # --- tables first, so we can remove their text from the prose ---
            tables = page.extract_tables() or []
            table_markdown = [_table_to_markdown(t) for t in tables]
            table_cells = {str(cell).strip()
                           for t in tables for row in t for cell in row
                           if cell and str(cell).strip()}
            # Individual words of every cell, used to spot a prose line that is
            # really a table row flattened by the text extractor.
            cell_tokens = {token for cell in table_cells for token in cell.split()}

            # --- prose ---
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                # Skip lines that are really table content; the table renders below.
                if line in table_cells:
                    continue
                if all(part.strip() in table_cells
                       for part in re.split(r"\s{2,}", line) if part.strip()):
                    continue
                tokens = line.split()
                if len(tokens) > 1 and all(token in cell_tokens for token in tokens):
                    continue
                parts.append(line)
            parts.append("")

            for markdown_table in table_markdown:
                if markdown_table:
                    parts.append(markdown_table)
                    parts.append("")

            # --- images: noted by caption, never OCR'd ---
            for index, _image in enumerate(page.images or [], start=1):
                caption = ""
                for raw_line in text.splitlines():
                    match = CAPTION_PATTERN.match(raw_line.strip())
                    if match:
                        caption = match.group(1).strip()
                        break
                label = caption or "no caption found in the page text"
                parts.append(
                    f"> **[Image {index} on page {page_number}]** — {label} "
                    f"_(image content not extracted; no OCR was performed)_"
                )
                parts.append("")

    return "\n".join(parts).rstrip() + "\n"


# ===========================================================================
# 3. TABLE EXTRACTION — numbers back out of the Markdown
# ===========================================================================

def extract_tables_from_markdown(markdown_text: str) -> list[dict[str, str]]:
    """Find Markdown pipe tables and return their rows as dictionaries.

    Deliberately simple and readable: a table is a run of lines starting with
    '|', the second of which is a separator row.
    """
    rows: list[dict[str, str]] = []
    lines = markdown_text.splitlines()
    index = 0
    while index < len(lines):
        if lines[index].strip().startswith("|") and index + 1 < len(lines) \
                and set(lines[index + 1].replace("|", "").strip()) <= set("-: "):
            header = [c.strip() for c in lines[index].strip().strip("|").split("|")]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [c.strip() for c in lines[index].strip().strip("|").split("|")]
                cells += [""] * (len(header) - len(cells))
                rows.append(dict(zip(header, cells[:len(header)])))
                index += 1
        else:
            index += 1
    return rows


def to_number(value: str) -> float | None:
    """'1 234,5' / '1,234.5' / '12' -> float, or None if it is not a number."""
    if value is None:
        return None
    cleaned = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")          # 1,234.5
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")          # 1234,5
    try:
        return float(cleaned)
    except ValueError:
        return None


# ===========================================================================
# 4. CHART — a static PNG, rendered locally, embedded in the HTML
# ===========================================================================

def render_chart_png(groups: dict[str, dict[str, float]], title: str,
                     y_label: str) -> bytes:
    """Grouped bar chart -> PNG bytes. Uses matplotlib's non-interactive backend.

    `groups` maps a series name (one document) to {category: value}.
    """
    import matplotlib
    matplotlib.use("Agg")               # no display server needed, no GUI, offline
    import matplotlib.pyplot as plt

    categories: list[str] = []
    for series in groups.values():
        for key in series:
            if key not in categories:
                categories.append(key)

    figure, axes = plt.subplots(figsize=(7.2, 3.4), dpi=140)
    series_names = list(groups.keys())
    bar_width = 0.8 / max(len(series_names), 1)

    for position, name in enumerate(series_names):
        offsets = [i + position * bar_width for i in range(len(categories))]
        values = [groups[name].get(category, 0) for category in categories]
        axes.bar(offsets, values, width=bar_width, label=name)

    axes.set_xticks([i + 0.4 - bar_width / 2 for i in range(len(categories))])
    axes.set_xticklabels(categories)
    axes.set_ylabel(y_label)
    axes.set_title(title)
    axes.legend(fontsize=8, frameon=False)
    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)
    figure.tight_layout()

    buffer = io.BytesIO()
    figure.savefig(buffer, format="png")
    plt.close(figure)
    return buffer.getvalue()


# ===========================================================================
# 5. HTML REPORT — one self-contained file
# ===========================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root{{--ink:#101d29;--ink2:#4a5d6d;--rule:#c7d3dc;--accent:#1a4f8a;--tint:#eff4f8;}}
*{{box-sizing:border-box}}
body{{margin:0;background:#dde5eb;color:var(--ink);
 font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
.wrap{{max-width:900px;margin:24px auto;background:#fff;padding:28px 32px 36px;
 box-shadow:0 1px 3px rgba(16,29,41,.18)}}
h1{{margin:0 0 4px;font-size:25px;letter-spacing:-.02em}}
.meta{{color:var(--ink2);font-size:12px;margin:0 0 20px;
 border-bottom:3px solid var(--ink);padding-bottom:12px}}
.meta code{{background:var(--tint);padding:1px 4px}}
h2{{font-size:11px;text-transform:uppercase;letter-spacing:.13em;
 border-bottom:1px solid var(--rule);padding-bottom:4px;margin:26px 0 10px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th{{text-align:left;background:var(--tint);border-bottom:2px solid var(--accent);
 padding:6px 8px;font-size:11px;text-transform:uppercase;letter-spacing:.06em}}
td{{border-bottom:1px solid var(--rule);padding:6px 8px}}
tr:hover td{{background:#f7fafc}}
td.num{{text-align:right;font-variant-numeric:tabular-nums}}
img.chart{{width:100%;height:auto;border:1px solid var(--rule);margin-top:6px}}
.doc{{border-left:3px solid var(--accent);padding:2px 0 2px 14px;margin:0 0 16px}}
.doc h3{{margin:0 0 3px;font-size:15px}}
.doc .src{{font-size:11px;color:var(--ink2);margin:0 0 6px}}
.doc p{{margin:0}}
.badge{{display:inline-block;font-size:10px;font-family:ui-monospace,Menlo,monospace;
 background:var(--tint);border:1px solid var(--rule);padding:1px 5px;margin-left:6px}}
footer{{margin-top:26px;padding-top:12px;border-top:1px solid var(--rule);
 font-size:11px;color:var(--ink2)}}
@media print{{body{{background:#fff}}.wrap{{box-shadow:none;margin:0;max-width:none;padding:0}}}}
</style></head><body><div class="wrap">
<h1>{title}</h1>
<p class="meta">{meta}</p>
{body}
<footer>{footer}</footer>
</div></body></html>
"""


def build_html_report(title: str, meta: str, documents: list[dict],
                      table_rows: list[dict], chart_png: bytes | None,
                      footer: str) -> str:
    """Assemble a single self-contained HTML file. No CDN, no external assets."""
    body: list[str] = []

    if chart_png:
        encoded = base64.b64encode(chart_png).decode("ascii")
        body.append("<h2>Visualisation</h2>")
        body.append(f'<img class="chart" alt="Chart of extracted values" '
                    f'src="data:image/png;base64,{encoded}">')

    if table_rows:
        headers = list(table_rows[0].keys())
        body.append("<h2>Extracted data</h2><table><thead><tr>")
        body += [f"<th>{h}</th>" for h in headers]
        body.append("</tr></thead><tbody>")
        for row in table_rows:
            body.append("<tr>")
            for header in headers:
                value = row.get(header, "")
                css = ' class="num"' if to_number(str(value)) is not None else ""
                body.append(f"<td{css}>{value}</td>")
            body.append("</tr>")
        body.append("</tbody></table>")

    if documents:
        body.append("<h2>Document summaries</h2>")
        for document in documents:
            body.append(
                f'<div class="doc"><h3>{document["name"]}'
                f'<span class="badge">model: {document.get("model", "n/a")}</span></h3>'
                f'<p class="src">source: {document.get("source", "")}</p>'
                f'<p>{document.get("summary", "")}</p></div>'
            )

    return HTML_TEMPLATE.format(title=title, meta=meta,
                                body="\n".join(body), footer=footer)


# ===========================================================================
# 6. PDF REPORT — optional, only if reportlab is available
# ===========================================================================

def markdown_to_pdf(markdown_text: str, output_path: str) -> bool:
    """Render a simple Markdown document to PDF. Returns False if unavailable.

    Deliberately minimal: headings, paragraphs and bullets. Anything fancier
    belongs in a real typesetting step, not in a teaching demo.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer
    except ImportError:
        return False

    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(output_path, pagesize=A4,
                                 leftMargin=20 * mm, rightMargin=20 * mm,
                                 topMargin=18 * mm, bottomMargin=18 * mm)
    story: list[Any] = []
    bullets: list[Any] = []

    def flush_bullets() -> None:
        if bullets:
            story.append(ListFlowable(list(bullets), bulletType="bullet",
                                      leftIndent=12))
            story.append(Spacer(1, 4))
            bullets.clear()

    def escape(text: str) -> str:
        return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            flush_bullets()
            continue
        if line.startswith("### "):
            flush_bullets(); story.append(Paragraph(escape(line[4:]), styles["Heading3"]))
        elif line.startswith("## "):
            flush_bullets(); story.append(Paragraph(escape(line[3:]), styles["Heading2"]))
        elif line.startswith("# "):
            flush_bullets(); story.append(Paragraph(escape(line[2:]), styles["Title"]))
        elif line.lstrip().startswith(("- ", "* ")):
            bullets.append(ListItem(Paragraph(escape(line.lstrip()[2:]), styles["BodyText"])))
        elif line.startswith("|"):
            continue  # tables live in the HTML file, by design
        else:
            flush_bullets(); story.append(Paragraph(escape(line), styles["BodyText"]))

    flush_bullets()
    document.build(story)
    return True


# ===========================================================================
# 7. REPORT ASSEMBLY — shared by both variants so only control flow differs
# ===========================================================================

def build_dataset(documents: list[dict]) -> tuple[list[dict], dict[str, dict[str, float]]]:
    """Flatten per-document table rows into one dataset and one chart series set.

    Returns (table_rows_for_html, chart_groups). A row is kept only if it has a
    category column and at least one numeric column — anything else would be a
    guess, and guessing is what we are trying to avoid.
    """
    flat: list[dict] = []
    chart_groups: dict[str, dict[str, float]] = {}

    for document in documents:
        short = document["name"]
        for row in document.get("rows", []):
            keys = list(row.keys())
            if not keys:
                continue
            category = str(row[keys[0]]).strip()
            numeric = {k: to_number(row[k]) for k in keys[1:]}
            numeric = {k: v for k, v in numeric.items() if v is not None}
            if not category or not numeric:
                continue
            flat.append({"Document": short, keys[0]: category,
                         **{k: row[k] for k in numeric}})
            first_metric = next(iter(numeric))
            chart_groups.setdefault(short, {})[category] = numeric[first_metric]

    return flat, chart_groups


def write_report_files(out_dir: str, title: str, subtitle: str,
                       documents: list[dict], provenance: list[str]) -> dict[str, str]:
    """Write report.md, report.html and (if possible) report.pdf. Returns paths.

    `documents` is a list of dicts with keys: name, source, summary, model, rows.
    `provenance` is a list of plain-language lines recording which model produced
    what — this is written into both outputs, not just the log.
    """
    os.makedirs(out_dir, exist_ok=True)
    table_rows, chart_groups = build_dataset(documents)

    metric_name = "value"
    if table_rows:
        keys = [k for k in table_rows[0] if k != "Document"]
        if len(keys) > 1:
            metric_name = keys[1]

    chart_png = None
    if chart_groups:
        chart_png = render_chart_png(
            chart_groups, f"{metric_name} by category, per document", metric_name)

    # ---- Markdown ----------------------------------------------------------
    lines = [f"# {title}", "", f"*{subtitle}*", "",
             "## Method", "",
             "Each source PDF was converted to Markdown (text and tables extracted; "
             "figures noted by caption, never OCR'd), summarised by a local model, and "
             "its tables parsed back into a dataset. Numbers that appear only inside a "
             "figure are absent from this report by design.", "",
             "## Provenance", ""]
    lines += [f"- {line}" for line in provenance]
    lines += ["", "## Documents", ""]
    for document in documents:
        lines += [f"### {document['name']}", "",
                  f"*Source: `{document['source']}` · summarised by "
                  f"`{document.get('model', 'n/a')}`*", "",
                  document.get("summary", "(no summary)"), ""]
    lines += ["## Extracted data", "",
              f"{len(table_rows)} rows were parsed from tables across "
              f"{len(documents)} documents. The table and the chart are in the "
              "companion file `report.html`.", ""]
    markdown_text = "\n".join(lines)

    md_path = os.path.join(out_dir, "report.md")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(markdown_text)

    # ---- HTML (table + chart) ---------------------------------------------
    html_path = os.path.join(out_dir, "report.html")
    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(build_html_report(
            title=title,
            meta=subtitle + " &middot; generated fully offline against "
                 f"<code>{OLLAMA_URL}</code>",
            documents=documents,
            table_rows=table_rows,
            chart_png=chart_png,
            footer=" &middot; ".join(provenance),
        ))

    paths = {"markdown": md_path, "html": html_path}

    # ---- PDF (optional) ----------------------------------------------------
    pdf_path = os.path.join(out_dir, "report.pdf")
    if markdown_to_pdf(markdown_text, pdf_path):
        paths["pdf"] = pdf_path

    return paths
