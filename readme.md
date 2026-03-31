# PTO Planner

`PTO Planner` is a cross-platform desktop app for projecting PTO balances with a modern `PySide6` UI. It supports user-selectable years, editable holiday calendars, planned PTO entries, CSV/XLSX export, and versioned scenario files.

## Features

- Planner dashboard with summary cards and a sortable/filterable projection grid
- User-selectable PTO year
- Biweekly projection anchored from a required last pay date
- Regular and float PTO tracking
- Range-based PTO entry creation
- Built-in US federal holiday defaults with per-scenario edits
- One-click add of remaining holidays as float PTO
- Scenario save/load with legacy JSON import support
- CSV and Excel export driven by the projection result

## Install

Runtime dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Test dependencies:

```bash
python3 -m pip install -r requirements-dev.txt
```

Packaging dependencies:

```bash
python3 -m pip install -r requirements-packaging.txt
```

## Run

Start the desktop app from the project root:

```bash
python3 -m pto_calculator
```

You can also launch the root `main.py` file directly from an editor/IDE that runs a single Python file.

## Testing

Run the automated test suite with:

```bash
python3 -m pytest
```

## Packaging

Build the native launcher artifact on each target OS with that platform's script:

```bash
./scripts/build-linux.sh
./scripts/build-macos.sh
```

```powershell
.\scripts\build-windows.ps1
```

Artifacts are written to `dist/linux/`, `dist/macos/`, and `dist/windows/`.

Install the launcher on each OS with:

```bash
./scripts/install-linux-launcher.sh
./scripts/install-macos-app.sh
```

```powershell
.\scripts\install-windows-launcher.ps1
.\scripts\install-windows-launcher.ps1 -DesktopShortcut
```

Linux installs the PyInstaller bundle into `~/.local/share/pto-planner/` and creates a `pto-planner.desktop` launcher in `~/.local/share/applications/`.

macOS copies `dist/macos/PTO Planner.app` into `~/Applications/PTO Planner.app`. You can pin that bundle to the Dock after the first launch.

Windows copies the bundle into `%LOCALAPPDATA%\Programs\PTO Planner\`, creates a Start Menu shortcut, and optionally adds a Desktop shortcut.

These builds are unsigned by design for personal use. Expect the normal first-launch trust prompts:

- macOS may require a control-click on `PTO Planner.app` and choosing `Open`.
- Windows SmartScreen may show a warning until you choose `More info` and `Run anyway`.

## Scenario Format

Saved scenarios use a versioned JSON schema:

- `schema_version`
- `scenario`
- `policy`
- `planned_entries`
- `holiday_overrides`

Legacy save files from the original Tkinter app are still importable.
