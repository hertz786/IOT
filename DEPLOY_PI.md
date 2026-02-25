# ELECTRONIC CLIKS SmartLock - Raspberry Pi 3 (Blank SD Card → Production)

This guide starts from a completely blank microSD card.

## 0) Before you start
- Hardware: Raspberry Pi 3, microSD card (16GB+), stable 5V/2.5A power supply.
- PC/Laptop with internet and SD card reader.
- Your repository must contain: `remote_install.sh`, `install_pi.sh`, `bootstrap.py`, `wifi_setup.py`, `gpio_main.py`.

## 1) Flash Raspberry Pi OS Lite
1. Install **Raspberry Pi Imager** on your PC.
2. Insert microSD card.
3. In Imager:
	- OS: **Raspberry Pi OS Lite (64-bit)**
	- Storage: your SD card
4. Open advanced options (gear icon):
	- Enable SSH
	- Set username/password
	- Set Wi-Fi SSID/password (optional)
	- Set locale/timezone
5. Write image, eject SD card, insert into Pi, and power on.

## 2) First login to Pi
Use monitor/keyboard or SSH:

```bash
ssh <pi-user>@<pi-ip>
```

Then run:

```bash
sudo apt update ; sudo apt upgrade -y
```

## 3) One-line full deployment
Run exactly this command:

```bash
curl -fsSL https://raw.githubusercontent.com/hertz786/IOT/main/remote_install.sh | sudo bash
```

If your repo/branch is different:

```bash
curl -fsSL https://raw.githubusercontent.com/<org>/<repo>/<branch>/remote_install.sh | sudo REPO_URL=https://github.com/<org>/<repo>.git REPO_BRANCH=<branch> bash
```

## 4) Verify service is running

```bash
systemctl status electronicclicks-bootstrap.service
journalctl -u electronicclicks-bootstrap.service -f
```

## 5) Reboot validation (self-heal test)

```bash
sudo reboot
```

After reboot:

```bash
systemctl status electronicclicks-bootstrap.service
```

## 6) If Pi has no Wi-Fi internet
Start setup portal:

```bash
sudo -u electronicclickspi python3 /opt/electronic-cliks-smartlock/wifi_setup.py
```

Then:
1. Connect phone/laptop to hotspot **SmartLock-Setup**.
2. Open local portal URL (usually `http://192.168.4.1` or `http://10.42.0.1`).
3. Enter your Wi-Fi SSID/password.

## 7) Important production note (cloud update URL)
`bootstrap.py` downloads cloud GPIO from GitHub raw URL. Ensure one of these is valid and public (or provide token env if private):
- `https://raw.githubusercontent.com/hertz786/IOT/main/gpio_main.py`
- `https://raw.githubusercontent.com/hertz786/IOT/master/gpio_main.py`

If cloud URL is unavailable, service automatically falls back to local `gpio_main.py`.
