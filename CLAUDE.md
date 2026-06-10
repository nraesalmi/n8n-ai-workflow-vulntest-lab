# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Security research lab studying prompt-injection-class attacks in n8n-based AI agent workflow systems. Four n8n workflows form an escalating attack surface: basic chatbot → classification → database persistence → cross-workflow second-order injection chain.

## Commands

### Environment Management
```bash
docker compose up -d                    # Start all services (n8n, Postgres, Ollama, mockapi)
docker compose down                     # Stop all services
docker compose up -d n8n                # Start a single service
docker compose logs -f n8n              # Watch n8n execution logs
```

### Setup (run after `docker compose up -d`)
```bash
./scripts/pull-model.sh                 # Download default Ollama model (from .env)
./scripts/pull-model.sh llama3          # Download a specific model
./scripts/setup.sh                      # Import credentials & workflows into n8n
```

### Research & Debugging
```bash
docker compose logs -f n8n              # Watch workflow executions
docker exec -it n8n-postgres psql -U n8n -d n8n -c \
  "SELECT * FROM telegram_messages ORDER BY timestamp DESC LIMIT 20;"
docker exec n8n-ollama ollama list      # Verify downloaded models
docker exec n8n-ollama ollama pull <model>  # Pull additional models
```

### GPU Acceleration
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

## Architecture

### Services (Docker Compose)
- **n8n** (port 5678) — Workflow orchestration with PostgreSQL-backed storage
- **PostgreSQL** (port 5432) — n8n state + `telegram_messages` table (created by `postgres/init/01-init.sql`)
- **Ollama** (port 11434) — Local LLM inference, no external API calls
- **mockapi** (port 3000) — `json-server` with document data (`mockapi/db.json`)

### Workflows (in escalating attack complexity)

| # | File | Path | Attack Surface |
|---|------|------|----------------|
| 01 | `01-telegram-llm-chatbot.json` | Telegram → Ollama → Telegram | Direct prompt injection |
| 02 | `02-telegram-llm-classification.json` | Telegram → Ollama → Set → Telegram | System prompt injection, output format deviation |
| 03 | `03-telegram-db-storage.json` | Telegram → Postgres INSERT → Telegram | Persistent state poisoning |
| 04 | `04-telegram-db-llm-summary.json` | Telegram → Postgres SELECT → Aggregate → Ollama → Telegram | Second-order/indirect injection via DB |

Workflow 03 + 04 form the critical **cross-workflow attack chain**: attacker plants payload via 03, it persists in Postgres, and activates in a separate execution context when 04 fetches and summarizes stored messages.

### Key Research Areas
- **Execution flow hijacking** — crafted inputs redirecting control flow across nodes
- **Persistent state poisoning** — injections stored in DB re-emerging in later executions
- **Unintended tool invocations** — LLM outputs triggering external API calls or data mutations
- **Cross-node trust boundary bypass** — implicit data passing between nodes without validation

### Project Layout
- `n8n/workflows/*.json` — n8n workflow definitions (imported by setup script)
- `postgres/init/01-init.sql` — `telegram_messages` table schema
- `scripts/setup.sh` / `scripts/setup.ps1` — credential + workflow import
- `mockapi/db.json` — mock REST API data (document corpus)
- `research/` — architecture diagrams, experiment templates, workflow inventory
- `.env.example` — template for required environment variables

### Working with Workflow JSON
Each workflow is a standard n8n export JSON. Nodes reference credentials by UUID — after import, credentials must be linked in the n8n UI. The setup script auto-generates credential files with UUIDs and imports them.
