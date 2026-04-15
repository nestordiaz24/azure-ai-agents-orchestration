# Chapter 1 – Deploy Your First Foundry Agent

This chapter walks you through creating a simple Q&A agent on **Azure AI Foundry** using the **Azure AI Projects SDK** (`azure-ai-projects`) and the **Azure Developer CLI (`azd`)** for infrastructure.

By the end of this chapter you will have:

- An **Azure AI Hub** and **Azure AI Project** provisioned via Bicep IaC
- An **Azure OpenAI** model deployment (`gpt-4o`) inside the AI Services account
- A running **Foundry Agent** created inline by `chat.py`, with an interactive CLI you can chat with immediately

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
│  │  │   ┌─────────────────────────────────┐   │   │   │
│  │  │   │   AIProjectClient               │   │   │   │
│  │  │   │   → client.agents.create_agent  │   │   │   │
│  │  │   │   → gpt-4o                      │   │   │   │
│  │  │   └─────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────┘   │   │
│  │                                                 │   │
│  │  Connections:                                   │   │
│  │    • Azure OpenAI (gpt-4o model)               │   │
│  └─────────────────────────────────────────────────┘   │
│                                                        │
│  ┌───────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Azure OpenAI  │  │  Key Vault  │  │   Storage   │  │
│  │  (AIServices) │  │             │  │             │  │
│  └───────────────┘  └─────────────┘  └─────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | ≥ 3.10 | [python.org](https://www.python.org/downloads/) |
| Azure Developer CLI (`azd`) | ≥ 1.9.0 | [Install guide](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) |
| Azure CLI (`az`) | ≥ 2.60.0 | [Install guide](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| Azure CLI ML extension | latest | `az extension add --name ml` |

You also need:

- An **Azure subscription** with access to Azure OpenAI (`gpt-4o` or equivalent) in your target region.
- Owner or Contributor + User Access Administrator rights on the subscription/resource group.

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

### 3. Set environment variables

```bash
azd env set AZURE_LOCATION eastus2   # or any region with gpt-4o quota
azd env set AZURE_ENV_NAME my-foundry-dev
```

### 4. Provision infrastructure

```bash
azd up
```

`azd up` will:

1. Run the **pre-provision hook** to validate tool dependencies.
2. Deploy all Bicep templates to your subscription.
3. Run the **post-provision hook** to install Python dependencies.

Expected output (abridged):

```
Provisioning Azure resources (azd provision)
  (✓) Done: Resource group: rg-my-foundry-dev
  (✓) Done: Azure AI Services: aoai-<token>
  (✓) Done: AI Hub: hub-<token>
  (✓) Done: AI Project: project-<token>
```

### 5. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure environment

Copy `.env.example` to `.env` and fill in the endpoint (or they are already populated after `azd up`):

```bash
cp .env.example .env
# Edit .env with your AZURE_AI_PROJECT_ENDPOINT
```

Get the endpoint from `azd`:

```bash
azd env get-values | grep AZURE_AI_PROJECT_ENDPOINT
```

### 7. Start chatting

```bash
python src/chat.py
```

Expected output:

```
Creating agent 'foundry-qa-agent' …
Agent created: asst_abc123def456

🤖  Chatting with agent 'foundry-qa-agent' (id=asst_abc123def456)
    Type 'quit' or 'exit' to end the session.

You: What is Azure AI Foundry?
Agent: Azure AI Foundry is a unified platform for building, deploying, and managing
       AI applications and agents on Microsoft Azure …

You: exit
Session ended.

Cleaning up agent 'asst_abc123def456' …
Done.
```

---

## Repository Structure

```
chapter-01/
├── azure.yaml                    # Azure Developer CLI project config
├── requirements.txt              # Python dependencies
├── .env.example                  # Template for local .env file
├── README.md                     # This file
├── src/
│   ├── __init__.py               # Makes src a proper Python package
│   ├── config.py                 # Loads settings from environment variables
│   └── chat.py                   # Creates the agent and starts an interactive CLI
└── infra/
    ├── main.bicep                # Subscription-scoped entry point
    ├── main.parameters.json      # Parameter defaults (azd substitutes env vars)
    └── modules/
        ├── ai-services.bicep     # Azure AI Services + gpt-4o deployment
        ├── ai-hub.bicep          # AI Hub with connection to OpenAI
        ├── ai-project.bicep      # AI Project (child of Hub)
        ├── search-service.bicep  # Azure AI Search service
        ├── storage.bicep         # Storage account (required by Hub)
        ├── keyvault.bicep        # Key Vault (required by Hub)
        └── scripts/
            ├── preprovision.sh   # Pre-provision hook (Linux/macOS)
            └── preprovision.ps1  # Pre-provision hook (Windows)
```

---

## Code Walkthrough

### `src/config.py`

Loads settings from environment variables (with `.env` file support):

```python
from src.config import get_settings

settings = get_settings()
# settings.azure_ai_project_endpoint  → AZURE_AI_PROJECT_ENDPOINT
# settings.azure_openai_deployment    → AZURE_OPENAI_DEPLOYMENT (default: gpt-4o)
# settings.agent_name                 → AGENT_NAME (default: foundry-qa-agent)
```

This pattern is extended in Chapter 2 with additional settings for tools and the API server.

### `src/chat.py`

The agent is created using the **Azure AI Projects SDK**:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient(
    endpoint=settings.azure_ai_project_endpoint,
    credential=DefaultAzureCredential(),
)

agent = client.agents.create_agent(
    model=settings.azure_openai_deployment,
    name=settings.agent_name,
    instructions="You are a helpful Q&A assistant …",
)
```

Multi-turn conversations use **threads**:

```python
thread = client.agents.create_thread()

# Each turn:
client.agents.create_message(thread_id=thread.id, role=MessageRole.USER, content=question)
run = client.agents.create_run(thread_id=thread.id, agent_id=agent.id)

# Poll until complete
while run.status in (RunStatus.QUEUED, RunStatus.IN_PROGRESS):
    time.sleep(0.5)
    run = client.agents.get_run(thread_id=thread.id, run_id=run.id)

# Read the reply
messages = client.agents.list_messages(thread_id=thread.id)
```

---

## What's Next

In **Chapter 2**, you'll extend this exact pattern by:

- Adding **custom Python function tools** (product catalog lookup) to the agent
- Wrapping the agent in a **FastAPI web server** for HTTP access
- Packaging it in a **Docker container** for deployment

The `AIProjectClient`, `create_agent()`, `create_thread()`, and polling patterns you learned here are the foundation for Chapter 2.  Chapter 2 introduces the **Microsoft Agent Framework** (`agent-framework` package) as an evolution: it replaces the manual polling loop with the `Agent` class and `@tool` decorator, while continuing to use Azure AI Foundry for model hosting.

---

## Testing the Agent

### Option A – CLI chat (recommended)

```bash
python src/chat.py
```

### Option B – Azure AI Foundry Portal

1. Navigate to the [Azure AI Foundry Portal](https://ai.azure.com).
2. Select your project (`project-<token>`).
3. Open **Agents** in the left nav and find your agent.
4. Use the built-in **Playground** to send a test message.

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
| `AZURE_AI_PROJECT_ENDPOINT is not set` | Run `azd env get-values \| grep AZURE_AI_PROJECT_ENDPOINT` and add it to your `.env` file |
| Agent not visible in portal | Wait ~30 seconds after running `chat.py`; the agent is created on first run |

---

## References

- 📘 [Azure AI Foundry documentation](https://learn.microsoft.com/azure/ai-studio/)
- 📘 [Quickstart: Create an agent with Azure AI Foundry](https://learn.microsoft.com/azure/ai-services/agents/quickstart)
- 📘 [azure-ai-projects SDK reference](https://learn.microsoft.com/python/api/overview/azure/ai-projects-readme)
- 📘 [Azure Developer CLI (azd) overview](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview)
- 📘 [Bicep documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/overview)
