# RUNBOOK — macOS

Copy-paste sequence, top to bottom. Shell: **zsh** (the macOS default; bash works identically here).
Skip any step whose ✅ check already passes.

Total time: about 20 minutes, almost all of it downloading two models. Start Step 2 before the coffee
break.

Assumes you are in the package folder, e.g. `~/unevoc-harness-package`.

---

## Step 0 — Check what you have (20 s)

```bash
cd ~/unevoc-harness-package
python3 --version
ls part2_teaching part3_worked_example tools
```

✅ Python reports **3.9 or newer**, and all three folders list.

> macOS ships an old Python. If `python3 --version` says 3.8 or lower, install a current one from
> <https://www.python.org/downloads/macos/> or with `brew install python@3.12`, then re-run this step.

---

## Step 1 — Install Ollama (2 min)

```bash
brew install ollama
```

No Homebrew? Download the app from <https://ollama.com/download/mac>, drag it to Applications, and
open it once. Then continue.

Start the server:

```bash
ollama serve &
sleep 3
```

✅ No error, and the process keeps running. If you installed the desktop app instead, it starts the
server for you and this command will report that the address is already in use — that is fine, the
server is up.

---

## Step 2 — Pull two models (5–15 min, mostly download)

Two models, because the whole package is built around switching between them.

```bash
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
ollama list
```

✅ `ollama list` prints a table containing **both** `llama3.1:8b` and `qwen2.5:7b`.

> On a Mac with 8 GB of memory, use the smaller pair instead: `ollama pull llama3.2:3b` and
> `ollama pull qwen2.5:3b`, and substitute those tags everywhere below. The demos do not care which
> models you use — they read `ollama list` rather than assuming.

---

## Step 3 — Verify the REST API on 127.0.0.1:11434 (10 s)

This is the interface every script in this package uses. If this step passes, nothing later can fail
for connection reasons.

```bash
curl -s http://127.0.0.1:11434/api/tags | head -c 200; echo
```

✅ A line of JSON appears, starting `{"models":[...` and naming your models.

```bash
curl -s http://127.0.0.1:11434/api/generate \
  -d '{"model":"llama3.1:8b","prompt":"Reply with one word: ready","stream":false}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["response"])'
```

✅ A short reply is printed. The **first** call is slow (30–90 s) because the model is being loaded
into memory; later calls are fast.

> Nothing printed, or "connection refused"? The server is not running. Go back to Step 1 and run
> `ollama serve &` again. Note the address: **127.0.0.1**, not a cloud endpoint. Nothing in this
> package talks to anything else.

---

## Step 4 — Python virtual environment (1 min)

```bash
cd ~/unevoc-harness-package/part3_worked_example
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

✅ The prompt now starts with `(.venv)`, and `pip install` ends with a `Successfully installed …`
line mentioning `pdfplumber`, `matplotlib` and `reportlab`.

You must re-run `source .venv/bin/activate` in every new terminal window.

---

## Step 5 — The minimal harness, File D (1 min)

Start with the smallest example. This is the one to run while explaining state, verification, retry
and logging.

```bash
cd ~/unevoc-harness-package/part2_teaching/file_d_min_harness
python3 min_harness.py --list-models
python3 min_harness.py --model llama3.1:8b
```

✅ The screen shows `ASK` / `GOT` / `CHECK` lines for three topics and ends with
`3 of 3 topics have an accepted objective`. Two files now exist: `harness_state.json` and
`harness_log.md`.

Now run it again, and again with the other model:

```bash
python3 min_harness.py --model qwen2.5:7b
```

✅ Every topic reports `SKIP … already accepted in an earlier run`. That is the state file working.
Add `--reset` to start over.

> Seeing `CHECK failed` lines? That is the demo succeeding, not failing. The verification step is
> rejecting an answer and the harness is re-asking with the reason attached. Smaller models produce
> more of these, which makes the point better.

---

## Step 6 — Create the sample PDFs (10 s)

```bash
cd ~/unevoc-harness-package/part3_worked_example
source .venv/bin/activate
python3 make_sample_pdfs.py
```

✅ Three lines reporting written files, and `input_pdfs/` now contains three PDFs.

To use your own documents instead, drop them into `input_pdfs/` — both demos read whatever is there.

---

## Step 7 — Variant A: the semi-agent (1–3 min)

```bash
python3 semi_agent.py --model llama3.1:8b
```

✅ Six numbered steps run. At **STEP 5** the program stops and asks
`Generate the report from this data? [y/N]`. Type `y` and press Enter. It finishes by listing
`report.md`, `report.html` and `report.pdf`.

Add `--pause` to stop after every step, which is better for a live session:

```bash
python3 semi_agent.py --model llama3.1:8b --pause
```

---

## Step 8 — Variant B: the agent (2–5 min)

```bash
python3 agent.py --model qwen2.5:7b --reset
```

✅ Numbered steps scroll past. Each one shows what the model proposed, whether the harness accepted
or overrode it, what was run, and whether verification passed. The run ends with
`Stopping. The report exists and contains a section for all 3 input documents.`

> If it ends with `I reached the hard limit of 40 steps`, the loop did not converge — usually because
> a very small model keeps proposing illegal actions. Re-run with `--no-planner` to confirm the
> harness itself is sound; that flag skips the model's proposals entirely.

---

## Step 9 — Open the results (1 min)

```bash
open output_agent/report.html
open output_agent/agent_log.md
open output_semi/report.html
```

✅ `report.html` opens in your browser showing a data table and a bar chart. It is one
self-contained file — turn off your Wi-Fi and reload it to prove the point.

Read `agent_log.md` last, and read it aloud. It is the teaching artefact.

---

## Step 10 — Optional: run the whole thing with no model at all

For laptops that cannot run a model, or a spare machine at the back of the room:

```bash
# terminal 1
python3 ~/unevoc-harness-package/tools/mock_ollama.py

# terminal 2
cd ~/unevoc-harness-package/part3_worked_example && source .venv/bin/activate
python3 agent.py --model mock:demo --reset
```

✅ The full loop runs in a couple of seconds. The text is canned — do not present it as model output.

---

## The whole happy path in one block

```bash
brew install ollama && ollama serve & sleep 3
ollama pull llama3.1:8b && ollama pull qwen2.5:7b
curl -s http://127.0.0.1:11434/api/tags | head -c 120; echo
cd ~/unevoc-harness-package/part3_worked_example
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 make_sample_pdfs.py
python3 ../part2_teaching/file_d_min_harness/min_harness.py --model llama3.1:8b
python3 semi_agent.py --model llama3.1:8b --yes
python3 agent.py --model qwen2.5:7b --reset
open output_agent/report.html output_agent/agent_log.md
```

---

## Reset / re-run cheatsheet

```bash
rm -rf output_semi output_agent                      # discard all Part 3 results
python3 agent.py --model qwen2.5:7b --reset          # same, for the agent only
rm ../part2_teaching/file_d_min_harness/harness_*    # reset File D
deactivate                                           # leave the venv
pkill ollama                                         # stop the model server
```
