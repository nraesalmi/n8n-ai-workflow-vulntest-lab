# Workflow Inventory Template

## Overview

| ID | Name | Purpose | Status | Trigger | Nodes Used | Notes |
|----|------|---------|--------|---------|------------|-------|
| 01 | Telegram LLM Chatbot | AI chatbot via Telegram | Active | Telegram Message | Trigger, HTTP Request, Telegram | Basic conversational flow |
| 02 | Telegram LLM Classification | Message classification | Active | Telegram Message | Trigger, HTTP Request, Set, Telegram | Categorizes into support/sales/technical/general |
| 03 | Telegram Database Storage | Message persistence | Active | Telegram Message | Trigger, PostgreSQL, Telegram | Stores to telegram_messages table |
| 04 | Telegram DB LLM Summary | Retriever summary | Active | Telegram Message | Trigger, PostgreSQL, Aggregate, Set, HTTP Request, Telegram | Fetches and summarizes recent messages |

## Detailed Workflow Information

### Workflow 01: Telegram LLM Chatbot

- **File:** `01-telegram-llm-chatbot.json`
- **Trigger:** Telegram message (any message)
- **Nodes:**
  - Telegram Trigger: Receives incoming message
  - HTTP Request: Sends message to Ollama `/api/chat` endpoint
  - Telegram: Sends LLM response back to user
- **Credentials Required:** Telegram Bot
- **Environment Variables:** `OLLAMA_MODEL`

### Workflow 02: Telegram LLM Classification

- **File:** `02-telegram-llm-classification.json`
- **Trigger:** Telegram message (any message)
- **Nodes:**
  - Telegram Trigger: Receives incoming message
  - HTTP Request: Classification prompt to Ollama
  - Set: Formats the category response
  - Telegram: Sends classification result
- **Categories:** support, sales, technical, general
- **Credentials Required:** Telegram Bot
- **Environment Variables:** `OLLAMA_MODEL`

### Workflow 03: Telegram Database Storage

- **File:** `03-telegram-db-storage.json`
- **Trigger:** Telegram message (any message)
- **Nodes:**
  - Telegram Trigger: Receives incoming message
  - PostgreSQL: INSERT into telegram_messages
  - Telegram: Confirmation with row ID
- **Table:** `telegram_messages`
- **Credentials Required:** Telegram Bot, PostgreSQL Database
- **Environment Variables:** None (uses database config)

### Workflow 04: Telegram DB LLM Summary

- **File:** `04-telegram-db-llm-summary.json`
- **Trigger:** Telegram message (any message)
- **Nodes:**
  - Telegram Trigger: Receives incoming message
  - PostgreSQL: SELECT recent 20 messages
  - Aggregate: Combines all rows into array
  - Set: Builds chat history string
  - HTTP Request: Summarization prompt to Ollama
  - Telegram: Sends summary
- **Credentials Required:** Telegram Bot, PostgreSQL Database
- **Environment Variables:** `OLLAMA_MODEL`

## Dependencies

| Dependency | Used By | Notes |
|------------|---------|-------|
| Telegram Bot credential | All workflows | Must be configured in n8n UI |
| PostgreSQL credential | Workflow 03, 04 | Must be configured in n8n UI |
| Ollama API | Workflow 01, 02, 04 | Accessed via Docker network |
| telegram_messages table | Workflow 03, 04 | Created by init script |
