# AGENTS.md

## Repository Scope and Goals
- This repository contains a multi-agent orchestration demo using Microsoft’s AI platforms.
- It is organized into sequential **chapters** (each chapter adds a new capability or agent).
- The target scenario is a **unified support and sales assistant** (fictitious company example) – it can answer technical questions and recommend products.

## Setup & Dependencies
- **Language & Tools:** Python 3.10+ required. Code is written in Python (use PEP 8 style).
- **Local Development:** Ensure you have https://learn.microsoft.com/azure/developer/azure-developer-cli/overview installed for provisioning Azure resources.
- **Azure AI Foundry:** Install the Azure Developer CLI Foundry extension (e.g., `az extension add --name ml`). Use `az login` to authenticate Azure, then `azd up` to deploy services as defined.
- **Python Dependencies:** Use `pip install agent-framework` to get the Microsoft Agent Framework SDK. For local runs, the project may use a `requirements.txt` or `poetry`/`pipenv` – ensure Agent Framework and any needed libraries are installed.

## Project Structure
- `chapter1-basic-agent/` – Example initial agent (e.g., Q&A support agent). Likely uses Azure AI Foundry (declarative YAML configuration in `agent.yaml`).
- `chapter2-second-agent/` – Second agent (e.g., recommendation agent), possibly code-driven with Agent Framework, including source code and Dockerfile.
- `chapter3-orchestrator/` – Orchestrator agent that coordinates multiple agents.
- `chapter4-advanced/` – Advanced patterns and integration (e.g., parallel execution, logging, etc.).
- `.ai/` – AI agent guidance folder (this folder). Contains context, specs, and memory for AI to reference when generating code.
- Other standard folders (e.g., `src/`, `data/`, `docs/`, `infra/`, `tests/`) as needed per chapter.

## Coding & Style Guidelines
- **Coding Style:** Follow Python best practices (PEP 8). Use clear, descriptive naming for files, variables, classes, and functions.
- **Type Annotations:** Use Python type hints for function signatures and major variables to improve code clarity and assist with static analysis.
- **Documentation:** Every public class or function should have a concise docstring explaining its purpose. Update README files in each chapter to reflect new features.
- **Error Handling:** Anticipate common error conditions (e.g., missing data, invalid inputs) and handle them gracefully (raising exceptions or returning error messages) rather than failing silently.
- **Security:** *No real credentials or proprietary data* should appear in code or config. Use placeholders and environment variables. Commit an `.env.example` file if needed to show required environment variables (with dummy values).

## Testing & Verification
- **Manual test scenario:** After implementing each agent, perform a simple verification. For example, after Chapter 1, call the Q&A agent with a sample query to ensure it returns a plausible answer.
- **Automated tests:** If a `tests/` directory is present, run `pytest` or `unittest` as appropriate. All tests should pass.
- **Linting:** Use flake8 or pylint if configured (ensure code has no linter errors).
- **Continuous Integration:** If GitHub Actions or other CI workflows are configured (see `.github/workflows/`), ensure that pipeline passes after each change.

## Workflow and Autonomy
- Work on **one issue (chapter) at a time**. See the spec in `.ai/issue-<N>.md` for requirements.
- After completing a chapter, update `.ai/memory.md` with what was done and any new insights or remaining TODOs.
- If new issues or enhancements are identified, you can create additional spec files under `.ai/` (and corresponding GitHub issues if applicable).
- Strive to minimize human intervention by relying on the provided context and these instructions.
- Keep commits and PRs atomic per chapter. Use clear commit messages referencing the issue (e.g., `Fix #2: Implement product recommendation agent`).

## Data and Content Guidelines
- Use only **synthetic data** and generic placeholders in all examples and code. For instance, use generic names like “Alice” or “AcmeCorp” if you need to create sample users or organizations. Use fictional product names (e.g. “ProductX”) for any sample product data.
- Do not include any references to real companies, proprietary technologies, or internal identifiers. This project should remain technology-focused and generally applicable to any enterprise.
- If you need to demonstrate database or API integration, simulate it. For example, use a local JSON file or an in-memory list to stand in for a database, or create a mock function that represents an external API call (without making real network requests).

## Memory and State
- The file `.ai/memory.md` is used as a **persistent memory log**. Use it to record key decisions, context learned, and summaries of completed work. This helps ensure continuity across sessions.
- The memory file can be free-form, but consider using timestamps or chapter headers to separate entries.
- Only include non-sensitive, relevant information in memory. Do not copy entire code or large text into memory; instead, summarize important details or unresolved questions.

## Additional Notes
- This project is for demonstration and learning. The focus is on correctness, clarity, and best practices, not on shipping a production system.
- Document any deviations from these guidelines in the memory or in commit messages to keep stakeholders informed.