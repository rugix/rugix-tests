#!/usr/bin/env bash

set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_dir="$(cd "${project_dir}/.." && pwd)"

# Prefer freshly built repo binaries when available, but let callers and Bakery
# image tests keep their explicit/default binary source.
if [ -z "${RUGIX_BINARIES_DIR:-}" ] && [ -d "${repo_dir}/build/binaries" ]; then
    export RUGIX_BINARIES_DIR="${repo_dir}/build/binaries"
fi

exec uv run --group dev pytest "$@"
