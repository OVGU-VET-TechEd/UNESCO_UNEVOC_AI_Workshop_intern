#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
layer3_harness.py — Layer 3: `make verify`, the real definition of done.

    python layer3_harness.py            # run the nine checks
    python layer3_harness.py --break    # plant an email in the corpus, run, restore

This layer deliberately uses NO model: feedback must come from a command with an
exit code, not from the model's opinion of its own work. --break writes a fake
address into corpus/07_steering_minutes.md for the duration of the run and puts
the original file back afterwards, even if the run is interrupted.
"""

from __future__ import annotations

import os
import re
import subprocess

import layer_common as lc

CORPUS_FILE = os.path.join(lc.ROOT, "part4_unesco_brief", "demo_assistant", "corpus",
                           "07_steering_minutes.md")
PLANTED = "\nContact: maria.sanchez@example-partner.org\n"

# Shown when the [structure]/[agents] checks fail only because the dot-folders
# are absent. That is not a teaching failure but a lost copy of the package.
MISSING_ADAPTERS_HINT = """\
WHY THIS FAILS: the assistant adapters .github/, .continue/ and .vscode/ are
missing from this copy of the package. Folders whose names start with a dot are
hidden in Finder/Explorer and are skipped by GitHub's "Add files via upload".

HOW TO FIX: restore them from the shipped archive (existing files are kept):

    cd V4
    unzip -n unevoc-harness-package.zip 'unevoc-harness-package/.github/*' \\
          'unevoc-harness-package/.continue/*' 'unevoc-harness-package/.vscode/*'

then run this script again. Commit them with `git add .github .continue .vscode`
from a terminal rather than the GitHub web upload, so they are not lost again."""


def run_verify() -> tuple[int, str]:
    result = subprocess.run([lc.python_with_deps(),
                             os.path.join(lc.ROOT, "tools", "verify_package.py")],
                            cwd=lc.ROOT, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def main() -> int:
    args = lc.parse_args(__doc__.splitlines()[1],
                         lambda p: p.add_argument("--break", dest="broken", action="store_true",
                                                  help="plant an unredacted email first"))
    name = "layer3_harness_break" if args.broken else "layer3_harness"
    original = None
    if args.broken:
        original = lc.read(CORPUS_FILE)
        with open(CORPUS_FILE, "a", encoding="utf-8") as handle:
            handle.write(PLANTED)
        print(f"Planted an email address in {os.path.relpath(CORPUS_FILE, lc.ROOT)}\n")
    try:
        code, output = run_verify()
    finally:
        if original is not None:
            with open(CORPUS_FILE, "w", encoding="utf-8") as handle:
                handle.write(original)
            print("(original corpus file restored)\n")
    restored = original is None or lc.read(CORPUS_FILE) == original

    print("$ make verify\n")
    print(output)
    print(f"exit code {code}")

    hint = ""
    if re.search(r"missing (required file: )?\.(github|continue|vscode)", output):
        hint = MISSING_ADAPTERS_HINT
        print(hint)

    body = (f"{'An email address was planted in the corpus before this run (`--break`) and removed afterwards.' if args.broken else 'Unmodified package.'}"
            f"\n\n{lc.fence('$ make verify' + chr(10) + chr(10) + output)}\n\n**Exit code:** {code}\n\n"
            + (f"{hint}\n\n" if hint else "") +
            "No language model was called. That is the lesson of this layer.")
    lc.write_report(f"{name}.md", "Layer 3 — harness: make verify", "none (no model call)", body)
    lc.write_data(name, "none (no model call)", {
        "planted_leak": args.broken,
        "corpus_restored": restored,
        "verify_exit_code": code,
        "checks_ok": re.findall(r"^\s+ok\s+(.*)$", output, re.MULTILINE),
        "failures": re.findall(r"^\s+FAIL\s+(.*)$", output, re.MULTILINE),
        "adapters_missing": bool(hint),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
