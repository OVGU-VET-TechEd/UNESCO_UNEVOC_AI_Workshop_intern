# RUNBOOK — Windows

Copy-paste sequence, top to bottom. Shell: **PowerShell** (not Command Prompt). Skip any step whose
✅ check already passes.

Total time: about 20 minutes, almost all of it downloading two models. Start Step 2 before the coffee
break.

Open PowerShell: press <kbd>Win</kbd>, type `powershell`, press Enter. Assumes the package is in
`C:\unevoc-harness-package`.

---

## Step 0 — Check what you have (20 s)

```powershell
cd C:\unevoc-harness-package
python --version
Get-ChildItem -Name part2_teaching, part3_worked_example, tools
```

✅ Python reports **3.9 or newer**, and all three folders list.

> If `python` opens the Microsoft Store, Python is not properly installed. Get it from
> <https://www.python.org/downloads/windows/> and **tick "Add python.exe to PATH"** in the installer.
> Close and reopen PowerShell afterwards.

---

## Step 1 — Install Ollama (3 min)

Download and run the Windows installer from <https://ollama.com/download/windows>.

Or, if you have winget:

```powershell
winget install --id Ollama.Ollama -e
```

Close and reopen PowerShell so the new `ollama` command is on your PATH, then:

```powershell
ollama --version
```

✅ A version number is printed.

The Windows installer runs Ollama as a background service automatically — there is no
`ollama serve` step on Windows. If the next step fails, open the Ollama app from the Start menu once
and try again.

---

## Step 2 — Pull two models (5–15 min, mostly download)

Two models, because the whole package is built around switching between them.

```powershell
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
ollama list
```

✅ `ollama list` prints a table containing **both** `llama3.1:8b` and `qwen2.5:7b`.

> On a laptop with 8 GB of RAM, use the smaller pair instead: `ollama pull llama3.2:3b` and
> `ollama pull qwen2.5:3b`, and substitute those tags everywhere below. The demos read `ollama list`
> rather than assuming which models exist.

---

## Step 3 — Verify the REST API on 127.0.0.1:11434 (20 s)

This is the interface every script in this package uses. If this step passes, nothing later can fail
for connection reasons.

```powershell
(Invoke-WebRequest -Uri http://127.0.0.1:11434/api/tags -UseBasicParsing).Content.Substring(0,200)
```

✅ A line of JSON appears, starting `{"models":[...` and naming your models.

```powershell
$body = '{"model":"llama3.1:8b","prompt":"Reply with one word: ready","stream":false}'
(Invoke-RestMethod -Uri http://127.0.0.1:11434/api/generate -Method Post -Body $body -ContentType 'application/json').response
```

✅ A short reply is printed. The **first** call is slow (30–90 s) because the model is being loaded
into memory; later calls are fast.

> "Unable to connect to the remote server"? The Ollama service is not running. Open the Ollama app
> from the Start menu, wait ten seconds, and repeat this step. Note the address: **127.0.0.1**, not a
> cloud endpoint. Nothing in this package talks to anything else.
>
> Do **not** use `curl` in PowerShell — it is an alias for `Invoke-WebRequest` and takes different
> arguments than the `curl` you may have seen in macOS or Linux instructions.

---

## Step 4 — Python virtual environment (1 min)

```powershell
cd C:\unevoc-harness-package\part3_worked_example
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

✅ The prompt now starts with `(.venv)`, and `pip install` ends with a `Successfully installed …`
line mentioning `pdfplumber`, `matplotlib` and `reportlab`.

> **`Activate.ps1 cannot be loaded because running scripts is disabled on this system`** — this is
> the one genuinely fragile step on Windows. Run this once, in the same window, then repeat the
> activate command:
>
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
>
> This affects only your own user account and only unsigned local scripts.

You must re-run `.\.venv\Scripts\Activate.ps1` in every new PowerShell window.

---

## Step 5 — The minimal harness, File D (1 min)

Start with the smallest example. This is the one to run while explaining state, verification, retry
and logging.

```powershell
cd C:\unevoc-harness-package\part2_teaching\file_d_min_harness
python min_harness.py --list-models
python min_harness.py --model llama3.1:8b
```

✅ The screen shows `ASK` / `GOT` / `CHECK` lines for three topics and ends with
`3 of 3 topics have an accepted objective`. Two files now exist: `harness_state.json` and
`harness_log.md`.

Now run it again with the other model:

```powershell
python min_harness.py --model qwen2.5:7b
```

✅ Every topic reports `SKIP … already accepted in an earlier run`. That is the state file working.
Add `--reset` to start over.

> Seeing `CHECK failed` lines? That is the demo succeeding, not failing. The verification step is
> rejecting an answer and the harness is re-asking with the reason attached.

---

## Step 6 — Create the sample PDFs (10 s)

```powershell
cd C:\unevoc-harness-package\part3_worked_example
.\.venv\Scripts\Activate.ps1
python make_sample_pdfs.py
```

✅ Three lines reporting written files, and `input_pdfs\` now contains three PDFs.

To use your own documents instead, drop them into `input_pdfs\` — both demos read whatever is there.

---

## Step 7 — Variant A: the semi-agent (1–3 min)

```powershell
python semi_agent.py --model llama3.1:8b
```

✅ Six numbered steps run. At **STEP 5** the program stops and asks
`Generate the report from this data? [y/N]`. Type `y` and press Enter. It finishes by listing
`report.md`, `report.html` and `report.pdf`.

Add `--pause` to stop after every step, which is better for a live session:

```powershell
python semi_agent.py --model llama3.1:8b --pause
```

---

## Step 8 — Variant B: the agent (2–5 min)

```powershell
python agent.py --model qwen2.5:7b --reset
```

✅ Numbered steps scroll past. Each one shows what the model proposed, whether the harness accepted
or overrode it, what was run, and whether verification passed. The run ends with
`Stopping. The report exists and contains a section for all 3 input documents.`

> If it ends with `I reached the hard limit of 40 steps`, the loop did not converge — usually because
> a very small model keeps proposing illegal actions. Re-run with `--no-planner` to confirm the
> harness itself is sound; that flag skips the model's proposals entirely.

---

## Step 9 — Open the results (1 min)

```powershell
Invoke-Item output_agent\report.html
Invoke-Item output_agent\agent_log.md
Invoke-Item output_semi\report.html
```

✅ `report.html` opens in your browser showing a data table and a bar chart. It is one
self-contained file — disconnect from the network and reload it to prove the point.

Read `agent_log.md` last, and read it aloud. It is the teaching artefact.

---

## Step 10 — Optional: run the whole thing with no model at all

For laptops that cannot run a model, or a spare machine at the back of the room. Use two PowerShell
windows:

```powershell
# window 1
python C:\unevoc-harness-package\tools\mock_ollama.py
```

```powershell
# window 2
cd C:\unevoc-harness-package\part3_worked_example
.\.venv\Scripts\Activate.ps1
python agent.py --model mock:demo --reset
```

✅ The full loop runs in a couple of seconds. The text is canned — do not present it as model output.

> "Only one usage of each socket address is normally permitted": the real Ollama service already owns
> port 11434. Either stop it from the Ollama tray icon, or skip this step and use the real models.

---

## The whole happy path in one block

```powershell
ollama pull llama3.1:8b; ollama pull qwen2.5:7b
(Invoke-WebRequest -Uri http://127.0.0.1:11434/api/tags -UseBasicParsing).StatusCode
cd C:\unevoc-harness-package\part3_worked_example
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python make_sample_pdfs.py
python ..\part2_teaching\file_d_min_harness\min_harness.py --model llama3.1:8b
python semi_agent.py --model llama3.1:8b --yes
python agent.py --model qwen2.5:7b --reset
Invoke-Item output_agent\report.html
```

---

## Reset / re-run cheatsheet

```powershell
Remove-Item -Recurse -Force output_semi, output_agent    # discard all Part 3 results
python agent.py --model qwen2.5:7b --reset               # same, for the agent only
Remove-Item ..\part2_teaching\file_d_min_harness\harness_*
deactivate                                               # leave the venv
```
