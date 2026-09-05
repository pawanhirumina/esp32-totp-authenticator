#!/usr/bin/env bash

set -e

INSTALL_DIR="$HOME/.local/bin"
SCRIPT_NAME="pyauth.py"
COMMAND_NAME="pyauth"

echo "==> Installing PyAuth..."

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
  echo "[!] Python 3 is not installed."

  if command -v dnf >/dev/null 2>&1; then
    echo "==> Installing Python 3..."
    sudo dnf install -y python3 python3-pip
  elif command -v apt >/dev/null 2>&1; then
    echo "==> Installing Python 3..."
    sudo apt update
    sudo apt install -y python3 python3-pip
  else
    echo "[!] Please install Python 3 manually."
    exit 1
  fi
fi

# Create local bin directory
mkdir -p "$INSTALL_DIR"

# Check that pyauth.py exists
if [ ! -f "$SCRIPT_NAME" ]; then
  echo "[!] $SCRIPT_NAME not found."
  echo "    Run this installer from the directory containing $SCRIPT_NAME."
  exit 1
fi

# Install pyserial
echo "==> Installing pyserial..."

python3 -m pip install --user --upgrade pyserial 2>/dev/null || {
  echo "[!] pip installation failed."
  echo "    Trying system package..."

  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3-pyserial
  elif command -v apt >/dev/null 2>&1; then
    sudo apt install -y python3-serial
  else
    exit 1
  fi
}

# Install the script
echo "==> Installing $COMMAND_NAME..."

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

  if ! grep -q 'HOME/.local/bin' "$RC_FILE" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >>"$RC_FILE"
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
echo "  pyauth remove NAME"
echo "  pyauth codes"
echo "  pyauth show"
echo "  pyauth clear"
echo
echo "If the command is not found in your current terminal:"
echo "  source ~/.zshrc"
echo
