"""
Alert Events Generator
======================
Generates simulated events and pushes them to the alerts database.
Events are used by the AlertEngine to evaluate metrics and trigger alerts.

Event Types:
- user: New user registrations
- login: Login attempts (success/failed)
- transaction: Financial transactions (success/failed)
- kyc: KYC status changes (pending/approved/rejected)
"""

import random
import time
import json
from datetime import datetime
from threading import Thread, Event
from typing import Optional

# Import alert engine
from app.services.alert_engine import AlertEngineService, ALERTS_DB_URL


class EventGenerator:
    """
    Generates simulated events for testing the alert engine.
    """
    
    def __init__(self, db_url: str = None):
        self.engine_service = AlertEngineService(db_url or ALERTS_DB_URL)
        self._stop_event = Event()
        self._threads = []
    
    def write_event(self, event_type: str, data: dict):
        """Write an event to the database."""
        event_id = self.engine_service.insert_event(event_type, data)
        print(f"[EVENT] {event_type} → {data} (id={event_id})")
        return event_id
    
    # ================= USERS (every ~1 hour) =================
    
    def generate_users(self, interval: float = 3600):
        """Generate user registration events."""
        while not self._stop_event.is_set():
            user = {
                "user_id": random.randint(1, 10000),
                "name": f"user_{random.randint(1000, 9999)}",
                "email": f"user{random.randint(1000, 9999)}@example.com"
            }
            self.write_event("user", user)
            
            # Wait with check for stop event
            for _ in range(int(interval)):
                if self._stop_event.is_set():
                    break
                time.sleep(1)
    
    # ================= LOGIN EVENTS (2–10 sec) =================
    
    def generate_logins(self, min_interval: float = 2, max_interval: float = 10):
        """Generate login events with success/failed status."""
        while not self._stop_event.is_set():
            login = {
                "user_id": random.randint(1, 100),
                "status": random.choices(["success", "failed"], weights=[0.85, 0.15])[0],
                "ip_address": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                "user_agent": random.choice(["Chrome", "Firefox", "Safari", "Edge"])
            }
            self.write_event("login", login)
            
            sleep_time = random.uniform(min_interval, max_interval)
            self._sleep_interruptible(sleep_time)
    
    # ================= TRANSACTIONS (1–4 sec) =================
    
    def generate_transactions(self, min_interval: float = 1, max_interval: float = 4):
        """Generate transaction events."""
        while not self._stop_event.is_set():
            txn = {
                "user_id": random.randint(1, 100),
                "amount": random.randint(100, 5000),
                "currency": random.choice(["USD", "EUR", "GBP"]),
                "status": random.choices(["success", "failed"], weights=[0.92, 0.08])[0],
                "type": random.choice(["deposit", "withdrawal", "transfer"])
            }
            self.write_event("transaction", txn)
            
            sleep_time = random.uniform(min_interval, max_interval)
            self._sleep_interruptible(sleep_time)
    
    # ================= KYC EVENTS (every 10–20 sec) =================
    
    def generate_kyc_events(self, min_interval: float = 10, max_interval: float = 20):
        """Generate KYC status events."""
        kyc_statuses = ["pending", "approved", "rejected"]
        weights = [0.4, 0.45, 0.15]  # realistic distribution
        
        while not self._stop_event.is_set():
            user_id = random.randint(1, 100)
            status = random.choices(kyc_statuses, weights=weights)[0]
            
            kyc_event = {
                "user_id": user_id,
                "kyc_status": status,
                "document_type": random.choice(["passport", "id_card", "drivers_license"]),
                "verification_source": random.choice(["manual", "automated"])
            }
            self.write_event("kyc", kyc_event)
            
            sleep_time = random.uniform(min_interval, max_interval)
            self._sleep_interruptible(sleep_time)
    
    # ================= BURST GENERATORS (for testing alerts) =================
    
    def generate_login_burst(self, count: int = 15, status: str = "failed"):
        """Generate a burst of login events (useful for testing alerts)."""
        print(f"\n[BURST] Generating {count} {status} login events...")
        for i in range(count):
            login = {
                "user_id": random.randint(1, 100),
                "status": status,
                "ip_address": f"192.168.1.{random.randint(1, 255)}",
                "user_agent": "BurstTest"
            }
            self.write_event("login", login)
            time.sleep(0.1)  # Small delay between events
        print(f"[BURST] Completed {count} {status} login events\n")
    
    def generate_transaction_burst(self, count: int = 25, status: str = "success"):
        """Generate a burst of transaction events."""
        print(f"\n[BURST] Generating {count} {status} transaction events...")
        for i in range(count):
            txn = {
                "user_id": random.randint(1, 100),
                "amount": random.randint(100, 5000),
                "currency": "USD",
                "status": status,
                "type": "transfer"
            }
            self.write_event("transaction", txn)
            time.sleep(0.1)
        print(f"[BURST] Completed {count} {status} transaction events\n")
    
    def generate_kyc_rejection_burst(self, count: int = 5):
        """Generate a burst of KYC rejection events."""
        print(f"\n[BURST] Generating {count} KYC rejection events...")
        for i in range(count):
            kyc_event = {
                "user_id": random.randint(1, 100),
                "kyc_status": "rejected",
                "document_type": "passport",
                "verification_source": "automated"
            }
            self.write_event("kyc", kyc_event)
            time.sleep(0.2)
        print(f"[BURST] Completed {count} KYC rejection events\n")
    
    # ================= HELPER METHODS =================
    
    def _sleep_interruptible(self, seconds: float):
        """Sleep that can be interrupted by stop event."""
        chunks = int(seconds)
        remainder = seconds - chunks
        
        for _ in range(chunks):
            if self._stop_event.is_set():
                return
            time.sleep(1)
        
        if not self._stop_event.is_set() and remainder > 0:
            time.sleep(remainder)
    
    # ================= RUN ALL =================
    
    def start_all(self, 
                  user_interval: float = 60,      # 1 minute for demo (normally 1 hour)
                  login_interval: tuple = (2, 10),
                  txn_interval: tuple = (1, 4),
                  kyc_interval: tuple = (10, 20)):
        """Start all event generators in background threads."""
        
        self._stop_event.clear()
        
        # Start user generator
        t1 = Thread(target=self.generate_users, args=(user_interval,), daemon=True)
        t1.start()
        self._threads.append(t1)
        
        # Start login generator
        t2 = Thread(target=self.generate_logins, args=login_interval, daemon=True)
        t2.start()
        self._threads.append(t2)
        
        # Start transaction generator
        t3 = Thread(target=self.generate_transactions, args=txn_interval, daemon=True)
        t3.start()
        self._threads.append(t3)
        
        # Start KYC generator
        t4 = Thread(target=self.generate_kyc_events, args=kyc_interval, daemon=True)
        t4.start()
        self._threads.append(t4)
        
        print("[EventGenerator] All generators started")
    
    def stop_all(self):
        """Stop all event generators."""
        print("[EventGenerator] Stopping all generators...")
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=2)
        self._threads = []
        print("[EventGenerator] All generators stopped")


# ================= LEGACY FUNCTIONS (for backward compatibility) =================

EVENT_FILE = "events.jsonl"
event_id = 0

def write_event(event_type, data):
    """Legacy function - writes to JSONL file."""
    global event_id
    event_id += 1
    
    event = {
        "id": event_id,
        "type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    with open(EVENT_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")
    
    print(f"[EVENT] {event_type} → {data}")


def generate_users():
    """Legacy user generator."""
    while True:
        user = {
            "user_id": random.randint(1, 10000),
            "name": f"user_{random.randint(1000, 9999)}"
        }
        write_event("user", user)
        time.sleep(3600)


def generate_logins():
    """Legacy login generator."""
    while True:
        login = {
            "user_id": random.randint(1, 100),
            "status": random.choice(["success", "failed"])
        }
        write_event("login", login)
        time.sleep(random.uniform(2, 10))


def generate_transactions():
    """Legacy transaction generator."""
    while True:
        txn = {
            "user_id": random.randint(1, 100),
            "amount": random.randint(100, 5000),
            "status": random.choice(["success", "failed"])
        }
        write_event("transaction", txn)
        time.sleep(random.uniform(1, 4))


def generate_kyc_events():
    """Legacy KYC generator."""
    kyc_statuses = ["pending", "approved", "rejected"]
    weights = [0.4, 0.45, 0.15]
    
    while True:
        user_id = random.randint(1, 100)
        status = random.choices(kyc_statuses, weights=weights)[0]
        
        kyc_event = {
            "user_id": user_id,
            "kyc_status": status
        }
        write_event("kyc", kyc_event)
        time.sleep(random.uniform(10, 20))


# ================= MAIN =================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--legacy":
        # Run legacy file-based generators
        print("Running legacy file-based event generators...")
        Thread(target=generate_users, daemon=True).start()
        Thread(target=generate_logins, daemon=True).start()
        Thread(target=generate_transactions, daemon=True).start()
        Thread(target=generate_kyc_events, daemon=True).start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        # Run database-based generators
        print("Running database-based event generators...")
        print("Make sure to initialize the database first with: python init_alerts_db.py")
        
        generator = EventGenerator()
        generator.start_all()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            generator.stop_all()
            print("\nStopped.")
