#!/usr/bin/env bash

set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "scripts/install-linux-launcher.sh must be run on Linux." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_APP="${ROOT_DIR}/dist/linux/PTO Planner"
DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
INSTALL_DIR="${DATA_HOME}/pto-planner"
APPLICATIONS_DIR="${DATA_HOME}/applications"
ICON_DIR="${DATA_HOME}/icons/hicolor/512x512/apps"
DESKTOP_FILE="${APPLICATIONS_DIR}/pto-planner.desktop"
EXECUTABLE_PATH="${INSTALL_DIR}/PTO Planner"
EXECUTABLE_FIELD="${EXECUTABLE_PATH// /\\ }"

if [[ ! -d "${SOURCE_APP}" ]]; then
    echo "Build output not found at ${SOURCE_APP}. Run scripts/build-linux.sh first." >&2
    exit 1
fi

mkdir -p "${APPLICATIONS_DIR}" "${ICON_DIR}"
rm -rf "${INSTALL_DIR}"
cp -R "${SOURCE_APP}" "${INSTALL_DIR}"
install -m 0644 "${ROOT_DIR}/pto_calculator/assets/pto-planner.png" "${ICON_DIR}/pto-planner.png"

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PTO Planner
Comment=Project PTO balances with a desktop planner
Exec=${EXECUTABLE_FIELD}
Icon=pto-planner
Path=${INSTALL_DIR}
Terminal=false
Categories=Office;Utility;
StartupWMClass=PTO Planner
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APPLICATIONS_DIR}" >/dev/null 2>&1 || true
fi
