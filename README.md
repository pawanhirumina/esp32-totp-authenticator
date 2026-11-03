# ESP32-C3 Offline TOTP Vault (v1.2.0)

**100% offline hardware TOTP authenticator. No WiFi, no cloud, no phone. Secrets never leave the ESP32-C3.**

Built on ESP32-C3-DevKitM-1 / C3 Super Mini + Python CLI.

---

### Features

- Offline: No internet needed, ever
- CLI tool `pyauth` - `list / add / remove / codes / show / bulk`
- TOTP secrets (base32) **and** normal plain-text passwords
- Auto `otpauth://totp/...` URI parsing - paste the full import URI, the `secret=` is stripped automatically
- Bulk adding from a file: `pyauth bulk accounts.txt`
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
- `GET` -> return codes (`name|code|secs` for TOTP, `name|password|--` for passwords)
- `ADD:name:SECRET` -> save permanently as TOTP (default)
- `ADD:name:SECRET:TYPE` -> save as `totp` or `pass`
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
pyauth add Google 1234                          # TOTP (base32 secret, auto-detected)
pyauth add GitHub hunter2                       # normal password (auto-detected)
pyauth add Work "my p@ss:w0rd" -t pass          # force password type (keep spaces/symbols)
pyauth add - "-"                                # read password securely from stdin (getpass)
pyauth list
pyauth codes          # quick terminal codes (passwords show as-is)
pyauth                # or pyauth show -> GUI, no flashing
pyauth remove GitHub
pyauth clear
```

**Auto `otpauth://` import** (paste the full URI, `secret=` is stripped automatically):

```bash
pyauth add Google "otpauth://totp/Google:user%40example.com?secret=dummysecretbase32example&issuer=Google"
pyauth add GitHub "otpauth://totp/GitHub:user?secret=DUMMYSECRETBASE32EXAMPLE&issuer=Example"
# name is taken from the URI if you don't give one:
pyauth add "otpauth://totp/Google:user%40example.com?secret=...&issuer=Google"
```

**Bulk add** (from a file, one entry per line):

```bash
cat accounts.txt
# Google
Google 12345678901234567890
# plain password
GitHub:hunter2
# full otpauth URI
otpauth://totp/Google:user%40example.com?secret=dummysecretbase32example&issuer=Google

pyauth bulk accounts.txt
```

Bulk file formats: `NAME SECRET`, `NAME:SECRET` (use this for passwords with spaces/symbols), or a bare `otpauth://` URI. Lines starting with `#` and blank lines are skipped.

Auto-finds port `/dev/ttyACM0`, `/dev/ttyUSB0`, etc. No more hardcoded port.

### How to Import from Authenticator App

**V2:** paste the full `otpauth://` URI - `pyauth` strips the `secret=` part automatically:

```bash
pyauth add "Google" "otpauth://totp/Google:user%40example.com?secret=dummysecretbase32example&issuer=Google"
```

If you prefer, you can still enter just the base32 secret:

```bash
pyauth add "Google" "DUMMYSECRETBASE32EXAMPLE"
```

**V1:** secrets are hardcoded in `src/main.cpp` and require re-flash (see V1 vs V2 below).

### V1 vs V2

| Feature        | V1                                      | V2                                       |
| -------------- | --------------------------------------- | ---------------------------------------- |
| Secret storage | `src/main.cpp` hardcoded array          | Preferences (NVS) flash, survives reboot |
| Add secret     | Edit file + re-flash                    | `pyauth add name secret` / `pyauth bulk file` (TOTP or password, auto `otpauth://` URI parsing) |
| Security       | Secrets only in source, not in NVS dump | Secrets in flash, but no re-flash needed |
| Best for       | Max air-gap, learn CDC fix              | Daily use                                |

**V1 Example (hardcoded):**

```cpp
Account accounts[] = {
   {"GitHub", "YOUR SECRET HERE"},
  {"Google", "YOUR SECRET HERE"}
};
```

### Troubleshooting

**`rst:0x15` loop, no READY:** Add CDC flags to `platformio.ini` (see above).

**`Permission denied /dev/ttyACM0`:**

```bash
sudo chmod 666 /dev/ttyACM0
# permanent:
sudo usermod -a -G dialout $USER
```

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
