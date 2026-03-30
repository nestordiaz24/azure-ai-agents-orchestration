#!/bin/sh
# Post-provision hook: deploy agent.yaml to the Azure AI Project
set -e

echo "Deploying agent configuration..."

if [ -z "$AZURE_AI_PROJECT_NAME" ] || [ -z "$AZURE_RESOURCE_GROUP" ]; then
  echo "WARNING: AZURE_AI_PROJECT_NAME or AZURE_RESOURCE_GROUP is not set. Skipping agent deployment."
  exit 0
fi

# azd hooks run with the working directory set to the project root (where azure.yaml lives)
AGENT_YAML="${AZD_PROJECT_DIR:-$(pwd)}/agent.yaml"

if [ ! -f "$AGENT_YAML" ]; then
  echo "WARNING: agent.yaml not found at $AGENT_YAML. Skipping agent deployment."
  exit 0
fi

# Substitute environment variables in agent.yaml and deploy
TEMP_AGENT_YAML="/tmp/agent_resolved.yaml"
envsubst < "$AGENT_YAML" > "$TEMP_AGENT_YAML"

echo "Creating/updating agent in project: $AZURE_AI_PROJECT_NAME"
az ml agent create \
  --file "$TEMP_AGENT_YAML" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_AI_PROJECT_NAME" \
  2>/dev/null || \
az ml agent update \
  --file "$TEMP_AGENT_YAML" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_AI_PROJECT_NAME"

rm -f "$TEMP_AGENT_YAML"
echo "Agent deployed successfully."
