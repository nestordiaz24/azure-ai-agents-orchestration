# Post-provision hook: deploy agent.yaml to the Azure AI Project
$ErrorActionPreference = "Stop"

Write-Host "Deploying agent configuration..."

if (-not $env:AZURE_AI_PROJECT_NAME -or -not $env:AZURE_RESOURCE_GROUP) {
    Write-Warning "AZURE_AI_PROJECT_NAME or AZURE_RESOURCE_GROUP is not set. Skipping agent deployment."
    exit 0
}

# azd hooks run with the working directory set to the project root (where azure.yaml lives)
$ProjectDir = if ($env:AZD_PROJECT_DIR) { $env:AZD_PROJECT_DIR } else { (Get-Location).Path }
$AgentYaml = Join-Path $ProjectDir "agent.yaml"

if (-not (Test-Path $AgentYaml)) {
    Write-Warning "agent.yaml not found at $AgentYaml. Skipping agent deployment."
    exit 0
}

# Substitute environment variables and write to temp file
$content = Get-Content $AgentYaml -Raw
$content = $content -replace '\$\{AZURE_AI_SEARCH_CONNECTION_ID\}', $env:AZURE_AI_SEARCH_CONNECTION_ID
$content = $content -replace '\$\{AZURE_AI_SEARCH_INDEX_NAME\}', $env:AZURE_AI_SEARCH_INDEX_NAME
$TempYaml = Join-Path $env:TEMP "agent_resolved.yaml"
$content | Set-Content $TempYaml

Write-Host "Creating/updating agent in project: $env:AZURE_AI_PROJECT_NAME"
try {
    az ml agent create `
        --file $TempYaml `
        --resource-group $env:AZURE_RESOURCE_GROUP `
        --workspace-name $env:AZURE_AI_PROJECT_NAME
} catch {
    az ml agent update `
        --file $TempYaml `
        --resource-group $env:AZURE_RESOURCE_GROUP `
        --workspace-name $env:AZURE_AI_PROJECT_NAME
}

Remove-Item $TempYaml -ErrorAction SilentlyContinue
Write-Host "Agent deployed successfully."
