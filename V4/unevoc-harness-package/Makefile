# Makefile — the verification commands, in one place.
#
# Every agent surface (Copilot, Continue, Claude Code, a human) runs these same
# targets. That is the point: one definition of done, not four.
#
# Usage:  make help

PY        ?= python3
DEMO      ?= part4_unesco_brief/demo_assistant
MODEL     ?= mock:demo
# The mock runs on its own port, not Ollama's 11434, so the mock-backed targets
# work even when a real Ollama is already running on this machine.
MOCK_PORT ?= 11435
MOCK      := $(PY) tools/mock_ollama.py

# WITH_MOCK — shell preamble shared by demo / eval / evolve. When MODEL is a
# mock:* name it starts tools/mock_ollama.py on MOCK_PORT, points OLLAMA_URL at
# it, waits until it actually answers (failing loudly if it never does), and
# arranges to kill it on exit. For a real MODEL it is a no-op, so
# `make eval MODEL=llama3.1:8b` still talks to the real Ollama on 11434.
# Collapses to a single logical line so it can be dropped into a recipe.
WITH_MOCK = set -e; MOCK_PID=""; \
	case "$(MODEL)" in \
	  mock:*) \
	    MOCK_OLLAMA_PORT=$(MOCK_PORT) $(MOCK) > /tmp/unevoc-mock.log 2>&1 & \
	    MOCK_PID=$$!; \
	    export OLLAMA_URL=http://127.0.0.1:$(MOCK_PORT); \
	    n=0; \
	    until $(PY) -c "import sys,urllib.request; sys.exit(0 if b'mock:' in urllib.request.urlopen('$$OLLAMA_URL/api/tags', timeout=1).read() else 1)" 2>/dev/null; do \
	      n=$$((n+1)); \
	      if [ $$n -ge 20 ]; then \
	        echo "ERROR: the mock server is not answering on port $(MOCK_PORT)."; \
	        echo "(If a real Ollama already owns that port, pick another: MOCK_PORT=11500)"; \
	        echo "--- /tmp/unevoc-mock.log ---"; cat /tmp/unevoc-mock.log; \
	        kill $$MOCK_PID 2>/dev/null || true; \
	        exit 1; \
	      fi; \
	      sleep 0.5; \
	    done; \
	    echo "mock server up on $$OLLAMA_URL (canned responses)"; \
	    ;; \
	esac; \
	trap 'if [ -n "$$MOCK_PID" ]; then kill "$$MOCK_PID" 2>/dev/null || true; fi' EXIT

.PHONY: help verify corpus kb eval demo clean package init evolve learn

help:
	@echo "make init      one-time: create venv, install deps, build corpus + kb"
	@echo "make verify    THE definition of done. Exits non-zero on failure."
	@echo "make corpus    regenerate corpus_raw/ and re-run the anonymiser"
	@echo "make kb        rebuild kb.json from corpus/"
	@echo "make eval      run the assistant against the fixed question set"
	@echo "make demo      end-to-end smoke test of Parts 2-4 against the mock server"
	@echo "make package   clean-room rebuild + zip into dist/"
	@echo "make evolve    layer 5: the agent writes its own skill file"
	@echo "make learn     open the interactive six-layer page"
	@echo "make clean     remove generated artefacts"
	@echo ""
	@echo "Override the model:  make eval MODEL=llama3.1:8b"
	@echo "demo/eval/evolve auto-start the mock for a mock:* MODEL (default)."
	@echo "If port $(MOCK_PORT) is taken:  make demo MOCK_PORT=11500"

verify:
	@$(PY) tools/verify_package.py

corpus:
	@cd $(DEMO) && $(PY) make_corpus.py && $(PY) anonymise.py
	@echo ""
	@echo ">>> Now READ $(DEMO)/anonymisation_report.md before running 'make kb'."

kb:
	@cd $(DEMO) && $(PY) kb_build.py

eval:
	@$(WITH_MOCK); \
	( cd $(DEMO) && $(PY) eval_kb.py --model $(MODEL) )

# Starts the mock server, exercises every runnable component, stops the server.
# Runs in seconds and needs no model, so it is safe in CI and on a workshop laptop.
demo:
	@$(WITH_MOCK); \
	echo "--- Part 2: minimal harness ---"; \
	$(PY) part2_teaching/file_d_min_harness/min_harness.py --model $(MODEL) --reset; \
	echo "--- Part 3: semi-agent ---"; \
	( cd part3_worked_example && $(PY) make_sample_pdfs.py >/dev/null && \
	  $(PY) semi_agent.py --model $(MODEL) --yes >/dev/null ); \
	echo "--- Part 3: agent ---"; \
	( cd part3_worked_example && $(PY) agent.py --model $(MODEL) --reset >/dev/null ); \
	echo "--- Part 4: assistant eval ---"; \
	( cd $(DEMO) && $(PY) eval_kb.py --model $(MODEL) | tail -4 ); \
	echo "--- Part 5: self-improving agent ---"; \
	( cd part5_self_improving && $(PY) wiki_agent.py --model $(MODEL) --reset --iterations 5 \
	  | grep -E "ITERATION|gate|Baseline" )
	@echo ""
	@echo "Smoke test complete. Output was CANNED (mock server) - not model output."

evolve:
	@$(WITH_MOCK); \
	( cd part5_self_improving && $(PY) wiki_agent.py --model $(MODEL) --reset )

# Opens in the default browser. The page is self-contained: no server needed.
learn:
	@$(PY) -c "import webbrowser,os; webbrowser.open('file://'+os.path.abspath('part5_self_improving/LEARN_the_five_layers.html'))"
	@echo "Opened part5_self_improving/LEARN_the_five_layers.html"

# Note: $(notdir $(CURDIR)) is NOT used here. Make's notdir/dir/wildcard
# functions treat their argument as a space-separated list of words, so on any
# checkout path containing a space (this one has "Tegelbeckers Hannes") it
# silently splits CURDIR into two bogus "files" and zip fails with
# "Nothing to do!". $(shell basename ...) hands the whole path to a real
# shell, which quotes it correctly regardless of spaces.
PKG_NAME := $(shell basename "$(CURDIR)")

package: clean verify
	@mkdir -p dist
	@cd .. && zip -qr "$(CURDIR)/dist/unevoc-harness-package.zip" \
	  "$(PKG_NAME)" -x '*/dist/*' '*/__pycache__/*' '*/.venv/*'
	@echo "dist/unevoc-harness-package.zip"

clean:
	@rm -rf part3_worked_example/output_semi part3_worked_example/output_agent
	@rm -f  part2_teaching/file_d_min_harness/harness_state.json
	@rm -f  part2_teaching/file_d_min_harness/harness_log.md
	@rm -f  $(DEMO)/ask_log.md $(DEMO)/eval_report.md $(DEMO)/kb_embed.json
	@rm -rf part5_self_improving/workspace
	@find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Generated artefacts removed. corpus/ and kb.json kept - rebuild with 'make corpus kb'."

init:
	@$(PY) -m venv .venv
	@./.venv/bin/pip install -q --upgrade pip
	@./.venv/bin/pip install -q -r part3_worked_example/requirements.txt
	@$(MAKE) corpus kb verify
	@echo ""
	@echo "Ready. Activate with:  source .venv/bin/activate"
