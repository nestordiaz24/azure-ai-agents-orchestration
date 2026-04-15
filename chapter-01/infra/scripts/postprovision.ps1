# Post-provision hook: install Python dependencies after provisioning
$ErrorActionPreference = "Stop"

function Get-PythonCommand {
    try {
        & py -3 --version *> $null
        return @('py', '-3')
    } catch {
    }

    foreach ($candidate in @('python', 'python3')) {
        try {
            & $candidate --version *> $null
            return @($candidate)
        } catch {
        }
    }

    return $null
}

function Invoke-PythonCommand {
    param(
        [string[]] $PythonCommand,
        [string[]] $Arguments
    )

    if ($PythonCommand.Length -gt 1) {
        & $PythonCommand[0] $PythonCommand[1..($PythonCommand.Length - 1)] @Arguments
        return
    }

    & $PythonCommand[0] @Arguments
}

# azd hooks run with the working directory set to the project root (where azure.yaml lives)
$ProjectDir = if ($env:AZD_PROJECT_DIR) { $env:AZD_PROJECT_DIR } else { (Get-Location).Path }
$RequirementsFile = Join-Path $ProjectDir "requirements.txt"

if (-not (Test-Path $RequirementsFile)) {
    Write-Warning "requirements.txt not found. Skipping dependency installation."
    exit 0
}

$pythonCommand = Get-PythonCommand
if (-not $pythonCommand) {
    Write-Warning "Python 3.10+ not found. Skipping dependency installation."
    exit 0
}

Write-Host "Installing Python dependencies..."
Invoke-PythonCommand -PythonCommand $pythonCommand -Arguments @('-m', 'pip', 'install', '-q', '-r', $RequirementsFile)
Write-Host "Done. Run 'python src/chat.py' to start chatting with your agent."
