#!/usr/bin/env bash
set -e

INSTALL_DIR="$HOME/.local/bin"
SCRIPT_NAME="pyauth.py"
COMMAND_NAME="pyauth"
REQUIREMENTS_FILE="requirements.txt"

echo "==> Installing PyAuth..."

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
  echo "[!] Python 3 is not installed."
  if command -v dnf >/dev/null 2>&1; then
    echo "==> Installing Python 3..."
    sudo dnf install -y python3 python3-pip python3-tkinter
  elif command -v apt >/dev/null 2>&1; then
    echo "==> Installing Python 3..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-tk
  else
    echo "[!] Please install Python 3 manually."
    exit 1
  fi
fi

mkdir -p "$INSTALL_DIR"

if [ ! -f "$SCRIPT_NAME" ]; then
  echo "[!] $SCRIPT_NAME not found."
  echo "    Run this installer from the directory containing $SCRIPT_NAME."
  exit 1
fi

# Install dependencies
echo "==> Installing dependencies..."

if [ -f "$REQUIREMENTS_FILE" ]; then
  echo "    Found $REQUIREMENTS_FILE, installing from it..."
  python3 -m pip install --user --upgrade -r "$REQUIREMENTS_FILE" 2>/dev/null || python3 -m pip install --user --upgrade -r "$REQUIREMENTS_FILE" --break-system-packages 2>/dev/null || {
    echo "    [!] pip failed, trying system packages..."
    if command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y python3-pyserial python3-colorama
    elif command -v apt >/dev/null 2>&1; then
      sudo apt install -y python3-serial python3-colorama
    fi
  }
else
  echo "    No $REQUIREMENTS_FILE found, installing pyserial + colorama..."
  python3 -m pip install --user --upgrade pyserial colorama 2>/dev/null || python3 -m pip install --user --upgrade pyserial colorama --break-system-packages 2>/dev/null || {
    if command -v dnf >/dev/null 2>&1; then
      sudo dnf install -y python3-pyserial python3-colorama
    elif command -v apt >/dev/null 2>&1; then
      sudo apt install -y python3-serial python3-colorama
    fi
  }
fi

echo "==> Installing $COMMAND_NAME to $INSTALL_DIR..."
cp "$SCRIPT_NAME" "$INSTALL_DIR/$COMMAND_NAME"
chmod +x "$INSTALL_DIR/$COMMAND_NAME"

# Make sure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
  echo
  echo "[!] $INSTALL_DIR is not currently in your PATH."
  SHELL_NAME="$(basename "$SHELL")"
  if [ "$SHELL_NAME" = "zsh" ]; then
    RC_FILE="$HOME/.zshrc"
  else
    RC_FILE="$HOME/.bashrc"
  fi
  if ! grep -q '.local/bin' "$RC_FILE" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC_FILE"
    echo "==> Added ~/.local/bin to $RC_FILE"
  fi
  export PATH="$HOME/.local/bin:$PATH"
fi

echo
echo "================================"
echo " PyAuth installed successfully!"
echo "================================"
echo
echo "Run:"
echo "  pyauth"
echo
echo "Commands:"
echo "  pyauth list"
echo "  pyauth add NAME SECRET"
echo "  pyauth add NAME -"
echo "  pyauth bulk FILE"
echo "  pyauth remove NAME"
echo "  pyauth codes"
echo "  pyauth show"
echo "  pyauth clear"
echo
echo "If the command is not found, run:"
echo "  source ~/.bashrc  # or ~/.zshrc"