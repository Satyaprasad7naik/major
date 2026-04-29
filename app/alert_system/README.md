# Alert System Module

This module is completely independent from the core NL2SQL pipeline. It focuses on:
1. Negotiating alert criteria based on existing SQL queries.
2. Generating specialized SQL for monitoring/alerting.
3. Managing alert configurations (frequency, channels).

## Components:
- `models.py`: API Request/Response models for alerts.
- `service.py`: Logic for interpreting alert instructions and generating the monitoring SQL.

## Usage:
The `/alert` endpoint in the API uses this module. It is designed to work as a "sidekick" to the main query interface, allowing users to turn any query into a long-running alert.
