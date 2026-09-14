# A — AI assistants, agents and knowledge bases: what they are and how they work

*Draft teaching material for UNESCO UNEVOC Magdeburg. Audience: lecturers, TVET instructors and
researchers. Technical accuracy first; every definition here is one you can hold someone to.*

---

## Why definitions matter more than usual here

Most of the confusion in this field is vocabulary, not technology. "AI assistant", "agent",
"knowledge base" and "the AI knows our documents" are used interchangeably in vendor material, and
they describe things with different costs, different failure modes and different governance
requirements. Procuring the wrong one is expensive; the wrong one is also usually the more expensive
one.

This file defines eleven terms precisely, then gives a decision table.

---

## 1. The pieces, precisely

### 1.1 Language model (the "model", the "weights")

**Definition.** A mathematical function, fixed at the moment it was trained, that takes a sequence of
text and returns a probability distribution over what token comes next. Running it repeatedly
produces text.

**What follows from that definition — and this is the part that matters practically:**

- It has **no memory**. Each call is independent. Anything it "remembers" was put back into the input
  by software around it.
- It has **no access to your files, your email or the internet**, unless something outside it fetches
  that material and pastes it into the input.
- It does not **look things up**. It produces the continuation that fits the patterns it was trained
  on. When those patterns and the truth coincide, the output is correct. The model cannot tell the
  difference between the two cases.
- It cannot **do** anything. It emits text. If that text causes a file to be written, some other
  program did the writing.

**Practical consequence:** every capability you actually care about — knowing your documents,
remembering last week, checking its own work, taking an action — lives in the software *around* the
model, not in the model.

### 1.2 Context window

**Definition.** The maximum amount of text (measured in tokens, roughly ¾ of a word each) that can be
supplied to one model call.

**Practical consequence:** this is a hard budget per call, and everything competes for it — the
instructions, the retrieved documents, the conversation so far, and the answer. "Just give it all our
documents" fails for a simple reason: they do not fit. Even where a large window makes them fit,
quality falls as the relevant sentence gets buried. Selecting what goes in is the job (see §1.6).

### 1.3 Prompt

**Definition.** The complete text supplied to one model call: instructions, any supplied documents,
the conversation history, and the question.

**Practical consequence:** if a fact is not in the prompt and not in the weights, the model does not
have it. Assistants that appear to "know" your policy documents work by putting the relevant part of
those documents into the prompt, every single time, before you see anything.

### 1.4 AI assistant

**Definition.** A language model wrapped in a fixed instruction and a conversation history,
responding to a human who triggers every turn. It answers; it does not act.

**Discriminating test:** *who decides what happens next?* In an assistant, the human decides, every
time.

**Examples:** a chat interface over a model; a "summarise this document" button; the demo in this
folder.

### 1.5 Tool (function call)

**Definition.** A named operation the surrounding software is willing to perform on the model's
behalf — search a folder, read a file, run a query, send an email — together with a description the
model can read and a schema for its arguments.

**How it actually works, mechanically:** the model does not execute anything. It emits text naming a
tool and its arguments. The surrounding program parses that text, decides whether to allow it, runs
the operation itself, and pastes the result back into the next prompt.

**Practical consequence:** "the agent can send email" always means "we wrote code that sends email
when the model asks for it". The permission is yours to grant and yours to withhold. The list of
tools *is* the list of things that can go wrong.

### 1.6 Knowledge base

**Definition.** A collection of documents that has been prepared for retrieval: split into passages
("chunks"), labelled with metadata (source document, section, date), and indexed so that passages
relevant to a query can be found quickly.

**What it is not — three common and consequential misunderstandings:**

| Misunderstanding | Reality |
|---|---|
| "We trained the AI on our documents." | Nothing was trained. The documents sit in a file; passages are copied into the prompt at question time. |
| "The knowledge base is the AI's memory." | It is a searchable folder. It has no notion of a conversation, and it changes only when you rebuild it. |
| "Once it's in the knowledge base, it's private/safe." | The knowledge base is as sensitive as its most sensitive passage, and every passage is a candidate for being shown to a user in an answer. |

**Practical consequence:** knowledge base quality is a *document* problem, not an AI problem. The
three decisions that determine whether the assistant works — how documents are split, what metadata
is kept, and how passages are matched to questions — are made before any model runs. In this
package's demo, `kb_build.py` makes all three, and it never calls a language model at all unless you
ask for embeddings.

### 1.7 Embedding and vector store

**Definition.** An *embedding* is a list of numbers produced by a (small, separate) model, positioned
so that passages with similar meaning have similar lists. A *vector store* is an index over those
lists supporting "find the most similar".

**Why it exists:** keyword search fails when the question and the document use different words for
the same thing — "staff qualification records" versus "instructor credentials". Embeddings find that
match; keywords do not.

**Where it is oversold:** embeddings are not required for a working assistant, and for policy and
project documents — where people search using the document's own vocabulary — keyword ranking is
often equal or better. The demo in this folder ships with keyword retrieval by default and embeddings
as an optional flag, precisely so you can measure the difference on your own documents instead of
assuming it.

### 1.8 Retrieval-augmented generation (RAG)

**Definition.** A three-step pattern:

```text
       question
          │
          ▼
   (1) RETRIEVE ─── find the k passages in the knowledge base most likely
          │          to be relevant.        [no language model involved]
          ▼
   (2) GROUND ───── build a prompt containing those passages, numbered,
          │          plus an instruction to use only them and to cite.
          ▼                                  [this is the model call]
   (3) VERIFY ───── check the answer before anyone sees it: does it cite?
          │          do the citations exist? if not, retry, then refuse.
          ▼                                 [no language model involved]
        answer + citations, or an explicit refusal
```

**Practical consequence:** two of the three steps contain no AI. Most of what makes a RAG assistant
trustworthy or untrustworthy is in steps 1 and 3.

### 1.9 Agent

**Definition.** A system in which the model chooses the next action from a defined toolset, the
surrounding software executes it, the result is fed back, and the cycle repeats until a stop
condition is met.

**Three discriminating tests.** A thing is an agent only if all three hold:

1. **It chooses.** The order of operations is not fixed in advance by a person.
2. **It acts.** Its choices cause things to happen — files written, records updated, messages sent.
3. **It stops on a rule.** There is a written, checkable condition for being finished, plus a hard
   cap on iterations.

A system missing (3) is not an agent; it is an unbounded expense with write access.

**Semi-agent** (used throughout this package): a fixed sequence of steps written by a person, each
producing an inspectable artefact, with human checkpoints and no autonomous retry. It is not a
lesser agent — for most institutional work it is the appropriate design, because it is auditable and
predictable.

### 1.10 Harness

**Definition.** Everything in the engineering infrastructure outside the model weights: instructions,
tools, environment, state, and feedback. In the Meta-Harness paper's formulation, the code
determining what to store, retrieve and present to a model.

> **Simplicity Statement — Harness Engineering**
> A harness does not make the model smarter. It gives a fixed model a place to keep state, a way to
> check its own work, and rules for when to stop. Everything else in this package is one worked
> example of that idea.

### 1.11 Hallucination, grounding, refusal

**Hallucination (precisely).** Fluent output that is not entailed by any source the system was given.
Not lying — the model has no notion of truth to depart from. It is the expected behaviour of a
next-token predictor asked a question its inputs do not answer.

**Grounding.** Constraining an answer to supplied passages and requiring a citation for each claim.
This reduces hallucination; it does not eliminate it, because a model can cite a real passage that
does not support the claim it is attached to.

**Refusal.** The system declining to answer when retrieval found nothing relevant. This must be
designed in deliberately — the default behaviour of every model is to produce something. In the demo,
three independent layers can produce a refusal: the retrieval gate (before any model call), the
model's own insufficient-evidence signal, and the citation check afterwards.

---

## 2. Commonly confused pairs

| These get conflated | The actual difference |
|---|---|
| **Assistant** vs **agent** | Who decides the next step. Human → assistant. System → agent. |
| **Knowledge base** vs **training** | A knowledge base is read at question time and can be changed in a minute. Training alters the weights, costs orders of magnitude more, and is almost never the right answer to "it doesn't know our documents". |
| **RAG** vs **fine-tuning** | RAG changes *what the model is shown*. Fine-tuning changes *how the model writes*. If the complaint is "it doesn't know X", you need RAG. If the complaint is "it doesn't sound like us" or "it won't follow our output format", fine-tuning may help. |
| **Guardrail** vs **verification** | A guardrail is an instruction in the prompt asking the model to behave. Verification is code that checks the output and can reject it. Only the second is enforceable. |
| **Citation** vs **correct citation** | That a marker points at a real passage is machine-checkable. That the passage supports the claim is not, and needs a person. |
| **Local** vs **private** | Running a model on your own hardware means no data leaves the machine. It does not mean the outputs are accurate or that the corpus was cleared for the audience seeing it. |

---

## 3. Which one do you actually need?

Read down the left column and stop at the first row that matches.

| If the need is… | Build this | Why | Effort |
|---|---|---|---|
| Rewrite, translate, shorten, restructure text someone pastes in | **Plain assistant**, no knowledge base | The material arrives with the question; nothing needs retrieving | Days |
| "What does our policy say about X?" across a stable document set | **Assistant + knowledge base (RAG)** | The corpus is the value; the model only phrases the answer | 2–6 weeks |
| The same fixed multi-step job repeatedly, where a human should see the intermediate results | **Semi-agent** | Auditable, predictable, and the checkpoint is a real control | 4–8 weeks |
| A job whose steps vary by input, run unattended, with a clear finish line | **Agent** | Only justified when the ordering genuinely cannot be written down in advance | 3–6 months |
| "It doesn't sound like our house style" | **Prompt or skill file first**, fine-tuning only if that fails | Fine-tuning is the last resort, not the first | Days, then months |
| A number that must be exactly right every time | **Not a language model.** A query, a spreadsheet, a script | Use a system that is deterministic where determinism is available | — |

The last row is the one most often skipped. A language model is the right tool when the input is
unstructured text and the output tolerates review. It is the wrong tool for arithmetic on a table you
already have in machine-readable form.

---

## 4. What "offline" means in this package

Every executable component here runs against a local inference server (Ollama) on `127.0.0.1`, with
the model weights on disk. There is no cloud API key anywhere in the package and no code that could
use one. On UNEVOC/OVGU infrastructure the same stack runs on an on-premises GPU server reached over
an SSH tunnel, with the service bound to localhost only.

This matters for three separate reasons, which are often collapsed into one:

1. **Data protection.** Draft policy, unpublished project data and partner correspondence never leave
   the institution.
2. **Reproducibility.** A pinned local model gives the same answer next year. A hosted model is
   updated underneath you, silently, which is fatal for any published methodology.
3. **Cost predictability.** The cost is the hardware, known in advance, not a per-token bill that
   scales with enthusiasm.

The trade-off is honest: an 8B model running on a laptop is meaningfully weaker at reasoning than the
largest hosted models. For grounded question answering over your own documents — where the answer is
in the retrieved passage and the model's job is to phrase it and cite it — this matters much less
than people expect. For open-ended analysis with no supplied source, it matters a lot. Test on your
own questions; `eval_kb.py` in the demo folder exists for exactly this.

---

## 5. UNESCO framework alignment

This file is *Acquire*-level material under the **UNESCO AI competency framework for teachers**
(2024) — 15 competencies across five aspects (human-centred mindset; ethics of AI; AI foundations and
applications; AI pedagogy; AI for professional learning), in three progression levels: **Acquire,
Deepen, Create**. It sits under *AI foundations and applications*: knowing what an AI system is
composed of well enough to evaluate and select tools rather than accept vendor descriptions of them.
The companion **AI competency framework for students** (12 competencies across four dimensions, at
**Understand, Apply, Create**) covers the same ground under *AI techniques and applications*.

---

## Sources

- UNESCO AI competency framework for teachers (2024) —
  <https://www.unesco.org/en/articles/ai-competency-framework-teachers>
- UNESCO AI competency framework for students (2024) —
  <https://www.unesco.org/en/articles/ai-competency-framework-students>
- Meta-Harness: End-to-End Optimization of Model Harnesses — Lee, Nair, Zhang, Lee, Khattab & Finn,
  COLM 2026 — <https://yoonholee.com/meta-harness/>
- Learn Harness Engineering (Walking Labs), lectures 01, 02, 13 —
  <https://walkinglabs.github.io/learn-harness-engineering/en/>
