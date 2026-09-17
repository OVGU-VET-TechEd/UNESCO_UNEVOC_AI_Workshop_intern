# AGENTS.md - instructions for any AI coding or chat agent

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
