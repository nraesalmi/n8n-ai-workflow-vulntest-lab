# AI Workflow Security Research Environment

A local, Docker-based environment for studying AI workflow security in n8n. This project provides a realistic enterprise-style automation platform with Telegram integration and local LLM inference via Ollama.

> **Purpose:** Defensive security research. Study how AI-driven workflow automation behaves under normal operation to build a baseline for understanding semantic workflow attack vectors.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Docker Network                         │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────┐  │
│  │              │    │              │    │                │  │
│  │     n8n      │───▶│  PostgreSQL  │    │    Ollama      │  │
│  │    :5678     │    │   :5432      │    │   :11434       │  │
│  │              │◀───│              │    │                │  │
│  └──────┬───────┘    └──────────────┘    └────────────────┘  │
│         │                                                     │
│         │  HTTP polling                                       │
│         ▼                                                     │
│  ┌──────────────┐                                             │
│  │  Telegram API │  (external)                                │
│  └──────────────┘                                             │
└──────────────────────────────────────────────────────────────┘
```

| Service        | Port (host)  | Purpose                                  |
|----------------|--------------|------------------------------------------|
| n8n            | 5678         | Workflow orchestration and UI            |
| PostgreSQL     | 5432         | Persistent database backend for n8n      |
| Ollama         | 11434        | Local LLM inference API                  |
| Telegram       | external     | Bot interface via Telegram API           |

## Service Descriptions

### n8n
Workflow automation platform serving as the core orchestration layer. Connected to PostgreSQL for persistence and configured to reach Ollama over the Docker network.

- **Editor URL:** http://localhost:5678
- **API:** Internal REST API for workflow management
- **Logging:** Debug-level output to container logs

### PostgreSQL
Relational database providing persistent storage for n8n's internal data and a custom `telegram_messages` table used by the example workflows.

- **Initialized automatically** on first run
- **Data persists** across container restarts via Docker volume
- **Custom schema** includes indexed message storage table

### Ollama
Local LLM inference server. Serves models via a REST API that n8n workflows call directly.

- **Model storage** persists via Docker volume
- **Configurable model** via `OLLAMA_MODEL` environment variable
- **No GPU required** (optional GPU support available)

### Telegram Bot Integration
n8n workflows use the Telegram Trigger and Telegram Send nodes to interact with users via the Telegram platform.

- **No webhook server needed** - n8n polls the Telegram API
- **Bot token** configured via environment variable only
- **Credentials** stored encrypted in n8n

---

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- 8 GB RAM minimum (16 GB recommended for LLM)
- A Telegram Bot token (see [Telegram Bot Setup](#telegram-bot-setup))

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:

| Variable             | Description                                      | Example                        |
|----------------------|--------------------------------------------------|--------------------------------|
| `N8N_ENCRYPTION_KEY` | 32+ character random string for credential encryption | `openssl rand -hex 32`  |
| `POSTGRES_PASSWORD`  | Database password                                | `your-secure-password`         |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather                        | `123456:ABC-DEF...`            |
| `OLLAMA_MODEL`       | LLM model name to use                            | `mistral` or `llama3`          |

Generate a secure encryption key:

```bash
openssl rand -hex 32
```

### 3. Start Services

**CPU-only (default):**
```bash
docker compose up -d
```

**With NVIDIA GPU acceleration:**
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

The first startup will take several minutes as:
1. Docker images are pulled
2. PostgreSQL initializes the database and schema
3. Ollama starts up
4. n8n imports the example workflows
5. n8n completes its first-run setup

### 4. Download the LLM Model

After services are running, pull your selected model:

```bash
# Uses the model specified in .env
./scripts/pull-model.sh

# Or specify a model directly
./scripts/pull-model.sh llama3
./scripts/pull-model.sh mistral
./scripts/pull-model.sh phi3
```

Check downloaded models:

```bash
docker exec n8n-ollama ollama list
```

### 5. Access n8n

Open http://localhost:5678 in your browser and complete the initial user setup.

---

## Telegram Bot Setup

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Choose a name for your bot (e.g., "My Research Bot")
4. Choose a username (must end in `bot`, e.g., `my_research_bot`)
5. BotFather will provide a **token** in the format: `123456789:ABCdefGHIjklMNOpqrSTUvwxYZ`
6. Copy this token into your `.env` file as `TELEGRAM_BOT_TOKEN`

### Configuring the Telegram Credential in n8n

1. Open n8n at http://localhost:5678
2. Go to **Credentials** in the left sidebar
3. Click **Add Credential**
4. Select **Telegram API**
5. Set the following:
   - **Name:** `Telegram Bot` (must match exactly - workflows reference this name)
   - **Access Token:** Your bot token from BotFather
6. Click **Save**

---

## Ollama Model Setup

### Available Models

| Model        | Size     | Quality    | Speed     | RAM Required |
|--------------|----------|------------|-----------|--------------|
| `phi3`       | ~2.3 GB  | Good       | Fast      | 4 GB         |
| `mistral`    | ~4.1 GB  | Very Good  | Moderate  | 8 GB         |
| `llama3`     | ~4.7 GB  | Very Good  | Moderate  | 8 GB         |
| `llama3:70b` | ~39 GB   | Excellent  | Slow      | 48 GB+       |

For research environments, `mistral` or `llama3` provides a good balance of quality and resource usage.

### Changing the Model

1. Update `OLLAMA_MODEL` in `.env`
2. Pull the new model:
   ```bash
   ./scripts/pull-model.sh <model-name>
   ```
3. Restart n8n:
   ```bash
   docker compose restart n8n
   ```

### Verifying Ollama

```bash
# Check API health
curl http://localhost:11434/api/tags

# Check running containers
docker ps | grep ollama
```

---

## Database Access

### Connect via psql

```bash
docker exec -it n8n-postgres psql -U n8n -d n8n
```

### Useful Queries

```sql
-- View all stored messages
SELECT id, sender_id, sender_username, message_text, timestamp
FROM telegram_messages
ORDER BY timestamp DESC
LIMIT 20;

-- Count messages per sender
SELECT sender_id, sender_username, COUNT(*) as message_count
FROM telegram_messages
GROUP BY sender_id, sender_username
ORDER BY message_count DESC;

-- View table structure
\d telegram_messages;

-- Check n8n workflow executions (internal n8n table)
SELECT id, workflow_id, started_at, finished_at, status
FROM execution_entity
ORDER BY started_at DESC
LIMIT 10;
```

### Data Persistence

Data is stored in Docker volumes and survives container restarts:

| Volume           | Contains                                    |
|------------------|---------------------------------------------|
| `n8n_postgres_data` | All database content                      |
| `n8n_ollama_data`   | Downloaded Ollama models                    |
| `n8n_n8n_data`      | n8n workflows, credentials, execution data  |

---

## Workflow Descriptions

All workflows are auto-imported on first startup. They require credentials to be configured in the n8n UI before activation.

### Workflow 01: Telegram LLM Chatbot

A simple AI chatbot that responds to Telegram messages.

```
Telegram Message → Ollama API → Telegram Response
```

| Node              | Type           | Description                          |
|-------------------|----------------|--------------------------------------|
| Telegram Trigger  | Trigger        | Listens for new Telegram messages    |
| Call Ollama       | HTTP Request   | Sends message to local LLM           |
| Send Response     | Telegram       | Returns LLM response to the user     |

**Use case:** Baseline conversational AI interaction.

### Workflow 02: Telegram LLM Classification

Classifies incoming messages into categories using an LLM.

```
Telegram Message → Classification Prompt → Format → Telegram Response
```

Categories: `support`, `sales`, `technical`, `general`

| Node                | Type           | Description                          |
|---------------------|----------------|--------------------------------------|
| Telegram Trigger    | Trigger        | Listens for new Telegram messages    |
| Classification Prompt | HTTP Request | LLM classifies the message           |
| Format Response     | Set            | Structures the output                |
| Send Category       | Telegram       | Returns classification to user       |

**Use case:** Automated message routing and categorization.

### Workflow 03: Telegram Database Storage

Persists incoming messages to PostgreSQL.

```
Telegram Message → PostgreSQL INSERT → Telegram Confirmation
```

Stored fields: `timestamp`, `sender_id`, `sender_username`, `chat_id`, `message_text`

| Node                | Type           | Description                          |
|---------------------|----------------|--------------------------------------|
| Telegram Trigger    | Trigger        | Listens for new Telegram messages    |
| Store in PostgreSQL | PostgreSQL     | Inserts message into database        |
| Send Confirmation   | Telegram       | Confirms storage with row ID         |

**Use case:** Message audit trail and data collection.

### Workflow 04: Telegram DB LLM Summary

Retrieves recent messages and generates an LLM summary.

```
Telegram Message → PostgreSQL SELECT → Aggregate → Summary Prompt → Telegram Response
```

| Node                | Type           | Description                          |
|---------------------|----------------|--------------------------------------|
| Telegram Trigger    | Trigger        | Triggers on command                  |
| Fetch Recent Messages | PostgreSQL   | Queries last 20 messages             |
| Aggregate Messages  | Aggregate      | Combines rows into array             |
| Build Summary Prompt | Set           | Formats messages as text             |
| Call Ollama Summary | HTTP Request   | LLM generates summary                |
| Send Summary        | Telegram       | Returns summary to user              |

**Use case:** Context retrieval and summarization pipeline.

---

## Log Locations

### Container Logs

```bash
# All services
docker compose logs -f

# n8n only
docker compose logs -f n8n

# PostgreSQL only
docker compose logs -f postgres

# Ollama only
docker compose logs -f ollama

# Last 100 lines of n8n
docker compose logs --tail=100 n8n
```

### n8n Execution History

View in the n8n UI:
1. Open http://localhost:5678
2. Click **Executions** in the left sidebar
3. Select a workflow to see its execution history

Or query directly:

```bash
docker exec -it n8n-postgres psql -U n8n -d n8n -c \
  "SELECT id, workflow_id, started_at, status FROM execution_entity ORDER BY started_at DESC LIMIT 10;"
```

### PostgreSQL Query Logging

Enable detailed query logging by adding to `.env`:

```env
# Add these lines to .env to enable PostgreSQL statement logging
POSTGRES_LOG_STATEMENTS=all
```

Then restart PostgreSQL:

```bash
docker compose restart postgres
```

View PostgreSQL logs:

```bash
docker compose logs -f postgres
```

---

## Backup and Restore

### Backup

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d)

# Export n8n workflows
docker exec n8n-app n8n export:workflow --output=/tmp/workflow-backup
docker cp n8n-app:/tmp/workflow-backup backups/$(date +%Y%m%d)/workflows

# Export n8n credentials
docker exec n8n-app n8n export:credentials --output=/tmp/credential-backup
docker cp n8n-app:/tmp/credential-backup backups/$(date +%Y%m%d)/credentials

# Backup database
docker exec n8n-postgres pg_dump -U n8n n8n > backups/$(date +%Y%m%d)/database.sql

# Backup Ollama models list (models themselves are in the volume)
docker exec n8n-ollama ollama list > backups/$(date +%Y%m%d)/ollama-models.txt
```

### Restore

```bash
# Restore database
docker exec -i n8n-postgres psql -U n8n n8n < backups/YYYYMMDD/database.sql

# Restore workflows
docker cp backups/YYYYMMDD/workflows n8n-app:/tmp/workflow-restore
docker exec n8n-app n8n import:workflow --input=/tmp/workflow-restore

# Restore credentials
docker cp backups/YYYYMMDD/credentials n8n-app:/tmp/credential-restore
docker exec n8n-app n8n import:credentials --input=/tmp/credential-restore
```

### Full Volume Backup

```bash
# Backup all Docker volumes
docker run --rm -v n8n_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-data.tar.gz -C /data .
docker run --rm -v n8n_ollama_data:/data -v $(pwd):/backup alpine tar czf /backup/ollama-data.tar.gz -C /data .
docker run --rm -v n8n_n8n_data:/data -v $(pwd):/backup alpine tar czf /backup/n8n-data.tar.gz -C /data .
```

---

## Research Directory

The `/research` directory contains templates for documenting your research:

| Path | Purpose |
|------|---------|
| `research/architecture/` | Architecture diagrams and documentation |
| `research/experiments/` | Experiment notes and observations |
| `research/inventory/` | Workflow inventory and dependency tracking |

Copy the templates and fill them in for each experiment:

```bash
cp research/experiments/experiment-notes-template.md research/experiments/EXP-001-notes.md
```

---

## Project Structure

```
├── docker-compose.yml              # CPU-only compose (default)
├── docker-compose.gpu.yml          # GPU override overlay
├── .env.example                    # Environment variable template
├── .env                            # Your configuration (gitignored)
├── requirements.txt                # Python research utilities
├── .venv/                          # Python virtual environment
├── README.md                       # This file
├── postgres/
│   └── init/
│       └── 01-init.sql             # Database initialization
├── n8n/
│   ├── workflows/                  # Exported workflow JSON files
│   │   ├── 01-telegram-llm-chatbot.json
│   │   ├── 02-telegram-llm-classification.json
│   │   ├── 03-telegram-db-storage.json
│   │   └── 04-telegram-db-llm-summary.json
│   └── import-workflows.sh         # Auto-import on first boot
├── research/
│   ├── architecture/
│   │   └── architecture-diagram.md
│   ├── experiments/
│   │   └── experiment-notes-template.md
│   └── inventory/
│       └── workflow-inventory-template.md
└── scripts/
    └── pull-model.sh               # Ollama model download helper
```

---

## Troubleshooting

### n8n workflows not imported
Check the n8n container logs:
```bash
docker compose logs n8n | grep -i import
```
If the import failed, you can re-import manually:
```bash
docker exec n8n-app n8n import:workflow --input=/tmp/workflows
```

### Ollama model not responding
Verify the model is loaded:
```bash
docker exec n8n-ollama ollama list
```
If empty, pull the model:
```bash
./scripts/pull-model.sh
```

### Telegram not receiving messages
1. Verify the bot token is correct
2. Check that the credential name in n8n is exactly `Telegram Bot`
3. View n8n execution logs for errors

### PostgreSQL connection refused
Wait for the health check to pass:
```bash
docker compose ps
```
All services should show `(healthy)`.

### GPU not detected
Ensure you have the NVIDIA Container Toolkit installed:
https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

Then start with the GPU overlay:
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

---

## Security Notes

This environment is designed for **defensive security research**. It contains:

- Standard n8n workflows with normal functionality
- Encrypted credential storage via n8n's built-in encryption
- Database-backed persistence with proper initialization
- Container isolation via Docker networking

It does **not** contain exploits, attack tools, or malicious payloads.

---

## License

This project is provided for educational and research purposes.
