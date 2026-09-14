# File D — The minimal harness

One Python file, standard library only, under two minutes on a laptop CPU.

It asks a local model to write one learning objective for each of three TVET topics, and then
**checks each answer against three rules a human wrote in advance**:

1. it must start with an approved action verb (identify, describe, demonstrate, …),
2. it must be at most 20 words,
3. it must be exactly one sentence.

If an answer fails, the harness re-asks — telling the model precisely which rule it broke — up to
three times, and then gives up and says so.

## Run it

```bash
ollama serve                                   # if it isn't already running
python min_harness.py --list-models            # what is installed here?
python min_harness.py --model llama3.1:8b
python min_harness.py --model qwen2.5:7b       # switch models with one flag
python min_harness.py --model qwen2.5:7b --reset
```

Run it a second time without `--reset` and it skips everything already accepted. That is the state
file doing its job.

No model installed? Start `../../tools/mock_ollama.py` in another terminal and use
`--model mock:demo`. It returns canned text — a teaching aid, not a language model.

## The four parts, and where they are in the file

| Part | Function | File it writes |
|---|---|---|
| **State** — memory that survives the program exiting | `load_state()` / `save_state()` | `harness_state.json` |
| **Verification** — the rules the answer must satisfy | `verify()` | — |
| **Bounded retry** — never infinite | `process_topic()`, `MAX_ATTEMPTS = 3` | — |
| **Log** — every attempt, in plain sentences | `log()` | `harness_log.md` |
| *the model call* | `call_ollama()` | — |

`call_ollama()` is about fifteen lines. Everything else in the file is harness. Notice also that
`verify()` contains no AI at all: it is ordinary, boring, readable code, and that is exactly why it
can be trusted to judge the model's output.

Two details worth pointing out in a session:

- **The retry is not a repeat.** `build_prompt()` puts the specific failure reason into the next
  prompt. A retry loop that just asks again is a slot machine.
- **The script's exit code is 0 only if every topic succeeded**, so this file can itself be used as
  the verification command inside a larger harness.

## What to change first

Everything a facilitator needs to edit is in the CONFIGURATION block at the top: `DEFAULT_MODEL`,
`MAX_ATTEMPTS`, `TOPICS`, `ALLOWED_VERBS`, `MAX_WORDS`. Swapping `TOPICS` for topics from your own
department takes about a minute and makes the demo land much harder.

## UNESCO alignment

The `verify()` function and `harness_log.md` are this package's most direct answer to the UNESCO AI
competency framework for teachers' emphasis on transparency and on the critical evaluation of AI
output: the verification step means nothing is accepted on the model's own say-so, and the log means
a colleague who does not read Python can still reconstruct what happened and why. Building a
verification rule for your own subject area is *Create*-level work under that framework (aspects: AI
foundations and applications; AI pedagogy). UNESCO's progression labels are Acquire / Deepen /
Create for teachers and Understand / Apply / Create for students.
