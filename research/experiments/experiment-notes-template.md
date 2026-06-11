# Experiment Notes Template

## Experiment Information

- **Date:** YYYY-MM-DD
- **Researcher:**
- **Experiment ID:** EXP-001
- **Related Workflow(s):** Workflow #1, #2, #3, #4

## Objective

Describe what this experiment aims to observe or measure.

## Environment

- **n8n Version:**
- **Ollama Model:**
- **Ollama Version:**
- **PostgreSQL Version:**
- **Docker Compose:**

## Setup

Describe the configuration changes, workflow modifications, or environment setup required.

## Procedure

1. Step one
2. Step two
3. Step three

## Observations

### Workflow Execution Logs

Paste relevant log output here.

```
docker compose logs n8n
```

### PostgreSQL Activity

```sql
SELECT * FROM agent_messages ORDER BY timestamp DESC LIMIT 10;
```

### Ollama Response Behavior

Note any patterns in model responses, latency, or behavior.

## Results

Summarize findings.

## Conclusions

What was learned? What defensive insights were gained?

## Follow-up

- [ ] Next experiment idea
- [ ] Related observation to investigate

## Artifacts

- Screenshots:
- Log files:
- Modified workflows:
