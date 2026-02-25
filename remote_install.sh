#!/usr/bin/env bash
set -euo pipefail

# ELECTRONIC CLIKS SmartLock - One-command Raspberry Pi installer
# Usage examples:
#   curl -fsSL <RAW_REMOTE_INSTALL_URL> | sudo bash
#   curl -fsSL <RAW_REMOTE_INSTALL_URL> | sudo REPO_URL=https://gitlab.com/<org>/<repo>.git bash
#
# Optional env vars:
#   REPO_URL        Git repository URL
#   REPO_BRANCH     Branch/tag to deploy (default: main)
#   INSTALL_DIR     Target directory on Pi (default: /opt/electronic-cliks-smartlock)

REPO_URL="${REPO_URL:-https://gitlab.com/electronic-cliks/smartlock-iot.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/electronic-cliks-smartlock}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "[ELECTRONIC CLIKS] Please run with sudo/root."
  echo "Example: curl -fsSL <RAW_REMOTE_INSTALL_URL> | sudo bash"
  exit 1
fi

echo "[ELECTRONIC CLIKS] Starting one-command SmartLock deployment"
echo "[ELECTRONIC CLIKS] Repo: ${REPO_URL}"
echo "[ELECTRONIC CLIKS] Branch: ${REPO_BRANCH}"
echo "[ELECTRONIC CLIKS] Install dir: ${INSTALL_DIR}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git curl

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  echo "[ELECTRONIC CLIKS] Existing repo detected. Updating..."
  git -C "${INSTALL_DIR}" fetch --all --tags --prune
  git -C "${INSTALL_DIR}" checkout "${REPO_BRANCH}"
  git -C "${INSTALL_DIR}" reset --hard "origin/${REPO_BRANCH}"
else
  echo "[ELECTRONIC CLIKS] Cloning repository..."
  rm -rf "${INSTALL_DIR}"
  git clone --branch "${REPO_BRANCH}" --single-branch "${REPO_URL}" "${INSTALL_DIR}"
fi

if [[ ! -f "${INSTALL_DIR}/install_pi.sh" ]]; then
  echo "[ELECTRONIC CLIKS] install_pi.sh not found in ${INSTALL_DIR}"
  exit 1
fi

chmod +x "${INSTALL_DIR}/install_pi.sh"
cd "${INSTALL_DIR}"

bash "${INSTALL_DIR}/install_pi.sh"

echo
echo "[ELECTRONIC CLIKS] Deployment complete."
echo "Check status:  systemctl status electronicclicks-bootstrap.service"
echo "View logs:     journalctl -u electronicclicks-bootstrap.service -f"
