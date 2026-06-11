# Architecture Diagram

## Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                       Docker Network                              │
│                                                                   │
│  ┌────────────────┐     ┌──────────────┐     ┌────────────────┐  │
│  │                │     │              │     │                │  │
│  │     n8n        │────▶│  PostgreSQL  │     │    Ollama      │  │
│  │   :5678        │     │   :5432      │     │   :11434       │  │
│  │                │◀────│              │     │                │  │
│  └───────┬────────┘     └──────────────┘     └────────────────┘  │
│          │                                                         │
│          │  File I/O mounts                                        │
│          ▼                                                         │
│  ┌────────────────────────────────────┐                           │
│  │  n8n/inputs/ → /data/inputs/      │                           │
│  │  n8n/outputs/ → /data/outputs/    │                           │
│  └────────────────────────────────────┘                           │
└──────────────────────────────────────────────────────────────────┘
```

## Service Communication Flow

### Workflow 1: Direct Injection (Baseline)
```
User → Input File → n8n Manual Trigger → Read Input Code Node → Ollama LLM → Write Output Code Node → Output File
```

### Workflow 2: Indirect Web Scrape
```
User → Input File → n8n Manual Trigger → Read Input → LLM → HTTP Request (web page fetch) → LLM → Write Output → Output File
```

### Workflow 3: Indirect Database Row
```
User → Input File → n8n Manual Trigger → Read Input → LLM → PostgreSQL Query → LLM → Write Output → Output File
```

### Workflow 4: Code Execution
```
User → Input File → n8n Manual Trigger → Read Input → LLM → Code Node (execute LLM output) → Write Output → Output File
```

## Data Flow

```
agent_messages table:
┌────────┬───────────┬──────────┬───────────┬──────────────┬───────────┐
│   id   │ timestamp │ sender_id│ chat_id   │ message_text │ processed │
├────────┼───────────┼──────────┼───────────┼──────────────┼───────────┤
│ SERIAL │ timestamptz│ BIGINT  │ BIGINT    │ TEXT         │ BOOLEAN   │
└────────┴───────────┴──────────┴───────────┴──────────────┴───────────┘
```

## Volumes

| Volume            | Service    | Purpose                           |
|-------------------|------------|-----------------------------------|
| `n8n_data`        | n8n        | Workflow configs, credentials, DB |
| `postgres_data`   | PostgreSQL | Persistent database storage       |
| `ollama_data`     | Ollama     | Downloaded model storage          |
