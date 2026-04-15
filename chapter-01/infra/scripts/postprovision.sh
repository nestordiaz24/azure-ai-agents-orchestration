#!/bin/sh
# Post-provision hook: install Python dependencies after provisioning
set -e

resolve_python() {
  if command -v python3 > /dev/null 2>&1; then
    echo python3
    return 0
  fi

  if command -v python > /dev/null 2>&1; then
    echo python
    return 0
  fi

  return 1
}

# azd hooks run with the working directory set to the project root (where azure.yaml lives)
PROJECT_DIR="${AZD_PROJECT_DIR:-$(pwd)}"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"

if [ ! -f "$REQUIREMENTS_FILE" ]; then
  echo "WARNING: requirements.txt not found. Skipping dependency installation."
  exit 0
fi

PYTHON_CMD="$(resolve_python)" || {
  echo "WARNING: Python 3.10+ not found. Skipping dependency installation."
  exit 0
}

echo "Installing Python dependencies..."
"$PYTHON_CMD" -m pip install -q -r "$REQUIREMENTS_FILE"
echo "Done. Run 'python src/chat.py' to start chatting with your agent."
