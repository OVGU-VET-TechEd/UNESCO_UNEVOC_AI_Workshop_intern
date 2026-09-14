# Makefile — root wrapper.
#
# The package itself lives in unevoc-harness-package/, and that copy is the
# single source of truth (its Makefile has the real recipes). This file exists
# so `make verify` / `make demo` / etc. also work from V4/ without having to
# `cd unevoc-harness-package` first. It does nothing but forward.
#
# Do not duplicate recipes here — edit unevoc-harness-package/Makefile instead,
# this wrapper never goes stale because it has no logic of its own to drift.
#
# Usage:  make help

PKG := unevoc-harness-package

.PHONY: help verify corpus kb eval demo clean package init evolve learn

help verify corpus kb eval demo clean package init evolve learn:
	@$(MAKE) -C $(PKG) $@
