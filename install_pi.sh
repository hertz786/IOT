#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="electronicclicks-bootstrap.service"
SERVICE_USER="electronicclickspi"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_TEMPLATE="${PROJECT_DIR}/electronicclicks-bootstrap.service"
SERVICE_TARGET="/etc/systemd/system/${SERVICE_NAME}"
TMP_SERVICE="/tmp/${SERVICE_NAME}"

echo "[ELECTRONIC CLIKS] SmartLock Raspberry Pi installer starting..."

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo/root."
  exit 1
fi

if [[ ! -f "${SERVICE_TEMPLATE}" ]]; then
  echo "Missing service template: ${SERVICE_TEMPLATE}"
  exit 1
fi

apt-get update
apt-get install -y python3-pip network-manager

if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "${SERVICE_USER}"
  echo "Created service user: ${SERVICE_USER}"
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r "${PROJECT_DIR}/requirements.txt"

chmod +x "${PROJECT_DIR}/bootstrap.py"
chmod +x "${PROJECT_DIR}/wifi_setup.py"
chmod +x "${PROJECT_DIR}/install_pi.sh"
if [[ -f "${PROJECT_DIR}/gpio_main.py" ]]; then
  chmod +x "${PROJECT_DIR}/gpio_main.py"
fi

sed "s|__PROJECT_DIR__|${PROJECT_DIR}|g" "${SERVICE_TEMPLATE}" > "${TMP_SERVICE}"
install -m 644 "${TMP_SERVICE}" "${SERVICE_TARGET}"
rm -f "${TMP_SERVICE}"

chown -R "${SERVICE_USER}:${SERVICE_USER}" "${PROJECT_DIR}"

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}"

echo
echo "[ELECTRONIC CLIKS] Installation complete."
echo "View live service logs: journalctl -u ${SERVICE_NAME} -f"
echo "Check service status:     systemctl status ${SERVICE_NAME}"
echo "Run Wi-Fi setup portal:   sudo -u ${SERVICE_USER} python3 ${PROJECT_DIR}/wifi_setup.py"
echo "Reboot device:            sudo reboot"
