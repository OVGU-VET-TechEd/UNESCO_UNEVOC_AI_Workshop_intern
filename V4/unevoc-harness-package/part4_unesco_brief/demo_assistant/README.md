# Demo assistant — a document assistant you can read end to end

**Read this before running anything.** This folder is the practical demonstration for the UNESCO
brief: *build or test a simple assistant using public or anonymised documents*.

It is about 700 lines of Python, all of it readable, and it does one job properly: answer questions
about a folder of documents, **with a citation for every claim and an explicit refusal when the
documents do not cover the question**.

It runs entirely against a local model on `127.0.0.1`. Nothing is sent anywhere.

---

## The pipeline, and where the AI actually is

```text
  corpus_raw/          your documents, as given                    make_corpus.py (demo only)
      │
      ├─ anonymise.py  scrub direct identifiers, write a report    ← no AI
      ▼
  corpus/              cleared documents, ready to index
      │
      ├─ kb_build.py   split into passages, keep metadata          ← no AI (embeddings optional)
      ▼
  kb.json              the knowledge base — plain text, open it
      │
      ├─ ask.py        RETRIEVE → GROUND → VERIFY                  ← AI in the middle step only
      ▼
  answer + citations, or a refusal                                 ask_log.md records everything
      │
      └─ eval_kb.py    run a fixed question set, report 3 numbers  ← no AI in the scoring
```

Four of the five programs contain **no language model at all**. In `ask.py`, exactly one function
calls a model. Everything that determines whether the assistant is trustworthy — how documents are
split, how passages are found, whether an answer is allowed through — is ordinary code you can read.

That is the point of the demonstration.

---

## Run it

```bash
# 0. dependencies (only needed if your corpus contains PDFs)
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 1. create the synthetic demo corpus (skip if using your own documents)
python make_corpus.py

# 2. scrub direct identifiers, and READ THE REPORT
python anonymise.py
open anonymisation_report.md

# 3. build the knowledge base
python kb_build.py
#    optional, if you have pulled an embedding model:
#    python kb_build.py --embed nomic-embed-text --output kb_embed.json

# 4. ask it things
python ask.py "What evidence counts for quality assurance self-assessment?" --model llama3.1:8b
python ask.py "How many learners completed at partner B?" --model llama3.1:8b --show-sources
python ask.py "What is the capital city of Peru?" --model llama3.1:8b      # → refusal

# 5. measure it
python eval_kb.py --model llama3.1:8b
open eval_report.md
```

No model on the machine? Start `../../tools/mock_ollama.py` in a second terminal and use
`--model mock:demo`. Its replies are canned text, and its "embeddings" are a hashed bag of words, not
meaning — the mock exists to demonstrate control flow, not answer quality. Never present its output
as model output.

---

## The three defences against invention

Run the Peru question in front of the room. Nothing is invented, and there are three separate reasons
why — each one visible in `ask_log.md`.

**1. The retrieval gate — before any model call.** Two conditions, both cheap and both explainable:
something must score above a keyword threshold, **and** at least 55% of the question's content words
must actually appear in what was retrieved. "Capital city Peru" scores near zero against a corpus of
TVET policy documents, so `ask.py` refuses without spending a model call at all.

**2. The model's own signal.** The prompt permits exactly one escape: reply `INSUFFICIENT_EVIDENCE`.
When the model uses it, the harness passes the refusal through rather than pressing for an answer.

**3. The citation check — after the model call.** Every `[S1]`-style marker must resolve to a source
that was actually supplied. If the model cites `[S9]` when only four sources exist, the answer is
rejected, the model is re-asked with that specific reason, and after two failures the assistant
refuses rather than showing an answer whose citations do not check out.

You will see layer 3 fire against the mock server, which is rigged to invent a citation on every
fourth call:

```text
- **Verification failed:** it cited source(s) that were not supplied: [S9]; only S1 to S4 exist.
  Re-asking with that reason attached.
- Attempt 2: asking `mock:demo` with 4 sources.
- Verification passed: cited 1 of 4 supplied sources.
```

**What none of these catch.** A citation can resolve to a real passage that does not support the
claim attached to it. That is not machine-checkable, and it is why the citation is printed with the
answer: so a person can open it.

---

## The thresholds are corpus-specific, and that is the lesson

`MIN_RETRIEVAL_SCORE` and `MIN_TERM_COVERAGE` at the top of `ask.py` are tuned for the eight-document
demo corpus. **They will be wrong for yours.** Tune them with `eval_kb.py`: raise them until the
questions that should be refused are refused, then lower them until the questions that should be
answered are answered again.

If no setting satisfies both, that is a genuine finding rather than a bug — usually it means the
corpus does not actually cover what people want to ask, which is worth knowing in week two rather
than month six.

---

## What `eval_kb.py` reports, and why three numbers

| Number | What it tells you | What to do if it is low |
|---|---|---|
| **Retrieval hit rate** | Did the right document reach the prompt at all? | Fix chunking, metadata or retrieval. Changing the model will not help. |
| **Answered when expected** | Questions the corpus covers got an answer. | Usually the thresholds are too strict, or the corpus genuinely lacks the material. |
| **Refused when expected** | Questions outside the corpus were declined, not invented. | Thresholds too loose. This is the number vendors do not publish. |

Report all three separately. A single blended "accuracy" figure hides which one broke.

Twelve questions is a demonstration. **Thirty to fifty real questions, collected from real staff
before anything is built, is a pilot.** Collecting them first is what prevents building an assistant
for questions nobody asks.

---

## The documents

`make_corpus.py` writes eight **synthetic** documents into `corpus_raw/`. They were invented for this
demonstration. They are not UNESCO or UNEVOC documents, they contain no real policy or project data,
and the people in `07_steering_minutes.md` do not exist. That file contains invented names, email
addresses and phone numbers for exactly one reason: so `anonymise.py` has something to remove in
front of an audience.

For your own session, replace `corpus_raw/` with your own material. `.md`, `.txt` and `.pdf` are all
read.

### About `anonymise.py` — read this before using it on anything real

It is a **redaction aid, not a compliance tool**. It finds identifiers with a predictable shape:
emails, phone numbers, IBANs, handles, and names preceded by a title. Each becomes a stable
pseudonym, so the same person is `[PERSON_1]` everywhere and the text stays readable, and every
replacement is listed in `anonymisation_report.md`.

Three limits, stated plainly:

1. **It cannot find names it was not told about.** Pass `--names names.txt` for the reliable path.
2. **It cannot remove indirect identifiers.** "The only female welding instructor at partner C"
   identifies someone perfectly and contains no name at all. No regular expression will ever catch
   that.
3. **It does not judge sensitivity.** A document can be fully de-identified and still be one you are
   not permitted to circulate.

PDFs are copied through **unchanged** and flagged in the report. Scrubbing a PDF in place is a
different job, and a redaction that merely hides text visually is not a redaction.

The rule this package follows: a human reads `anonymisation_report.md` before the corpus is indexed.
The scrubber narrows what you have to look for. It does not replace you.

**For a live session, prefer documents that are already public.**

---

## Things to try in front of an audience

| Do this | What it shows |
|---|---|
| Open `kb.json` in a text editor | A knowledge base is a list of passages with labels. There is nothing hidden in it. |
| Ask the Peru question | Refusal is designed in, and it happened before any model was called. |
| Ask with `--show-sources` | The answer is assembled from passages you can read yourself. |
| Delete a document from `corpus/`, rebuild, ask about it again | The assistant now refuses. It never "knew" anything. |
| Add a document, rebuild, ask again | Updating a knowledge base takes seconds. This is why "retrain it on our documents" is almost always the wrong answer. |
| Run `eval_kb.py` with two different models | Retrieval hit rate barely moves; phrasing does. Most of the quality is not in the model. |
| Set `MIN_TERM_COVERAGE = 0.0` and re-run the eval | The refusal rate collapses. This is what an assistant with no gate looks like. |

The last one is the most useful five minutes in the session.

---

## UNESCO framework alignment

This demonstration targets the *Deepen* and *Create* levels of the **UNESCO AI competency framework
for teachers** (2024), aspects *AI foundations and applications* and *ethics of AI*. The citation
requirement, the designed refusal and `ask_log.md` are concrete mechanisms for the framework's
emphasis on transparency and on critical evaluation of AI outputs: no answer is accepted on the
model's own say-so, every claim is traceable to a passage a human can open, and every run is
auditable after the fact. `anonymise.py` and its stated limits sit under the ethics aspect —
specifically, the framework's insistence that data protection is a professional responsibility rather
than a tool setting. UNESCO's progression levels are Acquire / Deepen / Create for teachers and
Understand / Apply / Create for students.

## Sources

- UNESCO AI competency frameworks for teachers and students (2024) —
  <https://www.unesco.org/en/articles/ai-competency-framework-teachers>
- Meta-Harness: End-to-End Optimization of Model Harnesses — Lee, Nair, Zhang, Lee, Khattab & Finn,
  COLM 2026 — <https://yoonholee.com/meta-harness/>
- Learn Harness Engineering (Walking Labs) —
  <https://walkinglabs.github.io/learn-harness-engineering/en/>
