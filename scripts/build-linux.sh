#!/usr/bin/env bash

set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "scripts/build-linux.sh must be run on Linux." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
    PYTHON_BIN="$(command -v python3)"
fi

if ! "${PYTHON_BIN}" -c "import PyInstaller" >/dev/null 2>&1; then
    echo "PyInstaller is not installed for ${PYTHON_BIN}. Run: ${PYTHON_BIN} -m pip install -r ${ROOT_DIR}/requirements-packaging.txt" >&2
    exit 1
fi

"${PYTHON_BIN}" -m PyInstaller \
    --noconfirm \
    --clean \
    --distpath "${ROOT_DIR}/dist/linux" \
    --workpath "${ROOT_DIR}/build/linux" \
    "${ROOT_DIR}/pto_planner.spec"
