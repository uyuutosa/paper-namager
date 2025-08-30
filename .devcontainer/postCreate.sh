#!/usr/bin/env bash
set -euo pipefail

echo "[postCreate] Ensuring uv is installed and syncing Python env..."

if ! command -v uv >/dev/null 2>&1; then
  echo "[postCreate] Installing uv (astral-sh/uv)"
  # Install for user 'vscode' into ~/.cargo/bin/uv
  curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
  # Make available in future shells
  if ! grep -q 'cargo/bin' "/home/vscode/.bashrc" 2>/dev/null; then
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "/home/vscode/.bashrc"
  fi
fi

UV_BIN="$(command -v uv || echo "$HOME/.cargo/bin/uv")"
echo "[postCreate] Using uv at: $UV_BIN"

# Sync environment (creates .venv)
"$UV_BIN" sync

echo "[postCreate] uv sync complete. Virtualenv at .venv"

echo "[postCreate] Ensuring Volta and Node LTS are available..."
if ! command -v volta >/dev/null 2>&1; then
  echo "[postCreate] Installing Volta (node toolchain)"
  curl -fsSL https://get.volta.sh | bash -s -- -y
  if ! grep -q 'VOLTA_HOME' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export VOLTA_HOME="$HOME/.volta"' >> "$HOME/.bashrc"
    echo 'export PATH="$VOLTA_HOME/bin:$PATH"' >> "$HOME/.bashrc"
  fi
  export VOLTA_HOME="$HOME/.volta"
  export PATH="$VOLTA_HOME/bin:$PATH"
fi
if ! command -v node >/dev/null 2>&1; then
  echo "[postCreate] Installing Node LTS via Volta"
  volta install node@lts npm@latest
fi
echo "[postCreate] Node version: $(node -v 2>/dev/null || echo 'not found')"
