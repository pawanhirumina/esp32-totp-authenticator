#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[*] Project dir: $PROJECT_DIR"

# --- check deps ---
if! command -v python3 &>/dev/null; then
  echo "[!] python3 not found"; exit 1
fi
if! command -v pip3 &>/dev/null &&! command -v pip &>/dev/null; then
  echo "[!] pip not found"; exit 1
fi

echo "[*] Installing python deps: pyserial, tkinter"
pip3 install pyserial --user -q || pip install pyserial --user -q

# Tkinter is usually included, check
python3 -c "import tkinter" 2>/dev/null || echo "[!] tkinter not found - install python3-tk: sudo apt install python3-tk / brew install python-tk"

# --- install pyauth CLI ---
echo "[*] Installing pyauth CLI"

# pyauth python script is in root as 'pyauth' or 'main.py' - find it
SRC_CLI="$PROJECT_DIR/pyauth"
if [! -f "$SRC_CLI" ]; then
  SRC_CLI="$PROJECT_DIR/main.py"
fi
if [! -f "$SRC_CLI" ]; then
  echo "[!] Can't find pyauth cli file (pyauth or main.py)"; exit 1
fi

chmod +x "$SRC_CLI"

# try /usr/local/bin, fallback to ~/.local/bin
TARGET_DIR="/usr/local/bin"
if [! -w "$TARGET_DIR" ]; then
  TARGET_DIR="$HOME/.local/bin"
  mkdir -p "$TARGET_DIR"
fi

cp "$SRC_CLI" "$TARGET_DIR/pyauth"
echo "[✓] Installed to $TARGET_DIR/pyauth"

if [[ ":$PATH:"!= *":$TARGET_DIR:"* ]]; then
  echo "[!] Add to your.zshrc/.bashrc: export PATH=\"\$PATH:$TARGET_DIR\""
fi

echo ""
echo "[✓] Done!"
echo " pio run --target upload # flash the ESP32"
echo " pyauth list"
echo " pyauth add <name> <secret>"
echo " pyauth show"
