# azure-ai-agents-orchestration

This repository provides a step-by-step guide to operationalize AI agents using Azure AI Foundry and the open-source Microsoft Agent Framework. It is organized as a series of incremental "chapters" (modules), each in its own folder with dedicated instructions and sample code. You'll start by deploying a simple AI agent to Foundry and gradually build up to a sophisticated multi-agent orchestration scenario. Along the way, the repository demonstrates best practices for enterprise AI agent development — including governance, observability, and secure deployment — using Microsoft's latest tools and platforms.

## Chapters

| Chapter | Title | Description |
|---------|-------|-------------|
| [Chapter 1](./chapter-01/README.md) | Deploy Basic Foundry Agent | Deploy a simple Q&A agent to Azure AI Foundry using `agent.yaml` and the Azure Developer CLI (`azd`). Provisions an AI Hub, AI Project, Azure OpenAI model, and Azure AI Search index via Bicep IaC. |

## Getting Started

Each chapter is self-contained. Navigate to the chapter folder and follow the `README.md` instructions.

```bash
# Chapter 1 – Deploy Basic Foundry Agent
cd chapter-01
azd auth login
azd up
```

## References

- [Azure AI Foundry documentation](https://learn.microsoft.com/azure/ai-studio/)
- [Azure Developer CLI (azd)](https://learn.microsoft.com/azure/developer/azure-developer-cli/overview)
- [Microsoft Agent Framework](https://learn.microsoft.com/azure/ai-services/agents/overview)
