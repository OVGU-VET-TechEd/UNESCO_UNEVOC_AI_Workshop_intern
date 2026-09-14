#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kb_build.py — turn a folder of documents into a knowledge base.

    corpus/  ->  kb.json

USAGE
    python kb_build.py                              # keyword retrieval only
    python kb_build.py --embed nomic-embed-text     # also compute embeddings
    python kb_build.py --input corpus --output kb.json

WHAT A KNOWLEDGE BASE IS, IN THIS FILE
    Not a database of facts. Not something the model "learns". It is a list of
    passages, each one small enough to fit in a prompt, each one carrying a label
    saying where it came from. That is all. `kb.json` is plain text — open it.

THE THREE DECISIONS THAT DETERMINE QUALITY
    1. What counts as a passage (chunking). Too big and the model gets padding;
       too small and it gets a sentence with no context. This file splits on
       Markdown headings first, then into overlapping word windows.
    2. What is stored alongside the text (metadata). Without a document name and
       a section title you cannot cite, and an answer you cannot check is not
       useful in an institutional setting.
    3. How a passage is found later (retrieval). See ask.py.

    None of the three involves the language model. This is the point people find
    surprising: most of the quality of a "document assistant" is decided before
    any model is called.

EMBEDDINGS ARE OPTIONAL, ON PURPOSE
    Without --embed, retrieval is keyword-based (BM25) and needs no model at all.
    That is a real, working assistant, and it is often good enough for policy and
    project documents where people search using the document's own vocabulary.
    With --embed, meaning-based retrieval is added and the two are combined.
    Run eval_kb.py both ways and compare — do not take anyone's word for it.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

TARGET_WORDS = 180      # aim for passages of about this many words
OVERLAP_WORDS = 40      # repeat this much of the previous passage, so a sentence
                        # split across a boundary still appears whole somewhere


# ---------------------------------------------------------------------------
# Reading documents
# ---------------------------------------------------------------------------

def read_document(path: str) -> str:
    """Return the plain text of one document. Markdown, text, or PDF."""
    lower = path.lower()
    if lower.endswith((".md", ".txt")):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    if lower.endswith(".pdf"):
        try:
            import pdfplumber
        except ImportError as error:
            raise SystemExit("pdfplumber is needed to read PDFs. "
                             "Run: pip install -r requirements.txt") from error
        parts = []
        with pdfplumber.open(path) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                parts.append(f"## Page {number}")
                parts.append(page.extract_text() or "")
                for table in page.extract_tables() or []:
                    for row in table:
                        cells = [(c or "").replace("\n", " ").strip() for c in row]
                        parts.append(" | ".join(cells))
        return "\n".join(parts)
    return ""


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")


def split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split on Markdown headings. Returns [(section_title, body), ...]."""
    sections: list[tuple[str, list[str]]] = [("(no section)", [])]
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            sections.append((match.group(2).strip(), []))
        else:
            sections[-1][1].append(line)
    return [(title, "\n".join(body).strip())
            for title, body in sections if "\n".join(body).strip()]


def window(body: str, size: int, overlap: int) -> list[str]:
    """Split a section body into overlapping word windows."""
    words = body.split()
    if len(words) <= size:
        return [body.strip()] if body.strip() else []
    chunks, start = [], 0
    step = max(size - overlap, 1)
    while start < len(words):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
        start += step
    return chunks


def chunk_document(doc_name: str, text: str) -> list[dict]:
    """One document -> a list of passages with metadata."""
    title = doc_name
    first_heading = HEADING.match(text.lstrip().splitlines()[0]) if text.strip() else None
    if first_heading:
        title = first_heading.group(2).strip()

    chunks: list[dict] = []
    for section_title, body in split_into_sections(text):
        for piece in window(body, TARGET_WORDS, OVERLAP_WORDS):
            chunks.append({
                "doc": doc_name,          # which file it came from
                "title": title,           # the document's own title
                "section": section_title,  # which section of it
                "text": piece,
                "words": len(piece.split()),
            })
    return chunks


# ---------------------------------------------------------------------------
# Embeddings (optional)
# ---------------------------------------------------------------------------

def embed_texts(model: str, texts: list[str]) -> list[list[float]] | None:
    """Ask Ollama for embeddings. Tries /api/embed, falls back to /api/embeddings."""
    def post(path: str, body: dict) -> dict:
        request = urllib.request.Request(
            f"{OLLAMA_URL}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        result = post("/api/embed", {"model": model, "input": texts})
        if "embeddings" in result:
            return result["embeddings"]
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        pass

    vectors: list[list[float]] = []
    try:
        for text in texts:
            result = post("/api/embeddings", {"model": model, "prompt": text})
            if "embedding" not in result:
                return None
            vectors.append(result["embedding"])
        return vectors
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Build a knowledge base from a folder.")
    parser.add_argument("--input", default=os.path.join(HERE, "corpus"))
    parser.add_argument("--output", default=os.path.join(HERE, "kb.json"))
    parser.add_argument("--embed", metavar="MODEL", default=None,
                        help="embedding model, e.g. nomic-embed-text (optional)")
    args = parser.parse_args()

    if not os.path.isdir(args.input):
        raise SystemExit(f"No folder {args.input}. Run make_corpus.py then anonymise.py, "
                         f"or point --input at your own anonymised documents.")

    files = sorted(f for f in os.listdir(args.input)
                   if f.lower().endswith((".md", ".txt", ".pdf")))
    if not files:
        raise SystemExit(f"No .md, .txt or .pdf files in {args.input}.")

    chunks: list[dict] = []
    for name in files:
        text = read_document(os.path.join(args.input, name))
        produced = chunk_document(name, text)
        for index, chunk in enumerate(produced):
            chunk["id"] = f"{name}#{index:03d}"
        chunks.extend(produced)
        print(f"{name}: {len(produced)} passage(s)")

    embedding_model = None
    if args.embed:
        print(f"\nComputing embeddings with `{args.embed}` ...")
        vectors = embed_texts(args.embed, [c["text"] for c in chunks])
        if vectors is None or len(vectors) != len(chunks):
            print("  Embeddings unavailable. Continuing with keyword retrieval only.")
            print(f"  (Is `{args.embed}` pulled? Try: ollama pull {args.embed})")
        else:
            for chunk, vector in zip(chunks, vectors):
                chunk["embedding"] = vector
            embedding_model = args.embed
            print(f"  {len(vectors)} embeddings of {len(vectors[0])} dimensions.")

    knowledge_base = {
        "built_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "source_folder": os.path.abspath(args.input),
        "documents": files,
        "embedding_model": embedding_model,
        "chunk_target_words": TARGET_WORDS,
        "chunk_overlap_words": OVERLAP_WORDS,
        "chunks": chunks,
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(knowledge_base, handle, indent=1, ensure_ascii=False)

    words = sum(c["words"] for c in chunks)
    print(f"\n{len(chunks)} passages from {len(files)} document(s), {words} words total.")
    print(f"Knowledge base: {args.output}")
    print("Open it. It is plain text — there is nothing hidden in a knowledge base.")
    print("\nNext:  python ask.py \"What evidence counts for quality assurance?\" --model <model>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
