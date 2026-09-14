# Checklist — session readiness

Complete on the machine that will be used in the room, the day before.

## The machine

- [ ] Ollama is installed and the service responds on `127.0.0.1:11434`
- [ ] **Both** models are pulled and appear in `ollama list`
- [ ] The venv exists and `pip install -r requirements.txt` completed
- [ ] `make verify` exits 0
- [ ] `make demo` completes
- [ ] `make eval MODEL=<real model>` completes — **not the mock**; this is what proves the model works
- [ ] First inference has been run once already, so the model is warm and the room does not watch a 90-second load

## The material

- [ ] The LiaScript deck renders at liascript.github.io
- [ ] The cheatsheet is printed, one A4 sheet both sides
- [ ] `kb.json` opens in an editor and is readable on the projector at a legible font size
- [ ] The two demonstration questions have been run and behave as expected — one answers with
      citations, one refuses

## The documents

- [ ] The corpus in use is the synthetic demo corpus, **or** every document in it has been
      cleared by a named owner
- [ ] `anonymisation_report.md` has been read by a human, and that human is in the room
- [ ] No PDF in the corpus went unscrubbed

## Fallbacks

- [ ] `tools/mock_ollama.py` is tested, in case a laptop cannot host a model
- [ ] A pre-generated `agent_log.md` and `eval_report.md` exist, in case a live run fails
- [ ] Someone other than the presenter can drive the terminal

**If the model checks fail and cannot be fixed:** run the session on the mock server and say so
clearly and repeatedly. Canned output presented as model output would undo the whole point of the
session.
