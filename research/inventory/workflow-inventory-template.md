# Workflow Inventory Template

## Overview

| ID | Name | Purpose | Status | Trigger | Nodes Used | Notes |
|----|------|---------|--------|---------|------------|-------|
| 01 | Direct Prompt Injection | Basic injection via file-based input | Active | Manual | Manual Trigger, Read Input, LLM, Write Output, Log | Single node, no persistence |
| 02 | Indirect Injection (Web) | Agent fetches poisoned web page | Active | Manual | Manual Trigger, Read Input, LLM, HTTP Request, LLM, Write Output, Log | External data source |
| 03 | Indirect Injection (DB) | Database row with hidden injection | Active | Manual | Manual Trigger, Read Input, LLM, PostgreSQL, LLM, Write Output, Log | Persistent storage |
| 04 | Code Execution via LLM | LLM output passed to code node | Active | Manual | Manual Trigger, Read Input, LLM, Code, Write Output, Log | Insecure output handling |
| 05 | Excessive Agency / Tool Hijack | Multiple tools — unintended call | Active | Manual | Manual Trigger, Read Input, LLM, Tool(s), Write Output, Log | Multi-tool surface |
| 06 | Credential Exfiltration | LLM tricked into exfiltrating secrets | Active | Manual | Manual Trigger, Read Input, LLM, HTTP Request, Write Output, Log | Credential leak |
| 07 | System Prompt Extraction | Multi-turn extraction attempt | Active | Manual | Manual Trigger, Read Input, LLM, Memory, Write Output, Log | Memory exploitation |
| 08 | Vector Store Poisoning | Phase A seed + Phase B query | Active | Manual (2 phases) | Manual Trigger A, LLM, Vector Store → Manual Trigger B, LLM, Vector Store, LLM, Write Output, Log | Semantic memory |
| 09 | Agent Loop / Resource Exhaustion | Infinite self-triggering | Active | Manual | Manual Trigger, Read Input, LLM, Agent, Write Output, Log | DoS via agent |
| 10 | Multi-Hop Trust Escalation | Cross-agent privilege chain | Active | Manual | Manual Trigger, Read Input, LLM, Agent A, Agent B, Write Output, Log | Composite |

## Dependencies

| Dependency | Used By | Notes |
|------------|---------|-------|
| OpenAI API credential | All workflows | Must be configured in n8n UI |
| PostgreSQL credential | Workflows 03, 04, 06, 09, 10 | Must be configured in n8n UI |
| Ollama API | All workflows | Accessed via Docker network (ollama:11434) |
| agent_messages table | (Optional) | Generic message persistence |
