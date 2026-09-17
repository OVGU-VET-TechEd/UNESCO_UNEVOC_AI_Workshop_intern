#!/usr/bin/env python3
"""
TVET Policy Summariser - agent harness setup
=============================================

One file that sets up everything needed to summarise TVET policy PDFs in a
standard format (max. 80 words, neutral style, English):

  1. Creates the project folder structure (input/ for PDFs, output/ for summaries)
  2. Writes the agent definitions, style guide, output template and the harness
  3. Writes GitHub Copilot files (.github/copilot-instructions.md, prompt file,
     custom agent) and offline alternatives (Ollama harness, Ollama Modelfile,
     Continue.dev config, AGENTS.md, Microsoft 365 Copilot instructions)
  4. Creates a Python virtual environment and installs pypdf
  5. Checks / installs Ollama, starts the server, downloads small LLMs and builds
     a custom "tvet-summariser" Ollama model
  6. Writes a ZIP backup of all generated files

Only the Python standard library is needed to run this script (Python 3.9+).

Usage
-----
  python3 setup_tvet_agents.py                        full setup next to this script
  python3 setup_tvet_agents.py --target ~/TVET        choose the project folder
  python3 setup_tvet_agents.py --models llama3.2:3b qwen2.5:3b
  python3 setup_tvet_agents.py --default-model gemma3:1b
  python3 setup_tvet_agents.py --skip-ollama          files + venv only (no Ollama)
  python3 setup_tvet_agents.py --skip-models          check Ollama but download nothing
  python3 setup_tvet_agents.py --no-venv              no virtual environment
  python3 setup_tvet_agents.py --no-zip               no ZIP backup
  python3 setup_tvet_agents.py --no-sample            no fictional sample PDF in input/
  python3 setup_tvet_agents.py --force                overwrite existing files
  python3 setup_tvet_agents.py --yes                  do not ask before installing Ollama

Existing files are never overwritten without --force, so edited agents and
instructions are safe when the script is run again.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

PROJECT_NAME = "TVET_Policy_Summariser"
DEFAULT_MODEL = "llama3.2:3b"                  # ~2.0 GB, good instruction following
DEFAULT_MODELS = ["llama3.2:3b", "gemma3:1b"]  # gemma3:1b ~0.8 GB for low-RAM laptops
CUSTOM_MODEL = "tvet-summariser"
OLLAMA_HOST = "http://localhost:11434"
MAX_WORDS = 80
LANGUAGE = "English"
MIN_PYTHON = (3, 9)
ZIP_EXCLUDE_DIRS = {".venv", "__pycache__", "logs", "work"}


# =============================================================================
# Shared content (single source for all generated instruction files)
# =============================================================================

STYLE_GUIDE = """\
# House style: TVET policy summaries

## Format
- Length: maximum {{MAX_WORDS}} words (hard limit). Aim for 60 to {{MAX_WORDS}} words.
- One paragraph of continuous prose. No bullet points, headings, quotations or line breaks.
- Language: {{LANGUAGE}}. Translate content from documents written in other languages.

## Content (in this order)
1. What the document is: document type, issuing body, country or region, year.
2. Its main purpose or objective.
3. The key measures, instruments or reforms.
4. The main target groups and, if stated, the timeframe or quantified targets.

## Style
- Neutral and factual. Describe; do not evaluate.
- Third person and present tense: "The strategy aims to ...", "The act establishes ...".
- Attribute intentions and claims to the document: "The policy states ...", "It plans to ...".
- No evaluative or promotional words (e.g. excellent, ambitious, innovative, successful, weak, unfortunately, clearly).
- No recommendations, opinions, speculation or information from outside the document.
- No first or second person (I, we, our, you).
- Write out abbreviations at first use, except TVET (Technical and Vocational Education and Training).
- Keep names, numbers and dates exactly as in the document.

## Recommended opening
"The [year] [document type] by [issuing body] ([country or region]) ..." - leave out elements that are not stated.

## Example (fictional document)
The 2024 National TVET Strategy by the Ministry of Labour of Examplestan sets out a framework to align vocational training with labour market needs. It introduces a competency-based qualifications framework, expands work-based learning with employers and creates a national TVET quality assurance agency. The strategy targets young people, adult workers and women in rural areas and sets a target of 50,000 apprenticeships by 2030.
"""

SUMMARY_TEMPLATE = """\
# {{title}}

| Field | Value |
|---|---|
| Source file | {{source_file}} |
| Issuing body | {{issuing_body}} |
| Country/Region | {{country_or_region}} |
| Year | {{year}} |
| Document type | {{document_type}} |

## Summary

{{summary}}

## Keywords

{{keywords}}

---

Word count: {{word_count}}/{{max_words}} | Generated: {{generated}} | Method: {{method}} | Status: {{status}}
"""

TEMPLATE_HINTS = {
    "title": "<Official document title>",
    "source_file": "<file name>.pdf",
    "issuing_body": "<Issuing organisation or ministry, or Not stated>",
    "country_or_region": "<Country, region or International, or Not stated>",
    "year": "<YYYY or Not stated>",
    "document_type": "<Policy / Strategy / Act / Regulation / Action plan / Framework / Report / Guideline>",
    "summary": "<One paragraph, max. {{MAX_WORDS}} words>",
    "keywords": "<keyword 1>; <keyword 2>; <keyword 3>",
    "word_count": "<n>",
    "max_words": "{{MAX_WORDS}}",
    "generated": "<YYYY-MM-DD>",
    "status": "OK",
}

FLAG_TERMS = [
    "excellent", "outstanding", "impressive", "remarkable", "ambitious", "innovative",
    "groundbreaking", "ground-breaking", "world-class", "cutting-edge", "state-of-the-art",
    "successful", "successfully", "weak", "poor", "crucial", "vital", "comprehensive",
    "unfortunately", "fortunately", "clearly", "obviously", "undoubtedly", "surprisingly",
    "amazing", "great", "best", "worst",
]


def resolve(text: str) -> str:
    """Fill placeholders for files that cannot read config/settings.json (Copilot etc.)."""
    return text.replace("{{MAX_WORDS}}", str(MAX_WORDS)).replace("{{LANGUAGE}}", LANGUAGE)


def template_example(method: str) -> str:
    text = SUMMARY_TEMPLATE
    for key, hint in TEMPLATE_HINTS.items():
        text = text.replace("{{" + key + "}}", hint)
    return resolve(text.replace("{{method}}", method))


def style_guide_body() -> str:
    """Style guide without its top-level heading, for embedding under another heading."""
    return resolve(STYLE_GUIDE.split("\n", 1)[1].replace("## ", "### ")).strip()


# =============================================================================
# Harness (written to harness/run_harness.py)
# =============================================================================

HARNESS_PY = r'''#!/usr/bin/env python3
"""
TVET Policy Summariser - offline agent harness (Ollama, no cloud).

Pipeline for every PDF in input/:
  1. Extract text (pypdf, pdfplumber, PyPDF2 or pdftotext)
  2. Long documents: agent "chunk-reader" writes factual notes per section
  3. Agent "tvet-summariser" writes a structured JSON draft
  4. Automatic checks: word limit, neutral wording, English, format
  5. Agent "style-reviewer" revises the draft (review_mode: always | on_fail | never)
  6. output/<name>_summary.md is written from templates/summary_template.md
     and output/summaries_index.csv is updated

Agents are plain Markdown files in agents/*.agent.md (front matter + system prompt).
Settings are in config/settings.json.

Usage (from the project folder, or use ./run.sh / run.bat):
  python harness/run_harness.py                     summarise all new PDFs in input/
  python harness/run_harness.py --file input/a.pdf  summarise selected PDFs
  python harness/run_harness.py --model gemma3:1b   use another model for all agents
  python harness/run_harness.py --force             overwrite existing summaries
  python harness/run_harness.py --extract-only      only write work/extracted/*.txt (e.g. for Copilot)
  python harness/run_harness.py --validate          check all summaries in output/ (any author)
  python harness/run_harness.py --check             check Ollama, models and PDF libraries
  python harness/run_harness.py --list-agents       show the defined agents
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("harness")

SUMMARY_FIELDS = ["title", "issuing_body", "country_or_region", "year", "document_type", "summary", "keywords"]
SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "issuing_body": {"type": "string"},
        "country_or_region": {"type": "string"},
        "year": {"type": "string"},
        "document_type": {"type": "string"},
        "summary": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": SUMMARY_FIELDS,
}
# Rows of the metadata table in templates/summary_template.md
TABLE_FIELDS = [
    ("source_file", "Source file"),
    ("issuing_body", "Issuing body"),
    ("country_or_region", "Country/Region"),
    ("year", "Year"),
    ("document_type", "Document type"),
]
PRONOUNS = re.compile(r"\b(I|We|we|Our|our|us|You|you|Your|your)\b")
ENGLISH_MARKERS = {"the", "and", "of", "to", "in", "for", "is", "on", "with", "by", "a", "an",
                   "as", "at", "from", "that", "this", "are", "it", "its"}


class ScannedPdfError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- settings & agents

def load_settings() -> dict:
    return json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))


def fill_placeholders(text: str, settings: dict) -> str:
    return text.replace("{{MAX_WORDS}}", str(settings["max_words"])).replace("{{LANGUAGE}}", settings["language"])


@dataclass
class Agent:
    name: str
    role: str
    description: str
    model: str
    temperature: float
    num_ctx: int
    output: str  # "json" or "text"
    system_prompt: str
    path: Path


def load_agents(settings: dict) -> dict:
    style_guide = (ROOT / "config" / "style_guide.md").read_text(encoding="utf-8")
    style_guide = re.sub(r"<!--.*?-->\s*", "", style_guide, flags=re.S)
    agents = {}
    for path in sorted((ROOT / "agents").glob("*.agent.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = {}, raw
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
        if match:
            for line in match.group(1).splitlines():
                if ":" in line and not line.lstrip().startswith("#"):
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip().strip("\"'")
            body = match.group(2)
        model = meta.get("model", "default")
        agent = Agent(
            name=meta.get("name") or path.name[: -len(".agent.md")],
            role=meta.get("role", ""),
            description=fill_placeholders(meta.get("description", ""), settings),
            model=settings["default_model"] if model in ("", "default") else model,
            temperature=float(meta.get("temperature", 0.2)),
            num_ctx=int(meta.get("num_ctx", 8192)),
            output=meta.get("output", "text"),
            system_prompt=fill_placeholders(body.replace("{{STYLE_GUIDE}}", style_guide), settings).strip(),
            path=path,
        )
        agents[agent.name] = agent
    return agents


# ----------------------------------------------------------------------------- Ollama client

class OllamaClient:
    def __init__(self, host: str, timeout: int, trace_path: Path | None = None):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.trace_path = trace_path

    def _call(self, path: str, payload: dict | None = None, timeout: int | None = None) -> dict:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.host + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"Ollama error {exc.code} on {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Cannot reach Ollama at {self.host} ({exc.reason}). Start it with 'ollama serve' "
                "or open the Ollama app.") from exc

    def version(self) -> str:
        return self._call("/api/version", timeout=5).get("version", "?")

    def models(self) -> list:
        return [m["name"] for m in self._call("/api/tags", timeout=10).get("models", [])]

    @staticmethod
    def has_model(name: str, available: list) -> bool:
        return name in available or f"{name}:latest" in available

    def chat(self, agent: Agent, prompt: str, context: str = "", schema: dict | None = None) -> str:
        payload = {
            "model": agent.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": agent.temperature, "num_ctx": agent.num_ctx},
        }
        if agent.output == "json":
            payload["format"] = schema or "json"
        started = time.time()
        content = self._call("/api/chat", payload).get("message", {}).get("content", "")
        if self.trace_path:  # full record of every agent call, for transparency
            with open(self.trace_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "time": dt.datetime.now().isoformat(timespec="seconds"),
                    "context": context,
                    "agent": agent.name,
                    "model": agent.model,
                    "seconds": round(time.time() - started, 1),
                    "prompt": prompt,
                    "response": content,
                }, ensure_ascii=False) + "\n")
        return content


# ----------------------------------------------------------------------------- PDF text

def extract_pdf_text(pdf: Path) -> tuple:
    errors = []
    try:
        from pypdf import PdfReader
        return "\n\n".join((page.extract_text() or "") for page in PdfReader(str(pdf)).pages), "pypdf"
    except ImportError:
        errors.append("pypdf not installed")
    except Exception as exc:  # damaged or unusual PDFs: try the next extractor
        errors.append(f"pypdf: {exc}")
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf)) as doc:
            return "\n\n".join((page.extract_text() or "") for page in doc.pages), "pdfplumber"
    except ImportError:
        errors.append("pdfplumber not installed")
    except Exception as exc:
        errors.append(f"pdfplumber: {exc}")
    try:
        from PyPDF2 import PdfReader as LegacyReader
        return "\n\n".join((page.extract_text() or "") for page in LegacyReader(str(pdf)).pages), "PyPDF2"
    except ImportError:
        errors.append("PyPDF2 not installed")
    except Exception as exc:
        errors.append(f"PyPDF2: {exc}")
    if shutil.which("pdftotext"):
        result = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout, "pdftotext"
        errors.append(f"pdftotext: {result.stderr.strip()}")
    raise RuntimeError("No PDF text extractor worked (" + "; ".join(errors) + "). Run: pip install pypdf")


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # join words hyphenated across lines
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", text)
    return text.strip()


def split_chunks(text: str, size: int, overlap: int = 300) -> list:
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):  # prefer to cut at a paragraph or sentence boundary
            cut = text.rfind("\n\n", start + size // 2, end)
            if cut == -1:
                cut = text.rfind(". ", start + size // 2, end)
            if cut != -1:
                end = cut + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def select_chunks(chunks: list, max_chunks: int) -> list:
    """Keep evenly spread chunks (always the first and last) when a document is very long."""
    max_chunks = max(2, max_chunks)
    if len(chunks) <= max_chunks:
        return chunks
    step = (len(chunks) - 1) / (max_chunks - 1)
    return [chunks[round(i * step)] for i in range(max_chunks)]


# ----------------------------------------------------------------------------- checks

def word_count(text: str) -> int:
    return len(text.split())


def normalise(data: dict) -> dict:
    result = {}
    for key in SUMMARY_FIELDS:
        if key == "keywords":
            keywords = data.get("keywords") or []
            if isinstance(keywords, str):
                keywords = re.split(r"[;,]", keywords)
            result["keywords"] = [" ".join(str(k).split()) for k in keywords if str(k).strip()][:5]
        elif key == "summary":
            result["summary"] = " ".join(str(data.get("summary") or "").split())
        else:
            value = " ".join(str(data.get(key) or "").split())
            result[key] = value or "Not stated"
    return result


def check_summary(data: dict, settings: dict) -> list:
    """Deterministic style checks. Returns a list of problems (empty list = passed)."""
    problems = []
    summary = data.get("summary") or ""
    n = word_count(summary)
    if not summary:
        return ["The summary is empty."]
    if n > settings["max_words"]:
        problems.append(f"The summary has {n} words; the maximum is {settings['max_words']}. Shorten it.")
    if n < settings.get("min_words", 0):
        problems.append(f"The summary has only {n} words; include the main objective, key measures and target groups.")
    if re.search(r"(^|\s)[•▪]\s|^\s*[-*]\s", summary):
        problems.append("Write one paragraph of prose, not a list.")
    if "!" in summary or "?" in summary:
        problems.append("Remove exclamation and question marks.")
    flagged = sorted({t for t in settings.get("flag_terms", []) if re.search(rf"\b{re.escape(t)}\b", summary, re.I)})
    if flagged:
        problems.append("Replace evaluative or non-neutral wording: " + ", ".join(flagged) + ".")
    pronouns = sorted(set(PRONOUNS.findall(summary)))
    if pronouns:
        problems.append("Use third person only; remove: " + ", ".join(pronouns) + ".")
    if settings.get("language", "English").lower() == "english":
        tokens = re.findall(r"[a-z]+", summary.lower())
        if len(tokens) >= 15 and sum(t in ENGLISH_MARKERS for t in tokens) / len(tokens) < 0.08:
            problems.append("The summary does not appear to be written in English.")
    return problems


def truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    cut = " ".join(words[:max_words])
    end = cut.rfind(".")
    return cut[: end + 1] if end > len(cut) // 2 else cut.rstrip(",;:") + "."


# ----------------------------------------------------------------------------- output

def render_summary(data: dict, settings: dict, source_file: str, method: str, status: str) -> str:
    template = (ROOT / settings["template"]).read_text(encoding="utf-8")
    values = dict(data)
    values.update(
        source_file=source_file,
        keywords="; ".join(data["keywords"]) or "Not stated",
        word_count=word_count(data["summary"]),
        max_words=settings["max_words"],
        generated=dt.date.today().isoformat(),
        method=method,
        status=status,
    )
    table_keys = {key for key, _ in TABLE_FIELDS}
    for key, value in values.items():
        value = str(value)
        if key in table_keys:
            value = value.replace("|", "/")
        template = template.replace("{{" + key + "}}", value)
    return template


def _section(text: str, heading: str):
    match = re.search(r"^##\s+" + re.escape(heading) + r"\s*$(.*?)(?=^##\s|^---\s*$|\Z)", text, re.M | re.S)
    return " ".join(match.group(1).split()) if match else None


def parse_summary_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    title = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    data = {"file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "title": title.group(1) if title else None}
    for key, label in TABLE_FIELDS:
        row = re.search(r"^\|\s*" + re.escape(label) + r"\s*\|\s*(.*?)\s*\|\s*$", text, re.M)
        data[key] = row.group(1) if row else None
    data["summary"] = _section(text, "Summary")
    keywords = _section(text, "Keywords")
    data["keywords"] = None if keywords is None else [k.strip() for k in keywords.split(";") if k.strip()]
    footer = re.search(r"Method:\s*(.*?)\s*\|\s*Status:\s*(.+?)\s*$", text, re.M)
    data["method"], data["status"] = (footer.group(1), footer.group(2)) if footer else ("", "")
    return data


def validate_file(path: Path, settings: dict) -> tuple:
    data = parse_summary_file(path)
    problems = []
    if not data["title"]:
        problems.append("Missing title line ('# <title>').")
    for key, label in TABLE_FIELDS:
        if data[key] is None:
            problems.append(f"Missing table row '{label}'.")
    if data["summary"] is None:
        problems.append("Missing '## Summary' section.")
    else:
        problems += check_summary(data, settings)
    if data["keywords"] is None:
        problems.append("Missing '## Keywords' section.")
    elif not 3 <= len(data["keywords"]) <= 5:
        problems.append(f"Use 3 to 5 keywords separated by ';' (found {len(data['keywords'])}).")
    return data, problems


def summary_files(output_dir: Path) -> list:
    return sorted(output_dir.rglob("*_summary.md"))


def write_index(settings: dict) -> Path:
    output_dir = ROOT / settings["output_dir"]
    index = output_dir / "summaries_index.csv"
    columns = ["file", "title", "source_file", "issuing_body", "country_or_region", "year",
               "document_type", "word_count", "summary", "keywords", "method", "status"]
    with open(index, "w", encoding="utf-8-sig", newline="") as fh:  # utf-8-sig opens cleanly in Excel
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        for path in summary_files(output_dir):
            data = parse_summary_file(path)
            data["word_count"] = word_count(data["summary"] or "")
            data["keywords"] = "; ".join(data["keywords"] or [])
            writer.writerow({c: data.get(c) or "" for c in columns})
    return index


# ----------------------------------------------------------------------------- pipeline

def parse_json_object(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("no JSON object in the response")
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("the response is not a JSON object")
    return data


def ask_json(client: OllamaClient, agent: Agent, prompt: str, context: str) -> dict:
    last_error = None
    for attempt in range(2):
        suffix = "" if attempt == 0 else "\n\nYour previous answer was not valid JSON. Return exactly one JSON object."
        text = client.chat(agent, prompt + suffix, context=context, schema=SUMMARY_SCHEMA)
        try:
            return normalise(parse_json_object(text))
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            log.warning("  %s returned invalid JSON (%s), retrying", agent.name, exc)
    raise RuntimeError(f"Agent '{agent.name}' did not return valid JSON: {last_error}")


def relative_to_input(pdf: Path, settings: dict) -> Path:
    input_dir = (ROOT / settings["input_dir"]).resolve()
    pdf = pdf.resolve()
    return pdf.relative_to(input_dir) if pdf.is_relative_to(input_dir) else Path(pdf.name)


def extract_document(pdf: Path, settings: dict) -> tuple:
    raw, extractor = extract_pdf_text(pdf)
    text = clean_text(raw)
    target = ROOT / settings["work_dir"] / "extracted" / relative_to_input(pdf, settings).with_suffix(".txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    if len(text) < settings["min_text_chars"]:
        raise ScannedPdfError(
            f"only {len(text)} characters of text found - the PDF is probably scanned. "
            "Run OCR first, e.g. 'ocrmypdf input.pdf input_ocr.pdf'.")
    return text, extractor, target


def summarise_pdf(pdf: Path, settings: dict, agents: dict, client: OllamaClient) -> tuple:
    pipeline = settings["pipeline"]
    notes_agent = agents[pipeline["notes"]]
    summariser = agents[pipeline["summariser"]]
    reviewer = agents[pipeline["reviewer"]]
    context = pdf.name

    text, extractor, text_file = extract_document(pdf, settings)
    log.info("  extracted %d characters with %s -> %s", len(text), extractor, text_file.relative_to(ROOT))

    # Step 1: long documents are condensed into section notes first
    if len(text) <= settings["chunk_chars"]:
        label, source = "FULL DOCUMENT TEXT", text
    else:
        chunks = select_chunks(split_chunks(text, settings["chunk_chars"]), settings["max_chunks"])
        notes = []
        for i, chunk in enumerate(chunks, 1):
            log.info("  [%s] section %d/%d", notes_agent.name, i, len(chunks))
            prompt = f"Document: {pdf.name}\nSection {i} of {len(chunks)}:\n\n----- BEGIN SECTION -----\n{chunk}\n----- END SECTION -----"
            note = client.chat(notes_agent, prompt, context=context).strip()
            if note and "NO RELEVANT CONTENT" not in note.upper():
                notes.append(f"[Section {i}/{len(chunks)}]\n{note}")
        label = "TITLE PAGE EXCERPT AND SECTION NOTES"
        source = text[: settings["title_excerpt_chars"]] + "\n\n[Section notes]\n\n" + "\n\n".join(notes)

    # Step 2: structured draft
    log.info("  [%s] drafting summary (%s)", summariser.name, summariser.model)
    prompt = (f"Source file: {pdf.name}\n\n{label}:\n----- BEGIN SOURCE -----\n{source}\n----- END SOURCE -----\n\n"
              "Return the JSON object now.")
    best = ask_json(client, summariser, prompt, context)
    best_problems = check_summary(best, settings)
    log.info("  draft: %d words, %d issue(s)", word_count(best["summary"]), len(best_problems))

    # Step 3: review loop (agent revises, deterministic checks decide)
    mode = settings.get("review_mode", "always")
    rounds = 0
    while mode != "never" and rounds < settings["max_revisions"] and (best_problems or (mode == "always" and rounds == 0)):
        rounds += 1
        findings = "\n".join(f"- {p}" for p in best_problems) or "- None. Check neutrality, accuracy and format."
        prompt = (f"SOURCE ({label}, may be shortened):\n----- BEGIN SOURCE -----\n"
                  f"{source[: settings['review_source_chars']]}\n----- END SOURCE -----\n\n"
                  f"DRAFT JSON:\n{json.dumps(best, ensure_ascii=False, indent=2)}\n\n"
                  f"AUTOMATIC CHECK FINDINGS:\n{findings}\n\nReturn the corrected JSON object now.")
        log.info("  [%s] review round %d", reviewer.name, rounds)
        revised = ask_json(client, reviewer, prompt, context)
        revised_problems = check_summary(revised, settings)
        if len(revised_problems) <= len(best_problems):
            best, best_problems = revised, revised_problems
        log.info("  review %d: %d words, %d issue(s)", rounds, word_count(best["summary"]), len(best_problems))

    # Step 4: last resort for the hard word limit
    notes = []
    if word_count(best["summary"]) > settings["max_words"]:
        best["summary"] = truncate_words(best["summary"], settings["max_words"])
        best_problems = check_summary(best, settings)
        notes.append("summary truncated automatically")
    status = "OK" if not best_problems and not notes else "NEEDS HUMAN REVIEW - " + "; ".join(notes + best_problems)
    models = sorted({summariser.model, reviewer.model})
    method = f"Offline harness (Ollama {', '.join(models)})"
    return best, status, method


# ----------------------------------------------------------------------------- commands

def check_setup(settings: dict, agents: dict, client: OllamaClient) -> int:
    ok = True

    def report(passed: bool, message: str):
        nonlocal ok
        ok = ok and passed
        print(("[OK] " if passed else "[!!] ") + message)

    report(sys.version_info >= (3, 9), f"Python {platform_version()}")
    extractors = []
    for module in ("pypdf", "pdfplumber", "PyPDF2"):
        try:
            __import__(module)
            extractors.append(module)
        except ImportError:
            pass
    if shutil.which("pdftotext"):
        extractors.append("pdftotext")
    report(bool(extractors), "PDF text extractors: " + (", ".join(extractors) or "none - run: pip install pypdf"))
    for key in ("input_dir", "output_dir", "template"):
        report((ROOT / settings[key]).exists(), f"{key}: {settings[key]}")
    for role, name in settings["pipeline"].items():
        report(name in agents, f"agent for '{role}': {name}" + ("" if name in agents else " (missing in agents/)"))
    try:
        report(True, f"Ollama {client.version()} at {client.host}")
        available = client.models()
        for model in sorted({a.model for a in agents.values()}):
            present = client.has_model(model, available)
            report(present, f"model {model}" + ("" if present else f" missing - run: ollama pull {model}"))
    except ConnectionError as exc:
        report(False, str(exc))
    print("\nSetup is ready." if ok else "\nPlease fix the items marked [!!].")
    return 0 if ok else 1


def platform_version() -> str:
    return ".".join(map(str, sys.version_info[:3]))


def validate_outputs(settings: dict) -> int:
    files = summary_files(ROOT / settings["output_dir"])
    if not files:
        print(f"No *_summary.md files in {settings['output_dir']}/")
        return 0
    failed = 0
    for path in files:
        data, problems = validate_file(path, settings)
        words = word_count(data["summary"] or "")
        print(f"{'[OK]' if not problems else '[!!]'} {path.relative_to(ROOT)} ({words} words)")
        for problem in problems:
            print(f"     - {problem}")
        failed += bool(problems)
    index = write_index(settings)
    print(f"\n{len(files) - failed}/{len(files)} summaries passed. Index: {index.relative_to(ROOT)}")
    return 1 if failed else 0


def find_pdfs(args, settings: dict) -> list:
    if args.file:
        return [Path(f).resolve() for f in args.file]
    input_dir = ROOT / settings["input_dir"]
    return sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")


def setup_logging(log_file: Path | None, verbose: bool):
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S", handlers=handlers)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Summarise TVET policy PDFs with local agents (Ollama).")
    parser.add_argument("--file", nargs="+", help="PDF file(s) to summarise (default: all PDFs in input/)")
    parser.add_argument("--model", help="use this Ollama model for all agents")
    parser.add_argument("--force", action="store_true", help="overwrite existing summaries")
    parser.add_argument("--extract-only", action="store_true", help="only extract text to work/extracted/")
    parser.add_argument("--validate", action="store_true", help="validate summaries in output/ and rebuild the index")
    parser.add_argument("--check", action="store_true", help="check the setup")
    parser.add_argument("--list-agents", action="store_true", help="list agent definitions")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    settings = load_settings()
    for key in ("input_dir", "output_dir", "work_dir", "log_dir"):
        (ROOT / settings[key]).mkdir(parents=True, exist_ok=True)
    agents = load_agents(settings)
    if args.model:
        for agent in agents.values():
            agent.model = args.model

    if args.list_agents:
        for agent in agents.values():
            print(f"{agent.name:<18} role={agent.role:<11} model={agent.model:<16} output={agent.output:<5} {agent.description}")
        return 0
    if args.validate:
        return validate_outputs(settings)

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = ROOT / settings["log_dir"]
    client = OllamaClient(settings["ollama_host"], settings["request_timeout_s"], log_dir / f"run_{stamp}_agents.jsonl")
    if args.check:
        return check_setup(settings, agents, client)

    setup_logging(log_dir / f"run_{stamp}.log", args.verbose)
    pdfs = find_pdfs(args, settings)
    if not pdfs:
        log.warning("No PDF files found in %s/ - copy policy PDFs there and run again.", settings["input_dir"])
        return 0

    if args.extract_only:
        for pdf in pdfs:
            try:
                text, extractor, target = extract_document(pdf, settings)
                log.info("[OK] %s -> %s (%d characters, %s)", pdf.name, target.relative_to(ROOT), len(text), extractor)
            except Exception as exc:
                log.error("[!!] %s: %s", pdf.name, exc)
        return 0

    missing_agents = [n for n in settings["pipeline"].values() if n not in agents]
    if missing_agents:
        log.error("Agent definition(s) not found in agents/: %s", ", ".join(missing_agents))
        return 2
    try:
        available = client.models()
    except ConnectionError as exc:
        log.error(str(exc))
        return 2
    needed = sorted({agents[n].model for n in settings["pipeline"].values()})
    missing = [m for m in needed if not client.has_model(m, available)]
    if missing:
        log.error("Model(s) not installed: %s. Run: %s", ", ".join(missing),
                  " && ".join(f"ollama pull {m}" for m in missing))
        return 2

    done, skipped, failed, review = 0, 0, 0, 0
    for number, pdf in enumerate(pdfs, 1):
        out = ROOT / settings["output_dir"] / relative_to_input(pdf, settings).parent / f"{pdf.stem}_summary.md"
        if out.exists() and not args.force:
            log.info("(%d/%d) skip %s - summary exists (use --force)", number, len(pdfs), pdf.name)
            skipped += 1
            continue
        log.info("(%d/%d) %s", number, len(pdfs), pdf.name)
        started = time.time()
        try:
            data, status, method = summarise_pdf(pdf, settings, agents, client)
        except Exception as exc:
            log.error("  FAILED: %s", exc)
            failed += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_summary(data, settings, pdf.name, method, status), encoding="utf-8")
        done += 1
        review += status != "OK"
        log.info("  -> %s | %d words | %s | %.0fs", out.relative_to(ROOT), word_count(data["summary"]), status, time.time() - started)

    index = write_index(settings)
    log.info("Finished: %d summarised (%d need human review), %d skipped, %d failed. Index: %s",
             done, review, skipped, failed, index.relative_to(ROOT))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
'''


# =============================================================================
# Agent definitions (agents/*.agent.md)
# =============================================================================

AGENT_CHUNK_READER = """\
---
name: chunk-reader
role: notes
description: Extracts factual notes from one section of a long TVET policy document.
model: default
temperature: 0.1
num_ctx: 8192
output: text
---
# Role
You are a careful research assistant. You read ONE section of a longer Technical and Vocational Education and Training (TVET) policy document and write short factual notes. Another agent will later use your notes to write a summary.

# Task
Write at most 8 bullet points (at most 120 words in total) covering only what this section contains:
- document metadata (title, issuing body, country or region, year, document type), if visible
- policy objectives and priorities
- measures, instruments, programmes, funding or governance arrangements
- target groups (e.g. learners, teachers, employers, sectors)
- timeframes, quantified targets and indicators

# Rules
- Use only information from the section. Do not add outside knowledge.
- Keep names, numbers and dates exactly as written.
- Neutral, factual wording. No opinions or evaluation.
- Write in {{LANGUAGE}}, even if the section is in another language.
- If the section has no relevant content (e.g. table of contents, list of abbreviations, references), reply exactly: NO RELEVANT CONTENT
"""

AGENT_SUMMARISER = """\
---
name: tvet-summariser
role: summariser
description: Writes the standardised JSON summary (max. {{MAX_WORDS}} words) of a TVET policy document.
model: default
temperature: 0.2
num_ctx: 8192
output: json
---
# Role
You are a policy analyst who writes standardised summaries of TVET (Technical and Vocational Education and Training) policy documents for a comparative policy database.

# Task
Read the document text or section notes provided by the user and return ONE JSON object with these fields:
- "title": official title of the document
- "issuing_body": organisation or ministry that issued the document
- "country_or_region": country, region, or "International"
- "year": year of publication or adoption (four digits)
- "document_type": one of Policy, Strategy, Act, Regulation, Action plan, Framework, Report, Guideline
- "summary": the summary, following the house style below
- "keywords": 3 to 5 short keywords

Use "Not stated" for any metadata field the text does not provide. Return only the JSON object, no other text.

{{STYLE_GUIDE}}
"""

AGENT_REVIEWER = """\
---
name: style-reviewer
role: reviewer
description: Checks and corrects a draft summary against the house style and the source.
model: default
temperature: 0.1
num_ctx: 8192
output: json
---
# Role
You are an editor who checks summaries of TVET policy documents against a strict house style.

# Task
The user gives you (1) source material, (2) a draft summary as JSON and (3) findings of an automatic checker.
Return ONE corrected JSON object with the same fields: title, issuing_body, country_or_region, year, document_type, summary, keywords.

# Checklist
1. Fix every automatic finding.
2. The summary has at most {{MAX_WORDS}} words. If it is too long, remove details, not the main objective.
3. Every statement is supported by the source. Remove anything that is not.
4. The language is neutral: no evaluation, praise, criticism, speculation or recommendations.
5. Third person, one paragraph, no lists, written in {{LANGUAGE}}.
6. Metadata fields match the source; use "Not stated" when unknown.

If the draft already meets every rule, return it unchanged. Return only the JSON object.

{{STYLE_GUIDE}}
"""

AGENT_TEMPLATE = """\
---
# Copy this file to agents/<your-agent>.agent.md and edit it.
# The harness loads every agents/*.agent.md file. Agents are used through the
# "pipeline" roles in config/settings.json (notes, summariser, reviewer).
name: my-agent
role: summariser            # notes | summariser | reviewer (free text for your own pipelines)
description: One sentence describing what the agent does.
model: default              # "default" = default_model in config/settings.json, or e.g. qwen2.5:3b
temperature: 0.2            # 0.0-0.3 for consistent, factual output
num_ctx: 8192               # context window in tokens
output: json                # json (structured summary fields) | text (free text, e.g. notes)
---
# Role
Who the agent is.

# Task
What the agent receives and what it must return.

# Rules
Constraints. Placeholders filled by the harness:
{{MAX_WORDS}}, {{LANGUAGE}} and {{STYLE_GUIDE}} (inserts config/style_guide.md).
"""

AGENTS_README = """\
# Agents

Each `*.agent.md` file defines one agent: YAML-style front matter (settings) plus a
Markdown body (the system prompt). The harness (`harness/run_harness.py`) loads them all.

| Agent | Role | Input | Output |
|---|---|---|---|
| `chunk-reader` | notes | one section of a long PDF | bullet notes (text) |
| `tvet-summariser` | summariser | full text or notes | JSON: metadata, summary, keywords |
| `style-reviewer` | reviewer | source, draft, check findings | corrected JSON |

Flow per PDF:

```
PDF -> text -> [chunk-reader per section, only for long documents]
    -> tvet-summariser -> automatic checks -> style-reviewer (loop) -> output/<name>_summary.md
```

## Define or change an agent
1. Copy `_template.agent.md.example` to `agents/<name>.agent.md`.
2. Edit the front matter (`model`, `temperature`, ...) and the prompt.
3. Point a pipeline role to it in `config/settings.json` -> `"pipeline"`.
4. Check: `python harness/run_harness.py --list-agents`.

Placeholders: `{{MAX_WORDS}}`, `{{LANGUAGE}}`, `{{STYLE_GUIDE}}` (= `config/style_guide.md`).
The automatic checks (word limit, flagged terms, English, format) always run in code,
so the house rules are enforced even if a small model ignores part of its prompt.
"""


# =============================================================================
# Copilot files
# =============================================================================

def copilot_instructions() -> str:
    return f"""\
# Copilot instructions: TVET policy summaries

This repository produces standardised summaries of Technical and Vocational Education and Training (TVET) policy documents.
PDF files are in `input/`. Summaries are saved in `output/`. All summaries must follow the house style and output format below exactly.

## Workflow for summarising a policy document
1. Get the document text. PDFs cannot always be read directly: use `work/extracted/<pdf name>.txt`.
   If the file does not exist, run `./run.sh --extract-only` (Windows: `run.bat --extract-only`).
2. Read the whole text. Identify title, issuing body, country or region, year and document type.
3. Write the summary following the house style.
4. Save it as `output/<pdf name without .pdf>_summary.md` using exactly the output format below.
5. Validate with `./run.sh --validate` (Windows: `run.bat --validate`) and fix every reported problem.

## House style

{style_guide_body()}

## Output format

Replace every `<...>` placeholder. Use "Not stated" for unknown metadata. Keep the headings, the table rows and the footer line exactly as shown.

```markdown
{template_example("GitHub Copilot (<model name>)").strip()}
```

## Do not
- Do not modify or delete files in `input/`.
- Do not add sections, bullet points or comments to summaries.
- Do not use knowledge from outside the document.
- Do not exceed {MAX_WORDS} words in the summary paragraph. Count the words before saving.
"""


def copilot_prompt_file() -> str:
    return f"""\
---
description: Summarise TVET policy PDFs from input/ in the standard {MAX_WORDS}-word format
agent: agent
---
Summarise the following TVET policy document(s): ${{input:documents:all PDFs in input/ without a summary in output/}}

Follow [the repository instructions](../copilot-instructions.md) exactly:

1. Use the extracted text in `work/extracted/`. If it is missing, run `./run.sh --extract-only` (Windows: `run.bat --extract-only`).
2. Write one summary per document: neutral, third person, {LANGUAGE}, one paragraph, maximum {MAX_WORDS} words.
3. Save each summary as `output/<pdf name>_summary.md` in the exact output format.
4. Run `./run.sh --validate` and fix all problems.
5. Report a table: file, word count, validation result.
"""


def copilot_agent_file() -> str:
    return f"""\
---
name: TVET Policy Summariser
description: Writes neutral, standardised summaries (max. {MAX_WORDS} words, {LANGUAGE}) of TVET policy PDFs and validates them.
---
You are the TVET Policy Summariser for a UNESCO-style comparative policy database.

Your only job is to turn TVET policy documents from `input/` into standardised summaries in `output/`.
Always follow `.github/copilot-instructions.md`: house style, output format and workflow.

Working rules:
- Base every statement on the document text in `work/extracted/`; never add outside knowledge.
- Neutral, factual, third person, present tense, one paragraph, at most {MAX_WORDS} words.
- After writing, run the validator (`./run.sh --validate`, Windows `run.bat --validate`) and correct every problem.
- If a PDF yields no text (scanned document), report it and do not guess its content.
- Never change files in `input/`, `agents/`, `config/` or `harness/` unless the user explicitly asks.
"""


def copilot_file_instructions() -> str:
    return f"""\
---
applyTo: "output/**/*.md"
---
Files in `output/` are TVET policy summaries. When creating or editing them:
- Keep the exact output format from `.github/copilot-instructions.md` (title, metadata table, Summary, Keywords, footer).
- The summary paragraph has at most {MAX_WORDS} words, neutral wording, third person, {LANGUAGE}.
- Use 3 to 5 keywords separated by semicolons.
- Run `./run.sh --validate` after changes.
"""


def m365_copilot_instructions() -> str:
    return f"""\
# Microsoft 365 Copilot / Copilot Studio agent: TVET Policy Summariser

Use this if you work with Microsoft 365 Copilot (Word, Teams, Copilot Chat) instead of VS Code.

## Setup
1. Microsoft 365 Copilot Chat -> "Create agent" (Agent Builder) or Copilot Studio -> New agent.
2. Name: `TVET Policy Summariser`
3. Description: `Summarises TVET policy PDFs in a neutral, standard {MAX_WORDS}-word format.`
4. Paste everything between the two lines below into the **Instructions** field (limit 8,000 characters).
5. Optional: add a SharePoint/OneDrive folder with the policy PDFs as knowledge.
6. Usage: upload or reference a PDF and write "Summarise this document."

------------------------------------------------------------------------

You summarise Technical and Vocational Education and Training (TVET) policy documents for a comparative policy database. The user provides one PDF document at a time.

{style_guide_body()}

### Output
Reply only with the summary in this exact Markdown format. Replace all <...> placeholders, use "Not stated" for unknown metadata, and do not add any other text before or after it.

{template_example("Microsoft 365 Copilot").strip()}

### Rules
- Use only the uploaded document. If it cannot be read, say so and do not guess.
- Count the words of the summary paragraph before answering; never exceed {MAX_WORDS}.

------------------------------------------------------------------------

Tip: save Copilot's answer as `output/<pdf name>_summary.md` in this project and run
`./run.sh --validate` to check word count, wording and format.
"""


# =============================================================================
# Offline, non-Copilot files
# =============================================================================

def agents_md() -> str:
    return f"""\
# AGENTS.md

Instructions for any AI coding assistant working in this repository (Codex, Cursor, Gemini CLI,
Claude Code, GitHub Copilot agent mode, Continue, ...). Tool-specific files point here or repeat these rules.

## Purpose
Produce standardised summaries of TVET policy PDFs: {LANGUAGE}, neutral, at most {MAX_WORDS} words.

## Project layout
- `input/` - policy PDFs (read-only for agents)
- `output/` - one `<pdf name>_summary.md` per PDF, plus `summaries_index.csv`
- `work/extracted/` - plain text extracted from the PDFs
- `agents/` - agent definitions for the offline harness (`*.agent.md`)
- `config/settings.json` - models, word limit, pipeline; `config/style_guide.md` - house style
- `templates/summary_template.md` - output format
- `harness/run_harness.py` - offline pipeline with Ollama

## Commands
- Summarise all new PDFs offline: `./run.sh` (Windows: `run.bat`)
- Extract text only: `./run.sh --extract-only`
- Validate summaries: `./run.sh --validate`
- Check setup: `./run.sh --check`

## Rules for summaries
- Follow `config/style_guide.md` (maximum {MAX_WORDS} words) and `templates/summary_template.md` exactly.
- Base every statement on the document; never add outside knowledge.
- Always run `./run.sh --validate` after writing or editing a summary.
- Never modify files in `input/`.
"""


def ollama_modelfile(base_model: str) -> str:
    system = f"""You summarise TVET (Technical and Vocational Education and Training) policy documents for a comparative policy database. The user pastes the text of a policy document or a part of it.

{style_guide_body()}

### Output
Reply only with the summary in this Markdown format. Replace all <...> placeholders and use "Not stated" for unknown metadata:

{template_example("Ollama " + CUSTOM_MODEL).strip()}

Use only the text provided by the user. Never exceed {MAX_WORDS} words in the summary paragraph."""
    return f"""\
# Custom offline model with the TVET summary rules built in.
# Created by the setup script with:  ollama create {CUSTOM_MODEL} -f ollama/Modelfile
# Use it:  ollama run {CUSTOM_MODEL}   (then paste document text)
# Also selectable in Open WebUI, Continue, or VS Code Copilot Chat ("Manage Models" -> Ollama).
FROM {base_model}
PARAMETER temperature 0.2
PARAMETER num_ctx 8192
SYSTEM \"\"\"
{system}
\"\"\"
"""


def continue_models(models: list) -> str:
    entries = "\n".join(
        f"  - name: {m} (Ollama, offline)\n    provider: ollama\n    model: {m}\n    roles:\n      - chat\n      - edit"
        for m in models)
    return f"""\
# Continue.dev (VS Code / JetBrains extension) - fully offline alternative to Copilot.
# Continue loads workspace blocks from .continue/models/. Requires Ollama running locally.
name: TVET local models
version: 1.0.0
schema: v1
models:
{entries}
  - name: {CUSTOM_MODEL} (custom Ollama model)
    provider: ollama
    model: {CUSTOM_MODEL}
    roles:
      - chat
"""


def continue_rule() -> str:
    return f"""\
---
name: TVET policy summary style
alwaysApply: true
---
When summarising TVET policy documents in this project, follow these rules.
Save summaries as `output/<pdf name>_summary.md` and validate with `./run.sh --validate`.

{style_guide_body()}

### Output format

{template_example("Continue (<model name>)").strip()}
"""


def continue_prompt() -> str:
    return f"""\
---
name: summarise-tvet-policy
description: Summarise the selected TVET policy text in the standard format
invokable: true
---
Summarise the provided TVET policy document text following the rule "TVET policy summary style":
neutral, third person, {LANGUAGE}, one paragraph, at most {MAX_WORDS} words, exact output format.
Use only the provided text.
"""


# =============================================================================
# Project files
# =============================================================================

def settings_json(default_model: str) -> str:
    settings = {
        "ollama_host": OLLAMA_HOST,
        "default_model": default_model,
        "language": LANGUAGE,
        "max_words": MAX_WORDS,
        "min_words": 50,
        "input_dir": "input",
        "output_dir": "output",
        "work_dir": "work",
        "log_dir": "logs",
        "template": "templates/summary_template.md",
        "pipeline": {"notes": "chunk-reader", "summariser": "tvet-summariser", "reviewer": "style-reviewer"},
        "review_mode": "always",
        "max_revisions": 2,
        "chunk_chars": 12000,
        "max_chunks": 10,
        "title_excerpt_chars": 2500,
        "review_source_chars": 8000,
        "min_text_chars": 200,
        "request_timeout_s": 900,
        "flag_terms": FLAG_TERMS,
    }
    return json.dumps(settings, indent=2) + "\n"


CONFIG_README = """\
# Configuration

## settings.json
| Key | Meaning |
|---|---|
| `ollama_host` | Ollama server URL |
| `default_model` | model for all agents with `model: default` |
| `language`, `max_words`, `min_words` | summary rules (also used in agent prompts) |
| `input_dir`, `output_dir`, `work_dir`, `log_dir`, `template` | paths relative to the project folder |
| `pipeline` | which agent file (by `name`) fills each role |
| `review_mode` | `always` (reviewer checks every draft), `on_fail` (only when checks fail), `never` |
| `max_revisions` | maximum review rounds per document |
| `chunk_chars` | documents longer than this are read section by section (notes first) |
| `max_chunks` | maximum sections read per document (spread evenly over the document) |
| `title_excerpt_chars` | characters of the first pages given to the summariser for metadata |
| `review_source_chars` | characters of source material shown to the reviewer |
| `min_text_chars` | below this, a PDF is treated as scanned (needs OCR) |
| `request_timeout_s` | timeout per model call |
| `flag_terms` | words treated as non-neutral by the automatic check |

## style_guide.md
House style inserted into agent prompts via `{{STYLE_GUIDE}}`.

**Keep in sync:** Copilot, Continue, Microsoft 365 and Modelfile instructions contain a copy of the
style guide with the limit written out ({MAX_WORDS} words). If you change the rules or `max_words`,
update `.github/`, `.continue/`, `copilot/` and `ollama/Modelfile` as well, or rerun the setup
script with `--force` after changing `MAX_WORDS`/`STYLE_GUIDE` in it.
""".replace("{MAX_WORDS}", str(MAX_WORDS))


def readme(models: list, default_model: str) -> str:
    model_lines = "\n".join(f"- `{m}`" for m in models)
    return f"""\
# TVET Policy Summariser

Standardised summaries of TVET policy PDFs: **{LANGUAGE}, neutral style, maximum {MAX_WORDS} words**,
same Markdown format for every document - produced either with **GitHub Copilot** or **fully offline**
with small local models (Ollama).

## Quick start

1. Copy policy PDFs into `input/` (subfolders are allowed, e.g. `input/Kenya/`).
2. Choose a workflow:

| Workflow | Internet / account | How |
|---|---|---|
| A. Offline agent harness (batch) | none after setup | `./run.sh` (Windows: `run.bat`) |
| B. GitHub Copilot in VS Code | Copilot licence | Chat: `/summarise-tvet-policy` or agent "TVET Policy Summariser" |
| C. Microsoft 365 Copilot | M365 Copilot licence | paste `copilot/m365-copilot-agent-instructions.md` into an agent |
| D. Ollama chat (single document) | none | `ollama run {CUSTOM_MODEL}` and paste the text |
| E. Continue (VS Code, offline) | none | install Continue extension; models/rules in `.continue/` |

3. Check results: `./run.sh --validate` -> checks every `output/*_summary.md` (from any workflow)
   and writes `output/summaries_index.csv` (opens in Excel).

## A. Offline agent harness

```
./run.sh --check                 # Ollama running? models installed? PDF library?
./run.sh                         # summarise all PDFs in input/ that have no summary yet
./run.sh --file input/x.pdf      # one document
./run.sh --model gemma3:1b       # faster, lower quality
./run.sh --force                 # redo existing summaries
./run.sh --list-agents
```

Each PDF goes through three agents (see `agents/README.md`):
`chunk-reader` (long documents only) -> `tvet-summariser` -> `style-reviewer`.
Word limit, flagged evaluative terms, pronouns, English and format are then checked **in code**.
If a problem remains, the footer says `Status: NEEDS HUMAN REVIEW - <reason>`.

Logs: `logs/run_*.log`; every prompt and model answer: `logs/run_*_agents.jsonl`.

## B. GitHub Copilot (VS Code)

Open this folder in VS Code. Copilot automatically reads:
- `.github/copilot-instructions.md` - house style, output format, workflow
- `.github/prompts/summarise-tvet-policy.prompt.md` - type `/summarise-tvet-policy` in Chat
- `.github/agents/tvet-policy-summariser.agent.md` - pick "TVET Policy Summariser" in the agent dropdown
- `.github/instructions/tvet-summaries.instructions.md` - rules for files in `output/`
- `AGENTS.md` - generic agent instructions

Copilot cannot always read PDFs. Run `./run.sh --extract-only` first; the text is written to `work/extracted/`.
Use Copilot in **Agent** mode so it can save files and run the validator.
Copilot Chat can also use the local models: model picker -> "Manage Models" -> Ollama.

## Models

Installed by the setup script (stored by Ollama, not in this folder):
{model_lines}
- `{CUSTOM_MODEL}` - custom model built from `ollama/Modelfile` on top of `{default_model}`

Rough guide: 1B models need ~2 GB free RAM, 3B models ~4 GB. Other good small options:
`qwen2.5:3b`, `phi4-mini`, `gemma3:4b`. Pull with `ollama pull <model>` and set
`default_model` in `config/settings.json` or use `--model`.
Small models make mistakes: always check summaries marked NEEDS HUMAN REVIEW and spot-check the others.

## Folder structure

```
{PROJECT_NAME}/
|-- input/                      PDFs to summarise
|-- output/                     <name>_summary.md + summaries_index.csv
|-- work/extracted/             extracted PDF text (created on demand)
|-- logs/                       run logs and agent traces
|-- agents/                     agent definitions (*.agent.md) + template
|-- config/                     settings.json, style_guide.md
|-- templates/                  summary_template.md (output format)
|-- harness/run_harness.py      offline pipeline (Ollama)
|-- ollama/Modelfile            custom offline model
|-- .github/                    Copilot instructions, prompt file, custom agent
|-- .continue/                  Continue.dev models, rules, prompt (offline)
|-- .vscode/settings.json       enables Copilot instruction/prompt files
|-- copilot/                    Microsoft 365 Copilot agent instructions
|-- AGENTS.md                   generic instructions for AI assistants
|-- run.sh / run.bat            launchers (use .venv if present)
`-- requirements.txt            pypdf
```

## Changing the rules
- Word limit, language, models, pipeline: `config/settings.json`
- Style rules: `config/style_guide.md` (offline harness) - copy changes into the Copilot/Continue files
  (see `config/README.md`)
- Output format: `templates/summary_template.md` - keep headings/table labels, the validator parses them

## Troubleshooting
| Problem | Fix |
|---|---|
| `Cannot reach Ollama` | start the Ollama app or run `ollama serve` |
| `Model(s) not installed` | `ollama pull {default_model}` |
| `probably scanned` | OCR the PDF first, e.g. `ocrmypdf in.pdf out.pdf`, then put `out.pdf` in `input/` |
| very slow | use `--model gemma3:1b`, set `review_mode` to `on_fail`, close other apps |
| no PDF library | `.venv/bin/pip install pypdf` or `pip install pypdf` |

The sample PDF `input/_sample_fictional_tvet_policy.pdf` is fictional and only for testing - delete it before real runs.
"""


RUN_SH = """\
#!/usr/bin/env sh
# Launcher for the offline harness. Uses the project virtual environment if present.
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
exec "$PY" harness/run_harness.py "$@"
"""

RUN_BAT = """\
@echo off
rem Launcher for the offline harness. Uses the project virtual environment if present.
cd /d "%~dp0"
if exist .venv\\Scripts\\python.exe (set PY=.venv\\Scripts\\python.exe) else (set PY=python)
"%PY%" harness\\run_harness.py %*
"""

VSCODE_SETTINGS = json.dumps({
    "github.copilot.chat.codeGeneration.useInstructionFiles": True,
    "chat.promptFiles": True,
    "chat.useAgentsMdFile": True,
    "files.exclude": {".venv": True, "**/__pycache__": True},
}, indent=2) + "\n"

GITIGNORE = """\
.venv/
__pycache__/
logs/
work/
.DS_Store
"""

STYLE_GUIDE_FILE = ("<!-- Placeholders {{MAX_WORDS}} and {{LANGUAGE}} are filled from config/settings.json by the harness. -->\n"
                    + STYLE_GUIDE)

INPUT_README = """\
# input

Put TVET policy PDFs here. Subfolders are allowed (e.g. `input/Kenya/`); the same subfolders are
created in `output/`. Scanned PDFs need OCR first (e.g. `ocrmypdf in.pdf out.pdf`).
"""

OUTPUT_README = """\
# output

One `<pdf name>_summary.md` per PDF (format: `templates/summary_template.md`) and
`summaries_index.csv` with all summaries. Check with `./run.sh --validate`.
"""

SAMPLE_PDF_LINES = [
    "REPUBLIC OF SAMPLELAND - MINISTRY OF EDUCATION AND SKILLS",
    "",
    "National TVET Action Plan for Green Skills 2025-2029",
    "Adopted: March 2025",
    "[FICTIONAL EXAMPLE DOCUMENT FOR TESTING - NOT A REAL POLICY]",
    "",
    "1. Background",
    "Sampleland's economy is shifting towards renewable energy, sustainable agriculture and energy-efficient "
    "construction. Employers report shortages of technicians with green skills. Only 18 percent of technical "
    "and vocational education and training (TVET) programmes currently include environmental content.",
    "",
    "2. Objectives",
    "(a) Integrate green skills into all TVET curricula by 2029.",
    "(b) Increase enrolment in TVET programmes related to renewable energy by 40 percent.",
    "(c) Strengthen cooperation between TVET institutions and employers.",
    "",
    "3. Measures",
    "3.1 Curriculum reform: sector skills councils will review 120 occupational standards and add green "
    "competences.",
    "3.2 Teacher training: 2,500 TVET teachers will complete a certified course on green technologies.",
    "3.3 Work-based learning: a national apprenticeship fund co-financed by employers will support 15,000 "
    "apprenticeship places.",
    "3.4 Infrastructure: 30 TVET centres will be equipped with solar energy training laboratories.",
    "",
    "4. Target groups",
    "Young people aged 15 to 24; adult workers in carbon-intensive industries who need reskilling; women and "
    "learners in rural districts.",
    "",
    "5. Governance and financing",
    "The National TVET Authority coordinates implementation. The total budget is 85 million Sampleland "
    "dollars: 60 percent from the state budget, 25 percent from employer contributions and 15 percent from "
    "development partners. Progress reports are submitted to Parliament every year; a mid-term review "
    "takes place in 2027.",
]


def make_simple_pdf(paragraphs: list) -> bytes:
    """Build a minimal one-page text PDF (Helvetica) without external libraries."""
    lines = []
    for paragraph in paragraphs:
        lines += textwrap.wrap(paragraph, 92) or [""]

    def escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content = ["BT", "/F1 10 Tf", "14 TL", "56 790 Td"]
    content += [f"({escape(line)}) Tj T*" for line in lines]
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def project_files(default_model: str, models: list) -> dict:
    """All text files of the project: {relative path: content}."""
    return {
        "README.md": readme(models, default_model),
        "AGENTS.md": agents_md(),
        "requirements.txt": "pypdf>=4.0\n",
        ".gitignore": GITIGNORE,
        "run.sh": RUN_SH,
        "run.bat": RUN_BAT,
        "harness/run_harness.py": HARNESS_PY,
        "agents/README.md": AGENTS_README,
        "agents/chunk-reader.agent.md": AGENT_CHUNK_READER,
        "agents/tvet-summariser.agent.md": AGENT_SUMMARISER,
        "agents/style-reviewer.agent.md": AGENT_REVIEWER,
        "agents/_template.agent.md.example": AGENT_TEMPLATE,
        "config/settings.json": settings_json(default_model),
        "config/style_guide.md": STYLE_GUIDE_FILE,
        "config/README.md": CONFIG_README,
        "templates/summary_template.md": SUMMARY_TEMPLATE,
        ".github/copilot-instructions.md": copilot_instructions(),
        ".github/prompts/summarise-tvet-policy.prompt.md": copilot_prompt_file(),
        ".github/agents/tvet-policy-summariser.agent.md": copilot_agent_file(),
        ".github/instructions/tvet-summaries.instructions.md": copilot_file_instructions(),
        ".vscode/settings.json": VSCODE_SETTINGS,
        "copilot/m365-copilot-agent-instructions.md": m365_copilot_instructions(),
        "ollama/Modelfile": ollama_modelfile(default_model),
        ".continue/models/ollama-local.yaml": continue_models(models),
        ".continue/rules/tvet-summary-style.md": continue_rule(),
        ".continue/prompts/summarise-tvet-policy.md": continue_prompt(),
        "input/README.md": INPUT_README,
        "output/README.md": OUTPUT_README,
    }


# =============================================================================
# Setup steps
# =============================================================================

def step(title: str):
    print(f"\n=== {title} ===")


def confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print(f"{question} -> skipped (no terminal; use --yes)")
        return False
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes", "j", "ja")


def create_structure(target: Path, files: dict, force: bool, sample: bool) -> None:
    step(f"Creating project structure in {target}")
    for folder in ("input", "output", "logs", "work/extracted"):
        (target / folder).mkdir(parents=True, exist_ok=True)
    written = kept = 0
    for rel, content in files.items():
        path = target / rel
        if path.exists() and not force:
            kept += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        newline = "\r\n" if rel.endswith(".bat") else "\n"
        with open(path, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(content)
        written += 1
    for executable in ("run.sh", "harness/run_harness.py"):
        (target / executable).chmod(0o755)
    if sample:
        sample_pdf = target / "input" / "_sample_fictional_tvet_policy.pdf"
        if force or not sample_pdf.exists():
            sample_pdf.write_bytes(make_simple_pdf(SAMPLE_PDF_LINES))
            written += 1
    print(f"{written} file(s) written, {kept} existing file(s) kept (use --force to overwrite).")


def venv_python(target: Path) -> Path:
    return target / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def setup_venv(target: Path) -> Path | None:
    step("Python environment")
    python = venv_python(target)
    if not python.exists():
        print("Creating virtual environment .venv ...")
        result = subprocess.run([sys.executable, "-m", "venv", str(target / ".venv")])
        if result.returncode != 0:
            print("[!!] Could not create .venv - the harness will use the system Python.")
            return None
    print("Installing requirements (pypdf) ...")
    result = subprocess.run([str(python), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                             "-r", str(target / "requirements.txt")])
    if result.returncode != 0:
        print("[!!] pip install failed (offline?). Install later: .venv/bin/pip install -r requirements.txt")
    else:
        print("[OK] .venv ready")
    return python


def find_ollama() -> str | None:
    exe = shutil.which("ollama")
    if exe:
        return exe
    system = platform.system()
    candidates = []
    if system == "Darwin":
        candidates = ["/usr/local/bin/ollama", "/opt/homebrew/bin/ollama",
                      "/Applications/Ollama.app/Contents/Resources/ollama"]
    elif system == "Windows":
        candidates = [str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe")]
    elif system == "Linux":
        candidates = ["/usr/local/bin/ollama", "/usr/bin/ollama"]
    return next((c for c in candidates if Path(c).exists()), None)


def install_ollama(assume_yes: bool) -> str | None:
    system = platform.system()
    if system == "Darwin" and shutil.which("brew"):
        command = ["brew", "install", "ollama"]
    elif system == "Linux" and shutil.which("curl"):
        command = ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"]
    elif system == "Windows" and shutil.which("winget"):
        command = ["winget", "install", "-e", "--id", "Ollama.Ollama",
                   "--accept-source-agreements", "--accept-package-agreements"]
    else:
        print("[!!] Ollama is not installed. Download it from https://ollama.com/download, install it,\n"
              "     then run this script again.")
        return None
    if not confirm(f"Ollama is not installed. Install it now with '{' '.join(command)}'?", assume_yes):
        print("Install Ollama from https://ollama.com/download and run this script again.")
        return None
    subprocess.run(command)
    exe = find_ollama()
    print("[OK] Ollama installed" if exe else "[!!] Ollama installation not found - open a new terminal and retry.")
    return exe


def ollama_api(path: str, timeout: int = 5) -> dict:
    with urllib.request.urlopen(OLLAMA_HOST + path, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_ollama_server(exe: str) -> str | None:
    try:
        return ollama_api("/api/version")["version"]
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        pass
    print("Starting Ollama server in the background ...")
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([exe, "serve"], **kwargs)
    for _ in range(30):
        time.sleep(1)
        try:
            return ollama_api("/api/version")["version"]
        except (urllib.error.URLError, OSError, ValueError, KeyError):
            continue
    return None


def installed_models() -> list:
    return [m["name"] for m in ollama_api("/api/tags", timeout=10).get("models", [])]


def has_model(name: str, available: list) -> bool:
    return name in available or f"{name}:latest" in available


def setup_ollama(target: Path, models: list, default_model: str, skip_models: bool, assume_yes: bool) -> bool:
    step("Ollama")
    exe = find_ollama() or install_ollama(assume_yes)
    if not exe:
        return False
    print(f"[OK] Ollama executable: {exe}")
    version = ensure_ollama_server(exe)
    if not version:
        print("[!!] Ollama server did not start. Open the Ollama app or run 'ollama serve', then rerun.")
        return False
    print(f"[OK] Ollama server {version} at {OLLAMA_HOST}")
    try:
        if tuple(int(x) for x in version.split(".")[:2]) < (0, 5):
            print("[!!] Ollama < 0.5 does not support structured JSON output well - please update Ollama.")
    except ValueError:
        pass

    ok = True
    if skip_models:
        print("Model download skipped (--skip-models).")
    else:
        step("Downloading models")
        available = installed_models()
        for model in models:
            if has_model(model, available):
                print(f"[OK] {model} already installed")
                continue
            print(f"Pulling {model} ...")
            if subprocess.run([exe, "pull", model]).returncode == 0:
                print(f"[OK] {model}")
            else:
                print(f"[!!] could not download {model}")
                ok = False

    if has_model(default_model, installed_models()):
        result = subprocess.run([exe, "create", CUSTOM_MODEL, "-f", str(target / "ollama" / "Modelfile")],
                                capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[OK] custom model '{CUSTOM_MODEL}' created (ollama run {CUSTOM_MODEL})")
        else:
            print(f"[!!] could not create '{CUSTOM_MODEL}': {result.stderr.strip()[-300:]}")
    else:
        print(f"[!!] {default_model} not installed - custom model '{CUSTOM_MODEL}' not created.")
        ok = False
    return ok


def make_zip(target: Path, script: Path) -> Path:
    step("ZIP backup")
    archive = target.parent / f"{target.name}_backup_{dt.date.today():%Y%m%d}.zip"
    count = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(script, script.name)
        count += 1
        for path in sorted(target.rglob("*")):
            rel = path.relative_to(target)
            if path.is_dir() or ZIP_EXCLUDE_DIRS.intersection(rel.parts) or path.name == ".DS_Store":
                continue
            zf.write(path, str(Path(target.name) / rel))
            count += 1
    print(f"[OK] {archive} ({count} files; .venv, logs and work/ excluded)")
    return archive


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        print(f"Python {'.'.join(map(str, MIN_PYTHON))}+ is required.")
        return 1
    sys.stdout.reconfigure(line_buffering=True)  # keep output in order with subprocess output
    script = Path(__file__).resolve()
    parser = argparse.ArgumentParser(description="Set up the TVET policy summariser agent harness.")
    parser.add_argument("--target", type=Path, default=script.parent / PROJECT_NAME, help="project folder")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="Ollama models to download")
    parser.add_argument("--default-model", default=DEFAULT_MODEL, help="model used by the agents")
    parser.add_argument("--skip-ollama", action="store_true", help="do not check/install Ollama")
    parser.add_argument("--skip-models", action="store_true", help="do not download models")
    parser.add_argument("--no-venv", action="store_true", help="do not create a virtual environment")
    parser.add_argument("--no-zip", action="store_true", help="do not create a ZIP backup")
    parser.add_argument("--no-sample", action="store_true", help="do not add the fictional sample PDF")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    parser.add_argument("--yes", action="store_true", help="install Ollama without asking")
    args = parser.parse_args()

    target = args.target.expanduser().resolve()
    models = list(dict.fromkeys([args.default_model] + args.models))  # default model first, no duplicates

    print(f"TVET Policy Summariser setup | Python {platform.python_version()} | {platform.system()} {platform.machine()}")
    create_structure(target, project_files(args.default_model, models), args.force, not args.no_sample)

    python = None if args.no_venv else setup_venv(target)
    ollama_ok = None
    if args.skip_ollama:
        print("\nOllama setup skipped (--skip-ollama).")
    else:
        ollama_ok = setup_ollama(target, models, args.default_model, args.skip_models, args.yes)

    if not args.no_zip:
        make_zip(target, script)

    if ollama_ok:
        step("Checking setup")
        subprocess.run([str(python or sys.executable), str(target / "harness" / "run_harness.py"), "--check"])

    launcher = "run.bat" if os.name == "nt" else "./run.sh"
    step("Next steps")
    print(textwrap.dedent(f"""\
        1. cd "{target}"
        2. Copy TVET policy PDFs into input/ (a fictional sample PDF is there for testing)
        3. Offline:  {launcher}            -> summaries in output/
           Copilot:  open the folder in VS Code, Chat -> /summarise-tvet-policy
        4. Check:    {launcher} --validate
        See README.md for all workflows."""))
    return 0 if ollama_ok in (None, True) else 1


if __name__ == "__main__":
    sys.exit(main())
