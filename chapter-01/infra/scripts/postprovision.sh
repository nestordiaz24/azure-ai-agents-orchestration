#!/bin/sh
# Post-provision hook: deploy agent.yaml to the Azure AI Project
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

echo "Deploying agent configuration..."

if [ -z "$AZURE_OPENAI_ENDPOINT" ]; then
  # Fallback: construct from AI Services endpoint if Bicep hasn't output it yet
  if [ -n "$AZURE_AI_SERVICES_ENDPOINT" ]; then
    AZURE_OPENAI_ENDPOINT="$(echo "$AZURE_AI_SERVICES_ENDPOINT" | sed 's/\.cognitiveservices\.azure\.com/.openai.azure.com/')"
    export AZURE_OPENAI_ENDPOINT
  else
    echo "WARNING: AZURE_OPENAI_ENDPOINT is not set. Skipping agent deployment."
    exit 0
  fi
fi

# azd hooks run with the working directory set to the project root (where azure.yaml lives)
PROJECT_DIR="${AZD_PROJECT_DIR:-$(pwd)}"
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
DEPLOY_SCRIPT="$PROJECT_DIR/src/deploy_agent.py"

if [ ! -f "$REQUIREMENTS_FILE" ] || [ ! -f "$DEPLOY_SCRIPT" ]; then
  echo "WARNING: Project files for agent deployment were not found. Skipping agent deployment."
  exit 0
fi

PYTHON_CMD="$(resolve_python)" || {
  echo "ERROR: Python 3.10+ is required for the post-provision deployment step."
  exit 1
}

echo "Installing Python dependencies for agent deployment..."
"$PYTHON_CMD" -m pip install -q -r "$REQUIREMENTS_FILE"

echo "Creating/updating agent (endpoint: $AZURE_OPENAI_ENDPOINT)..."
"$PYTHON_CMD" "$DEPLOY_SCRIPT"
