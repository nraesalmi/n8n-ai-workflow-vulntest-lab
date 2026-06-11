# AI Workflow Security Research Lab

**Security of low-code AI agent workflow platforms under prompt-injection and execution graph manipulation**

A controlled experimental framework for studying how prompt-injection-class attacks propagate through node-based AI workflow systems (n8n), where LLM outputs are compiled into executable workflow graphs with external side effects. Contains **20 attack workflows** (10 scenarios x baseline/guardrail variants) and **1 reusable security sub-workflow scaffold**, targeting 7 OWASP LLM categories across escalating attack complexity.

---

## Research Context

### Premise

Low-code automation systems such as n8n expose a fundamentally different attack surface compared to conversational chatbots. LLM outputs in these systems are not merely rendered as text — they are compiled into executable workflow graphs with real external side effects: database writes, HTTP calls, tool invocations, and control-flow decisions.

While prompt injection is well-studied in chat-based systems, there is limited understanding of how these attacks generalise when the model output becomes a **control plane for tool execution, branching logic, and stateful automation** across multiple execution contexts.

### Thesis

Prompt-injection-class attacks can propagate through workflow-based AI systems where trust boundaries are implicit and often span multiple nodes, credentials, and external integrations.

| Attack Class | Description | OWASP LLM |
|---|---|---|
| **Direct Prompt Injection** | Adversarial input embedded in user message overrides system instructions | LLM01 |
| **Indirect Prompt Injection** | Payloads hidden in upstream data (web pages, databases, email) activate when the LLM processes them | LLM01 |
| **Insecure Output Handling** | LLM output containing code or commands is passed directly to an executor (shell, eval) | LLM02 |
| **Tool / Agency Hijacking** | LLM output induces unintended tool calls — database mutations, HTTP requests, credential exfiltration | LLM06 |
| **Memory Poisoning** | Injected data persisted in LLM memory (buffer window, vector store) and re-activated across turns | LLM04/LLM08 |
| **System Prompt Extraction** | Crafted inputs that cause the LLM to leak its own system prompt or instructions | LLM07 |
| **Agent Looping** | Recursive self-triggering via output channels leading to resource exhaustion | LLM10 |
| **Multi-Hop Trust Escalation** | A chain of agents or tool calls where each step escalates privileges based on prior LLM output | Composite |

A central research question is whether traditional LLM safety mitigations (system prompts, output filtering, basic guardrails) remain effective once outputs are interpreted as **structured execution instructions** rather than natural language responses — particularly when injected data crosses trust boundaries between nodes, workflows, and execution contexts.

---

## Architecture

### Docker Services

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Docker Network                                  │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │              │    │              │    │              │              │
│  │     n8n      │───▶│  PostgreSQL  │    │    Ollama    │              │
│  │    :5678     │    │   :5432      │    │   :11434     │              │
│  │              │◀───│              │    │              │              │
│  └───┬────┬─────┘    └──────────────┘    └──────────────┘              │
│      │    │                                                            │
│      │    └──────────┐                                                 │
│      │               ▼                                                 │
│      │    ┌──────────────────┐                                         │
│      │    │    mockapi       │                                         │
│      │    │    :3000         │   (json-server — document corpus)       │
│      │    └──────────────────┘                                         │
│      │                                                                 │
│                                                                        │
│  ┌────────────────────────────────────────────────────┐                │
│  │  n8n/inputs/ → /data/inputs/  (payload file)      │               │
│  │  n8n/outputs/ → /data/outputs/ (run results)      │               │
│  └────────────────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────────────────┘
```

In addition to Docker services, two supporting Python servers can be run locally:

| Service | Port | Purpose |
|---|---|---|
| n8n | 5678 | Workflow orchestration engine and UI |
| PostgreSQL | 5432 | n8n state + `agent_messages` table |
| Ollama | 11434 | Local LLM inference (fallback / air-gapped mode) |
| mockapi | 3000 | `json-server` — serves mock documents, FAQs, notifications |
| Mock Server (Python) | 8080 | Flask server — 15+ endpoints for indirect injection experiments |
| Attacker Listener | 9999 | Flask server — captures exfiltrated data during experiments |

### Multi-Model LLM Backend

All workflows use the OpenAI-compatible `lmChatOpenAi` node, which works with any provider offering an OpenAI-compatible API:

| Provider | LLM_BASE_URL | LLM_MODEL |
|---|---|---|
| OpenAI | *(empty — defaults to api.openai.com)* | gpt-4o, gpt-4o-mini, ... |
| OpenCode | https://api.opencode.ai/v1 | opencode/deepseek-v4-flash-free, ... |
| OpenRouter | https://openrouter.ai/api/v1 | openai/gpt-4o, anthropic/claude-3, ... |
| Ollama | http://ollama:11434/v1 | mistral, llama3, ... |

Model and base URL are configured via environment variables and injected at runtime via n8n expressions (`{{ $env.LLM_MODEL }}`, `{{ $env.LLM_BASE_URL }}`). The batch patcher script (`scripts/patch_workflow_models.py`) stamps these expressions into all workflow JSONs. No model-specific node types are needed.

---

## Workflow Attack Scenarios

All 10 scenarios exist in two variants per subdirectory:

| # | Scenario | OWASP | Baseline | Guardrail | Trigger |
|---|----------|-------|----------|-----------|---------|
| 01 | Direct Prompt Injection | LLM01 | `baseline/wf_01_direct_injection_baseline.json` | `basic_guardrail/wf_01_direct_injection_guardrail.json` | Manual |
| 02 | Indirect Injection (Web) | LLM01 | `baseline/wf_02_indirect_webscrape_baseline.json` | `basic_guardrail/wf_02_indirect_webscrape_guardrail.json` | Manual |
| 03 | Indirect Injection (DB) | LLM01 | `baseline/wf_03_indirect_email_db_baseline.json` | `basic_guardrail/wf_03_indirect_email_db_guardrail.json` | Manual |
| 04 | Code Execution via LLM | LLM02/05 | `baseline/wf_04_code_execution_baseline.json` | `basic_guardrail/wf_04_code_execution_guardrail.json` | Manual |
| 05 | Excessive Agency / Tool Hijack | LLM06 | `baseline/wf_05_excessive_agency_baseline.json` | `basic_guardrail/wf_05_excessive_agency_guardrail.json` | Manual |
| 06 | Credential Exfiltration | LLM02/07 | `baseline/wf_06_credential_exfiltration_baseline.json` | `basic_guardrail/wf_06_credential_exfiltration_guardrail.json` | Manual |
| 07 | System Prompt Extraction | LLM07 | `baseline/wf_07_system_prompt_extraction_baseline.json` | `basic_guardrail/wf_07_system_prompt_extraction_guardrail.json` | Manual |
| 08 | Vector Store Poisoning | LLM04/08 | `baseline/wf_08_vector_store_poisoning_baseline.json` | `basic_guardrail/wf_08_vector_store_poisoning_guardrail.json` | Manual (Phase A + Phase B) |
| 09 | Agent Loop / Resource Exhaustion | LLM10 | `baseline/wf_09_agent_loop_baseline.json` | `basic_guardrail/wf_09_agent_loop_guardrail.json` | Manual |
| 10 | Multi-Hop Trust Escalation | Composite | `baseline/wf_10_multihop_trust_escalation_baseline.json` | `basic_guardrail/wf_10_multihop_trust_escalation_guardrail.json` | Manual |

### Custom Security Node

| File | Purpose |
|---|---|
| `custom_guardrail/wf_custom_security_node_scaffold.json` | 7-module security sub-workflow (injection detection, schema validation, rate limiting, output sanitization, anomaly detection, logging, alerting) — callable via Execute Workflow node |

### Attack Escalation Path

The workflows form a natural progression for systematic research:

```
wf_01 ── Direct injection into chat                     [single node, no persistence]
  │
  ├── wf_02 ── Indirect injection via web scrape         [external data source introduced]
  ├── wf_03 ── Indirect injection via database row       [persistent storage introduced]
  │
wf_04 ── Code execution from LLM output                 [insecure output handling]
wf_05 ── Tool hijacking / excessive agency               [multiple tools connected]
wf_06 ── Credential exfiltration                          [targeted data extraction]
wf_07 ── System prompt extraction                         [multi-turn memory exploitation]
  │
  ├── wf_08 ── Vector store poisoning                    [semantic memory poisoning]
  │
wf_09 ── Agent loop / resource exhaustion                 [denial of service via agent]
wf_10 ── Multi-hop trust escalation                       [cross-agent privilege chains]
```

---

## Setup

### Prerequisites

- Docker and Docker Compose v2
- 8 GB RAM minimum (16 GB recommended)
- (Optional) API key for your chosen LLM provider

### Step 1: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Required: generate a secure random 32-character key
N8N_ENCRYPTION_KEY=<your-random-key>

# Required: set a strong password
POSTGRES_PASSWORD=<your-postgres-password>

# LLM Backend Configuration
# Uncomment and set at least ONE API key:
OPENCODE_API_KEY=sk-...          # or
#OPENAI_API_KEY=sk-...           # or
#OPENROUTER_API_KEY=sk-...       #

# Set the model and base URL for your provider:
LLM_BASE_URL=https://api.opencode.ai/v1
LLM_MODEL=opencode/deepseek-v4-flash-free
```

**Important:** Ensure `N8N_ENCRYPTION_KEY` is at least 32 characters. n8n will refuse to start with a weak encryption key when using PostgreSQL.

### Step 2: Start Services

```bash
docker compose up -d
```

This starts n8n (port 5678), PostgreSQL (port 5432), Ollama (port 11434), and mockapi (port 3000).

### Step 3: (Optional) Pull Ollama Model

Only needed if using Ollama as your LLM backend (air-gapped mode):

```bash
./scripts/pull-model.sh        # pulls the model from .env OLLAMA_MODEL
./scripts/pull-model.sh llama3  # or specify a different model
```

### Step 4: Import Credentials and Workflows

```bash
# Linux / macOS
./scripts/setup.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

The setup script will:
- Wait for n8n to be healthy
- Generate credential JSON files with UUIDs and import them
- Import all workflow JSONs from `baseline/`, `basic_guardrail/`, and `custom_guardrail/` subdirectories
- Delete any stale workflows from previous imports

### Step 5: Start Supporting Services

For indirect injection and exfiltration experiments, start these local servers:

```bash
# Terminal 1: Mock API server (serves endpoints for wf_02, wf_03, etc.)
python test-servers/mock_server.py

# Terminal 2: Attacker listener (captures exfiltrated data for wf_01, wf_06, etc.)
python test-servers/attacker_listener.py
```

### Step 6: Run Workflows

All workflows import in **inactive** state and use **Manual Trigger** with file-based I/O:

1. Write your payload to `n8n/inputs/current_payload.json` (see `n8n/workflows/test_payloads.json` for examples)
2. Open the workflow in n8n editor (`http://localhost:5678`)
3. Click **Execute Workflow**
4. Result is written to `n8n/outputs/` as a timestamped JSON file

---

## Running Experiments

### Quick Start

1. Ensure all services are running (Docker + supporting servers)
2. Activate one or more workflows in n8n
3. Write test payloads to `n8n/inputs/current_payload.json` (see `test_payloads.json`)
4. Click **Execute Workflow** in the n8n editor
5. Check `n8n/outputs/` for run results
6. Watch execution logs and check for attack success indicators

### Attack Payloads

A comprehensive payload library is at `n8n/workflows/test_payloads.json` containing **46+ attack payloads** organized by workflow with severity ratings (high/medium/low), expected success indicators, and injection techniques. Payloads cover:

- Explicit instruction override
- System prompt extraction attempts
- Role-play / developer mode impersonation
- Delimiter injection / format breaking
- Base64 / hex / encoded payloads
- Tool call injection and hallucination
- Multi-turn extraction chains
- Indirect payloads (web pages, database rows, email bodies)

### Experiment Run Configuration

`n8n/workflows/experiment_run_config.json` defines standardized run parameters:

- 30 runs per configuration
- 2 LLM backends per run series
- Per-workflow payload assignments
- Success criteria definitions
- Metrics to collect per run

### Reproducibility

All LLM nodes use **temperature = 0** for deterministic outputs. For cross-session reproducibility:
- Use the same API key and model
- Pin n8n version via `N8N_VERSION` in `.env`
- Run each payload 30 times per LLM backend per workflow variant
- Record all outputs via the Log Execution Metadata terminal node

### Logging

```bash
# Watch n8n execution logs
docker compose logs -f n8n

# List recent workflow run outputs
ls -t n8n/outputs/

# Check downloaded Ollama models
docker exec n8n-ollama ollama list

# Check model patching status
python scripts/patch_workflow_models.py
```

---

## Project Structure

```
.
├── docker-compose.yml              # CPU-only compose
├── docker-compose.gpu.yml          # GPU override overlay (NVIDIA)
├── CLAUDE.md                       # Project-level AI assistant instructions
├── .env.example                    # Environment variable template
├── .gitignore
├── README.md                       # This file
│
├── n8n/
│   ├── inputs/
│   │   └── current_payload.json    # Shared input payload file (mounted at /data/inputs/)
│   ├── outputs/                    # Workflow run outputs (mounted at /data/outputs/)
│   └── workflows/
│       ├── README.md               # Workflow-specific documentation
│       ├── test_payloads.json      # 46+ attack payloads across 10 scenarios
│       ├── experiment_run_config.json  # Standardized run parameters
│       ├── baseline/               # 10 unprotected attack workflows
│       ├── basic_guardrail/        # 10 n8n built-in guardrail variants
│       └── custom_guardrail/       # Reusable security sub-workflow scaffold
│
├── postgres/
│   └── init/
│       └── 01-init.sql             # agent_messages table schema
│
├── mockapi/
│   └── db.json                     # json-server document corpus
│
├── test-servers/
│   ├── mock_server.py              # Flask server (15+ endpoints, port 8080)
│   └── attacker_listener.py        # Flask exfiltration listener (port 9999)
│
├── research/
│   ├── architecture/
│   │   └── architecture-diagram.md # System architecture documentation
│   ├── experiments/
│   │   └── experiment-notes-template.md  # Experiment notebook template
│   └── inventory/
│       └── workflow-inventory-template.md  # Workflow catalog template
│
└── scripts/
    ├── setup.sh                    # Credential + workflow import (Linux/macOS)
    ├── setup.ps1                   # Credential + workflow import (Windows)
    ├── pull-model.sh               # Ollama model download
    ├── batch_runner.py             # Automated experiment runner (n8n REST API)
    ├── convert_to_file_io.py       # Workflow trigger conversion script
    └── patch_workflow_models.py    # Batch LLM model expression patcher
```

---

## Safety & Ethics

This environment is designed for **defensive security research** in a fully controlled, isolated setup:

- All LLM inference can run locally via Ollama — no data leaves the host (air-gapped mode)
- When using external API providers, no sensitive or real-world data is used
- No real exploits, attack tools, or malicious software are included in the repository
- Mock servers simulate attacker infrastructure — no actual exfiltration occurs
- All workflow JSONs import with `active: false` — no automatic execution

---

## License

Provided for educational and research purposes.

## Related Work

This project sits at the intersection of LLM security, agentic workflow systems, and software supply-chain trust boundaries in AI orchestration platforms. Despite increasing adoption of tools like n8n for AI-driven automation, the security properties of these systems remain largely unexplored — particularly in settings where model outputs directly determine control flow and external actions. For OWASP LLM taxonomy references, see [OWASP Top 10 for LLM Applications](https://owasp.org/www-project-top-10-for-llm-applications/).
