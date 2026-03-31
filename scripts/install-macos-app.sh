#!/usr/bin/env bash

set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "scripts/install-macos-app.sh must be run on macOS." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_APP="${ROOT_DIR}/dist/macos/PTO Planner.app"
INSTALL_DIR="${HOME}/Applications/PTO Planner.app"

if [[ ! -d "${SOURCE_APP}" ]]; then
    echo "Build output not found at ${SOURCE_APP}. Run scripts/build-macos.sh first." >&2
    exit 1
fi

mkdir -p "${HOME}/Applications"
rm -rf "${INSTALL_DIR}"
ditto "${SOURCE_APP}" "${INSTALL_DIR}"
