# The parent repository: it pins Core, Memory, Peripherals, TopLevel and Tests, and
# this Makefile runs them together. Each of them has its own Makefile and uv project;
# `git submodule update --init --recursive` first.
SHELL := /bin/bash

SUBREPOS := Core Memory Peripherals TopLevel
GHDL     := ghdl
STD      := --std=08
WDIR     := build/ghdl

.PHONY: all sync check subrepos sim paths clean

all: paths check subrepos sim

sync:
	@set -e; for s in $(SUBREPOS) Tests; do (cd $$s && uv sync -q); done

# ---------------------------------------------------------------
# VHDL syntax check (GHDL), every source of the tree in ONE library: it also catches
# two repositories defining the same entity (as a stale ROM_simulation once did).
# Run with:  make check
# ---------------------------------------------------------------
# 1) All .vhd/.vhdl of the repositories that hold VHDL. The Quartus IPs (Memory/ips)
#    and the PLL need Intel libraries and are left out.
CHECK_SRCS := $(shell find TopLevel/platforms/internal-mem/rtl Memory/sim Peripherals/common Peripherals/GPIO Peripherals/TIMER Core/common Core/I Core/M Core/cores -type f \( -name '*.vhd' -o -name '*.vhdl' \) | sort)

# 2) Dependency order (topological sort, riscv-tools vhdl-sort)
ORDERED_SRCS := $(shell uv run --project Tests riscv-tools vhdl-sort $(CHECK_SRCS))

.PHONY: print-check
print-check:
	@echo "Files the check analyzes:"; echo
	@printf '  %s\n' $(ORDERED_SRCS)

check:
	@echo "Checking VHDL syntax with GHDL..."
	@mkdir -p $(WDIR)
	@rm -rf $(WDIR)/*
	@$(GHDL) -a $(STD) --work=work --workdir=$(WDIR) $(ORDERED_SRCS)
	@echo "VHDL syntax check passed"

# ---------------------------------------------------------------
# Each repository's own checks and tests, at the pinned versions. They find each
# other as siblings (../Core, ../Memory, ...), which is how the submodules sit.
# ---------------------------------------------------------------
subrepos: sync
	$(MAKE) -C Core paths check profiles test
	$(MAKE) -C Memory paths check test
	$(MAKE) -C Peripherals paths check test
	$(MAKE) -C TopLevel all

# ---------------------------------------------------------------
# The Tests project's simulation suite (the 89 programs on the core)
# ---------------------------------------------------------------
sim: sync
	cd Tests && uv run riscv-tools --config tools/riscv_build/config.yaml generate-header \
	  && uv run riscv-tools --config tools/riscv_build/config.yaml compile --emit hex \
	  && uv run riscv-tools --config tools/riscv_build/config.yaml sim

# Every file path the configuration lists exists (paths.yaml).
paths: sync
	cd Tests && uv run riscv-tools --root .. check-paths --manifest paths.yaml

clean:
	rm -rf build
	find . -path ./.git -prune -o -type f \( -name '*.vcd' -o -name '*.ghw' \) -print -delete
