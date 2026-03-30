# Pre-provision hook: validate required tools are installed
$ErrorActionPreference = "Stop"

Write-Host "Checking required tools..."

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: Azure CLI (az) is not installed. Please install it from https://aka.ms/install-azure-cli"
    exit 1
}

$mlExtension = az extension show --name ml 2>$null
if (-not $mlExtension) {
    Write-Host "Installing Azure ML CLI extension..."
    az extension add --name ml --yes
}

Write-Host "Pre-provision checks passed."
