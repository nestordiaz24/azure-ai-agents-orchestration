# Chapter 2 – Product Recommendation Agent (Microsoft Agent Framework)

This chapter introduces the **Microsoft Agent Framework** (`agent-framework` Python package)
as an evolution of the raw Azure AI Foundry Agents API used in Chapter 1.  The agent uses a
**product catalog lookup tool** to answer user queries about AcmeCorp products and recommend
complementary solutions.

**What's new compared to Chapter 1:**

| Aspect | Chapter 1 (raw Foundry API) | Chapter 2 (Agent Framework) |
|--------|-----------------------------|-----------------------------|
| **Package** | `azure-ai-projects` | `agent-framework` + `azure-ai-projects` |
| **Agent class** | `client.agents.create_agent()` (server-side) | `Agent(client, instructions, tools)` (local) |
| **Tool registration** | Raw JSON schema + manual dispatch dict | `@tool` decorator — schema inferred automatically |
| **Run management** | Manual polling loop (`while run.status …`) | Framework-managed; just `await agent.run(msg)` |
| **Conversation state** | `AgentThread` managed via SDK calls | `AgentSession` returned by `agent.create_session()` |
| **Model connection** | `AIProjectClient` → `create_run()` | `FoundryChatClient` wraps `AIProjectClient` |

By the end of this chapter you will have:

- A Python agent that registers custom **function tools** using the `@tool` decorator
- A **FastAPI** HTTP server exposing the agent over REST (`POST /recommend`, `POST /chat`)
- An **interactive CLI** for local testing without Azure credentials
- A **Dockerfile** and `docker-compose.yaml` for containerised deployment

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        chapter-02                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  FastAPI Server (api.py)              │   │
│  │                                                      │   │
│  │  POST /recommend   POST /chat   GET /health           │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │          RecommendationAgent (recommendation_agent.py)│   │
│  │                                                      │   │
│  │  • Creates agent in Azure AI Foundry (once)          │   │
│  │  • Manages conversation threads (multi-turn)         │   │
│  │  • Dispatches tool calls back to Python              │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │  tool calls                       │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │          ProductCatalog Tool (product_catalog.py)     │   │
│  │                                                      │   │
│  │  search_products(query)                              │   │
│  │  get_recommendations(product_id)                     │   │
│  │  list_all_products()                                 │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │          data/products.json  (synthetic catalog)      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│           ┌─────────────────────────────────┐              │
│           │  Azure AI Foundry Project       │              │
│           │  (gpt-4o model deployment)      │              │
│           └─────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| Docker | any recent | [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| Azure CLI | ≥ 2.60.0 | [Install guide](https://learn.microsoft.com/cli/azure/install-azure-cli) |

For the **agent mode** (Azure-hosted AI), you also need:

- An **Azure AI Foundry** project with a `gpt-4o` model deployment
- The project endpoint URL (format: `https://<name>.services.ai.azure.com/api/projects/<id>`)
- Azure credentials configured (e.g., `az login` for `DefaultAzureCredential`)

> **Tip:** You can run the catalog tool and the `/recommend` endpoint **without** any Azure
> credentials.  Only `POST /chat` and `python src/chat.py --mode agent` require an Azure connection.

---

## Repository Structure

```
chapter-02/
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
├── .env.example                     # Template for local .env file
├── Dockerfile                       # Container image
├── docker-compose.yaml              # Local dev convenience
├── data/
│   └── products.json                # Synthetic AcmeCorp product catalog
├── src/
│   ├── __init__.py
│   ├── config.py                    # Environment variable loader
│   ├── product_catalog.py           # Pure-Python product lookup tool
│   ├── recommendation_agent.py      # Azure AI Agents SDK agent
│   ├── api.py                       # FastAPI REST server
│   └── chat.py                      # Interactive CLI
└── tests/
    ├── __init__.py
    └── test_product_catalog.py      # Unit tests for the catalog tool
```

---

## Quick Start

### 1. Install dependencies

```bash
cd chapter-02
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env – fill in AZURE_AI_PROJECT_ENDPOINT for agent mode
```

### 3. Start the API server

```bash
uvicorn src.api:app --reload --port 8000
```

### 4. Test the `/recommend` endpoint (no Azure needed)

```bash
curl -s -X POST http://localhost:8000/recommend \
     -H "Content-Type: application/json" \
     -d '{"query": "monitoring infrastructure"}' | python -m json.tool
```

Sample response:

```json
{
  "query": "monitoring infrastructure",
  "results": [
    {
      "id": "ACME-MON-001",
      "name": "AcmeCorp CloudMonitor Pro",
      "description": "Real-time infrastructure monitoring platform ...",
      "category": "monitoring",
      "tags": ["monitoring", "cloud", "ai", "alerting", "infrastructure"],
      "price": 299.99
    }
  ],
  "total": 4
}
```

### 5. Interactive CLI (catalog mode – no Azure required)

```bash
python src/chat.py
# or explicitly:
python src/chat.py --mode catalog

# 🤖  AcmeCorp Product Recommendation Agent
#     Mode: catalog
#     (Running in catalog mode – no Azure credentials required)
#     Type 'quit' or 'exit' to end the session.
#
# You: What security products do you offer?
# Agent: Matching products:
#   • [ACME-SEC-006] AcmeCorp SecureVault IAM – $399.99
#     ...
```

### 6. Interactive CLI (agent mode – requires Azure)

```bash
python src/chat.py --mode agent
```

---

## Running Tests

```bash
# From the chapter-02 directory
pip install pytest
pytest tests/ -v
```

Tests in `tests/test_product_catalog.py` cover:
- `search_products()` – keyword matching, ranking, edge cases
- `get_recommendations()` – related products, tag similarity, deduplication
- `list_all_products()` – catalog completeness
- Error conditions – missing file, invalid JSON
- Integration – real `data/products.json`

---

## Docker Deployment

### Build and run locally

```bash
docker build -t acmecorp-recommendation-agent .
docker run -p 8000:8000 \
  -e AZURE_AI_PROJECT_ENDPOINT="$AZURE_AI_PROJECT_ENDPOINT" \
  -e AZURE_OPENAI_DEPLOYMENT=gpt-4o \
  acmecorp-recommendation-agent
```

### Docker Compose

```bash
# Copy .env.example to .env and fill in values, then:
docker-compose up --build
```

The service exposes `http://localhost:8000`.

---

## Code Walkthrough

### 1. Product Catalog Tool (`src/product_catalog.py`)

The tool is a plain Python module with three public functions:

```python
def search_products(query: str, ...) -> list[dict]:
    """Keyword search across name, description, category, tags."""
    ...

def get_recommendations(product_id: str, ...) -> list[dict]:
    """Related products by explicit links + shared tags."""
    ...

def list_all_products(...) -> list[dict]:
    """Return the full catalog."""
    ...
```

The catalog data lives in `data/products.json`.  No external API is called –
this is the "simulated external integration" pattern described in `AGENTS.md`.

### 2. Recommendation Agent (`src/recommendation_agent.py`)

Chapter 2 introduces the **Microsoft Agent Framework** to replace the manual
polling pattern from Chapter 1.

#### Step 1 – Register tools with `@tool`

Instead of defining raw JSON schemas and a manual dispatch dictionary, each
catalog function is decorated with `@tool`.  The framework infers the JSON
schema from the type annotations automatically:

```python
from agent_framework import tool
from typing import Annotated

@tool
def search_products_tool(
    query: Annotated[str, "Keywords describing the desired product or capability"],
) -> str:
    """Search the AcmeCorp product catalog for products matching the query."""
    import json
    results = search_products(query)
    return json.dumps({"results": results})

@tool
def get_recommendations_tool(
    product_id: Annotated[str, "The exact product ID (e.g., ACME-MON-001)"],
) -> str:
    """Return products recommended as companions to the given product ID."""
    ...

@tool
def list_all_products_tool() -> str:
    """Return all products in the AcmeCorp catalog."""
    ...
```

#### Step 2 – Construct the agent locally

`FoundryChatClient` connects to the Azure AI Foundry model deployment.  The
`Agent` class wires together the client, instructions, and tools — no remote
`create_agent()` call, no thread management:

```python
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential

client = FoundryChatClient(
    project_endpoint="https://your-project.services.ai.azure.com/...",
    model="gpt-4o",
    credential=DefaultAzureCredential(),
)

agent = Agent(
    client=client,
    instructions=AGENT_INSTRUCTIONS,
    tools=[search_products_tool, get_recommendations_tool, list_all_products_tool],
    name="product-recommendation-agent",
)
```

#### Step 3 – Manage conversation with `AgentSession`

`AgentSession` replaces the raw `AgentThread`.  The framework handles history,
tool dispatch, and run lifecycle internally:

```python
from agent_framework import AgentSession

session: AgentSession = agent.create_session()

# Each turn – no polling loop required
response = await agent.run("What monitoring products do you offer?", session=session)
print(response.text)
```

The complete `chat()` method in `RecommendationAgent` is now just:

```python
async def chat(self, message: str) -> str:
    response = await agent.run(message, session=self._get_session())
    return response.text or "[No response from agent]"
```

Compare this to the Chapter 1 approach which required explicit polling:

```python
# Chapter 1 pattern (replaced by Agent Framework in Chapter 2)
while run.status in (RunStatus.QUEUED, RunStatus.IN_PROGRESS, RunStatus.REQUIRES_ACTION):
    if run.status == RunStatus.REQUIRES_ACTION:
        outputs = self._execute_tool_calls(...)
        run = client.agents.submit_tool_outputs_to_run(...)
    else:
        time.sleep(0.5)
        run = client.agents.get_run(...)
```

### 3. FastAPI Server (`src/api.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness check |
| `/recommend` | POST | Catalog keyword search (no Azure) |
| `/chat` | POST | Multi-turn agent conversation |
| `/catalog` | GET | Full product list |
| `/catalog/{id}/recommendations` | GET | Related products |

---

## Chapter 1 vs Chapter 2 Comparison

| Aspect | Chapter 1 – Raw Foundry API | Chapter 2 – Agent Framework |
|--------|-----------------------------|-----------------------------|
| **Package** | `azure-ai-projects` | `agent-framework` + `azure-ai-projects` |
| **Agent creation** | `client.agents.create_agent()` (server-side) | `Agent(client, instructions, tools)` (local) |
| **Tool registration** | Raw JSON schema + manual dispatch dict | `@tool` decorator — schema auto-inferred |
| **Run management** | Manual polling loop (`while run.status …`) | Framework-managed; `await agent.run(msg)` |
| **Conversation state** | `AgentThread` via SDK calls | `AgentSession` from `agent.create_session()` |
| **Model connection** | `AIProjectClient` directly | `FoundryChatClient` wrapping `AIProjectClient` |
| **Tools** | `FunctionTool` + `ToolSet` | `@tool`-decorated Python functions |
| **Local dev** | Requires Azure | Catalog tool works offline |
| **Observability** | Foundry portal logs | Built-in OpenTelemetry via Agent Framework |
| **Best suited for** | Simple RAG Q&A, learning Foundry | Custom tools, clean agent abstractions |

---

## Deploy to Azure Container Apps

```bash
# Build and push the image to Azure Container Registry
az acr build --registry <your-acr> --image recommendation-agent:latest .

# Deploy to Azure Container Apps
az containerapp create \
  --name recommendation-agent \
  --resource-group <rg> \
  --environment <env-name> \
  --image <your-acr>.azurecr.io/recommendation-agent:latest \
  --ingress external \
  --target-port 8000 \
  --env-vars \
      AZURE_AI_PROJECT_ENDPOINT=<endpoint> \
      AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

---

## References

- 📘 [Microsoft Agent Framework overview](https://learn.microsoft.com/en-us/agent-framework/overview/)
- 📘 [Microsoft Agent Framework – GitHub](https://github.com/microsoft/agent-framework)
- 📘 [Azure AI Agents overview](https://learn.microsoft.com/azure/ai-services/agents/overview)
- 📘 [Quickstart: Create an agent (Python)](https://learn.microsoft.com/azure/ai-services/agents/quickstart?pivots=programming-language-python-azure)
- 📘 [azure-ai-projects SDK reference](https://learn.microsoft.com/python/api/azure-ai-projects)
- 📘 [Function tool calling](https://learn.microsoft.com/azure/ai-services/agents/how-to/tools/function-calling)
- 📘 [Hosted agents on Azure Container Apps](https://learn.microsoft.com/azure/ai-services/agents/how-to/hosted-agents/overview)
- 📘 [FastAPI documentation](https://fastapi.tiangolo.com/)
- 📘 [Azure Container Apps documentation](https://learn.microsoft.com/azure/container-apps/overview)
