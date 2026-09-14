#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ask.py — the assistant. Ask a question, get an answer with citations, or a refusal.

USAGE
    python ask.py "What evidence counts for quality assurance?" --model llama3.1:8b
    python ask.py "How many learners completed at partner B?" --model qwen2.5:7b --show-sources
    python ask.py "What is the capital of Peru?" --model llama3.1:8b     # -> refusal

WHAT THIS IS
    A retrieval-augmented assistant. Three steps, in this order:

        1  RETRIEVE   find the passages in kb.json most likely to answer the question
        2  GROUND     put those passages in the prompt, numbered, and forbid
                      anything not in them
        3  VERIFY     check the answer only cites sources that were actually
                      supplied; retry once if not; refuse if it still fails

    Step 2 is the model. Steps 1 and 3 are the harness, and they are what makes
    the difference between a demo and something an institution can use.

THE REFUSAL IS A FEATURE
    If the best retrieved passage scores below MIN_RETRIEVAL_SCORE, this program
    does not call the model at all. It says it has nothing relevant and stops.
    An assistant that always produces an answer is not an assistant; it is a
    hazard. Ask it something outside the corpus and watch it decline.

EVERY RUN IS LOGGED
    ask_log.md records the question, which passages were retrieved and with what
    score, which model was used, whether verification passed, and the final
    answer. This is what makes an answer auditable after the fact.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
KB_PATH = os.path.join(HERE, "kb.json")
LOG_PATH = os.path.join(HERE, "ask_log.md")

TOP_K = 4                      # how many passages go into the prompt
MIN_RETRIEVAL_SCORE = 5.0      # below this, refuse without calling the model
MIN_TERM_COVERAGE = 0.55       # ...and at least this share of the question's
                               #    content words must actually appear in them
MAX_ATTEMPTS = 2               # bounded retry on a failed citation check

# BOTH thresholds above are corpus-specific. They are tuned for the eight-document
# demo corpus. When you point this at your own documents, re-tune them with
# eval_kb.py: raise them until the questions that should be refused are refused,
# then lower them until the questions that should be answered are answered again.
# If no setting satisfies both, that is a real finding — usually it means the
# corpus does not actually cover what people want to ask.

# Words too common to tell us anything about whether a passage is relevant.
STOPWORDS = set(
    "a an the of to in on for and or is are was were be been being do does did "
    "can could should would will shall may might must what which who whom whose "
    "how why when where that this these those it its as at by with from into "
    "our we you they i not no any all some more most other such than then there "
    "about after before during over under between per".split()
)


# ===========================================================================
# 1. RETRIEVE — no language model is involved in this section
# ===========================================================================

TOKEN = re.compile(r"[a-z0-9]+")


def tokenise(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def content_terms(question: str) -> list[str]:
    """The words in a question that carry meaning. No model involved."""
    return [t for t in tokenise(question) if t not in STOPWORDS and len(t) > 2]


def term_coverage(question: str, passages: list[dict]) -> float:
    """What share of the question's content words appear in the retrieved text?

    This is the most interpretable signal available for "did we find anything
    relevant". A question about the capital of Peru scores near zero against a
    corpus of TVET policy documents, and that is exactly when the assistant
    should decline instead of inventing.
    """
    terms = content_terms(question)
    if not terms:
        return 0.0
    blob = " ".join((p["text"] + " " + p["section"] + " " + p["title"]).lower()
                    for p in passages)
    return sum(1 for term in terms if term in blob) / len(terms)

REFUSAL = ("I could not find anything in the knowledge base that answers this. "
           "Nothing has been made up. Either the documents do not cover it, or "
           "the question uses different words than the documents do.")


class Bm25:
    """Classic keyword ranking. Readable on purpose — this is not a black box.

    A passage scores highly when it contains the question's rare words often,
    adjusted so that long passages do not win merely by being long.
    """

    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1, self.b = k1, b
        self.lengths = [len(d) for d in documents]
        self.average_length = sum(self.lengths) / max(len(documents), 1)
        self.frequencies = [Counter(d) for d in documents]
        document_frequency: Counter = Counter()
        for document in documents:
            document_frequency.update(set(document))
        total = len(documents)
        self.idf = {
            term: math.log(1 + (total - count + 0.5) / (count + 0.5))
            for term, count in document_frequency.items()
        }

    def score(self, query_terms: list[str]) -> list[float]:
        scores = []
        for index, frequency in enumerate(self.frequencies):
            length = self.lengths[index]
            total = 0.0
            for term in query_terms:
                if term not in frequency:
                    continue
                count = frequency[term]
                numerator = count * (self.k1 + 1)
                denominator = count + self.k1 * (
                    1 - self.b + self.b * length / max(self.average_length, 1))
                total += self.idf.get(term, 0.0) * numerator / denominator
            scores.append(total)
        return scores


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def embed_query(model: str, text: str) -> list[float] | None:
    """Embed the question with the same model used to build the knowledge base."""
    def post(path: str, body: dict) -> dict:
        request = urllib.request.Request(
            f"{OLLAMA_URL}{path}", data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    try:
        result = post("/api/embed", {"model": model, "input": [text]})
        if "embeddings" in result:
            return result["embeddings"][0]
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        pass
    try:
        result = post("/api/embeddings", {"model": model, "prompt": text})
        return result.get("embedding")
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def retrieve(kb: dict, question: str, top_k: int = TOP_K) -> list[dict]:
    """Return the top passages, each with its score and how it was found.

    Keyword ranking always runs. If the knowledge base has embeddings, meaning
    ranking runs too, and the two rankings are merged by reciprocal rank fusion:
    a passage that both methods place near the top wins over one that only a
    single method loves.
    """
    chunks = kb["chunks"]
    keyword = Bm25([tokenise(c["text"] + " " + c["section"] + " " + c["title"])
                    for c in chunks])
    keyword_scores = keyword.score(tokenise(question))

    order_keyword = sorted(range(len(chunks)), key=lambda i: -keyword_scores[i])
    fused = {i: 1.0 / (60 + rank) for rank, i in enumerate(order_keyword)}
    method = "keyword"

    if kb.get("embedding_model"):
        vector = embed_query(kb["embedding_model"], question)
        if vector:
            similarity = [cosine(vector, c.get("embedding", [])) for c in chunks]
            order_meaning = sorted(range(len(chunks)), key=lambda i: -similarity[i])
            for rank, i in enumerate(order_meaning):
                fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
            method = "keyword + meaning"

    best = sorted(fused, key=lambda i: -fused[i])[:top_k]
    return [{
        "rank": position + 1,
        "score": round(keyword_scores[i], 2),   # the reported score stays interpretable
        "method": method,
        **chunks[i],
    } for position, i in enumerate(best)]


# ===========================================================================
# 2. GROUND — build the prompt. This is the only model call.
# ===========================================================================

def build_prompt(question: str, passages: list[dict], complaint: str | None) -> str:
    sources = "\n\n".join(
        f"[S{index}] (from {p['doc']}, section \"{p['section']}\")\n{p['text']}"
        for index, p in enumerate(passages, start=1)
    )
    prompt = (
        "Answer the question using ONLY the sources below.\n\n"
        "Rules:\n"
        "1. Use only information that appears in the sources. Do not add anything else.\n"
        f"2. Cite every claim with a marker like [S1]. Only S1 to S{len(passages)} exist.\n"
        "3. If the sources do not answer the question, reply with exactly: "
        "INSUFFICIENT_EVIDENCE\n"
        "4. Answer in 2 to 4 sentences. No preamble, no headings.\n\n"
        f"Sources:\n{sources}\n\n"
        f"Question: {question}\n\n"
    )
    if complaint:
        prompt += ("Your previous answer was rejected for this reason:\n"
                   f"  {complaint}\nCorrect it.\n\n")
    return prompt + "Answer:"


def call_ollama(model: str, prompt: str, num_predict: int = 260) -> str:
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0.1, "num_predict": num_predict},
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=payload,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8")).get("response", "").strip()


# ===========================================================================
# 3. VERIFY — the harness checking the answer before anyone sees it
# ===========================================================================

CITATION = re.compile(r"\[S(\d+)\]")


def verify_answer(answer: str, passage_count: int) -> tuple[bool, str]:
    """Three checks, none of which involve a model."""
    if not answer.strip():
        return False, "the answer was empty"
    cleaned = answer.strip().upper()
    # Treat this as a refusal only when it IS the answer, not when the phrase merely
    # appears somewhere inside a longer reply — models often echo the instruction.
    if cleaned.startswith("INSUFFICIENT_EVIDENCE") or (
            len(cleaned) < 60 and "INSUFFICIENT_EVIDENCE" in cleaned):
        return True, "the model declared the evidence insufficient, which is allowed"

    cited = [int(n) for n in CITATION.findall(answer)]
    if not cited:
        return False, ("it cited no sources; every claim must carry a marker "
                       "such as [S1]")
    invented = sorted({n for n in cited if n < 1 or n > passage_count})
    if invented:
        return False, (f"it cited source(s) that were not supplied: "
                       f"{', '.join(f'[S{n}]' for n in invented)}; only S1 to "
                       f"S{passage_count} exist")
    return True, f"cited {len(set(cited))} of {passage_count} supplied sources"


# ===========================================================================
# The pipeline, reusable by eval_kb.py
# ===========================================================================

def answer_question(kb: dict, question: str, model: str,
                    top_k: int = TOP_K, log=None) -> dict:
    """Run the full pipeline once. Returns a result dictionary."""
    def note(line: str) -> None:
        if log is not None:
            log.append(line)

    passages = retrieve(kb, question, top_k)
    best = passages[0]["score"] if passages else 0.0
    coverage = term_coverage(question, passages)
    note(f"Retrieved {len(passages)} passage(s); best keyword score {best:.2f}, "
         f"question-term coverage {coverage:.0%} "
         f"({passages[0]['method'] if passages else 'n/a'} retrieval).")

    # --- the retrieval gate: refuse BEFORE spending a model call ------------
    # Two conditions, both cheap and both explainable to a non-programmer:
    # something scored well enough, AND the question's own words actually turn up
    # in what was found.
    if not passages or best < MIN_RETRIEVAL_SCORE or coverage < MIN_TERM_COVERAGE:
        why = ("nothing scored above the threshold of "
               f"{MIN_RETRIEVAL_SCORE}" if best < MIN_RETRIEVAL_SCORE else
               f"only {coverage:.0%} of the question's key words appear in what was "
               f"found, below the {MIN_TERM_COVERAGE:.0%} threshold")
        note(f"Retrieval gate: {why}. **Refusing without calling the model.**")
        return {"question": question, "status": "refused_no_evidence",
                "answer": REFUSAL, "passages": passages, "model": model,
                "attempts": 0}

    complaint = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        note(f"Attempt {attempt}: asking `{model}` with {len(passages)} sources.")
        try:
            raw = call_ollama(model, build_prompt(question, passages, complaint))
        except urllib.error.URLError as error:
            note(f"Could not reach Ollama at {OLLAMA_URL}: {error}")
            return {"question": question, "status": "error", "answer": REFUSAL,
                    "passages": passages, "model": model, "attempts": attempt}

        ok, reason = verify_answer(raw, len(passages))
        if ok and "insufficient" in reason:
            note("The model reported insufficient evidence. Passing that through "
                 "unchanged rather than pressing it for an answer.")
            return {"question": question, "status": "refused_by_model",
                    "answer": REFUSAL, "passages": passages, "model": model,
                    "attempts": attempt}
        if ok:
            note(f"Verification passed: {reason}.")
            return {"question": question, "status": "answered", "answer": raw,
                    "passages": passages, "model": model, "attempts": attempt}

        note(f"**Verification failed:** {reason}. Re-asking with that reason attached.")
        complaint = reason

    note(f"Verification failed {MAX_ATTEMPTS} times. **Refusing** rather than "
         f"showing an answer whose citations do not check out.")
    return {"question": question, "status": "refused_failed_verification",
            "answer": REFUSAL, "passages": passages, "model": model,
            "attempts": MAX_ATTEMPTS}


def load_kb(path: str = KB_PATH) -> dict:
    if not os.path.exists(path):
        raise SystemExit(f"No knowledge base at {path}. Run kb_build.py first.")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# ===========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Ask the knowledge base a question.")
    parser.add_argument("question", nargs="+")
    parser.add_argument("--model", required=True, help="Ollama model tag")
    parser.add_argument("--kb", default=KB_PATH)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--show-sources", action="store_true",
                        help="print the retrieved passages in full")
    args = parser.parse_args()

    question = " ".join(args.question)
    kb = load_kb(args.kb)

    log: list[str] = []
    result = answer_question(kb, question, args.model, args.top_k, log)

    print(f"\nQ: {question}\n")
    print(result["answer"])
    print()
    if result["status"] == "answered":
        print("Sources used:")
        for passage in result["passages"]:
            print(f"  [S{passage['rank']}] {passage['doc']} — "
                  f"\"{passage['section']}\" (score {passage['score']})")
    if args.show_sources:
        print("\n--- retrieved passages in full ---")
        for passage in result["passages"]:
            print(f"\n[S{passage['rank']}] {passage['doc']} / {passage['section']} "
                  f"(score {passage['score']})\n{passage['text']}")

    with open(LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(f"\n## {_dt.datetime.now():%Y-%m-%d %H:%M:%S} — {question}\n\n")
        handle.write(f"Model: `{args.model}` · knowledge base: `{os.path.basename(args.kb)}` "
                     f"· embeddings: `{kb.get('embedding_model') or 'none'}`\n\n")
        for line in log:
            handle.write(f"- {line}\n")
        handle.write("\nPassages retrieved:\n\n")
        for passage in result["passages"]:
            handle.write(f"- `[S{passage['rank']}]` {passage['doc']} / "
                         f"{passage['section']} (score {passage['score']})\n")
        handle.write(f"\n**Status:** {result['status']} after "
                     f"{result['attempts']} model call(s).\n\n")
        handle.write(f"**Answer given to the user:**\n\n> "
                     f"{result['answer'].replace(chr(10), chr(10) + '> ')}\n")

    print(f"\nLog: {LOG_PATH}")
    return 0 if result["status"] == "answered" else 0


if __name__ == "__main__":
    raise SystemExit(main())
