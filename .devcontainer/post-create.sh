#!/usr/bin/env bash
set -euo pipefail

HA_VERSION="2025.12.3"
CONSTRAINTS_URL="https://raw.githubusercontent.com/home-assistant/core/${HA_VERSION}/homeassistant/package_constraints.txt"

python -m pip install --upgrade pip

echo "[devcontainer] Installing Home Assistant ${HA_VERSION} with constraints..."
if pip install "homeassistant==${HA_VERSION}" colorlog --constraint "${CONSTRAINTS_URL}"; then
  echo "[devcontainer] Home Assistant installed with constraints."
else
  echo "[devcontainer] WARNING: Constraints install failed (likely network/proxy issue with raw.githubusercontent.com)."
  echo "[devcontainer] Retrying install without constraints..."
  pip install "homeassistant==${HA_VERSION}" colorlog
  echo "[devcontainer] Home Assistant installed without constraints."
fi
