# TVET Policy Summariser - Agent Workspace

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
