#!/usr/bin/env bash
set -euo pipefail

echo "[postStart] Running uv sync to keep env up-to-date..."

if ! command -v uv >/dev/null 2>&1; then
  echo "[postStart] uv not found; installing"
  curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
  if ! grep -q 'cargo/bin' "/home/vscode/.bashrc" 2>/dev/null; then
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "/home/vscode/.bashrc"
  fi
fi

UV_BIN="$(command -v uv || echo "$HOME/.cargo/bin/uv")"
"$UV_BIN" sync

echo "[postStart] uv sync done."

