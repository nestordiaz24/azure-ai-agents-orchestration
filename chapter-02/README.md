# Chapter 2 – Product Recommendation Agent (Code-First)

This chapter introduces a **code-first agent** built with the
[Microsoft Agent Framework SDK](https://learn.microsoft.com/azure/ai-services/agents/overview)
(`azure-ai-projects`). The agent uses a **product catalog lookup tool** to answer
user queries about AcmeCorp products and recommend complementary solutions.

By the end of this chapter you will have:

- A Python agent that registers and calls a custom **function tool**
- A **FastAPI** HTTP server exposing the agent over REST (`POST /recommend`, `POST /chat`)
- An **interactive CLI** for local testing without Azure credentials
- A **Dockerfile** and `docker-compose.yaml` for containerised deployment
- A comparison of the declarative approach (Chapter 1) versus the code-first approach (Chapter 2)

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

The agent is created with the **Azure AI Agents SDK** pattern:

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, ToolSet

client = AIProjectClient(endpoint=..., credential=DefaultAzureCredential())

toolset = ToolSet()
toolset.add(FunctionTool(functions={"search_products", "get_recommendations", ...}))

agent = client.agents.create_agent(
    model="gpt-4o",
    name="product-recommendation-agent",
    instructions=AGENT_INSTRUCTIONS,
    toolset=toolset,
)
```

Multi-turn conversations use **threads**:

```python
thread = client.agents.create_thread()
client.agents.create_message(thread_id=thread.id, role="user", content=question)
run = client.agents.create_run(thread_id=thread.id, agent_id=agent.id)
```

When the model decides to call a tool, the run enters
`REQUIRES_ACTION` status.  The agent class polls for this, dispatches
the tool call to the local Python function, and submits the output back:

```python
while run.status == RunStatus.REQUIRES_ACTION:
    outputs = self._execute_tool_calls(run.required_action.submit_tool_outputs.tool_calls)
    run = client.agents.submit_tool_outputs_to_run(
        thread_id=thread.id, run_id=run.id, tool_outputs=outputs
    )
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

| Aspect | Chapter 1 – Declarative Agent | Chapter 2 – Code-First Agent |
|--------|-------------------------------|-------------------------------|
| **SDK / approach** | `agent.yaml` (declarative) | `azure-ai-projects` Python SDK |
| **Tools** | Azure AI Search (built-in) | Custom Python function tool |
| **Deployment** | `azd up` → Foundry managed | Docker container / Azure Container Apps |
| **Control** | Low (config-only) | High (arbitrary Python logic) |
| **Local dev** | Requires Azure | Catalog tool works offline |
| **Multi-turn** | Thread managed by Foundry | Thread managed in code |
| **Observability** | Foundry portal logs | Container stdout / Azure Monitor |
| **Best suited for** | Simple RAG Q&A | Complex workflows, custom data |

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

- 📘 [Azure AI Agents overview](https://learn.microsoft.com/azure/ai-services/agents/overview)
- 📘 [Quickstart: Create an agent (Python)](https://learn.microsoft.com/azure/ai-services/agents/quickstart?pivots=programming-language-python-azure)
- 📘 [azure-ai-projects SDK reference](https://learn.microsoft.com/python/api/azure-ai-projects)
- 📘 [Function tool calling](https://learn.microsoft.com/azure/ai-services/agents/how-to/tools/function-calling)
- 📘 [Hosted agents on Azure Container Apps](https://learn.microsoft.com/azure/ai-services/agents/how-to/hosted-agents/overview)
- 📘 [FastAPI documentation](https://fastapi.tiangolo.com/)
- 📘 [Azure Container Apps documentation](https://learn.microsoft.com/azure/container-apps/overview)
