---
description: Transform Natural Language into Structured Monitoring Metrics
---

This workflow defines how to convert a user's request for monitoring or alerting into a machine-readable JSON metric format.

### Steps:
1. **Request Reception**: Receive natural language query (e.g., "Alert me if failed transactions exceed 3 in a minute").
2. **Entity Extraction**: Identify the target event type (`transactions`, `login_events`) and the relevant fields (`status`, `amount`).
3. **Logic Mapping**: 
   - Identify the **Filter** (e.g., `status == 'failed'`).
   - Identify the **Aggregation** (e.g., `count`).
   - Identify the **Window** (e.g., `60` seconds).
   - Identify the **Threshold** (e.g., `3`).
4. **JSON Synthesis**: Generate the final payload:
   ```json
   {
     "metric_id": "m1",
     "event_type": "transaction",
     "filter": { "field": "status", "operator": "==", "value": "failed" },
     "aggregation": "count",
     "window_sec": 60,
     "threshold": 3
   }
   ```
5. **Validation**: Ensure the `field` exists in the core tables defined in the schema.
