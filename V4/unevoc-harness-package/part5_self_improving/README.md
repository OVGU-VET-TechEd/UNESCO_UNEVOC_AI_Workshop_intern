# Part 5 — The interactive page, and the agent that writes its own skill

Two files. One is for learning, one is for running.

| File | What it is |
|---|---|
| `LEARN_the_five_layers.html` | A self-contained interactive page. Six layers, from a bare prompt to a self-improving agent. Open it in a browser — no server, no network, no install. |
| `wiki_agent.py` | A working implementation of the fifth layer. An agent that writes its own `SKILL.md`, keeps a wiki of what it learned, and rolls back changes that make things worse. |

---

## `LEARN_the_five_layers.html`

Open it directly. Turn the network off first if you want to prove the point.

The page is built around one mechanic: **a prompt inspector on the right that grows as you
advance.** Layer 0 shows an empty prompt and a model waiting for text. By layer 5 there are eight
blocks in it, and one of them was written by a machine. Each new block flashes when it appears, so
"this layer adds to the last" is something you watch rather than something you are told.

| Layer | Covers | Interactive |
|---|---|---|
| 0 | Tokens, weights, context window | Type anything, watch it become tokens |
| 1 | Prompt engineering | Send a vague vs. a specific prompt |
| 2 | Skill engineering | Toggle the skill file on and off, same task |
| 3 | Harness engineering | Run `make verify`; break something and run it again |
| 4 | Loop engineering | Watch the agent propose, get overridden, and stop itself |
| 5 | Self-improving agents | Watch a skill file get written, rejected, and rewritten |

Every layer carries its benefits, its UNEVOC applications, Python you can run, and a short mapping
to the UNESCO competency frameworks.

**In a session:** project it and drive it yourself rather than handing it out. The two moments worth
pausing on are the harness override at layer 4 (a small model claiming it is finished, and the code
catching it) and the rollback at layer 5 (a change reverted while the knowledge that produced it is
kept).

**What is simulated:** the three demos replay real output from this package's scripts against the
mock server, so the page works on a laptop with no model. The tokenizer is a teaching approximation.
Every code sample is excerpted from a file that actually runs.

---

## `wiki_agent.py`

A scaled-down implementation of **WikiSkill** (Tang, Rashtchian, Ferng, Tomkins, Juan & Vu, Google
Research, arXiv:2608.27454), which itself builds on Karpathy's LLM Wiki proposal. Runs fully offline.

```bash
# with a real local model
python wiki_agent.py --model llama3.1:8b --iterations 5

# no model installed? the mock needs none
python ../tools/mock_ollama.py &
python wiki_agent.py --model mock:demo --reset

# then read what it wrote — nobody typed any of this
cat workspace/skills/SKILL.md
ls  workspace/wiki/patterns/
cat workspace/wiki/skill-impact.md
```

### The idea, in one asymmetry

A rejected skill is thrown away. **What was learned by trying it is not.** Three folders enforce it:

```text
workspace/
├── raw/      execution traces, complete           immutable
├── wiki/     patterns + evolution log + audit     GROWS ONLY, never rolled back
└── skills/   the active SKILL.md                  gated; reverted if it scores worse
```

Four roles per iteration: an **Inference Agent** does the task with the current skill; a **Wiki
Maintainer** turns the traces into pattern pages; a **Skill Proposer** reads the wiki and proposes
one edit; a **Gate** scores it on held-out tasks and keeps or reverts.

### The detail most people miss

The Inference Agent is **not given the wiki**. That is deliberate, and it is measured: the paper's
ablation found that giving the working agent wiki access made the *final skill worse* — 63.7% down
to 60.9% average — because the agent starts solving tasks from the wiki instead of from the skill,
and the traces stop revealing what the skill needs to fix. The wiki informs the Proposer, never the
worker.

### What a run looks like

Against the mock, the arc is:

```text
Baseline with no skill at all: 0%
ITERATION 1   gate  33% >  0% previous -> KEPT
ITERATION 2   gate  67% > 33% previous -> KEPT
ITERATION 3   gate   0% <= 67% previous -> ROLLED BACK
              the skill reverted; the three wiki pages did not
ITERATION 4   gate 100% > 67% previous -> KEPT
Baseline 0% -> final 100%
```

Iteration 3 is the one to show people. A change is reverted, and `skill-impact.md` records *"do not
propose this again"* — which is what stops the loop oscillating instead of converging.

### Before you point this at real work

- **Check the scoring function first.** `score_one()` is the ground truth the whole loop optimises
  against. If it is wrong, everything above it becomes confidently wrong too.
- **Only use it where the outcome is machine-checkable.** Module structure, export success, citation
  resolution — yes. Pedagogical quality or safety-critical content — no, and no amount of iteration
  changes that.
- **Read the skill before you ship it.** At this layer the instructions the model follows were
  written by a machine and accepted by a score. It is short and in Markdown; it takes two minutes.

---

## UNESCO framework alignment

Layer 5 is **Create**-level work under the UNESCO AI competency framework for teachers (2024),
aspects *AI system design* and *AI for professional learning*: designing a system that accumulates
institutional knowledge, and deciding what it is permitted to change about itself. The rollback gate
and the append-only audit trail are what keep the framework's accountability requirement
satisfiable — every change traces to a proposal, a score and a decision a person can read
afterwards. UNESCO's progression levels are Acquire / Deepen / Create for teachers and Understand /
Apply / Create for students.

It also sharpens the *human-centred mindset* requirement into a question worth asking any vendor:
**who approved the instructions your system is currently following, and when did they last read
them?**

## Sources

- WikiSkill — <https://arxiv.org/abs/2608.27454>
- Meta-Harness (Lee et al., COLM 2026) — <https://yoonholee.com/meta-harness/>
- Learn Harness Engineering — <https://walkinglabs.github.io/learn-harness-engineering/en/>
- UNESCO AI competency frameworks (2024) —
  <https://www.unesco.org/en/articles/ai-competency-framework-teachers>
