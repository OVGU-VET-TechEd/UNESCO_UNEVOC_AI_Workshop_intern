# Agent pipelines: policy_summary (map-reduce + validation loop) and summary_review.
from harness.agents import fill, read_prompt
from harness.pdf_text import chunk_text, clean_text, extract_pages, join_pages, select_chunks
from harness.validate import (check_summary_text, extract_json, normalise_payload, strip_think,
                              trim_to_limit, word_count)


class SkipFile(Exception):
    pass


def _feedback(errors, data, max_words):
    lines = ["Your previous answer cannot be accepted:"]
    lines += ["- " + e for e in errors]
    if data and data.get("summary"):
        lines.append("The summary currently has %d words; the limit is %d words." % (word_count(data["summary"]), max_words))
    lines.append("Return the corrected JSON object only, with the same keys. Keep all facts from the document; "
                 "shorten by removing detail, not by adding abbreviations.")
    return "\n".join(lines)


class Summarizer:
    def __init__(self, agent, backend, rules, verbose=True):
        self.agent = agent
        self.backend = backend
        self.rules = rules
        self.verbose = verbose
        self.max_words = int(agent.get("max_words", 80))
        self.max_retries = int(agent.get("max_retries", 3))
        self.temperature = float(agent.get("temperature", 0.1))
        self.chunk_chars = int(agent.get("chunk_chars", 6000))
        self.max_chunks = int(agent.get("max_chunks", 20))
        self.map_template = read_prompt(agent, "map_prompt", "prompts/map-step.md")
        self.reduce_template = read_prompt(agent, "reduce_prompt", "prompts/reduce-step.md")

    def _say(self, message):
        if self.verbose:
            print(message, flush=True)

    def _system(self):
        return {"role": "system", "content": self.agent.system_prompt}

    def _material(self, text):
        limit = int(self.chunk_chars * 1.5)
        if len(text) <= limit:
            return text, "full document text", 0
        current, passes, calls = text, 0, 0
        while len(current) > limit and passes < 3:
            passes += 1
            chunks = select_chunks(chunk_text(current, self.chunk_chars), self.max_chunks)
            notes = []
            for index, chunk in enumerate(chunks, 1):
                self._say("    reading part %d/%d (pass %d)" % (index, len(chunks), passes))
                prompt = fill(self.map_template, PART=index, TOTAL=len(chunks), TEXT=chunk)
                answer = strip_think(self.backend.chat([self._system(), {"role": "user", "content": prompt}],
                                                       json_mode=False, temperature=self.temperature)).strip()
                calls += 1
                if answer and "no relevant content" not in answer.lower()[:60]:
                    notes.append("[Part %d]\n%s" % (index, answer))
            condensed = "\n\n".join(notes) or current[:limit]
            if len(condensed) >= len(current):
                current = condensed[:limit]
                break
            current = condensed
        material = "FIRST PAGE OF THE DOCUMENT:\n%s\n\nNOTES FROM THE WHOLE DOCUMENT:\n%s" % (text[:1500], current[:limit])
        return material, "first page plus factual notes extracted from the whole document", calls

    def summarize(self, pdf_path):
        pages = extract_pages(pdf_path)
        text = clean_text(join_pages(pages))
        min_chars = int(self.agent.get("min_text_chars", 300))
        if len(text) < min_chars:
            raise SkipFile("only %d characters of text found - probably a scanned PDF; run OCR first" % len(text))
        self._say("    %d pages, %d characters" % (len(pages), len(text)))
        material, material_type, map_calls = self._material(text)
        prompt = fill(self.reduce_template, MAX_WORDS=self.max_words, FILENAME=pdf_path.name,
                      MATERIAL_TYPE=material_type, TEXT=material)
        messages = [self._system(), {"role": "user", "content": prompt}]
        best = None
        info = {"pages": len(pages), "chars": len(text), "material": material_type, "map_calls": map_calls}
        for attempt in range(1, self.max_retries + 2):
            raw = self.backend.chat(messages, json_mode=True, temperature=self.temperature)
            try:
                data, errors, warnings = normalise_payload(extract_json(raw), self.max_words, self.rules)
            except ValueError as exc:
                data, errors, warnings = None, [str(exc)], []
            if data is not None and not errors:
                info.update({"data": data, "status": "ok", "attempts": attempt, "warnings": warnings, "errors": []})
                return info
            if data is not None:
                best = (data, errors, warnings)
            self._say("    attempt %d rejected: %s" % (attempt, "; ".join(errors)))
            messages.append({"role": "assistant", "content": strip_think(raw)[:4000]})
            messages.append({"role": "user", "content": _feedback(errors, data, self.max_words)})
        if best is None:
            raise ValueError("no valid JSON after %d attempts" % (self.max_retries + 1))
        data, errors, warnings = best
        data["summary"], trim_mode = trim_to_limit(data["summary"], self.max_words)
        remaining, warnings2 = check_summary_text(data["summary"], self.max_words, self.rules)
        status = "needs_review" if remaining or trim_mode == "hard" else ("auto_trimmed" if trim_mode else "needs_review")
        info.update({"data": data, "status": status, "attempts": self.max_retries + 1,
                     "warnings": warnings + warnings2, "errors": remaining})
        return info


class Reviewer:
    def __init__(self, agent, backend, rules):
        self.agent = agent
        self.backend = backend
        self.rules = rules
        self.max_words = int(agent.get("max_words", 80))
        self.template = read_prompt(agent, "review_prompt", "prompts/review-step.md")

    def review(self, summary):
        prompt = fill(self.template, MAX_WORDS=self.max_words, WORD_COUNT=word_count(summary), TEXT=summary)
        raw = self.backend.chat([{"role": "system", "content": self.agent.system_prompt},
                                 {"role": "user", "content": prompt}],
                                json_mode=True, temperature=float(self.agent.get("temperature", 0.0)))
        obj = extract_json(raw)
        rule_errors, rule_warnings = check_summary_text(summary, self.max_words, self.rules)
        issues = obj.get("issues") or []
        if isinstance(issues, str):
            issues = [issues]
        return {
            "model_neutral": bool(obj.get("neutral", False)),
            "model_issues": [str(i) for i in issues],
            "suggested_revision": str(obj.get("suggested_revision") or "").strip(),
            "rule_errors": rule_errors,
            "rule_warnings": rule_warnings,
        }
