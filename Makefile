# Make sure /bin/bash is used for the 'find' in clean
SHELL := /bin/bash

.PHONY: test run clean

# Run all tests (no args). Test code itself lives in the Tests
# submodule (insper-riscv/RISC-V-Workstation-Tests), not here — run
# `git submodule update --init --recursive` first if Tests/ is empty.
test:
	cd Tests && uv run python tests/python/runner.py

# Run a single test by name
# Usage: make run TEST=<test_name>
run:
ifndef TEST
	$(error Usage: make run TEST=<test_name>)
endif
	cd Tests && uv run python tests/python/runner.py $(TEST)

# Remove generated waveforms
clean:
	find . -type f \( -name '*.vcd' -o -name '*.ghw' \) -print -delete


# ---------------------------------------------------------------
# VHDL Syntax Check (GHDL)
# Run with:  make check
# ---------------------------------------------------------------
GHDL := ghdl
STD  := --std=08
WDIR := build/ghdl

# 1) Coleta todos .vhd/.vhdl
# The core's VHDL lives in the Core submodule, the simulation memories in Memory,
# the peripherals in Peripherals and the simulation top in TopLevel.
CHECK_SRCS_ALL := $(shell find TopLevel/platforms/internal-mem/rtl Memory/sim Peripherals/common Peripherals/GPIO Peripherals/TIMER Core/common Core/I Core/M Core/cores -type f \( -name '*.vhd' -o -name '*.vhdl' \) | sort)

# 2) Nothing to exclude: the Quartus IPs (Memory/ips, which need Intel libraries) and the
# PLL are not in the list above.
CHECK_SRCS := $(CHECK_SRCS_ALL)

# 3) Ordena automaticamente por dependencias (topological sort)
ORDERED_SRCS := $(shell uv run --project Tests riscv-tools vhdl-sort $(CHECK_SRCS))

.PHONY: print-check check
print-check:
	@echo "Arquivos que o check vai analisar:"; echo
	@printf '  %s\n' $(ORDERED_SRCS)

check:
	@echo "🔍 Checking VHDL syntax with GHDL..."
	@mkdir -p $(WDIR)
	@rm -rf $(WDIR)/*
	@$(GHDL) -a $(STD) --work=work --workdir=$(WDIR) $(ORDERED_SRCS)
	@echo "✅ VHDL syntax check passed"
