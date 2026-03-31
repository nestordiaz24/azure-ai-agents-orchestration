#!/bin/sh
# Pre-provision hook: validate required tools are installed
set -e

echo "Checking required tools..."

if ! command -v az > /dev/null 2>&1; then
  echo "ERROR: Azure CLI (az) is not installed. Please install it from https://aka.ms/install-azure-cli"
  exit 1
fi

if ! command -v python3 > /dev/null 2>&1 && ! command -v python > /dev/null 2>&1; then
  echo "ERROR: Python 3.10+ is required for the post-provision deployment step. Install Python and ensure python3 or python is on PATH."
  exit 1
fi

if ! az extension show --name ml > /dev/null 2>&1; then
  echo "Installing Azure ML CLI extension..."
  az extension add --name ml --yes
fi

echo "Pre-provision checks passed."
