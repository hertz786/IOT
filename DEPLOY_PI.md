# ELECTRONIC CLIKS SmartLock - Raspberry Pi One-Line Deployment

## 1) Put project in GitLab
Push this folder to GitLab first so `remote_install.sh` can be downloaded and the repo can be cloned on device.

## 2) On Raspberry Pi 3 (fresh OS)
Run this single command:

```bash
curl -fsSL https://raw.githubusercontent.com/hertz786/IOT/main/remote_install.sh | sudo bash
```

If your repo URL is different, use:

```bash
curl -fsSL https://raw.githubusercontent.com/<org>/<repo>/main/remote_install.sh | sudo REPO_URL=https://github.com/<org>/<repo>.git bash
```

## 3) Verify

```bash
systemctl status electronicclicks-bootstrap.service
journalctl -u electronicclicks-bootstrap.service -f
```

## 4) Reboot test

```bash
sudo reboot
```

After reboot, check service again:

```bash
systemctl status electronicclicks-bootstrap.service
```

## 5) Wi-Fi setup portal (only if device has no internet)

```bash
sudo -u electronicclickspi python3 /opt/electronic-cliks-smartlock/wifi_setup.py
```

Connect phone/laptop to hotspot **SmartLock-Setup** and open local portal.
