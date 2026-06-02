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
│          │  HTTP polling                                           │
│          ▼                                                         │
│  ┌────────────────┐                                               │
│  │   Telegram API  │  (external service)                          │
│  └────────────────┘                                               │
└──────────────────────────────────────────────────────────────────┘
```

## Service Communication Flow

### Workflow 1: Chatbot
```
User → Telegram → n8n Trigger → HTTP Request (Ollama) → Telegram Response → User
```

### Workflow 2: Classification
```
User → Telegram → n8n Trigger → Classification Prompt (Ollama) → Format → Telegram Response → User
```

### Workflow 3: Storage
```
User → Telegram → n8n Trigger → PostgreSQL Insert → Telegram Confirmation → User
```

### Workflow 4: Summary
```
User → Telegram → n8n Trigger → PostgreSQL Fetch → Aggregate → Summary Prompt (Ollama) → Telegram Response → User
```

## Data Flow

```
telegram_messages table:
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
