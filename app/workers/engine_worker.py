"""
Alert Engine Worker
====================
Runs the alert engine loop in the foreground. Intended to run in a dedicated container.
Register this container's task ARN via POST /api/v1/alerts/engine/start with body {"task_arn": "<arn>"}
or have the API start the task via ECS and store the taskArn in Redis.
"""

import os
import signal
import sys

# Ensure app is on path when run as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.alert_engine import AlertEngineService, ALERTS_DB_PATH


def main():
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "files", "alerts_schema.sql"
    )
    if not os.path.exists(ALERTS_DB_PATH) and os.path.exists(schema_path):
        engine = AlertEngineService()
        engine.initialize_db(schema_path)
    elif not os.path.exists(ALERTS_DB_PATH):
        print("[EngineWorker] DB and schema not found; exiting.", file=sys.stderr)
        sys.exit(1)

    engine = AlertEngineService()
    tick_interval = float(os.environ.get("ENGINE_TICK_INTERVAL", "1.0"))

    def on_stop(signum=None, frame=None):
        print("[EngineWorker] Shutdown requested, stopping engine...")
        engine.stop()

    signal.signal(signal.SIGTERM, on_stop)
    signal.signal(signal.SIGINT, on_stop)

    print("[EngineWorker] Starting alert engine loop (tick_interval=%s)" % tick_interval)
    engine.run_engine(tick_interval=tick_interval)
    print("[EngineWorker] Stopped.")


if __name__ == "__main__":
    main()
