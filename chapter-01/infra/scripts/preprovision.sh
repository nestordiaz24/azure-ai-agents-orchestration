#!/bin/sh
# Pre-provision hook: validate required tools are installed
set -e

echo "Checking required tools..."

if ! command -v az > /dev/null 2>&1; then
  echo "ERROR: Azure CLI (az) is not installed. Please install it from https://aka.ms/install-azure-cli"
  exit 1
fi

if ! az extension show --name ml > /dev/null 2>&1; then
  echo "Installing Azure ML CLI extension..."
  az extension add --name ml --yes
fi

echo "Pre-provision checks passed."
