#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_package.py — root wrapper.

The real checker is unevoc-harness-package/tools/verify_package.py, and that
copy is the single source of truth. It anchors its checks two directories
above itself (tools/ -> package root), so a flat copy of it sitting here at
V4/ root would instead scan V4/'s *parent* folder — silently checking sibling
projects instead of this package. This wrapper just delegates to the real
script in place, so `python3 verify_package.py` (or `make verify`) works
correctly from V4/ too.

Do not duplicate checks here — edit unevoc-harness-package/tools/verify_package.py.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_SCRIPT = os.path.join(HERE, "unevoc-harness-package", "tools", "verify_package.py")

if __name__ == "__main__":
    if not os.path.isfile(REAL_SCRIPT):
        sys.exit(f"Cannot find {REAL_SCRIPT} — is unevoc-harness-package/ present?")
    sys.exit(subprocess.call([sys.executable, REAL_SCRIPT] + sys.argv[1:]))
