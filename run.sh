#!/usr/bin/env bash
# Convenience runner script for WoeUSB-GUI
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v uv >/dev/null 2>&1; then
    exec uv run python -m woeusb_gui_flasher "$@"
elif [ -d ".venv" ]; then
    exec .venv/bin/python -m woeusb_gui_flasher "$@"
else
    exec python3 -m woeusb_gui_flasher "$@"
fi

