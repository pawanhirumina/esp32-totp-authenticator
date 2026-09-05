# ESP32-C3 Offline TOTP Vault

**100% offline hardware TOTP authenticator. No WiFi, no cloud, no phone. Secrets never leave the ESP32-C3.**

Built on ESP32-C3-DevKitM-1 / C3 Super Mini + Python CLI.

---

### Features

- Offline: No internet needed, ever
- V1: Hardcoded secrets in source (max security, air-gapped)
- V2: Save secrets inside C3 flash, add/remove without re-flashing
- CLI tool `pyauth` - `list / add / remove / codes / show`
- Auto time-sync from PC (C3 has no battery)
- No flashing GUI, progress colors

### Hardware

- ESP32-C3-DevKitM-1 or C3 Super Mini
- USB Data cable
- Fedora / Linux / Windows with Python 3

### Quick Start

#### 1. PlatformIO Setup

```ini
; platformio.ini
[env:esp32-c3-devkitm-1]
platform = espressif32
board = esp32-c3-devkitm-1
framework = arduino
monitor_speed = 115200
monitor_port = /dev/ttyACM0
monitor_rts = 0
monitor_dtr = 0
build_flags =
    -DARDUINO_USB_CDC_ON_BOOT=1
    -DARDUINO_USB_MODE=1
lib_deps =
    lucadentella/TOTP@^1.0.2
```

> **C3 Fix:** Without `ARDUINO_USB_CDC_ON_BOOT=1` you will only see `rst:0x15 (USB_UART_CHIP_RESET)` and no `Serial`. Monitor must have `rts=0 dtr=0`.

#### 2. Flash Firmware (V2 - Recommended)

```bash
cd ~/esp32-totp-vault
pio run --target upload
# unplug / plug after upload
```

V2 firmware understands:

- `TIME:<unix>` -> sync time
- `GET` -> return codes
- `ADD:name:SECRET` -> save permanently
- `DEL:name` -> delete
- `LIST` -> list saved
- `CLEAR` -> wipe all

#### 3. Install CLI

```bash
chmod +x pyauth
sudo mv pyauth /usr/local/bin/pyauth
# Fedora needs tkinter for GUI
sudo dnf install python3-tkinter -y
pip install pyserial --user
```

#### 4. Use It

```bash
pyauth add Google 1234
pyauth add GitHub 1234
pyauth list
pyauth codes          # quick terminal codes
pyauth                # or pyauth show -> GUI, no flashing
pyauth remove GitHub
pyauth clear
```

Auto-finds port `/dev/ttyACM0`, `/dev/ttyUSB0`, etc. No more hardcoded port.

### How to Import from Authenticator App

You need only `secret=` part.

Example:

```bash
pyauth add "Google" "1234"
pyauth add "GitHub" "1234"
```

### V1 vs V2

| Feature        | V1                                      | V2                                       |
| -------------- | --------------------------------------- | ---------------------------------------- |
| Secret storage | `src/main.cpp` hardcoded array          | Preferences (NVS) flash, survives reboot |
| Add secret     | Edit file + re-flash                    | `pyauth add name secret`                 |
| Security       | Secrets only in source, not in NVS dump | Secrets in flash, but no re-flash needed |
| Best for       | Max air-gap, learn CDC fix              | Daily use                                |

**V1 Example (hardcoded) - V2 Fixed (now can upload via python script)**

```cpp
Account accounts[] = {
   {"GitHub", "YOUR SECRET HERE"},
  {"Google", "YOUR SECRET HERE"}
};
```

or

````bash

```bash
pio run --target upload
````

```

```

````


### Troubleshooting

**`rst:0x15` loop, no READY:** Add CDC flags to `platformio.ini` (see above).

**`Permission denied /dev/ttyACM0`:**

```bash
sudo chmod 666 /dev/ttyACM0
# permanent:
sudo usermod -a -G dialout $USER
````

**`ModuleNotFoundError: tkinter`:**

```bash
sudo dnf install python3-tkinter
```

**`pyauth list` empty but `pyauth codes` shows codes:** You are still on V1 firmware. Flash V2.

**GUI flashes:** Update to latest `pyauth` / `vault.py` that updates labels instead of destroying widgets.

### Security Notes

- Time is synced from your PC, so your PC clock must be correct (NTP)
- Drift: Re-synced every 5 min automatically
- No WiFi code in firmware = can't be remotely exfiltrated
- For extra security, wipe `otpauth://` URIs after importing

### License

MIT - Do what you want, keep it offline.
