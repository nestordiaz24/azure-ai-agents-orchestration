# Post-provision hook: deploy agent.yaml to the Azure AI Project
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

    throw "Python 3.10+ is required for the post-provision deployment step."
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

Write-Host "Deploying agent configuration..."

if (-not $env:AZURE_OPENAI_ENDPOINT) {
    # Fallback: construct from AI Services name if Bicep hasn't output it yet
    if ($env:AZURE_AI_SERVICES_ENDPOINT) {
        $uri = [System.Uri]$env:AZURE_AI_SERVICES_ENDPOINT
        $env:AZURE_OPENAI_ENDPOINT = "https://$($uri.Host.Replace('.cognitiveservices.azure.com', '.openai.azure.com'))/"
    } else {
        Write-Warning "AZURE_OPENAI_ENDPOINT is not set. Skipping agent deployment."
        exit 0
    }
}

# azd hooks run with the working directory set to the project root (where azure.yaml lives)
$ProjectDir = if ($env:AZD_PROJECT_DIR) { $env:AZD_PROJECT_DIR } else { (Get-Location).Path }
$RequirementsFile = Join-Path $ProjectDir "requirements.txt"
$DeployScript = Join-Path $ProjectDir "src\deploy_agent.py"

if (-not (Test-Path $RequirementsFile) -or -not (Test-Path $DeployScript)) {
    Write-Warning "Project files for agent deployment were not found. Skipping agent deployment."
    exit 0
}

$pythonCommand = Get-PythonCommand

Write-Host "Installing Python dependencies for agent deployment..."
Invoke-PythonCommand -PythonCommand $pythonCommand -Arguments @('-m', 'pip', 'install', '-q', '-r', $RequirementsFile)

Write-Host "Creating/updating agent (endpoint: $env:AZURE_OPENAI_ENDPOINT)..."
Invoke-PythonCommand -PythonCommand $pythonCommand -Arguments @($DeployScript)
