# Part 3 — Semi-agent vs. Agent: the same job, two control flows

**Read this before you run anything.** It is the most important file in the package.

Two programs in this folder do the same work: read a folder of PDFs, turn them into clean Markdown,
summarise each one with a local model, pull the numbers out of the tables, and produce a written
report plus an HTML page with a data table and a chart.

- `semi_agent.py` — **variant A.** A fixed sequence a human wrote. It stops and asks you before it
  writes the report. It never retries.
- `agent.py` — **variant B.** A loop. Each time round, the model proposes the next action, the
  program checks whether that action is allowed, runs it, verifies the result, and decides whether to
  stop.

Both run entirely against a local Ollama server at `http://127.0.0.1:11434`. Nothing is sent
anywhere else. There is no cloud API key in this folder and no code that could use one.

---

## The one thing to take away

> **Almost none of this code is "the AI".**

In `agent.py` there are exactly **two** places where text goes to a model:

| Line of code | What it does |
|---|---|
| `common.call_ollama(...)` inside `tool_summarize()` | asks the model to write a summary |
| `common.call_ollama(...)` inside `propose_action()` | asks the model which action to take next |

Everything else — several hundred lines — is **harness**. Here is the map:

| In the code | What it is | Which harness subsystem |
|---|---|---|
| `load_state()` / `save_state()` → `state.json` | memory that survives the program exiting | **State** |
| `precondition_ok()` | may this action be taken right now? | **Feedback** |
| `verify_output()` | did a real, non-empty file actually appear? | **Feedback** |
| `should_stop()` | the written rule for when the work is finished | **Feedback** |
| `next_required_action()` | the harness's own answer when the model's is unusable | **Control flow** |
| `TOOLS = {...}` | the five things the agent is permitted to do — and no more | **Tools** |
| `Log.write()` → `agent_log.md` | a plain-language record anyone can audit | **Feedback / observability** |
| `common.pdf_to_markdown()` | the ingestion step | **Environment / tools** |
| `MAX_STEPS = 40` | the loop can never run away | **Control flow** |

A useful exercise for a session: open `agent.py`, search for `call_ollama`, and count the hits. Two.
Then scroll through everything else. That scroll is the lesson.

---

## Why "the model proposes, the harness disposes"

`agent.py` genuinely asks the model what to do next. It does **not** genuinely let the model do it.
Every proposal passes through three gates:

1. **Is it one of the five tools?** If not, the harness overrides it.
2. **Is its precondition satisfied?** You cannot summarise a document that has not been converted
   yet. If the precondition fails, the harness overrides it.
3. **Did it actually produce something?** After the tool runs, the harness checks that a file exists
   and is non-empty. If not, the step is *not* marked done and the bookkeeping is rolled back.

Every override is written into `agent_log.md` in plain sentences, e.g.:

```text
The model proposed `write_report`, because: "I think we are probably finished."
  I checked whether that is allowed right now: it is not, because 2 document(s) are not
  ready yet (site_b_hydraulics_report.pdf, site_c_electrical_report.pdf). I overrode the
  proposal and will do `extract_table_data` on `site_b_hydraulics_report.pdf` instead.
```

Small local models propose `write_report` early quite often — they are optimistic about being
finished. That is precisely the "declaring victory too early" failure mode, and watching the harness
catch it live is more convincing than any slide.

---

## Why PDF → Markdown is mandatory, not optional

A PDF is a *layout* format. It stores glyph positions, not sentences. Handing a model badly ordered
PDF text produces fluent, confident nonsense, and every later step inherits that damage.

The ingestion step in `common.pdf_to_markdown()` therefore does three specific things:

- **Text** → Markdown paragraphs, in reading order.
- **Tables** → Markdown pipe tables, so the numbers survive as numbers and can be parsed back out.
- **Figures** → a note with the caption, and nothing more:

  ```text
  > **[Image 1 on page 1]** — Figure 1: Layout of the welding bays and extraction points.
  > _(image content not extracted; no OCR was performed)_
  ```

No OCR. If a number exists only inside a picture, it does not enter the dataset. That is a deliberate
accuracy decision, not a limitation: an unmarked guess is worse than an acknowledged gap.

---

## Running it

```bash
# 0. once: dependencies
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 1. once: create three sample PDFs (or drop your own into input_pdfs/)
python make_sample_pdfs.py

# 2. which models are installed here?
ollama list

# 3. variant A — fixed pipeline, stops at a human checkpoint
python semi_agent.py --model llama3.1:8b

# 4. variant B — control loop, stops itself
python agent.py --model qwen2.5:7b
```

Useful flags:

| Flag | Script | Effect |
|---|---|---|
| `--pause` | `semi_agent.py` | stop after every step so the room can inspect each file |
| `--yes` | `semi_agent.py` | skip the human confirmation (for unattended demo runs) |
| `--reset` | `agent.py` | delete `state.json` and `agent_log.md`, start clean |
| `--no-planner` | `agent.py` | skip the model's proposals; the harness decides every step |
| `--input` / `--output` | both | point at your own folders |

**No model on this machine?** There is a fake server in `../tools/mock_ollama.py` that returns canned
text so the control flow can still be demonstrated. Start it in a second terminal, then use
`--model mock:demo`. It is a teaching aid, not a language model — do not present its output as model
output.

---

## What you get

```text
output_semi/                       output_agent/
├─ 01_manifest.json                ├─ state.json          ← the harness's memory
├─ markdown/*.md                   ├─ agent_log.md        ← READ THIS ONE
├─ summaries/*.txt                 ├─ manifest.json
├─ 02_dataset.json                 ├─ markdown/*.md
├─ report.md                       ├─ summaries/*.txt
├─ report.pdf                      ├─ tables/*.json
└─ report.html   ← table + chart   ├─ report.md
                                   ├─ report.pdf
                                   └─ report.html   ← table + chart
```

`report.html` is a single self-contained file: the chart is embedded as base64 PNG and all styling is
inline. It opens on a machine with no network connection, which is the point.

Each generation step records **which model produced it**. That provenance appears in `report.md`,
in the HTML footer, in `state.json`, and in `agent_log.md` — four places, because provenance that
exists in only one place tends to get separated from the artefact.

---

## Try breaking it (recommended for the session)

| Do this | What you should see |
|---|---|
| Interrupt `agent.py` with Ctrl-C halfway, then run it again | it resumes; already-verified steps are skipped, because state is on disk |
| Delete one `output_agent/markdown/*.md` file and re-run | the harness notices, re-converts it, and logs why |
| Add a fourth PDF to `input_pdfs/` and re-run `agent.py` | the stop condition is no longer met, so the loop restarts work for that document only |
| Set `MAX_STEPS = 3` at the top of `agent.py` | the loop halts, says so plainly, and reports the work as incomplete |
| Run `agent.py --no-planner` | identical output, no planning calls — proof the *harness*, not the model, is doing the coordinating |

That last one is worth doing in front of an audience. It is the cleanest demonstration of the
Simplicity Statement in the whole package.

---

## UNESCO alignment

This worked example targets the *Deepen* and *Create* levels of the UNESCO AI competency framework
for teachers, under the aspects **AI foundations and applications** and **AI pedagogy**. The
verification step (`verify_output`) and the plain-language decision log (`agent_log.md`) are the
concrete mechanisms behind the framework's emphasis on transparency and on the critical evaluation of
AI outputs: the log makes every decision auditable by a non-programmer, and the verification step
means no output is accepted on the model's own say-so. For the students' framework, the same
material sits under **AI system design** at the *Understand → Apply* levels. UNESCO's progression
labels are Acquire / Deepen / Create (teachers) and Understand / Apply / Create (students).

## Sources

- Learn Harness Engineering (Walking Labs), lectures 01, 02 and 13 —
  <https://walkinglabs.github.io/learn-harness-engineering/en/>
- Meta-Harness: End-to-End Optimization of Model Harnesses — Lee, Nair, Zhang, Lee, Khattab & Finn,
  COLM 2026 — <https://yoonholee.com/meta-harness/>
