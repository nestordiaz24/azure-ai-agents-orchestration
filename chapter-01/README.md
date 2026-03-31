# Chapter 1 – Deploy Basic Foundry Agent

This chapter walks you through deploying a simple Q&A agent to **Azure AI Foundry** using the declarative `agent.yaml` approach and the **Azure Developer CLI (`azd`)**.

By the end of this chapter you will have:

- An **Azure AI Hub** and **Azure AI Project** provisioned via Bicep IaC
- An **Azure OpenAI** model deployment (`gpt-4o`) inside the AI Services account
- An **Azure AI Search** index connected to the project as a knowledge source
- A running **Foundry Agent** configured declaratively through `agent.yaml`

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Azure Resource Group                  │
│                                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Azure AI Hub (Hub)                 │   │
│  │                                                 │   │
│  │  ┌─────────────────────────────────────────┐   │   │
│  │  │        Azure AI Project (Project)       │   │   │
│  │  │                                         │   │   │
│  │  │   ┌───────────────┐  ┌───────────────┐  │   │   │
│  │  │   │  Foundry Agent │  │  agent.yaml   │  │   │   │
│  │  │   │  (gpt-4o)     │  │  (declarative)│  │   │   │
│  │  │   └───────────────┘  └───────────────┘  │   │   │
│  │  └─────────────────────────────────────────┘   │   │
│  │                                                 │   │
│  │  Connections:                                   │   │
│  │    • Azure OpenAI (gpt-4o model)               │   │
│  │    • Azure AI Search (documents index)          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                        │
│  ┌───────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Azure OpenAI  │  │  AI Search  │  │  Key Vault  │  │
│  │  (AIServices) │  │   (basic)   │  │             │  │
│  └───────────────┘  └─────────────┘  └─────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Azure Developer CLI (`azd`) | ≥ 1.9.0 | [Install guide](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) |
| Azure CLI (`az`) | ≥ 2.60.0 | [Install guide](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| Azure CLI ML extension | latest | `az extension add --name ml` |

You also need:

- An **Azure subscription** with access to Azure OpenAI (`gpt-4o` or equivalent) in your target region.
- Owner or Contributor + User Access Administrator rights on the subscription/resource group.

Python is only required for the optional local scripts in `src/deploy_agent.py` and `src/chat.py`. The `azd up` flow deploys the declarative agent through the Azure CLI post-provision hook and does not require the Windows `python` app alias.

### Check quota

Before deploying, verify your subscription has sufficient quota for `gpt-4o` (GlobalStandard) in your target region:

```bash
az cognitiveservices usage list --location <region> --query "[?name.value=='OpenAI.Standard.gpt-4o']"
```

---

## Quick Start

### 1. Authenticate

```bash
azd auth login
az login
```

### 2. Initialize the project

```bash
cd chapter-01
azd init
```

When prompted, choose **Use code in the current directory** and accept the detected settings.

> **Tip:** If you are starting from scratch you can also initialize from the upstream template:
> ```bash
> azd init -t Azure-Samples/azd-ai-starter-basic
> ```

### 3. Set environment variables

```bash
azd env set AZURE_LOCATION eastus2   # or any region with gpt-4o quota
azd env set AZURE_ENV_NAME my-foundry-dev
```

### 4. Provision and deploy

```bash
azd up
```

`azd up` will:

1. Run the **pre-provision hook** (`infra/scripts/preprovision.sh`) to validate tool dependencies.
2. Deploy all Bicep templates to your subscription.
3. Run the **post-provision hook** which resolves the project endpoint and search connection details, installs the Python dependencies, and calls `src/deploy_agent.py` to create or update the agent.

Expected output (abridged):

```
Packaging services (azd package)
  (✓) Done: Service foundry-qa-agent

Provisioning Azure resources (azd provision)
  (✓) Done: Resource group: rg-my-foundry-dev
  (✓) Done: Azure AI Services: aoai-<token>
  (✓) Done: AI Search: search-<token>
  (✓) Done: AI Hub: hub-<token>
  (✓) Done: AI Project: project-<token>

Deploying services (azd deploy)
  (✓) Done: Agent created: asst_abc123
```

---

## Repository Structure

```
chapter-01/
├── agent.yaml                    # Declarative agent definition
├── azure.yaml                    # Azure Developer CLI project config
├── requirements.txt              # Python dependencies
├── .env.example                  # Template for local .env file
├── README.md                     # This file
├── src/
│   ├── deploy_agent.py           # Creates/updates the Foundry agent via Python SDK
│   └── chat.py                   # Interactive CLI to chat with the agent
└── infra/
    ├── main.bicep                # Subscription-scoped entry point
    ├── main.parameters.json      # Parameter defaults (azd substitutes env vars)
    └── modules/
        ├── ai-services.bicep     # Azure AI Services + gpt-4o deployment
        ├── ai-hub.bicep          # AI Hub with connections to OpenAI & Search
        ├── ai-project.bicep      # AI Project (child of Hub)
        ├── search-service.bicep  # Azure AI Search service
        ├── storage.bicep         # Storage account (required by Hub)
        ├── keyvault.bicep        # Key Vault (required by Hub)
        └── scripts/
            ├── preprovision.sh   # Pre-provision hook (Linux/macOS)
            └── preprovision.ps1  # Pre-provision hook (Windows)
```

---

## The `agent.yaml` File

The `agent.yaml` uses the **declarative agent** format supported by Azure AI Foundry:

```yaml
name: foundry-qa-agent
model: gpt-4o
instructions: |
  You are a helpful Q&A assistant...
tools:
  - type: azure_ai_search
    azure_ai_search:
      indexes:
        - index_connection_id: ${AZURE_AI_SEARCH_CONNECTION_ID}
          index_name: ${AZURE_AI_SEARCH_INDEX_NAME}
          query_type: semantic
          top_k: 5
```

Key fields:

| Field | Description |
|-------|-------------|
| `name` | Unique agent name within the project |
| `model` | Model deployment name (must match the deployment in AI Services) |
| `instructions` | System prompt that governs agent behaviour |
| `tools[].type` | Tool type: `azure_ai_search`, `code_interpreter`, `function`, etc. |
| `azure_ai_search.indexes` | List of search indexes the agent can query |

---

## Testing the Agent

### Option A – Python scripts (recommended)

Install Python 3.10+ first, then install the project dependencies:

```bash
cd chapter-01
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the values (or they are already populated after `azd up`):

```bash
cp .env.example .env
# Edit .env with your AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_SEARCH_CONNECTION_ID
```

**Deploy (or re-deploy) the agent:**

```bash
python src/deploy_agent.py
# Creating agent 'foundry-qa-agent' …
# Agent created: asst_abc123def456
```

**Chat interactively with the agent:**

```bash
python src/chat.py

# 🤖  Chatting with agent 'foundry-qa-agent' (id=asst_abc123def456)
#     Type 'quit' or 'exit' to end the session.
#
# You: What is Azure AI Foundry?
# Agent: Azure AI Foundry is a unified platform for building, deploying, and managing
#        AI applications and agents on Microsoft Azure ...
#
# You: exit
# Session ended.
```

You can also pass the agent name explicitly:

```bash
python src/chat.py --agent-name foundry-qa-agent
```

### Option B – Azure AI Foundry Portal

1. Navigate to the [Azure AI Foundry Portal](https://ai.azure.com).
2. Select your project (`project-<token>`).
3. Open **Agents** in the left nav and click **foundry-qa-agent**.
4. Use the built-in **Playground** to send a test message.

### Option C – REST API

Retrieve the project endpoint and agent ID, then call the Responses API:

```bash
PROJECT_NAME=$(azd env get-values | grep AZURE_AI_PROJECT_NAME | cut -d= -f2 | tr -d '"')
RESOURCE_GROUP=$(azd env get-values | grep AZURE_RESOURCE_GROUP | cut -d= -f2 | tr -d '"')

# Get the project endpoint
PROJECT_ENDPOINT=$(az ml workspace show \
  --name "$PROJECT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "discovery_url" -o tsv | sed 's|/discovery||')

# Get an access token
TOKEN=$(az account get-access-token --query accessToken -o tsv)

# Send a test message (replace AGENT_ID with the ID shown in Foundry Portal)
curl -X POST "${PROJECT_ENDPOINT}/agents/v1.0/agents/${AGENT_ID}/runs" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "thread": {
      "messages": [{"role": "user", "content": "What documents are in the index?"}]
    }
  }'
```
---

## Clean Up

To remove all provisioned Azure resources:

```bash
azd down --purge
```

The `--purge` flag permanently deletes soft-delete-enabled resources (Key Vault, Cognitive Services) to avoid name conflicts on future deployments.

---

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| `QuotaExceeded` on model deployment | Reduce `modelCapacity` in `main.parameters.json` or switch region |
| `InvalidTemplate` on AI Hub | Ensure you have the `ml` CLI extension installed (`az extension add --name ml`) |
| Agent not visible in portal | Wait ~2 minutes after `azd up`; the post-provision hook may still be running |
| Search connection auth error | Verify the AI Hub's managed identity has the **Search Index Data Reader** role on the search service |

---

## References

- 📘 [Azure AI Foundry documentation](https://learn.microsoft.com/azure/ai-studio/)
- 📘 [Quickstart: Create an agent with Azure AI Foundry](https://learn.microsoft.com/azure/ai-services/agents/quickstart)
- 📘 [Azure Developer CLI (azd) overview](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview)
- 📘 [Develop AI agents on Azure AI Foundry](https://learn.microsoft.com/azure/ai-studio/how-to/develop-agents)
- 📘 [Azure AI Search – semantic ranking](https://learn.microsoft.com/azure/search/semantic-search-overview)
- 📘 [Bicep documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/overview)
