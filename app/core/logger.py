import logging
import sys
import time
import contextvars
from logging.handlers import RotatingFileHandler
import os

# ─── Per-mission log capture via contextvars ──────────────────────────────────
# Each asyncio Task gets its own copy, so concurrent missions don't mix logs.
_mission_log_buffer: contextvars.ContextVar[list | None] = contextvars.ContextVar(
    "_mission_log_buffer", default=None
)

# SSE real-time streaming: push log entries to an asyncio.Queue as they happen.
# Set by the SSE endpoint before spawning mission tasks; child tasks inherit it.
_sse_event_queue: contextvars.ContextVar = contextvars.ContextVar(
    "_sse_event_queue", default=None
)

# Per-mission metadata so the log handler can tag entries with mission info.
_mission_meta: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "_mission_meta", default=None
)


class MissionLogHandler(logging.Handler):
    """Captures log records into a per-task buffer AND streams to SSE queue."""

    # Map workflow filenames to friendly node labels
    _NODE_LABELS = {
        "workflow.py": "ORCHESTRATOR",
        "intent_classification.py": "INTENT",
        "clarification.py": "CLARIFY",
        "preprocessing.py": "PREPROCESS",
        "sql_generation.py": "SQL_GEN",
        "validation.py": "VALIDATE",
        "database.py": "DB_EXEC",
        "visualization.py": "VISUALIZE",
        "insight_generation.py": "INSIGHT",
        "sentinel_agent.py": "SENTINEL",
        "risk_scorer.py": "RISK_SCORE",
        "deep_dive.py": "DEEP_DIVE",
        "correlation_engine.py": "CORRELATE",
        "narrative_generator.py": "NARRATIVE",
        "sentinel.py": "API",
    }

    def emit(self, record: logging.LogRecord):
        buf = _mission_log_buffer.get(None)
        if buf is not None:
            node = self._NODE_LABELS.get(record.filename, record.filename)
            entry = {
                "ts": round(record.created, 3),
                "level": record.levelname,
                "node": node,
                "msg": record.getMessage(),
            }
            buf.append(entry)

            # Also push to SSE queue for real-time streaming
            sse_queue = _sse_event_queue.get(None)
            meta = _mission_meta.get(None)
            if sse_queue is not None and meta is not None:
                sse_entry = {
                    **entry,
                    "mission_id": meta.get("mission_id"),
                    "mission_name": meta.get("mission_name"),
                    "domain": meta.get("domain"),
                    "severity": meta.get("severity", "MEDIUM"),
                }
                try:
                    sse_queue.put_nowait(("log", sse_entry))
                except Exception:
                    pass  # Don't let SSE queue errors break logging


def setup_logging():
    """
    Central logging configuration for the DerivInsight NL2SQL system.
    Outputs to both console and a log file.
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Configure root logger
    logger = logging.getLogger("nl2sql")
    logger.setLevel(logging.INFO)

    # Prevent duplicate logs if already configured
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (with rotation)
    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Mission log capture handler (no formatter needed, stores structured data)
    logger.addHandler(MissionLogHandler())

    return logger

# Initialize on import
logger = setup_logging()
