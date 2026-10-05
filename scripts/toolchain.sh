#!/usr/bin/env bash
# Runs a command inside the infra-toolchain image (GCC with picolibc, Spike, GHDL,
# uv) with this repository mounted at /workspace, as the calling user so the files
# it writes are not owned by root; its virtualenv lives in the container (/tmp/venv),
# so it never clobbers the host's .venv. The working directory carries over: run from
# Tests/ and the command runs in /workspace/Tests.
#
#   scripts/toolchain.sh uv run riscv-tools --config tools/riscv_build/config.yaml compile --emit mif
set -euo pipefail

IMAGE="${TOOLCHAIN_IMAGE:-ghcr.io/insper-riscv/infra-toolchain:latest}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REL="$(realpath --relative-to="$ROOT" "$PWD")"

exec docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp -e UV_LINK_MODE=copy -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
  -v "$ROOT:/workspace" \
  -w "/workspace/$REL" \
  "$IMAGE" "$@"
