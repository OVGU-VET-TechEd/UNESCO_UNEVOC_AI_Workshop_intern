#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mock_ollama.py — a fake Ollama server for dry-running the demos.

WHY THIS EXISTS
    In a workshop room, some laptops will not have finished pulling a model, and
    some will not have the RAM to run one. This script pretends to be Ollama so
    that the control flow of the demos can still be shown and discussed.

    It is a TEACHING AID, not part of the harness. The answers it returns are
    canned. Nobody should mistake its output for model output.

    It is also how this package was tested: every script in the package was run
    end to end against this server before shipping.

USAGE
    Terminal 1:  python tools/mock_ollama.py
    Terminal 2:  python part2_teaching/file_d_min_harness/min_harness.py --model mock:demo

    Stop it with Ctrl-C.

BEHAVIOUR
    /api/tags      reports two fake models, `mock:demo` and `mock:other`.
    /api/generate  returns a DELIBERATELY BAD answer the first time it sees a
                   given topic and a good answer afterwards — so the verification
                   step visibly rejects something and the retry loop visibly runs.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import socketserver
import sys

# Default is Ollama's own port. Override with MOCK_OLLAMA_PORT when a real Ollama
# is already listening on 11434 — otherwise the bind below fails with
# "Address already in use" and the demos silently talk to the real server.
PORT = int(os.environ.get("MOCK_OLLAMA_PORT", "11434"))
_seen: dict[str, int] = {}

# Canned "good" replies keyed by a distinctive word in the prompt.
GOOD = {
    "hydraulic": "Inspect a hydraulic system for leaks and pressure faults before operation.",
    "circuit": "Identify the main components shown in a standard electrical circuit diagram.",
    "risk": "Assess common hazards in a metal workshop and record the required controls.",
    "summar": ("This document describes workshop safety procedures. It covers pressure "
               "checks, protective equipment and reporting duties for apprentices."),
    "table": '{"metric": "pages", "value": 3}',
}
BAD = "Understanding of the topic, which the learner will come to appreciate over time, is important."

_planner_calls = 0
_rag_calls = 0
_skill_calls = 0


def _rag_reply(prompt: str) -> str:
    """Answer a Part 4 ask.py prompt using the first supplied source.

    Every fourth reply cites a source that was never supplied, so that the
    citation check in ask.py visibly rejects it and the bounded retry runs.
    """
    global _rag_calls
    _rag_calls += 1
    body = ""
    match = re.search(r"^\[S1\] \(from [^\n]*\n(.{0,240})", prompt,
                      re.MULTILINE | re.DOTALL)
    if match:
        body = " ".join(match.group(1).split())[:200]
    if _rag_calls % 4 == 0 and "rejected" not in prompt.lower():
        return f"According to the documents, {body} [S9]"
    return f"According to the documents, {body} [S1]"


# The mock models a skill that improves in stages, so the evolution loop has a
# real gradient to climb and at least one proposal that must be rolled back.
_SKILL_RULES = [
    "- Begin with an approved action verb (identify, inspect, assess, calibrate).",
    "- Use at most twenty words.",
    "- Write exactly one sentence on one line.",
]
_HARMFUL_RULE = "- Add a second sentence giving background context for the learner."


def _skill_reply(prompt: str) -> str:
    """Answer wiki_agent.py prompts: rule extraction, and SKILL.md proposals.

    Proposals get better as the wiki accumulates, except for one deliberately
    harmful proposal so that the validation gate visibly rolls a change back.
    That rollback is the point of the demonstration.
    """
    global _skill_calls
    if "Write ONE imperative rule" in prompt:
        if "action verb" in prompt:
            return "Begin every objective with an approved action verb such as identify or inspect."
        if "limit is" in prompt:
            return "Keep each objective to twenty words or fewer."
        if "sentence" in prompt or "line" in prompt:
            return "Write exactly one sentence on one line, with no list formatting."
        return "Follow the stated output format exactly."

    _skill_calls += 1
    known = 0
    if "action verb" in prompt:
        known = 1
    if "limit is" in prompt or "twenty words" in prompt:
        known = 2
    if "one sentence" in prompt or "more than one sentence" in prompt:
        known = 3
    rules = _SKILL_RULES[:max(known, 1)]
    if _skill_calls == 3:                       # the proposal that must be rejected
        rules = rules + [_HARMFUL_RULE]
    return "# Writing learning objectives\n\n" + "\n".join(rules)


# Each topic "needs" a different number of rules before the mock answers it well,
# which gives the evolution loop a gradient to climb instead of an all-or-nothing
# cliff. The failure it returns is always the one the NEXT missing rule predicts,
# so the Wiki Maintainer has a diagnosable failure mode each iteration.
_TOPIC_DIFFICULTY = {
    "hydraulic": 0, "torque": 0,
    "circuit": 1, "safety data": 1,
    "risk": 2, "protective": 2, "isolation": 2,
}
_GOOD_ANSWER = {
    "hydraulic": "Inspect a hydraulic system for leaks and pressure faults before operation.",
    "circuit": "Identify the main components shown in a standard electrical circuit diagram.",
    "risk": "Assess common hazards in a metal workshop and record the required controls.",
    "protective": "Select appropriate protective equipment for a specified welding process.",
    "torque": "Calibrate a torque wrench against a reference standard and record the result.",
    "safety data": "Interpret a materials safety data sheet to identify required handling controls.",
    "isolation": "Isolate a three-phase supply safely and verify the absence of voltage.",
}


def _objective_reply(prompt: str) -> str:
    """Answer a learning-objective task, obeying whichever rules the skill states."""
    match = re.search(r"^Topic: (.+)$", prompt, re.MULTILINE)
    topic = (match.group(1).strip() if match else "").lower()

    sentence = "Describe the topic clearly for a vocational audience."
    difficulty = 2
    for key, value in _GOOD_ANSWER.items():
        if key in topic:
            sentence, difficulty = value, _TOPIC_DIFFICULTY[key]
            break

    block = re.search(r"Follow this guidance exactly:\n---\n(.*?)\n---", prompt, re.DOTALL)
    skill = block.group(1) if block else ""

    # The harmful rule is obeyed faithfully, and the one-sentence check catches it.
    if "second sentence" in skill:
        return sentence + " This matters for workplace safety."

    level = 0
    if "action verb" in skill:
        level = 1
    if level == 1 and "twenty words" in skill:
        level = 2
    if level == 2 and "one sentence" in skill:
        level = 3

    if difficulty < level:
        return sentence

    if level == 0:      # no verb rule -> opens with a noun
        return ("Understanding of " + (topic or "the topic") + " is something the learner "
                "will come to appreciate over time, and it matters a great deal in practice.")
    if level == 1:      # verb is right, nothing caps length
        return (sentence.rstrip(".") + ", taking into account the full range of workshop "
                "conditions, supervision arrangements and the equipment actually available "
                "on the day of the assessment.")
    if level == 2:      # nothing forbids a second line
        return sentence + "\nRefer to the workshop handbook for further detail."
    return sentence


def _fake_embedding(text: str, dimensions: int = 64) -> list[float]:
    """A deterministic hashed bag-of-words vector.

    This is NOT a semantic embedding. It only lets the embedding code path be
    exercised offline. Similarity between two of these vectors reflects shared
    words, nothing more. Never present it as meaning-based retrieval.
    """
    vector = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        vector[hash(token) % dimensions] += 1.0
    norm = sum(v * v for v in vector) ** 0.5 or 1.0
    return [v / norm for v in vector]


def _planner_reply(prompt: str) -> str:
    """Answer an agent.py planner prompt by reading the state block in the prompt.

    Every third reply is deliberately illegal, so that the harness's override path
    is exercised and visible in agent_log.md. That override is the lesson.
    """
    global _planner_calls
    _planner_calls += 1
    if _planner_calls % 3 == 0:
        return ('{"tool": "write_report", "target": "", '
                '"why": "I think we are probably finished."}')

    if "No PDFs have been listed yet" in prompt:
        return '{"tool": "list_pdfs", "target": "", "why": "Nothing is listed yet."}'

    entries = re.findall(r"^- (\S+\.pdf): (.*)$", prompt, re.MULTILINE)
    for name, done in entries:
        if "converted" not in done:
            return (f'{{"tool": "convert_pdf_to_md", "target": "{name}", '
                    f'"why": "It has not been converted yet."}}')
    for name, done in entries:
        if "summarised" not in done:
            return (f'{{"tool": "summarize_md", "target": "{name}", '
                    f'"why": "It is converted but not summarised."}}')
    for name, done in entries:
        if "tables extracted" not in done:
            return (f'{{"tool": "extract_table_data", "target": "{name}", '
                    f'"why": "Its tables have not been pulled out yet."}}')
    return ('{"tool": "write_report", "target": "", '
            '"why": "Every document is summarised and has table data."}')


def _canned_reply(prompt: str) -> str:
    lowered = prompt.lower()
    for key, reply in GOOD.items():
        if key in lowered:
            count = _seen.get(key, 0)
            _seen[key] = count + 1
            # First time we see this topic: fail verification on purpose.
            # Only do this for the short-objective task, not for summaries.
            if count == 0 and key not in ("summar", "table"):
                return BAD
            return reply
    return "Describe the topic clearly and accurately for a vocational audience."


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 — name fixed by the base class
        if self.path.startswith("/api/tags"):
            self._send({"models": [{"name": "mock:demo"}, {"name": "mock:other"}]})
        else:
            self.send_error(404)

    def do_POST(self):  # noqa: N802 — name fixed by the base class
        length = int(self.headers.get("Content-Length", 0))
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400)
            return
        if self.path.startswith("/api/embed"):
            # Covers both /api/embed (input: list) and /api/embeddings (prompt: str)
            if "input" in request:
                items = request["input"]
                items = items if isinstance(items, list) else [items]
                self._send({"embeddings": [_fake_embedding(t) for t in items]})
            else:
                self._send({"embedding": _fake_embedding(str(request.get("prompt", "")))})
            return
        if self.path.startswith("/api/generate"):
            prompt = request.get("prompt", "")
            if "Available tools:" in prompt:
                self._send({"response": _planner_reply(prompt), "done": True})
                return
            if "Write ONE imperative rule" in prompt or prompt.rstrip().endswith("SKILL.md:"):
                self._send({"response": _skill_reply(prompt), "done": True})
                return
            if "learning objective for a vocational training module." in prompt:
                self._send({"response": _objective_reply(prompt), "done": True})
                return
            if "Sources:" in prompt and "[S1]" in prompt:
                self._send({"response": _rag_reply(prompt), "done": True})
                return
            # If the harness told us why the last answer was rejected, behave.
            if re.search(r"rejected", prompt, re.IGNORECASE):
                for key, reply in GOOD.items():
                    if key in prompt.lower():
                        self._send({"response": reply, "done": True})
                        return
            self._send({"response": _canned_reply(prompt), "done": True})
        else:
            self.send_error(404)

    def log_message(self, *_args):  # keep the console readable
        return


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as server:
            print(f"Mock Ollama listening on http://127.0.0.1:{PORT}  (Ctrl-C to stop)")
            print("This returns CANNED text. It is not a language model.\n")
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
