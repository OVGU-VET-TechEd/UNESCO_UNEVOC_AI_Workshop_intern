#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anonymise.py — scrub direct identifiers before anything is indexed.

    corpus_raw/  ->  corpus/  +  anonymisation_report.md

USAGE
    python anonymise.py                    # corpus_raw -> corpus
    python anonymise.py --names names.txt  # also redact a list of known names
    python anonymise.py --dry-run          # report what would change, write nothing

WHAT THIS DOES
    Finds and replaces direct identifiers that follow a predictable shape:
    email addresses, telephone numbers, URLs containing a personal handle, IBANs,
    and (optionally) any name you list in a file. Each replacement is a stable
    pseudonym, so the same person is [PERSON_1] in every document and the text
    stays readable.

    It writes a report listing every replacement it made, per document.

WHAT THIS DOES *NOT* DO — read this before using it on real documents
    This is a REDACTION AID, not a compliance tool, and it is not a guarantee.

    1. It cannot find names it has not been told about. "Dr Maria Sanchez"
       is caught only if you pass a names list, or if a title precedes it.
    2. It cannot remove INDIRECT identifiers. "the only female welding
       instructor at partner C" identifies a person perfectly well and contains
       no name at all. No regular expression will ever catch that.
    3. It does not judge sensitivity. A document can be fully de-identified and
       still be one you are not permitted to share.

    The rule this package uses: a human reads the output of the report before the
    corpus is indexed. The scrubber narrows what the human has to look for. It
    does not replace the human.

    For a live session, prefer documents that are already public. Use the scrubber
    on internal documents only when someone with authority over those documents
    has signed off on the result.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "corpus_raw")
OUT_DIR = os.path.join(HERE, "corpus")
REPORT = os.path.join(HERE, "anonymisation_report.md")

# Each rule: (label, compiled pattern). Order matters — emails before URLs, so
# that an address inside a link is caught as an address.
RULES: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}\b")),
    ("PHONE", re.compile(r"(?<![\w.])\+?\d[\d\s().-]{7,}\d(?![\w.])")),
    ("HANDLE", re.compile(r"(?<![\w/])@[A-Za-z][\w.]{2,}\b")),
    # A title followed by capitalised words: catches "Dr Maria Sanchez",
    # "Ms Amina Diallo", "Ing. Tomas Novak". Deliberately conservative, and
    # restricted to spaces and tabs so it can never run across a line break and
    # swallow the next line's first word.
    ("PERSON", re.compile(
        r"\b(?:Dr|Prof|Mr|Mrs|Ms|Mx|Ing|Eng|Sr|Sra|Herr|Frau)\.?[ \t]+"
        r"(?:[A-ZÀ-Þ][\w'’-]+[ \t]+){0,2}[A-ZÀ-Þ][\w'’-]+")),
]


class Pseudonyms:
    """Stable, per-run pseudonyms: the same value always maps to the same token."""

    def __init__(self) -> None:
        self.map: dict[tuple[str, str], str] = {}
        self.counters: dict[str, int] = {}

    def token_for(self, label: str, value: str) -> str:
        key = (label, value.strip())
        if key not in self.map:
            self.counters[label] = self.counters.get(label, 0) + 1
            self.map[key] = f"[{label}_{self.counters[label]}]"
        return self.map[key]


def scrub(text: str, pseudonyms: Pseudonyms,
          names: list[str]) -> tuple[str, list[tuple[str, str, str]]]:
    """Return (scrubbed_text, [(label, original, replacement), ...])."""
    replacements: list[tuple[str, str, str]] = []

    # Explicit name list first: it is the only rule that is actually reliable.
    for name in sorted(names, key=len, reverse=True):
        if not name.strip():
            continue
        pattern = re.compile(r"\b" + re.escape(name.strip()) + r"\b")
        if pattern.search(text):
            token = pseudonyms.token_for("PERSON", name.strip())
            text, count = pattern.subn(token, text)
            if count:
                replacements.append(("PERSON", name.strip(), token))

    for label, pattern in RULES:
        def replace(match: re.Match) -> str:
            original = match.group(0)
            token = pseudonyms.token_for(label, original)
            replacements.append((label, original, token))
            return token
        text = pattern.sub(replace, text)

    return text, replacements


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrub direct identifiers before indexing.")
    parser.add_argument("--input", default=RAW_DIR)
    parser.add_argument("--output", default=OUT_DIR)
    parser.add_argument("--names", help="text file, one name per line, to redact explicitly")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = parser.parse_args()

    if not os.path.isdir(args.input):
        raise SystemExit(f"No input folder {args.input}. Run make_corpus.py first, "
                         f"or point --input at your own documents.")

    names: list[str] = []
    if args.names:
        with open(args.names, "r", encoding="utf-8") as handle:
            names = [line.strip() for line in handle if line.strip()]

    if not args.dry_run:
        os.makedirs(args.output, exist_ok=True)

    pseudonyms = Pseudonyms()
    report_lines = ["# Anonymisation report", "",
                    f"Input: `{args.input}`  →  output: `{args.output}`", "",
                    "Every replacement made is listed below. **A human must read this "
                    "list before the corpus is indexed.** The scrubber narrows what you "
                    "have to look for; it does not replace you. It cannot catch indirect "
                    "identifiers such as \"the only instructor at partner C\".", ""]
    total = 0

    for name in sorted(os.listdir(args.input)):
        source = os.path.join(args.input, name)
        if not os.path.isfile(source):
            continue

        if name.lower().endswith((".md", ".txt")):
            with open(source, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            scrubbed, replacements = scrub(text, pseudonyms, names)
            if not args.dry_run:
                with open(os.path.join(args.output, name), "w", encoding="utf-8") as handle:
                    handle.write(scrubbed)
        elif name.lower().endswith(".pdf"):
            # PDFs are copied through unchanged and flagged loudly: scrubbing a PDF
            # in place is a different job, and a redaction that only hides text
            # visually is not a redaction at all.
            replacements = []
            if not args.dry_run:
                shutil.copy2(source, os.path.join(args.output, name))
            report_lines += [f"## {name}", "",
                             "**Not scrubbed — copied through unchanged.** This is a PDF. "
                             "Convert it to text first, or confirm it is already public.", ""]
            continue
        else:
            continue

        total += len(replacements)
        report_lines.append(f"## {name}")
        report_lines.append("")
        if not replacements:
            report_lines += ["No direct identifiers found. This does **not** mean the "
                             "document is safe to share — check for indirect identifiers "
                             "by reading it.", ""]
        else:
            report_lines += ["| Type | Found | Replaced with |", "|---|---|---|"]
            seen: set[tuple[str, str]] = set()
            for label, original, token in replacements:
                if (label, original) in seen:
                    continue
                seen.add((label, original))
                report_lines.append(f"| {label} | `{original}` | `{token}` |")
            report_lines.append("")
        print(f"{name}: {len(replacements)} replacement(s)")

    report_lines += ["---", "",
                     f"**{total} replacement(s) across the corpus.**", "",
                     "Reminder of the limits: this tool finds identifiers with a "
                     "predictable shape. It cannot find names it was not given, and it "
                     "cannot find indirect identifiers at all.", ""]

    if args.dry_run:
        print("\n--dry-run: nothing was written.")
    else:
        with open(REPORT, "w", encoding="utf-8") as handle:
            handle.write("\n".join(report_lines))
        print(f"\nScrubbed corpus: {args.output}")
        print(f"Report:          {REPORT}   <- read this before indexing")
        print("\nNext:  python kb_build.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
