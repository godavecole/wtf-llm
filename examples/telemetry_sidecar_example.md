# Telemetry sidecar examples (`ingest-usage` / `link-events`)

Copy shapes into **`.wtf/token_ledger.jsonl`** and **`.wtf/incident_links.json`** (gitignored in real projects). **`ingest-usage`** expects CSV like **[`usage_template.csv`](./usage_template.csv)**; see **[Third-party telemetry](../PROTOCOL.md#third-party-telemetry)** in **[PROTOCOL](../PROTOCOL.md)** for Langfuse, LangSmith, gateways, etc.

See **[PROTOCOL](../PROTOCOL.md)** and **`wtf.py ingest-usage`**.

## `token_ledger.jsonl` (one JSON object per line)

```jsonl
{"cost_usd":0.0123,"event_id":"evt_example_001","input_tokens":1200,"model":"claude-sonnet-4.5","output_tokens":450,"provider":"anthropic","source":"manual_export","timestamp":"2026-03-30T10:00:00Z","total_tokens":1650}
{"cost_usd":0.0088,"event_id":"evt_example_002","input_tokens":900,"model":"gpt-5","output_tokens":300,"provider":"openai","source":"manual_export","timestamp":"2026-03-30T10:01:00Z","total_tokens":1200}
```

## `incident_links.json`

```json
{
  "001": ["evt_example_001", "evt_example_002"]
}
```
