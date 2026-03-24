#!/usr/bin/env bash
set -euo pipefail

HA_VERSION="2026.3.1"
CONSTRAINTS_URL="https://raw.githubusercontent.com/home-assistant/core/${HA_VERSION}/homeassistant/package_constraints.txt"
PIP_OPTS=(--disable-pip-version-check --timeout 60 --retries 5)

echo "[devcontainer] Installing Home Assistant ${HA_VERSION} with constraints..."
if python -m pip install "${PIP_OPTS[@]}" "homeassistant==${HA_VERSION}" colorlog --constraint "${CONSTRAINTS_URL}"; then
  echo "[devcontainer] Home Assistant installed with constraints."
else
  echo "[devcontainer] WARNING: Constraints install failed (likely network/proxy issue with raw.githubusercontent.com)."
  echo "[devcontainer] Retrying install without constraints..."
  python -m pip install "${PIP_OPTS[@]}" "homeassistant==${HA_VERSION}" colorlog
  echo "[devcontainer] Home Assistant installed without constraints."
fi
