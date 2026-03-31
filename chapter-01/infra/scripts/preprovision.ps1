# Pre-provision hook: validate required tools are installed
$ErrorActionPreference = "Stop"

Write-Host "Checking required tools..."

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: Azure CLI (az) is not installed. Please install it from https://aka.ms/install-azure-cli"
    exit 1
}

$pythonAvailable = $false

try {
    & py -3 --version *> $null
    $pythonAvailable = $true
} catch {
}

if (-not $pythonAvailable) {
    foreach ($candidate in @('python', 'python3')) {
        try {
            & $candidate --version *> $null
            $pythonAvailable = $true
            break
        } catch {
        }
    }
}

if (-not $pythonAvailable) {
    Write-Error "ERROR: Python 3.10+ is required for the post-provision deployment step. Install Python or make the 'py -3' launcher available."
    exit 1
}

$mlExtension = az extension show --name ml 2>$null
if (-not $mlExtension) {
    Write-Host "Installing Azure ML CLI extension..."
    az extension add --name ml --yes
}

Write-Host "Pre-provision checks passed."
