"""
Event Generator Worker
======================
Runs the event generator in the foreground. Intended to run in a dedicated container.
Register this container's task ARN via POST /api/v1/alerts/generator/start with body {"task_arn": "<arn>"}
or have the API start the task via ECS and store the taskArn in Redis.
"""

import os
import signal
import sys
import time
from threading import Event as ThreadEvent

# Ensure app is on path when run as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.alert_events_generate import EventGenerator
from app.services.alert_engine import ALERTS_DB_PATH

_shutdown = ThreadEvent()


def main():
    if not os.path.exists(ALERTS_DB_PATH):
        print("[GeneratorWorker] Alerts DB not found; exiting.", file=sys.stderr)
        sys.exit(1)

    generator = EventGenerator()

    # Config from env (optional)
    user_interval = float(os.environ.get("GENERATOR_USER_INTERVAL", "60"))
    login_min = float(os.environ.get("GENERATOR_LOGIN_MIN", "2"))
    login_max = float(os.environ.get("GENERATOR_LOGIN_MAX", "10"))
    txn_min = float(os.environ.get("GENERATOR_TXN_MIN", "1"))
    txn_max = float(os.environ.get("GENERATOR_TXN_MAX", "4"))
    kyc_min = float(os.environ.get("GENERATOR_KYC_MIN", "10"))
    kyc_max = float(os.environ.get("GENERATOR_KYC_MAX", "20"))

    def on_stop(signum=None, frame=None):
        print("[GeneratorWorker] Shutdown requested, stopping generator...")
        generator.stop_all()
        _shutdown.set()

    signal.signal(signal.SIGTERM, on_stop)
    signal.signal(signal.SIGINT, on_stop)

    print("[GeneratorWorker] Starting event generator")
    generator.start_all(
        user_interval=user_interval,
        login_interval=(login_min, login_max),
        txn_interval=(txn_min, txn_max),
        kyc_interval=(kyc_min, kyc_max),
    )
    try:
        while not _shutdown.is_set():
            _shutdown.wait(timeout=1)
    finally:
        generator.stop_all()
    print("[GeneratorWorker] Stopped.")


if __name__ == "__main__":
    main()
