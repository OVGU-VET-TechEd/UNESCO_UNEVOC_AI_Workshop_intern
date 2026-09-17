#!/usr/bin/env python3
"""
setup_tvet_agents.py  -  One-file installer for the TVET Policy Summariser agent workspace.

What it does
  1. Writes the complete workspace (agents, harness, Copilot instructions, Continue
     configuration, AGENTS.md, VS Code tasks, input/ and output/ folders, scripts).
  2. Creates a Python virtual environment (.venv) and installs requirements.
  3. Checks for Ollama, offers to install it (winget or official installer on Windows),
     starts the Ollama server if needed and pulls small example models.
  4. Runs a health check of the harness.
  5. Creates a ZIP backup of the workspace.

Usage (Windows PowerShell or cmd, Python 3.9+):
  python setup_tvet_agents.py
  python setup_tvet_agents.py --target D:\\AI\\tvet-policy-summarizer
  python setup_tvet_agents.py --models llama3.2:3b,gemma3:4b --yes
  python setup_tvet_agents.py --skip-ollama            (files + venv only)
  python setup_tvet_agents.py --zip-only               (backup an existing workspace)

Only the Python standard library is needed to run this script.
"""

import argparse
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

VERSION = "1.0.0"
IS_WINDOWS = os.name == "nt"
DEFAULT_TARGET = "tvet-policy-summarizer"
DEFAULT_MODELS = ["llama3.2:3b", "qwen2.5:3b"]
OLLAMA_API = "http://127.0.0.1:11434"
OLLAMA_WINDOWS_INSTALLER = "https://ollama.com/download/OllamaSetup.exe"
APPROX_MODEL_SIZES = {
    "llama3.2:1b": "1.3 GB",
    "llama3.2:3b": "2.0 GB",
    "qwen2.5:3b": "1.9 GB",
    "qwen2.5:7b": "4.7 GB",
    "gemma3:1b": "0.8 GB",
    "gemma3:4b": "3.3 GB",
    "gemma3:12b": "8.1 GB",
    "phi4-mini": "2.5 GB",
    "mistral:7b": "4.1 GB",
}
ZIP_EXCLUDE_DIRS = {".venv", "__pycache__", "backups", ".git", ".pytest_cache"}
ZIP_DATA_DIRS = {"input", "output", "work", "logs", "reports"}
CRLF_SUFFIXES = {".bat", ".cmd", ".ps1"}


# =====================================================================================
# Embedded workspace files
# (all file bodies are raw strings; placeholders {{...}} are filled in by build_files)
# =====================================================================================

README_MD = r'''# TVET Policy Summariser - Agent Workspace

Standardised, neutral summaries (maximum 80 words) of TVET policy documents supplied as PDF files.
The workspace supports three ways of working that share one set of rules:

| Mode | Runs where | Entry point |
|---|---|---|
| A. Offline harness | Local Ollama models, terminal or VS Code task | `python -m harness run` |
| B. GitHub Copilot Chat | VS Code, Copilot (online) | `.github/copilot-instructions.md`, `/summarize-tvet-policy` |
| C. Continue extension | VS Code, local Ollama models | `.continue/` rules, prompt and model block |

## Quick start (Windows)

```powershell
# 1. put PDF files into .\input
# 2. run the offline pipeline
.\scripts\harness.ps1 run            # or: scripts\run_summarizer.bat
# 3. read results in .\output, check them
.\scripts\harness.ps1 validate
```

If PowerShell blocks scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use the `.bat` files.
In VS Code: *Terminal > Run Task > TVET: ...*

## Folder structure

```
tvet-policy-summarizer/
|-- input/                      PDF files to summarise (read-only for agents)
|-- output/                     <pdf-name>.summary.md, one per PDF
|-- work/extracted/             plain text extracted from PDFs (for Copilot / Continue)
|-- reports/                    reviewer-agent reports
|-- logs/                       JSONL run logs
|-- agents/                     agent definitions (*.agent.md, front matter + system prompt)
|-- prompts/                    style guide and step prompts shared by all modes
|-- config/                     harness.json (backends), style_rules.json (neutral-language checks)
|-- harness/                    Python harness (PDF extraction, LLM backends, validation)
|-- examples/                   reference summary
|-- .github/                    Copilot: instructions, prompt file, custom agent, file instructions
|-- .continue/                  Continue: rules, prompt, local Ollama model block
|-- .vscode/                    tasks, settings, recommended extensions
|-- scripts/                    .bat and .ps1 launchers
|-- AGENTS.md                   tool-agnostic agent instructions
`-- setup_tvet_agents.py        the installer that created this workspace
```

## Mode A - offline harness

```
python -m harness check                      health check (Python packages, Ollama, models, input)
python -m harness run                        summarise all PDFs in input/
python -m harness run input\file.pdf --overwrite
python -m harness run --model qwen2.5:3b     try another model
python -m harness extract                    PDF -> work/extracted/*.txt
python -m harness validate                   check every file in output/
python -m harness review                     second agent checks neutrality -> reports/
python -m harness agents                     list agent definitions
python -m harness new-agent my-agent         scaffold agents/my-agent.agent.md
```

How the pipeline works:

1. Text is extracted with `pypdf` (fallback `pdfplumber` if installed).
2. Short documents go to the model directly. Long documents are split into chunks; the model writes
   factual notes per chunk (map), then produces the record from the first page plus notes (reduce).
3. The model must return JSON (title, issuing body, country/region, year, type, summary, keywords).
4. The harness validates: word limit, single paragraph, no bullets, no first person, no evaluative terms
   from `config/style_rules.json`. Errors are sent back to the model (up to `max_retries`).
5. The harness renders the Markdown itself, so the output format is always identical.
   If the model still exceeds the limit, the summary is trimmed at sentence level and logged as
   `auto_trimmed` or `needs_review`.

Scanned (image-only) PDFs contain no text layer. They are skipped with a message; run OCR first
(e.g. OCRmyPDF) and put the OCR'd file into `input/`.

## Mode B - GitHub Copilot

1. Open the folder in VS Code with GitHub Copilot Chat enabled.
2. Run task *TVET: Extract PDF text* (Copilot cannot reliably read PDFs; it reads `work/extracted`).
3. In Copilot Chat (Agent mode) type `/summarize-tvet-policy` or select the custom agent
   *tvet-policy-summarizer*.
4. Run task *TVET: Validate summaries* - the same validator checks Copilot output.

Files used by Copilot:
- `.github/copilot-instructions.md` - always-on repository instructions
- `.github/instructions/tvet-summaries.instructions.md` - applied when editing `output/**/*.md`
- `.github/prompts/summarize-tvet-policy.prompt.md` - reusable slash command
- `.github/agents/tvet-policy-summarizer.agent.md` - custom agent (older VS Code versions used
  `.github/chatmodes/*.chatmode.md`; copy the file there if your version does not list it)

## Mode C - Continue (offline)

The workspace contains `.continue/rules`, `.continue/prompts` and `.continue/models/local-ollama.yaml`.
Continue picks up workspace blocks automatically in recent versions. If yours does not, copy the
model entries from `.continue/models/local-ollama.yaml` into `%USERPROFILE%\.continue\config.yaml`.
Small models have limited context: attach the file from `work/extracted`, not the PDF.

## Defining agents

An agent is a Markdown file in `agents/` with front matter (settings) and a body (system prompt):

```
---
name: tvet-policy-summarizer
task: policy_summary          # policy_summary | summary_review
backend: ollama               # ollama | openai_compatible | mock
model: llama3.2:3b
temperature: 0.1
max_words: 80
max_retries: 3
chunk_chars: 6000
include: [prompts/style-guide.md]
---
System prompt text ...
```

Settings can be overridden per run (`--model`, `--backend`) or by environment variables
`TVET_BACKEND`, `TVET_MODEL`, `OLLAMA_HOST` (also read from a `.env` file, see `.env.example`).

## Online models without Copilot

Copilot has no scripting API. For online batch runs use any OpenAI-compatible endpoint
(`backend: openai_compatible`), configured in `config/harness.json`:
`base_url`, `api_key_env` (name of the environment variable holding the key), optional `extra_headers`.
Only send documents to online services if this is permitted for the material.

## Keeping the rules in sync

The authoritative style rules are in `prompts/style-guide.md`. Short copies exist in
`.github/copilot-instructions.md`, `.github/instructions/...`, `.continue/rules/...` and `AGENTS.md`.
When you change the standard (e.g. word limit), update all of them and `max_words` in the agent files.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Cannot reach http://127.0.0.1:11434` | Start the Ollama app or run `ollama serve` |
| `Model ... is not available` | `ollama pull <model>` |
| Very slow / out of memory | Use a smaller model (`llama3.2:1b`, `gemma3:1b`) or reduce `num_ctx` in config/harness.json |
| Summaries often too long | Lower `temperature`, try `qwen2.5:3b`, or a larger model such as `gemma3:12b` |
| pip fails offline | On a connected PC: `pip download -r requirements.txt -d wheels`; then `python setup_tvet_agents.py --wheelhouse wheels` |
| Corporate proxy | Local Ollama calls bypass proxies automatically; for pip set `HTTPS_PROXY` |
'''

AGENTS_MD = r'''# AGENTS.md - instructions for any AI coding or chat agent

This file follows the tool-agnostic AGENTS.md convention (read by GitHub Copilot agent mode,
Continue, Codex CLI, Aider and similar tools). Copilot-specific files are in `.github/`.

## Purpose
Produce standardised summaries of TVET (Technical and Vocational Education and Training) policy
documents. Sources are PDF files in `input/`. Results go to `output/<pdf-name>.summary.md`.

## Hard rules
- Summary section: maximum 80 words, one paragraph, English, neutral and factual, third person.
- Use only information from the document. Unknown metadata is written as `Not stated`.
- Never modify, rename or delete files in `input/`.
- Follow the template in `examples/example-summary.md` exactly.
- The full style guide is `prompts/style-guide.md`; it overrides anything else.

## Commands
- Extract text: `python -m harness extract` (writes `work/extracted/*.txt`)
- Offline batch summaries with Ollama: `python -m harness run`
- Validate summaries (run after writing any summary): `python -m harness validate`
- Neutrality review by a second agent: `python -m harness review`

On Windows use `.venv\Scripts\python.exe` instead of `python` if the virtual environment is not active.

## Code changes
The harness is plain Python 3.9+ with `pypdf` as the only required dependency.
Keep it dependency-light and runnable offline. Do not add network calls other than to the
configured LLM backend.
'''

STYLE_GUIDE_MD = r'''# Style guide: TVET policy summaries

This guide is authoritative for every agent, model and person producing summaries in this workspace.

## 1. Length and form
- The **Summary** section has a **maximum of 80 words** (target 60-80 words).
- Exactly one paragraph. No bullet points, no headings, no line breaks, no quotations.
- Complete sentences. No exclamation marks, no rhetorical questions.

## 2. Language and tone
- English, consistent British spelling (e.g. "programme", "organisation"), regardless of source language.
- Neutral and factual. Describe what the document says; do not evaluate, praise, criticise or recommend.
- Third person only. Never use "I", "we", "our", "you".
- Present tense for what the document does ("The strategy sets out ..."); past tense only for completed events.
- Attribute content to the document: "The document states / aims to / introduces / assigns ...".
- No speculation about impact, success or intentions beyond what is written.
- Avoid evaluative words such as: groundbreaking, landmark, ambitious, impressive, excellent,
  outstanding, remarkable, innovative-as-praise, crucial, vital, comprehensive, robust, successfully.
- Spell out abbreviations at first use, except TVET. Keep abbreviations to a minimum.
- Numbers as digits; reproduce targets, dates and figures exactly as stated.

## 3. Content of the summary (recommended order)
1. Document type, issuing body, country or region, year and scope.
2. Main objectives.
3. Key measures or instruments.
4. Target groups, governance, funding or timeframe where stated.

## 4. Metadata
- **Title**: official title as written. If not in English, add an English translation in square brackets.
- **Issuing body**, **Country / region**, **Year**, **Document type**: as stated in the document.
- Write `Not stated` if the document does not provide the information. Do not guess.

## 5. Keywords
- 3 to 5 keywords, lowercase except proper nouns, separated by semicolons.

## 6. Output template

```
# <Title>

| Field | Value |
|---|---|
| Source file | <file name>.pdf |
| Issuing body | <...> |
| Country / region | <...> |
| Year | <...> |
| Document type | <...> |

## Summary

<one neutral paragraph, maximum 80 words>

## Keywords

<keyword>; <keyword>; <keyword>

---

*Word count: <n>/80 | Generated: <YYYY-MM-DD> | Agent: <agent> | Model: <model>*
```
'''

MAP_STEP_MD = r'''Read the following excerpt from a TVET policy document (part {{PART}} of {{TOTAL}}).

Write up to 8 short factual notes as a plain list. Only record what the excerpt states about:
document title, issuing body, country or region, year, document type, objectives, measures and
instruments, target groups, governance, funding, timeframe and targets.

Do not interpret or evaluate. Do not add information that is not in the excerpt.
If the excerpt contains none of this information, write exactly: No relevant content.

<document>
{{TEXT}}
</document>
'''

REDUCE_STEP_MD = r'''Using only the material below, create a summary record of the TVET policy document.

Return ONLY a JSON object with exactly these keys:
{
  "title": "official document title; add an English translation in square brackets if the title is not in English",
  "issuing_body": "organisation that issued the document, or Not stated",
  "country_or_region": "country or region covered, or Not stated",
  "year": "year of publication or adoption, or Not stated",
  "document_type": "for example strategy, law, regulation, action plan, guideline, report; or Not stated",
  "summary": "one neutral paragraph of at most {{MAX_WORDS}} words",
  "keywords": ["3 to 5 lowercase keywords"]
}

Requirements for "summary":
- At most {{MAX_WORDS}} words, one paragraph, complete sentences, no bullet points.
- English, neutral and factual, third person. No praise, criticism, recommendations or speculation.
- Recommended order: document type, issuer and scope; main objectives; key measures;
  target groups, governance, funding or timeframe if stated.

Source file name: {{FILENAME}}
Material provided: {{MATERIAL_TYPE}}

<document>
{{TEXT}}
</document>
'''

REVIEW_STEP_MD = r'''Check the TVET policy summary below against the style guide in your instructions.

Return ONLY a JSON object with exactly these keys:
{
  "neutral": true or false,
  "within_limit": true or false,
  "issues": ["short description of each problem, empty list if none"],
  "suggested_revision": "corrected summary of at most {{MAX_WORDS}} words, or an empty string if no change is needed"
}

Word count measured by the harness: {{WORD_COUNT}} (limit {{MAX_WORDS}}).

<summary>
{{TEXT}}
</summary>
'''

EXAMPLE_SUMMARY_MD = r'''# National TVET Strategy 2025-2030

| Field | Value |
|---|---|
| Source file | example-national-tvet-strategy.pdf |
| Issuing body | Ministry of Education (fictional example) |
| Country / region | Examplia |
| Year | 2025 |
| Document type | Strategy |

## Summary

The National TVET Strategy 2025-2030, issued by the Ministry of Education of Examplia, sets out a framework for aligning vocational training with labour market needs. It aims to expand work-based learning, introduce a national qualifications framework and strengthen quality assurance in training institutions. Measures include employer partnerships, teacher training programmes and a skills forecasting system. The strategy targets young people and adults seeking reskilling and assigns coordination to a national TVET council.

## Keywords

work-based learning; qualifications framework; quality assurance; skills forecasting

---

*Word count: 72/80 | Generated: 2026-01-01 | Agent: example | Model: none (reference example)*
'''

SUMMARIZER_AGENT_MD = r'''---
name: tvet-policy-summarizer
description: Summarises TVET policy PDFs in the standard format (max. 80 words, neutral style)
task: policy_summary
backend: ollama
model: {{DEFAULT_MODEL}}
temperature: 0.1
max_words: 80
max_retries: 3
chunk_chars: 6000
max_chunks: 20
min_text_chars: 300
output_suffix: .summary.md
map_prompt: prompts/map-step.md
reduce_prompt: prompts/reduce-step.md
include: [prompts/style-guide.md]
---
You are a documentation analyst for Technical and Vocational Education and Training (TVET) policy.
Your only task is to produce factual, neutral summary records of TVET policy documents for a
standardised policy collection.

Rules you always follow:
- Use only information contained in the supplied document material. Never add outside knowledge.
- Write in English, even if the source document is in another language.
- The summary has at most 80 words and is a single neutral paragraph.
- Write "Not stated" for any metadata the document does not provide.
- Return exactly the output format requested in the user message and nothing else.

The style guide below is binding.
'''

REVIEWER_AGENT_MD = r'''---
name: tvet-summary-reviewer
description: Second-pass reviewer that checks existing summaries for neutrality and the word limit
task: summary_review
backend: ollama
model: {{REVIEW_MODEL}}
temperature: 0.0
max_words: 80
review_prompt: prompts/review-step.md
include: [prompts/style-guide.md]
---
You are a careful copy editor for a TVET policy summary collection.
You check summaries against the style guide below: neutral and factual tone, third person,
no evaluation or recommendation, one paragraph, at most 80 words, English.
You report problems precisely and briefly. You only propose a revision when a rule is broken,
and a revision must not add information that is not in the original summary.
Return exactly the JSON format requested in the user message.

The style guide below is binding.
'''

AGENT_TEMPLATE_MD = r'''---
name: {{AGENT_NAME}}
description: Describe what this agent does in one sentence
# task selects the harness pipeline: policy_summary | summary_review
task: policy_summary
# backend: ollama | openai_compatible | mock
backend: ollama
model: {{DEFAULT_MODEL}}
temperature: 0.1
max_words: 80
max_retries: 3
chunk_chars: 6000
max_chunks: 20
output_suffix: .summary.md
map_prompt: prompts/map-step.md
reduce_prompt: prompts/reduce-step.md
include: [prompts/style-guide.md]
---
Write the system prompt for this agent here.
Files listed in "include" are appended to this prompt.
'''

HARNESS_JSON = r'''{
  "input_dir": "input",
  "output_dir": "output",
  "work_dir": "work",
  "log_dir": "logs",
  "report_dir": "reports",
  "default_agent": "tvet-policy-summarizer",
  "default_reviewer": "tvet-summary-reviewer",
  "backends": {
    "ollama": {
      "host": "http://127.0.0.1:11434",
      "num_ctx": 8192,
      "timeout": 900,
      "keep_alive": "10m"
    },
    "openai_compatible": {
      "base_url": "http://127.0.0.1:11434/v1",
      "api_key_env": "OPENAI_API_KEY",
      "json_mode": true,
      "timeout": 300,
      "extra_headers": {}
    },
    "mock": {}
  }
}
'''

STYLE_RULES_JSON = r'''{
  "min_words": 40,
  "banned_terms": [
    "groundbreaking", "ground-breaking", "landmark", "ambitious", "impressive", "excellent",
    "outstanding", "remarkable", "commendable", "exemplary", "world-class", "cutting-edge",
    "state-of-the-art", "revolutionary", "game-changing", "amazing", "unfortunately",
    "fortunately", "obviously", "undoubtedly", "in my opinion", "we recommend",
    "it is recommended", "it is important to note"
  ],
  "discouraged_terms": [
    "comprehensive", "robust", "crucial", "vital", "significant", "successfully", "effectively",
    "clearly", "very", "highly", "strongly", "holistic", "transformative", "great", "best practice"
  ],
  "first_person_regex": "(?<![A-Za-z])(I(?=\\s+[a-z])|me|my|we|We|us|our|Our|ours|you|You|your|Your)(?![A-Za-z])"
}
'''

HARNESS_INIT_PY = r'''# TVET policy summariser harness
__version__ = "1.0.0"
'''

HARNESS_MAIN_PY = r'''from harness.cli import main

raise SystemExit(main())
'''

HARNESS_CONFIG_PY = r'''# Configuration loading: config/harness.json, .env file and environment variables.
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "input_dir": "input",
    "output_dir": "output",
    "work_dir": "work",
    "log_dir": "logs",
    "report_dir": "reports",
    "default_agent": "tvet-policy-summarizer",
    "default_reviewer": "tvet-summary-reviewer",
    "backends": {
        "ollama": {"host": "http://127.0.0.1:11434", "num_ctx": 8192, "timeout": 900, "keep_alive": "10m"},
        "openai_compatible": {"base_url": "http://127.0.0.1:11434/v1", "api_key_env": "OPENAI_API_KEY",
                              "json_mode": True, "timeout": 300, "extra_headers": {}},
        "mock": {},
    },
}


def _merge(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_dotenv(path=None):
    # Minimal .env reader: KEY=VALUE lines; existing environment variables win.
    env_path = Path(path) if path else ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def normalise_ollama_host(host):
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    host = host.replace("0.0.0.0", "127.0.0.1")
    scheme, rest = host.split("://", 1)
    if ":" not in rest.split("/")[0]:
        rest = rest.split("/")[0] + ":11434"
    return scheme + "://" + rest


def load_config(path=None):
    load_dotenv()
    cfg = json.loads(json.dumps(DEFAULTS))
    cfg_path = Path(path) if path else ROOT / "config" / "harness.json"
    if cfg_path.exists():
        with cfg_path.open(encoding="utf-8-sig") as fh:
            _merge(cfg, json.load(fh))
    if os.environ.get("OLLAMA_HOST"):
        cfg["backends"]["ollama"]["host"] = normalise_ollama_host(os.environ["OLLAMA_HOST"])
    return cfg


def resolve_dir(cfg, key):
    path = Path(cfg[key])
    if not path.is_absolute():
        path = ROOT / path
    return path
'''

HARNESS_AGENTS_PY = r'''# Agent definitions: agents/<name>.agent.md = front matter (settings) + body (system prompt).
import re
from dataclasses import dataclass, field
from pathlib import Path

from harness.config import ROOT

AGENT_DIR = ROOT / "agents"


@dataclass
class Agent:
    name: str
    description: str
    system_prompt: str
    settings: dict = field(default_factory=dict)
    path: Path = None

    def get(self, key, default=None):
        value = self.settings.get(key, default)
        return default if value is None or value == "" else value


def _coerce(raw):
    value = raw.strip()
    if " #" in value and not value.startswith(("'", '"')):
        value = value.split(" #", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        return [_coerce(item) for item in value[1:-1].split(",") if item.strip()]
    lowered = value.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    return value


def parse_front_matter(text):
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)(.*)$", text, re.S)
    if not match:
        return {}, text
    meta = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        meta[key.strip()] = _coerce(value)
    return meta, match.group(2)


def agent_path(name_or_path):
    candidate = Path(name_or_path)
    if candidate.suffix == ".md" and candidate.exists():
        return candidate
    candidate = AGENT_DIR / (str(name_or_path) + ".agent.md")
    if candidate.exists():
        return candidate
    raise FileNotFoundError("Agent '%s' not found in %s" % (name_or_path, AGENT_DIR))


def load_agent(name_or_path):
    path = agent_path(name_or_path)
    meta, body = parse_front_matter(path.read_text(encoding="utf-8-sig"))
    includes = meta.get("include", [])
    if isinstance(includes, str):
        includes = [includes]
    parts = [body.strip()]
    for rel in includes:
        inc_path = ROOT / rel
        if not inc_path.exists():
            raise FileNotFoundError("Agent '%s' includes missing file %s" % (path.name, rel))
        parts.append(inc_path.read_text(encoding="utf-8-sig").strip())
    name = meta.get("name") or path.name.replace(".agent.md", "")
    return Agent(name=name, description=meta.get("description", ""),
                 system_prompt="\n\n".join(p for p in parts if p), settings=meta, path=path)


def list_agents():
    agents = []
    for path in sorted(AGENT_DIR.glob("*.agent.md")):
        if path.name.startswith("_"):
            continue
        agents.append(load_agent(path))
    return agents


def read_prompt(agent, key, default_rel):
    rel = agent.get(key, default_rel)
    path = ROOT / rel
    if not path.exists():
        raise FileNotFoundError("Prompt file not found: %s" % rel)
    return path.read_text(encoding="utf-8-sig")


def fill(template, **values):
    # Replace {{KEY}} placeholders; TEXT is replaced last so document text is never re-processed.
    text_value = values.pop("TEXT", None)
    for key, value in values.items():
        template = template.replace("{{%s}}" % key, str(value))
    if text_value is not None:
        template = template.replace("{{TEXT}}", str(text_value))
    return template
'''

HARNESS_PDF_PY = r'''# PDF text extraction and chunking.
import re


class PdfExtractionError(Exception):
    pass


def _chars(pages):
    return sum(len(p.strip()) for p in pages)


def extract_pages(pdf_path):
    pages, error = [], None
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PdfExtractionError("pypdf is not installed. Run: pip install -r requirements.txt") from exc
    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise PdfExtractionError("PDF is password protected: %s" % pdf_path) from exc
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
    except PdfExtractionError:
        raise
    except Exception as exc:
        error = exc
    if _chars(pages) < 200:
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf:
                alternative = [(page.extract_text() or "") for page in pdf.pages]
            if _chars(alternative) > _chars(pages):
                pages, error = alternative, None
        except Exception:
            pass
    if not pages and error is not None:
        raise PdfExtractionError("Could not read %s: %s" % (pdf_path, error))
    return pages


def join_pages(pages):
    return "\n\n".join("[Page %d]\n%s" % (i, text.strip()) for i, text in enumerate(pages, 1) if text.strip())


def clean_text(text):
    text = text.replace("\u00ad", "").replace("\x00", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text, size=6000, overlap=300):
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        while len(para) > size:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:size])
            para = para[size - overlap:]
        if len(current) + len(para) + 2 > size and current:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            current = (current + "\n\n" + para) if current else para
    if current.strip():
        chunks.append(current)
    return chunks


def select_chunks(chunks, max_chunks):
    # Keep the opening chunks (title, issuer, objectives) and spread the rest evenly.
    if max_chunks <= 0 or len(chunks) <= max_chunks:
        return chunks
    head = chunks[:2]
    rest = chunks[2:]
    slots = max_chunks - len(head)
    step = len(rest) / float(slots)
    picked = [rest[int(i * step)] for i in range(slots)]
    return head + picked
'''

HARNESS_BACKENDS_PY = r'''# LLM backends: Ollama (local), OpenAI-compatible (local or online), Mock (testing without a model).
import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse


class BackendError(Exception):
    pass


def _opener_for(url):
    host = (urlparse(url).hostname or "").lower()
    if host in ("localhost", "127.0.0.1", "::1"):
        return urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener()


def _request(url, payload=None, headers=None, timeout=300):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req_headers = {"Content-Type": "application/json"}
    req_headers.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST" if data else "GET")
    try:
        with _opener_for(url).open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise BackendError("HTTP %s from %s: %s" % (exc.code, url, body[:500])) from exc
    except urllib.error.URLError as exc:
        raise BackendError("Cannot reach %s (%s)" % (url, exc.reason)) from exc
    except (TimeoutError, OSError) as exc:
        raise BackendError("Request to %s failed: %s" % (url, exc)) from exc


class OllamaBackend:
    name = "ollama"

    def __init__(self, cfg, model):
        if not model:
            raise ValueError("No model configured for the Ollama backend")
        self.model = model
        self.host = cfg.get("host", "http://127.0.0.1:11434").rstrip("/")
        self.num_ctx = int(cfg.get("num_ctx", 8192))
        self.timeout = int(cfg.get("timeout", 900))
        self.keep_alive = cfg.get("keep_alive", "10m")

    def check(self):
        tags = _request(self.host + "/api/tags", timeout=10)
        names = [m.get("name", "") for m in tags.get("models", [])]
        wanted = self.model if ":" in self.model else self.model + ":latest"
        return wanted in names or self.model in names, names

    def chat(self, messages, json_mode=False, temperature=0.1):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"temperature": temperature, "num_ctx": self.num_ctx},
        }
        if json_mode:
            payload["format"] = "json"
        data = _request(self.host + "/api/chat", payload, timeout=self.timeout)
        return (data.get("message") or {}).get("content", "")


class OpenAICompatibleBackend:
    name = "openai_compatible"

    def __init__(self, cfg, model):
        if not model:
            raise ValueError("No model configured for the OpenAI-compatible backend")
        self.model = model
        self.base_url = (os.environ.get("TVET_OPENAI_BASE_URL") or cfg.get("base_url", "")).rstrip("/")
        self.api_key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"), "")
        self.json_mode = bool(cfg.get("json_mode", True))
        self.timeout = int(cfg.get("timeout", 300))
        self.headers = dict(cfg.get("extra_headers") or {})
        if self.api_key:
            self.headers.setdefault("Authorization", "Bearer " + self.api_key)

    def check(self):
        try:
            data = _request(self.base_url + "/models", headers=self.headers, timeout=15)
            names = [m.get("id", "") for m in data.get("data", [])]
            return (self.model in names) if names else True, names
        except BackendError as exc:
            if "HTTP 404" in str(exc):
                return True, []
            raise

    def chat(self, messages, json_mode=False, temperature=0.1):
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_mode and self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = _request(self.base_url + "/chat/completions", payload, headers=self.headers, timeout=self.timeout)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError("Unexpected response format: %s" % str(data)[:300]) from exc


class MockBackend:
    # Deterministic fake model for testing the pipeline without Ollama or network access.
    name = "mock"

    def __init__(self, cfg, model):
        self.model = model or "mock"

    def check(self):
        return True, [self.model]

    def chat(self, messages, json_mode=False, temperature=0.1):
        source, is_review = "", False
        for message in messages:
            if message["role"] != "user":
                continue
            match = re.search(r"<(document|summary)>\s*(.*?)\s*</\1>", message["content"], re.S)
            if match:
                source, is_review = match.group(2), match.group(1) == "summary"
                break
        words = re.sub(r"\[Page \d+\]", " ", source).split()
        if not json_mode:
            return "- " + " ".join(words[:40])
        if is_review:
            return json.dumps({"neutral": True, "within_limit": len(words) <= 80, "issues": [],
                               "suggested_revision": ""})
        excerpt = " ".join(w for w in words[:40] if w.isalpha())
        summary = "This mock summary tests the pipeline without a language model. The document text begins: %s." % excerpt
        return json.dumps({
            "title": "Mock record", "issuing_body": "Not stated", "country_or_region": "Not stated",
            "year": "Not stated", "document_type": "Not stated", "summary": summary,
            "keywords": ["mock", "pipeline test", "tvet"],
        })


def get_backend(cfg, agent, backend_override=None, model_override=None):
    name = backend_override or os.environ.get("TVET_BACKEND") or agent.get("backend", "ollama")
    model = model_override or os.environ.get("TVET_MODEL") or agent.get("model")
    backends = cfg.get("backends", {})
    if name == "ollama":
        return OllamaBackend(backends.get("ollama", {}), model)
    if name in ("openai", "openai_compatible"):
        return OpenAICompatibleBackend(backends.get("openai_compatible", {}), model)
    if name == "mock":
        return MockBackend(backends.get("mock", {}), model)
    raise ValueError("Unknown backend '%s' (use ollama, openai_compatible or mock)" % name)
'''

HARNESS_VALIDATE_PY = r'''# Validation of model output and of summary Markdown files; deterministic rendering.
import datetime
import json
import re

from harness.config import ROOT

META_FIELDS = [
    ("title", "Title"),
    ("issuing_body", "Issuing body"),
    ("country_or_region", "Country / region"),
    ("year", "Year"),
    ("document_type", "Document type"),
]
TABLE_FIELDS = ["Source file", "Issuing body", "Country / region", "Year", "Document type"]


def load_style_rules():
    path = ROOT / "config" / "style_rules.json"
    if path.exists():
        with path.open(encoding="utf-8-sig") as fh:
            return json.load(fh)
    return {"min_words": 40, "banned_terms": [], "discouraged_terms": []}


def word_count(text):
    return len((text or "").split())


def strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)


def extract_json(raw):
    text = strip_think(raw).strip()
    if not text:
        raise ValueError("the model returned an empty response")
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError("the response was not a valid JSON object")


def _term_found(term, text):
    pattern = r"(?<![\w-])" + re.escape(term.lower()) + r"(?![\w-])"
    return re.search(pattern, text.lower()) is not None


def check_summary_text(summary, max_words, rules):
    errors, warnings = [], []
    count = word_count(summary)
    if count > max_words:
        errors.append("summary has %d words; the maximum is %d" % (count, max_words))
    elif count < int(rules.get("min_words", 40)):
        warnings.append("summary is short (%d words)" % count)
    if re.search(r"^\s*([-*\u2022]|\d+[.)])\s", summary, re.M):
        errors.append("summary must not contain bullet points or numbered lists")
    if len([p for p in re.split(r"\n\s*\n", summary.strip()) if p.strip()]) > 1:
        errors.append("summary must be a single paragraph")
    if "!" in summary:
        errors.append("summary must not contain exclamation marks")
    for term in rules.get("banned_terms", []):
        if _term_found(term, summary):
            errors.append("remove the non-neutral expression '%s'" % term)
    regex = rules.get("first_person_regex")
    if regex:
        hit = re.search(regex, summary)
        if hit:
            errors.append("use third person only (found '%s')" % hit.group(0))
    for term in rules.get("discouraged_terms", []):
        if _term_found(term, summary):
            warnings.append("consider replacing '%s' with a more neutral wording" % term)
    return errors, warnings


def _flat(value):
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value)
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalise_payload(obj, max_words, rules):
    if not isinstance(obj, dict):
        return None, ["the JSON must be an object with the requested keys"], []
    data = {}
    for key, _label in META_FIELDS:
        value = _flat(obj.get(key))
        data[key] = value if value and value.lower() not in ("none", "null", "n/a", "unknown") else "Not stated"
    raw_summary = obj.get("summary", "")
    if isinstance(raw_summary, list):
        raw_summary = " ".join(str(s) for s in raw_summary)
    raw_summary = str(raw_summary or "").strip()
    errors, warnings = [], []
    if not raw_summary:
        errors.append("the 'summary' field is empty")
    else:
        errors, warnings = check_summary_text(raw_summary, max_words, rules)
    data["summary"] = re.sub(r"\s+", " ", raw_summary)
    keywords = obj.get("keywords", [])
    if isinstance(keywords, str):
        keywords = re.split(r"[;,]", keywords)
    cleaned = []
    for keyword in keywords or []:
        keyword = _flat(keyword).strip(" .")
        if keyword and keyword.lower() not in [k.lower() for k in cleaned]:
            cleaned.append(keyword)
    data["keywords"] = cleaned[:5]
    if len(cleaned) < 3:
        warnings.append("fewer than 3 keywords")
    return data, errors, warnings


def trim_to_limit(summary, max_words):
    # Returns (text, mode) with mode in None | "sentence" | "hard".
    if word_count(summary) <= max_words:
        return summary, None
    sentences = re.split(r"(?<=[.!?])\s+", summary.strip())
    while len(sentences) > 1 and word_count(" ".join(sentences)) > max_words:
        sentences.pop()
    text = " ".join(sentences)
    if word_count(text) <= max_words:
        return text, "sentence"
    text = " ".join(text.split()[:max_words]).rstrip(",;:-")
    if not text.endswith((".", "?")):
        text += "."
    return text, "hard"


def _cell(value):
    value = _flat(value).replace("|", "\\|")
    return value or "Not stated"


def render_markdown(data, source_name, agent_name, model, max_words):
    title = data.get("title") or "Not stated"
    if title == "Not stated":
        title = source_name.rsplit(".", 1)[0]
    keywords = "; ".join(data.get("keywords") or []) or "Not stated"
    lines = [
        "# %s" % _flat(title),
        "",
        "| Field | Value |",
        "|---|---|",
        "| Source file | %s |" % _cell(source_name),
        "| Issuing body | %s |" % _cell(data.get("issuing_body")),
        "| Country / region | %s |" % _cell(data.get("country_or_region")),
        "| Year | %s |" % _cell(data.get("year")),
        "| Document type | %s |" % _cell(data.get("document_type")),
        "",
        "## Summary",
        "",
        data.get("summary", "").strip(),
        "",
        "## Keywords",
        "",
        keywords,
        "",
        "---",
        "",
        "*Word count: %d/%d | Generated: %s | Agent: %s | Model: %s*" % (
            word_count(data.get("summary", "")), max_words, datetime.date.today().isoformat(), agent_name, model),
        "",
    ]
    return "\n".join(lines)


def parse_summary_markdown(text):
    result = {"title": None, "fields": {}, "summary": None, "keywords": None}
    title = re.search(r"^#\s+(.+)$", text, re.M)
    if title:
        result["title"] = title.group(1).strip()
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if len(cells) == 2 and cells[0] not in ("Field", "") and not set(cells[0]) <= set("-: "):
            result["fields"][cells[0]] = cells[1].replace("\\|", "|")
    for block in re.split(r"^##\s+", text, flags=re.M)[1:]:
        heading, _, body = block.partition("\n")
        body = re.split(r"^\s*---\s*$", body, maxsplit=1, flags=re.M)[0].strip()
        if heading.strip().lower() == "summary":
            result["summary"] = body
        elif heading.strip().lower() == "keywords":
            result["keywords"] = [k.strip() for k in body.split(";") if k.strip()]
    return result


def validate_markdown_file(path, max_words, rules):
    text = path.read_text(encoding="utf-8-sig")
    parsed = parse_summary_markdown(text)
    errors, warnings = [], []
    if not parsed["title"]:
        errors.append("missing level-1 title line ('# Title')")
    for field_name in TABLE_FIELDS:
        if not parsed["fields"].get(field_name):
            errors.append("missing table field '%s'" % field_name)
    if parsed["summary"] is None:
        errors.append("missing '## Summary' section")
        count = 0
    else:
        count = word_count(parsed["summary"])
        e, w = check_summary_text(parsed["summary"], max_words, rules)
        errors += e
        warnings += w
    if parsed["keywords"] is None:
        errors.append("missing '## Keywords' section")
    elif not 3 <= len(parsed["keywords"]) <= 5:
        warnings.append("expected 3 to 5 keywords, found %d" % len(parsed["keywords"]))
    return errors, warnings, count, parsed
'''

HARNESS_PIPELINE_PY = r'''# Agent pipelines: policy_summary (map-reduce + validation loop) and summary_review.
from harness.agents import fill, read_prompt
from harness.pdf_text import chunk_text, clean_text, extract_pages, join_pages, select_chunks
from harness.validate import (check_summary_text, extract_json, normalise_payload, strip_think,
                              trim_to_limit, word_count)


class SkipFile(Exception):
    pass


def _feedback(errors, data, max_words):
    lines = ["Your previous answer cannot be accepted:"]
    lines += ["- " + e for e in errors]
    if data and data.get("summary"):
        lines.append("The summary currently has %d words; the limit is %d words." % (word_count(data["summary"]), max_words))
    lines.append("Return the corrected JSON object only, with the same keys. Keep all facts from the document; "
                 "shorten by removing detail, not by adding abbreviations.")
    return "\n".join(lines)


class Summarizer:
    def __init__(self, agent, backend, rules, verbose=True):
        self.agent = agent
        self.backend = backend
        self.rules = rules
        self.verbose = verbose
        self.max_words = int(agent.get("max_words", 80))
        self.max_retries = int(agent.get("max_retries", 3))
        self.temperature = float(agent.get("temperature", 0.1))
        self.chunk_chars = int(agent.get("chunk_chars", 6000))
        self.max_chunks = int(agent.get("max_chunks", 20))
        self.map_template = read_prompt(agent, "map_prompt", "prompts/map-step.md")
        self.reduce_template = read_prompt(agent, "reduce_prompt", "prompts/reduce-step.md")

    def _say(self, message):
        if self.verbose:
            print(message, flush=True)

    def _system(self):
        return {"role": "system", "content": self.agent.system_prompt}

    def _material(self, text):
        limit = int(self.chunk_chars * 1.5)
        if len(text) <= limit:
            return text, "full document text", 0
        current, passes, calls = text, 0, 0
        while len(current) > limit and passes < 3:
            passes += 1
            chunks = select_chunks(chunk_text(current, self.chunk_chars), self.max_chunks)
            notes = []
            for index, chunk in enumerate(chunks, 1):
                self._say("    reading part %d/%d (pass %d)" % (index, len(chunks), passes))
                prompt = fill(self.map_template, PART=index, TOTAL=len(chunks), TEXT=chunk)
                answer = strip_think(self.backend.chat([self._system(), {"role": "user", "content": prompt}],
                                                       json_mode=False, temperature=self.temperature)).strip()
                calls += 1
                if answer and "no relevant content" not in answer.lower()[:60]:
                    notes.append("[Part %d]\n%s" % (index, answer))
            condensed = "\n\n".join(notes) or current[:limit]
            if len(condensed) >= len(current):
                current = condensed[:limit]
                break
            current = condensed
        material = "FIRST PAGE OF THE DOCUMENT:\n%s\n\nNOTES FROM THE WHOLE DOCUMENT:\n%s" % (text[:1500], current[:limit])
        return material, "first page plus factual notes extracted from the whole document", calls

    def summarize(self, pdf_path):
        pages = extract_pages(pdf_path)
        text = clean_text(join_pages(pages))
        min_chars = int(self.agent.get("min_text_chars", 300))
        if len(text) < min_chars:
            raise SkipFile("only %d characters of text found - probably a scanned PDF; run OCR first" % len(text))
        self._say("    %d pages, %d characters" % (len(pages), len(text)))
        material, material_type, map_calls = self._material(text)
        prompt = fill(self.reduce_template, MAX_WORDS=self.max_words, FILENAME=pdf_path.name,
                      MATERIAL_TYPE=material_type, TEXT=material)
        messages = [self._system(), {"role": "user", "content": prompt}]
        best = None
        info = {"pages": len(pages), "chars": len(text), "material": material_type, "map_calls": map_calls}
        for attempt in range(1, self.max_retries + 2):
            raw = self.backend.chat(messages, json_mode=True, temperature=self.temperature)
            try:
                data, errors, warnings = normalise_payload(extract_json(raw), self.max_words, self.rules)
            except ValueError as exc:
                data, errors, warnings = None, [str(exc)], []
            if data is not None and not errors:
                info.update({"data": data, "status": "ok", "attempts": attempt, "warnings": warnings, "errors": []})
                return info
            if data is not None:
                best = (data, errors, warnings)
            self._say("    attempt %d rejected: %s" % (attempt, "; ".join(errors)))
            messages.append({"role": "assistant", "content": strip_think(raw)[:4000]})
            messages.append({"role": "user", "content": _feedback(errors, data, self.max_words)})
        if best is None:
            raise ValueError("no valid JSON after %d attempts" % (self.max_retries + 1))
        data, errors, warnings = best
        data["summary"], trim_mode = trim_to_limit(data["summary"], self.max_words)
        remaining, warnings2 = check_summary_text(data["summary"], self.max_words, self.rules)
        status = "needs_review" if remaining or trim_mode == "hard" else ("auto_trimmed" if trim_mode else "needs_review")
        info.update({"data": data, "status": status, "attempts": self.max_retries + 1,
                     "warnings": warnings + warnings2, "errors": remaining})
        return info


class Reviewer:
    def __init__(self, agent, backend, rules):
        self.agent = agent
        self.backend = backend
        self.rules = rules
        self.max_words = int(agent.get("max_words", 80))
        self.template = read_prompt(agent, "review_prompt", "prompts/review-step.md")

    def review(self, summary):
        prompt = fill(self.template, MAX_WORDS=self.max_words, WORD_COUNT=word_count(summary), TEXT=summary)
        raw = self.backend.chat([{"role": "system", "content": self.agent.system_prompt},
                                 {"role": "user", "content": prompt}],
                                json_mode=True, temperature=float(self.agent.get("temperature", 0.0)))
        obj = extract_json(raw)
        rule_errors, rule_warnings = check_summary_text(summary, self.max_words, self.rules)
        issues = obj.get("issues") or []
        if isinstance(issues, str):
            issues = [issues]
        return {
            "model_neutral": bool(obj.get("neutral", False)),
            "model_issues": [str(i) for i in issues],
            "suggested_revision": str(obj.get("suggested_revision") or "").strip(),
            "rule_errors": rule_errors,
            "rule_warnings": rule_warnings,
        }
'''

HARNESS_CLI_PY = r'''# Command line interface: python -m harness <command>
import argparse
import datetime
import json
import platform
import sys
import time
from pathlib import Path

from harness import __version__
from harness.agents import AGENT_DIR, list_agents, load_agent
from harness.backends import BackendError, get_backend
from harness.config import ROOT, load_config, resolve_dir
from harness.pdf_text import PdfExtractionError, clean_text, extract_pages, join_pages
from harness.pipeline import Reviewer, SkipFile, Summarizer
from harness.validate import load_style_rules, render_markdown, validate_markdown_file


def _safe_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except Exception:
            pass


def _pdfs(folder):
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")


def _summary_files(folder):
    if not folder.exists():
        return []
    return sorted(p for p in folder.glob("*.md") if not p.name.startswith(("_", "README")))


def _log(cfg, record):
    log_dir = resolve_dir(cfg, "log_dir")
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / ("runs_%s.jsonl" % datetime.date.today().strftime("%Y%m"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _backend_ready(backend):
    try:
        ok, names = backend.check()
    except BackendError as exc:
        print("[error] %s" % exc)
        if backend.name == "ollama":
            print("        Start Ollama (Ollama app or 'ollama serve') and try again.")
        return False
    if not ok:
        print("[error] Model '%s' is not available on backend '%s'." % (backend.model, backend.name))
        if names:
            print("        Available: %s" % ", ".join(names[:15]))
        if backend.name == "ollama":
            print("        Run: ollama pull %s" % backend.model)
        return False
    return True


def cmd_run(args):
    cfg = load_config()
    agent = load_agent(args.agent or cfg["default_agent"])
    if agent.get("task", "policy_summary") != "policy_summary":
        print("[error] Agent '%s' has task '%s'; 'run' needs a policy_summary agent." % (agent.name, agent.get("task")))
        return 2
    backend = get_backend(cfg, agent, args.backend, args.model)
    input_dir, output_dir = resolve_dir(cfg, "input_dir"), resolve_dir(cfg, "output_dir")
    files = [Path(f) for f in args.files] if args.files else _pdfs(input_dir)
    if not files:
        print("No PDF files found in %s" % input_dir)
        return 1
    print("Agent: %s | backend: %s | model: %s | files: %d" % (agent.name, backend.name, backend.model, len(files)))
    if not _backend_ready(backend):
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    summarizer = Summarizer(agent, backend, load_style_rules(), verbose=not args.quiet)
    counts = {"ok": 0, "auto_trimmed": 0, "needs_review": 0, "skipped": 0, "failed": 0}
    for index, pdf in enumerate(files, 1):
        out = output_dir / (pdf.stem + agent.get("output_suffix", ".summary.md"))
        if out.exists() and not args.overwrite:
            print("[%d/%d] %s -> exists, skipped (use --overwrite)" % (index, len(files), pdf.name))
            counts["skipped"] += 1
            continue
        print("[%d/%d] %s" % (index, len(files), pdf.name), flush=True)
        started = time.time()
        record = {"time": datetime.datetime.now().isoformat(timespec="seconds"), "file": pdf.name,
                  "agent": agent.name, "backend": backend.name, "model": backend.model}
        try:
            if not pdf.exists():
                raise PdfExtractionError("file not found: %s" % pdf)
            result = summarizer.summarize(pdf)
            markdown = render_markdown(result["data"], pdf.name, agent.name, backend.model, summarizer.max_words)
            out.write_text(markdown, encoding="utf-8")
            counts[result["status"]] += 1
            record.update({k: result[k] for k in ("status", "attempts", "warnings", "errors", "pages", "chars", "material")})
            record["output"] = str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)
            print("    -> %s [%s]" % (out.name, result["status"]))
            for warning in result["warnings"]:
                print("       warning: %s" % warning)
        except SkipFile as exc:
            counts["skipped"] += 1
            record.update({"status": "skipped", "reason": str(exc)})
            print("    -> skipped: %s" % exc)
        except (BackendError, PdfExtractionError, ValueError) as exc:
            counts["failed"] += 1
            record.update({"status": "failed", "reason": str(exc)})
            print("    -> failed: %s" % exc)
        record["seconds"] = round(time.time() - started, 1)
        _log(cfg, record)
    print("\nDone: " + ", ".join("%s=%d" % kv for kv in counts.items()))
    if counts["needs_review"]:
        print("Files marked needs_review should be checked manually or with: python -m harness review")
    return 0 if counts["failed"] == 0 else 1


def cmd_extract(args):
    cfg = load_config()
    input_dir = resolve_dir(cfg, "input_dir")
    target = resolve_dir(cfg, "work_dir") / "extracted"
    target.mkdir(parents=True, exist_ok=True)
    files = [Path(f) for f in args.files] if args.files else _pdfs(input_dir)
    if not files:
        print("No PDF files found in %s" % input_dir)
        return 1
    status = 0
    for pdf in files:
        try:
            pages = extract_pages(pdf)
            text = clean_text(join_pages(pages))
            out = target / (pdf.stem + ".txt")
            out.write_text("SOURCE FILE: %s\nPAGES: %d\n\n%s\n" % (pdf.name, len(pages), text), encoding="utf-8")
            note = "  WARNING: little or no text - scanned PDF? run OCR first" if len(text) < 300 else ""
            print("%s -> work/extracted/%s (%d pages, %d chars)%s" % (pdf.name, out.name, len(pages), len(text), note))
        except PdfExtractionError as exc:
            status = 1
            print("%s -> failed: %s" % (pdf.name, exc))
    return status


def cmd_validate(args):
    cfg = load_config()
    agent = load_agent(args.agent or cfg["default_agent"])
    max_words = int(agent.get("max_words", 80))
    rules = load_style_rules()
    files = [Path(f) for f in args.files] if args.files else _summary_files(resolve_dir(cfg, "output_dir"))
    if not files:
        print("No summary files to validate.")
        return 1
    failed = 0
    for path in files:
        errors, warnings, count, _parsed = validate_markdown_file(path, max_words, rules)
        label = "FAIL" if errors else "PASS"
        print("[%s] %s (%d/%d words)" % (label, path.name, count, max_words))
        for error in errors:
            print("       error: %s" % error)
        for warning in warnings:
            print("       warning: %s" % warning)
        failed += bool(errors)
    print("\n%d of %d files passed." % (len(files) - failed, len(files)))
    return 1 if failed else 0


def cmd_review(args):
    cfg = load_config()
    agent = load_agent(args.agent or cfg["default_reviewer"])
    backend = get_backend(cfg, agent, args.backend, args.model)
    files = [Path(f) for f in args.files] if args.files else _summary_files(resolve_dir(cfg, "output_dir"))
    if not files:
        print("No summary files to review.")
        return 1
    if not _backend_ready(backend):
        return 2
    rules = load_style_rules()
    reviewer = Reviewer(agent, backend, rules)
    report_dir = resolve_dir(cfg, "report_dir")
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    lines = ["# Review report %s" % stamp, "", "Agent: %s | Model: %s" % (agent.name, backend.model), ""]
    for path in files:
        _e, _w, count, parsed = validate_markdown_file(path, reviewer.max_words, rules)
        if not parsed["summary"]:
            print("%s -> no summary section, skipped" % path.name)
            continue
        print("Reviewing %s ..." % path.name, flush=True)
        try:
            result = reviewer.review(parsed["summary"])
        except (BackendError, ValueError) as exc:
            print("    failed: %s" % exc)
            lines += ["## %s" % path.name, "", "Review failed: %s" % exc, ""]
            continue
        verdict = "OK" if result["model_neutral"] and not result["rule_errors"] else "CHECK"
        print("    %s" % verdict)
        lines += ["## %s - %s" % (path.name, verdict), "", "- Word count: %d" % count,
                  "- Model judges neutral: %s" % result["model_neutral"]]
        lines += ["- Rule error: %s" % e for e in result["rule_errors"]]
        lines += ["- Rule warning: %s" % w for w in result["rule_warnings"]]
        lines += ["- Model issue: %s" % i for i in result["model_issues"]]
        if result["suggested_revision"]:
            lines += ["", "Suggested revision (not applied):", "", "> " + result["suggested_revision"]]
        lines.append("")
    report = report_dir / ("review_%s.md" % stamp)
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\nReport: %s" % report)
    return 0


def cmd_check(args):
    cfg = load_config()
    problems = 0
    print("Harness %s | Python %s | %s" % (__version__, platform.python_version(), platform.platform()))
    try:
        import pypdf
        print("[ok]   pypdf %s" % pypdf.__version__)
    except ImportError:
        problems += 1
        print("[fail] pypdf missing - pip install -r requirements.txt")
    try:
        import pdfplumber  # noqa: F401
        print("[ok]   pdfplumber (optional fallback)")
    except ImportError:
        print("[info] pdfplumber not installed (optional)")
    agents = list_agents()
    print("[ok]   %d agent(s): %s" % (len(agents), ", ".join(a.name for a in agents)))
    for key in ("input_dir", "output_dir"):
        folder = resolve_dir(cfg, key)
        print("[%s] %s: %s" % ("ok  " if folder.exists() else "fail", key, folder))
        problems += not folder.exists()
    print("[info] PDFs waiting in input: %d" % len(_pdfs(resolve_dir(cfg, "input_dir"))))
    seen = set()
    for agent in agents:
        backend = get_backend(cfg, agent, args.backend, args.model)
        key = (backend.name, backend.model)
        if key in seen:
            continue
        seen.add(key)
        try:
            ok, names = backend.check()
            print("[%s] backend %s, model %s%s" % ("ok  " if ok else "fail", backend.name, backend.model,
                                                  "" if ok else " not found (ollama pull %s)" % backend.model))
            problems += not ok
        except BackendError as exc:
            problems += 1
            print("[fail] backend %s: %s" % (backend.name, exc))
    print("\n%s" % ("All checks passed." if not problems else "%d problem(s) found." % problems))
    return 1 if problems else 0


def cmd_agents(args):
    for agent in list_agents():
        print("%-28s task=%-15s backend=%-18s model=%s" % (agent.name, agent.get("task", "policy_summary"),
                                                           agent.get("backend", "ollama"), agent.get("model")))
        if agent.description:
            print("    %s" % agent.description)
    return 0


def cmd_new_agent(args):
    template = AGENT_DIR / "_template.agent.md"
    target = AGENT_DIR / ("%s.agent.md" % args.name)
    if target.exists():
        print("[error] %s already exists" % target)
        return 1
    cfg = load_config()
    default_model = load_agent(cfg["default_agent"]).get("model", "llama3.2:3b")
    text = template.read_text(encoding="utf-8").replace("{{AGENT_NAME}}", args.name).replace("{{DEFAULT_MODEL}}", default_model)
    target.write_text(text, encoding="utf-8")
    print("Created %s - edit the front matter and system prompt." % target)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="python -m harness", description="TVET policy summariser agent harness")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    def common(p, files_help):
        p.add_argument("files", nargs="*", help=files_help)
        p.add_argument("--agent", help="agent name or path to *.agent.md")
        p.add_argument("--backend", help="override backend: ollama | openai_compatible | mock")
        p.add_argument("--model", help="override model name")

    p = sub.add_parser("run", help="summarise PDFs from input/ into output/")
    common(p, "specific PDF files (default: all PDFs in input/)")
    p.add_argument("--overwrite", action="store_true", help="replace existing summaries")
    p.add_argument("--quiet", action="store_true", help="less progress output")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("extract", help="extract PDF text to work/extracted/ (for Copilot or Continue)")
    p.add_argument("files", nargs="*")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("validate", help="check summary files against the standard")
    common(p, "summary files (default: all in output/)")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("review", help="second-pass neutrality review with the reviewer agent")
    common(p, "summary files (default: all in output/)")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("check", help="health check of packages, folders, backend and models")
    p.add_argument("--backend")
    p.add_argument("--model")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("agents", help="list agent definitions")
    p.set_defaults(func=cmd_agents)

    p = sub.add_parser("new-agent", help="create a new agent file from the template")
    p.add_argument("name")
    p.set_defaults(func=cmd_new_agent)
    return parser


def main(argv=None):
    _safe_console()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError) as exc:
        print("[error] %s" % exc)
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
'''

COPILOT_INSTRUCTIONS_MD = r'''# Copilot instructions: TVET policy summaries

This workspace produces standardised summaries of Technical and Vocational Education and Training
(TVET) policy documents. Apply these instructions to every chat, edit and agent request here.

## Workspace layout
- `input/` - source PDF files. Read-only: never edit, rename, move or delete them.
- `work/extracted/` - plain text of each PDF, created by `python -m harness extract`.
- `output/` - one summary per PDF, named `<pdf name without .pdf>.summary.md`.
- `prompts/style-guide.md` - the full, authoritative style guide.
- `examples/example-summary.md` - reference output.
- `agents/`, `harness/`, `config/` - offline pipeline with local Ollama models. Do not change unless asked.

## Workflow for summarising documents
1. If `work/extracted/<name>.txt` is missing, run in the terminal:
   `.venv\Scripts\python.exe -m harness extract` (Windows) or `python -m harness extract`.
2. Read the extracted text completely. Base the summary only on that text.
3. Write `output/<name>.summary.md` using the template below. Do not overwrite existing summaries
   unless the user asks for it.
4. Run `.venv\Scripts\python.exe -m harness validate output/<name>.summary.md` and fix every error.

## Summary rules (mandatory)
- The Summary section has at most **80 words**: one paragraph, complete sentences, no bullet points.
- English, British spelling, regardless of the source language.
- Neutral and factual, third person, present tense for what the document does.
- Describe only. No praise, criticism, recommendations, speculation or outside knowledge.
- No evaluative words (for example groundbreaking, ambitious, excellent, crucial, comprehensive, robust).
- Recommended order: document type, issuer, country/region, year and scope; main objectives;
  key measures; target groups, governance, funding or timeframe where stated.
- Metadata that is not in the document is written as `Not stated`.
- 3 to 5 lowercase keywords separated by semicolons.

## Output template

```
# <Official title> [English translation if the title is not in English]

| Field | Value |
|---|---|
| Source file | <file name>.pdf |
| Issuing body | <...> |
| Country / region | <...> |
| Year | <...> |
| Document type | <...> |

## Summary

<one neutral paragraph, maximum 80 words>

## Keywords

<keyword>; <keyword>; <keyword>

---

*Word count: <n>/80 | Generated: <YYYY-MM-DD> | Agent: GitHub Copilot | Model: <model>*
```

## Answers in chat
When asked about a document in chat without writing a file, still keep summaries within 80 words
and in the same neutral style.
'''

COPILOT_PROMPT_MD = r'''---
description: Summarise TVET policy PDFs from input/ into the standard 80-word format
agent: agent
---
Summarise the TVET policy documents in `input/` following `.github/copilot-instructions.md`
and `prompts/style-guide.md`.

Steps:
1. Run `.venv\Scripts\python.exe -m harness extract` in the terminal (use `python -m harness extract`
   on macOS/Linux) unless `work/extracted/` already contains a text file for every PDF.
2. For each text file in `work/extracted/` without a matching `output/<name>.summary.md`
   (or only for ${input:files:all or specific file names}), read the full text.
3. Write `output/<name>.summary.md` exactly in the template from the instructions,
   using `examples/example-summary.md` as the model. Maximum 80 words in the Summary section.
4. Run `.venv\Scripts\python.exe -m harness validate` and correct every reported error.
5. Report a short table: file, word count, validation result.
'''

COPILOT_FILE_INSTRUCTIONS_MD = r'''---
applyTo: "output/**/*.md"
---
Files in `output/` are TVET policy summaries. When creating or editing them:
- Keep the exact template of `examples/example-summary.md` (title, metadata table, Summary, Keywords, footer).
- Summary section: maximum 80 words, one paragraph, English, neutral, third person, no evaluation.
- Use `Not stated` for missing metadata. Never invent facts.
- Update the word count in the footer after every edit.
'''

COPILOT_AGENT_MD = r'''---
description: Summarises TVET policy PDFs into neutral 80-word records and validates them
---
You are the TVET policy summariser for this workspace.

Your job:
- Turn TVET policy documents from `input/` into summaries in `output/`, following
  `.github/copilot-instructions.md` and `prompts/style-guide.md` without exception.
- Work from `work/extracted/*.txt`. If the text files are missing, run
  `.venv\Scripts\python.exe -m harness extract` first.
- After writing summaries, run `.venv\Scripts\python.exe -m harness validate` and fix all errors.

Boundaries:
- Never modify files in `input/`.
- Never add information that is not in the source document.
- Maximum 80 words in each Summary section; neutral, factual, third person, English.
- If a document has no extractable text (scanned PDF), say so and do not write a summary.
'''

CONTINUE_RULE_MD = r'''---
name: TVET policy summary standard
description: Format and neutral style for TVET policy summaries (max. 80 words)
alwaysApply: true
---
When summarising TVET policy documents in this workspace:
- Use the template in `examples/example-summary.md` and the rules in `prompts/style-guide.md`.
- Summary section: maximum 80 words, one paragraph, English, neutral and factual, third person.
- No praise, criticism, recommendations, speculation or outside knowledge.
- Write `Not stated` for missing metadata; 3 to 5 lowercase keywords separated by semicolons.
- Work from `work/extracted/*.txt` (create with `python -m harness extract`); never modify `input/`.
- Save results as `output/<pdf name>.summary.md` and check them with `python -m harness validate`.
'''

CONTINUE_PROMPT_MD = r'''---
name: summarize-tvet-policy
description: Summarise the attached TVET policy text in the standard 80-word format
invokable: true
---
Summarise the attached TVET policy document text (from `work/extracted/`) using the workspace rules.

Output only the Markdown record in this exact structure:
- `# <Official title>`
- metadata table with rows: Source file, Issuing body, Country / region, Year, Document type
- `## Summary` with one neutral paragraph of at most 80 words
- `## Keywords` with 3 to 5 lowercase keywords separated by semicolons
- footer line: `*Word count: <n>/80 | Generated: <date> | Agent: Continue | Model: <model>*`

Use only information from the text. Write `Not stated` for missing metadata.
'''

VSCODE_TASKS_JSON = r'''{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "TVET: Summarise PDFs (offline, Ollama)",
      "type": "shell",
      "command": "python -m harness run",
      "windows": { "command": ".\\.venv\\Scripts\\python.exe -m harness run" },
      "linux": { "command": ".venv/bin/python -m harness run" },
      "osx": { "command": ".venv/bin/python -m harness run" },
      "problemMatcher": [],
      "group": { "kind": "build", "isDefault": true }
    },
    {
      "label": "TVET: Summarise PDFs (overwrite existing)",
      "type": "shell",
      "command": "python -m harness run --overwrite",
      "windows": { "command": ".\\.venv\\Scripts\\python.exe -m harness run --overwrite" },
      "linux": { "command": ".venv/bin/python -m harness run --overwrite" },
      "osx": { "command": ".venv/bin/python -m harness run --overwrite" },
      "problemMatcher": []
    },
    {
      "label": "TVET: Extract PDF text",
      "type": "shell",
      "command": "python -m harness extract",
      "windows": { "command": ".\\.venv\\Scripts\\python.exe -m harness extract" },
      "linux": { "command": ".venv/bin/python -m harness extract" },
      "osx": { "command": ".venv/bin/python -m harness extract" },
      "problemMatcher": []
    },
    {
      "label": "TVET: Validate summaries",
      "type": "shell",
      "command": "python -m harness validate",
      "windows": { "command": ".\\.venv\\Scripts\\python.exe -m harness validate" },
      "linux": { "command": ".venv/bin/python -m harness validate" },
      "osx": { "command": ".venv/bin/python -m harness validate" },
      "problemMatcher": [],
      "group": "test"
    },
    {
      "label": "TVET: Review summaries (reviewer agent)",
      "type": "shell",
      "command": "python -m harness review",
      "windows": { "command": ".\\.venv\\Scripts\\python.exe -m harness review" },
      "linux": { "command": ".venv/bin/python -m harness review" },
      "osx": { "command": ".venv/bin/python -m harness review" },
      "problemMatcher": []
    },
    {
      "label": "TVET: Check setup",
      "type": "shell",
      "command": "python -m harness check",
      "windows": { "command": ".\\.venv\\Scripts\\python.exe -m harness check" },
      "linux": { "command": ".venv/bin/python -m harness check" },
      "osx": { "command": ".venv/bin/python -m harness check" },
      "problemMatcher": []
    }
  ]
}
'''

VSCODE_SETTINGS_JSON = r'''{
  "python.defaultInterpreterPath": ".venv\\Scripts\\python.exe",
  "python.terminal.activateEnvironment": true,
  "github.copilot.chat.codeGeneration.useInstructionFiles": true,
  "chat.promptFiles": true,
  "chat.useAgentsMdFile": true,
  "files.exclude": {
    "**/__pycache__": true
  },
  "search.exclude": {
    "**/.venv": true,
    "backups": true
  }
}
'''

VSCODE_EXTENSIONS_JSON = r'''{
  "recommendations": [
    "ms-python.python",
    "github.copilot-chat",
    "continue.continue"
  ]
}
'''

REQUIREMENTS_TXT = r'''pypdf>=4.0
'''

REQUIREMENTS_OPTIONAL_TXT = r'''# Optional: better text extraction for some PDFs (used automatically as a fallback)
pdfplumber>=0.10
'''

GITIGNORE = r'''.venv/
__pycache__/
*.pyc
.env
work/
logs/
reports/
backups/
input/*.pdf
input/*.PDF
'''

ENV_EXAMPLE = r'''# Copy this file to .env and adjust. The harness reads .env automatically;
# real environment variables take precedence.
TVET_BACKEND=ollama
TVET_MODEL={{DEFAULT_MODEL}}
OLLAMA_HOST=http://127.0.0.1:11434

# Only for backend openai_compatible (online or another local server):
# TVET_OPENAI_BASE_URL=https://your-endpoint.example/v1
# OPENAI_API_KEY=
'''

HARNESS_PS1 = r'''# Usage: .\scripts\harness.ps1 run | extract | validate | review | check | agents
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
if (-not $Rest) { $Rest = @("--help") }
& $Py -m harness @Rest
exit $LASTEXITCODE
'''


def bat_launcher(command):
    return (
        "@echo off\n"
        "setlocal\n"
        'cd /d "%~dp0.."\n'
        'set "PY=python"\n'
        'if exist ".venv\\Scripts\\python.exe" set "PY=.venv\\Scripts\\python.exe"\n'
        '"%PY%" -m harness ' + command + " %*\n"
        "echo.\n"
        "pause\n"
        "endlocal\n"
    )


FOLDER_README = {
    "input/README.md": "# input\n\nPut the TVET policy PDF files to be summarised here.\n"
                       "Agents must treat this folder as read-only.\n",
    "output/README.md": "# output\n\nSummaries are written here as `<pdf name>.summary.md`.\n"
                        "Check them with `python -m harness validate`.\n",
    "work/extracted/.gitkeep": "",
    "logs/.gitkeep": "",
    "reports/.gitkeep": "",
}


def continue_models_yaml(models):
    lines = [
        "name: Local Ollama models (TVET summariser)",
        "version: 0.0.1",
        "schema: v1",
        "models:",
    ]
    for model in models:
        lines += [
            "  - name: %s (local)" % model,
            "    provider: ollama",
            "    model: %s" % model,
            "    apiBase: http://127.0.0.1:11434",
            "    roles:",
            "      - chat",
            "      - edit",
            "    defaultCompletionOptions:",
            "      contextLength: 8192",
            "      temperature: 0.1",
        ]
    return "\n".join(lines) + "\n"


def build_files(models):
    default_model = models[0] if models else DEFAULT_MODELS[0]
    review_model = models[1] if len(models) > 1 else default_model

    def sub(text):
        return text.replace("{{DEFAULT_MODEL}}", default_model).replace("{{REVIEW_MODEL}}", review_model)

    files = {
        "README.md": README_MD,
        "AGENTS.md": AGENTS_MD,
        "requirements.txt": REQUIREMENTS_TXT,
        "requirements-optional.txt": REQUIREMENTS_OPTIONAL_TXT,
        ".gitignore": GITIGNORE,
        ".env.example": sub(ENV_EXAMPLE),
        "prompts/style-guide.md": STYLE_GUIDE_MD,
        "prompts/map-step.md": MAP_STEP_MD,
        "prompts/reduce-step.md": REDUCE_STEP_MD,
        "prompts/review-step.md": REVIEW_STEP_MD,
        "examples/example-summary.md": EXAMPLE_SUMMARY_MD,
        "agents/tvet-policy-summarizer.agent.md": sub(SUMMARIZER_AGENT_MD),
        "agents/tvet-summary-reviewer.agent.md": sub(REVIEWER_AGENT_MD),
        "agents/_template.agent.md": AGENT_TEMPLATE_MD,
        "config/harness.json": HARNESS_JSON,
        "config/style_rules.json": STYLE_RULES_JSON,
        "harness/__init__.py": HARNESS_INIT_PY,
        "harness/__main__.py": HARNESS_MAIN_PY,
        "harness/config.py": HARNESS_CONFIG_PY,
        "harness/agents.py": HARNESS_AGENTS_PY,
        "harness/pdf_text.py": HARNESS_PDF_PY,
        "harness/backends.py": HARNESS_BACKENDS_PY,
        "harness/validate.py": HARNESS_VALIDATE_PY,
        "harness/pipeline.py": HARNESS_PIPELINE_PY,
        "harness/cli.py": HARNESS_CLI_PY,
        ".github/copilot-instructions.md": COPILOT_INSTRUCTIONS_MD,
        ".github/prompts/summarize-tvet-policy.prompt.md": COPILOT_PROMPT_MD,
        ".github/instructions/tvet-summaries.instructions.md": COPILOT_FILE_INSTRUCTIONS_MD,
        ".github/agents/tvet-policy-summarizer.agent.md": COPILOT_AGENT_MD,
        ".continue/rules/tvet-policy-summaries.md": CONTINUE_RULE_MD,
        ".continue/prompts/summarize-tvet-policy.md": CONTINUE_PROMPT_MD,
        ".continue/models/local-ollama.yaml": continue_models_yaml(models or DEFAULT_MODELS),
        ".vscode/tasks.json": VSCODE_TASKS_JSON,
        ".vscode/settings.json": VSCODE_SETTINGS_JSON,
        ".vscode/extensions.json": VSCODE_EXTENSIONS_JSON,
        "scripts/harness.ps1": HARNESS_PS1,
        "scripts/run_summarizer.bat": bat_launcher("run"),
        "scripts/extract_pdfs.bat": bat_launcher("extract"),
        "scripts/validate_summaries.bat": bat_launcher("validate"),
        "scripts/review_summaries.bat": bat_launcher("review"),
        "scripts/check_setup.bat": bat_launcher("check"),
    }
    files.update(FOLDER_README)
    return files


# =====================================================================================
# Installer logic
# =====================================================================================

def say(message="", level="info"):
    prefix = {"info": "      ", "ok": "[ok]  ", "warn": "[warn]", "fail": "[fail]", "step": "\n==>"}[level]
    print("%s %s" % (prefix, message) if level != "step" else "%s %s" % (prefix, message), flush=True)


def ask_yes(question, assume_yes):
    if assume_yes:
        return True
    if not sys.stdin or not sys.stdin.isatty():
        return False
    answer = input("%s [Y/n] " % question).strip().lower()
    return answer in ("", "y", "yes", "j", "ja")


def write_files(root, models, force):
    written = skipped = 0
    for rel, content in build_files(models).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not force:
            skipped += 1
            continue
        newline = "\r\n" if path.suffix.lower() in CRLF_SUFFIXES else "\n"
        with open(path, "w", encoding="utf-8", newline=newline) as fh:
            fh.write(content)
        written += 1
    try:
        me = Path(__file__).resolve()
        dest = root / "setup_tvet_agents.py"
        if me != dest.resolve():
            shutil.copy2(str(me), str(dest))
    except (NameError, OSError):
        pass
    say("%d files written, %d existing files kept (use --force to overwrite)" % (written, skipped), "ok")


def venv_python(root):
    return root / ".venv" / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def create_venv(root, wheelhouse=None):
    py = venv_python(root)
    if not py.exists():
        say("creating virtual environment .venv")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", str(root / ".venv")])
        except subprocess.CalledProcessError:
            say("could not create .venv - the harness will use the system Python", "warn")
            return None
    pip = [str(py), "-m", "pip", "install", "--disable-pip-version-check"]
    if wheelhouse:
        pip += ["--no-index", "--find-links", str(Path(wheelhouse).resolve())]
    rc = subprocess.call(pip + ["-r", str(root / "requirements.txt")])
    if rc != 0:
        say("pip install failed (offline?). See README: 'pip fails offline'", "warn")
    else:
        say("requirements installed in .venv", "ok")
        subprocess.call(pip + ["-q", "-r", str(root / "requirements-optional.txt")],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return py


def http_json(url, payload=None, timeout=5):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"},
                                 method="POST" if data else "GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ollama_running():
    try:
        return http_json(OLLAMA_API + "/api/version", timeout=3).get("version")
    except Exception:
        return None


def find_ollama():
    exe = shutil.which("ollama")
    if exe:
        return exe
    candidates = []
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Ollama" / "ollama.exe")
    if os.environ.get("ProgramFiles"):
        candidates.append(Path(os.environ["ProgramFiles"]) / "Ollama" / "ollama.exe")
    candidates += [Path("/usr/local/bin/ollama"), Path("/usr/bin/ollama"), Path("/opt/homebrew/bin/ollama")]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def download(url, dest):
    say("downloading %s" % url)
    with urllib.request.urlopen(url, timeout=60) as resp, open(dest, "wb") as fh:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            block = resp.read(1024 * 256)
            if not block:
                break
            fh.write(block)
            done += len(block)
            if total:
                print("\r       %5.1f %% of %d MB" % (100.0 * done / total, total // 1048576), end="", flush=True)
    print()


def install_ollama(assume_yes):
    if not IS_WINDOWS:
        say("Ollama not found. Install it from https://ollama.com/download "
            "(Linux: curl -fsSL https://ollama.com/install.sh | sh)", "warn")
        return None
    if not ask_yes("Ollama is not installed. Install it now?", assume_yes):
        say("skipping Ollama installation", "warn")
        return None
    winget = shutil.which("winget")
    if winget:
        say("installing Ollama with winget")
        subprocess.call([winget, "install", "-e", "--id", "Ollama.Ollama",
                         "--accept-package-agreements", "--accept-source-agreements"])
        exe = find_ollama()
        if exe:
            return exe
        say("winget did not complete the installation - trying the official installer", "warn")
    try:
        installer = Path(tempfile.gettempdir()) / "OllamaSetup.exe"
        download(OLLAMA_WINDOWS_INSTALLER, installer)
        say("starting the Ollama installer - finish the installation window")
        subprocess.call([str(installer)])
    except (urllib.error.URLError, OSError) as exc:
        say("download failed: %s. Install manually from https://ollama.com/download" % exc, "fail")
        return None
    for _ in range(30):
        exe = find_ollama()
        if exe:
            return exe
        time.sleep(2)
    say("Ollama executable not found after installation. Open a new terminal and re-run this script.", "warn")
    return None


def start_ollama(exe):
    version = ollama_running()
    if version:
        say("Ollama server running (version %s)" % version, "ok")
        return True
    if not exe:
        return False
    say("starting Ollama server")
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
    if IS_WINDOWS:
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen([exe, "serve"], **kwargs)
    except OSError as exc:
        say("could not start Ollama: %s" % exc, "fail")
        return False
    for _ in range(40):
        time.sleep(1)
        version = ollama_running()
        if version:
            say("Ollama server running (version %s)" % version, "ok")
            return True
    say("Ollama server did not respond on %s" % OLLAMA_API, "fail")
    return False


def installed_models():
    try:
        return [m.get("name", "") for m in http_json(OLLAMA_API + "/api/tags").get("models", [])]
    except Exception:
        return []


def pull_models(exe, models):
    present = installed_models()
    for model in models:
        wanted = model if ":" in model else model + ":latest"
        if wanted in present or model in present:
            say("model %s already available" % model, "ok")
            continue
        say("pulling %s (approx. %s)" % (model, APPROX_MODEL_SIZES.get(model, "size unknown")))
        if exe:
            rc = subprocess.call([exe, "pull", model])
        else:
            try:
                http_json(OLLAMA_API + "/api/pull", {"model": model, "stream": False}, timeout=7200)
                rc = 0
            except Exception as exc:
                say("pull failed: %s" % exc, "fail")
                rc = 1
        say("model %s %s" % (model, "ready" if rc == 0 else "NOT pulled"), "ok" if rc == 0 else "fail")


def make_zip(root, include_data=False):
    backup_dir = root / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = backup_dir / ("%s_backup_%s.zip" % (root.name, stamp))
    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if any(part in ZIP_EXCLUDE_DIRS for part in rel.parts):
                continue
            is_data = rel.parts[0] in ZIP_DATA_DIRS
            if is_data and not include_data and path.is_file() and path.name not in ("README.md", ".gitkeep"):
                continue
            if path.name == ".env":
                continue
            arcname = (Path(root.name) / rel).as_posix()
            if path.is_file():
                archive.write(path, arcname)
                count += 1
            elif path.is_dir() and not any(path.iterdir()):
                archive.writestr(arcname + "/", "")
    say("backup: %s (%d files%s)" % (zip_path, count, "" if include_data else ", PDFs and results excluded"), "ok")
    return zip_path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Set up the TVET policy summariser agent workspace")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="workspace folder (default: %(default)s)")
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS),
                        help="comma-separated Ollama models; the first is the summariser default (default: %(default)s)")
    parser.add_argument("--skip-ollama", action="store_true", help="do not check, install or start Ollama")
    parser.add_argument("--skip-models", action="store_true", help="do not pull models")
    parser.add_argument("--skip-venv", action="store_true", help="do not create .venv / install requirements")
    parser.add_argument("--wheelhouse", help="install requirements offline from this folder of wheels")
    parser.add_argument("--force", action="store_true", help="overwrite existing workspace files")
    parser.add_argument("--yes", "-y", action="store_true", help="answer yes to installation prompts")
    parser.add_argument("--no-zip", action="store_true", help="do not create a ZIP backup")
    parser.add_argument("--zip-only", action="store_true", help="only create a ZIP backup of an existing workspace")
    parser.add_argument("--zip-include-data", action="store_true", help="include PDFs, outputs and logs in the ZIP")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if sys.version_info < (3, 9):
        print("Python 3.9 or newer is required.")
        return 1
    root = Path(args.target).expanduser().resolve()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print("TVET Policy Summariser setup %s | Python %s | %s" % (VERSION, platform.python_version(), platform.platform()))
    print("Workspace: %s" % root)

    if args.zip_only:
        if not root.exists():
            say("workspace does not exist", "fail")
            return 1
        make_zip(root, args.zip_include_data)
        return 0

    say("Step 1/5  Writing workspace files", "step")
    root.mkdir(parents=True, exist_ok=True)
    write_files(root, models, args.force)

    say("Step 2/5  Python environment", "step")
    py = None
    if args.skip_venv:
        say("skipped (--skip-venv)")
    else:
        py = create_venv(root, args.wheelhouse)

    say("Step 3/5  Ollama and models", "step")
    if args.skip_ollama:
        say("skipped (--skip-ollama)")
    else:
        exe = find_ollama()
        if exe:
            say("Ollama found: %s" % exe, "ok")
        elif not ollama_running():
            exe = install_ollama(args.yes)
        if start_ollama(exe):
            if args.skip_models:
                say("model download skipped (--skip-models)")
            else:
                pull_models(exe, models)
        else:
            say("Ollama not available - offline harness runs need it; Copilot mode works without it", "warn")

    say("Step 4/5  Health check", "step")
    runner = str(py) if py and py.exists() else sys.executable
    check_cmd = [runner, "-m", "harness", "check"]
    if args.skip_ollama:
        check_cmd += ["--backend", "mock"]
    subprocess.call(check_cmd, cwd=str(root))

    say("Step 5/5  Backup", "step")
    if args.no_zip:
        say("skipped (--no-zip)")
    else:
        make_zip(root, args.zip_include_data)

    activate = ".venv\\Scripts\\activate" if IS_WINDOWS else "source .venv/bin/activate"
    print("\nNext steps:")
    print("  cd \"%s\"" % root)
    print("  %s" % activate)
    print("  copy PDF files into input\\ and run:  python -m harness run")
    print("  open the folder in VS Code: code .   (tasks: Terminal > Run Task > TVET: ...)")
    print("  Copilot: run 'TVET: Extract PDF text', then /summarize-tvet-policy in Copilot Chat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
