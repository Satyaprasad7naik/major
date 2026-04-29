"""
Alert Engine Service
====================
Core alert processing engine that follows the architecture:
- Fetch new events from the events table
- For each event, find matching metrics and update sliding windows (Redis)
- Evaluate alerts and trigger/resolve as needed
"""

import json
import time
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from threading import Thread, Event
import redis

from app.core.config import settings

# Database path for alerts
ALERTS_DB_PATH = "derivinsight_alerts.db"
ALERTS_DB_URL = f"sqlite:///./{ALERTS_DB_PATH}"


class AlertEngineService:
    """
    Alert Engine that processes events and evaluates alerts.
    
    Architecture:
    - events table (SQLite): stores incoming events (id, table_name, payload_json, created_at)
    - metric_specs table (SQLite): defines alert conditions (metric_id, table_name, filter_json, window_sec, threshold, is_active)
    - Redis ZSET: stores event timestamps for sliding window calculations (replaces metric_windows table)
    - alert_history table (SQLite): logs alert triggers and resolutions
    
    Redis Key Pattern:
    - metric:{metric_id} -> ZSET with event timestamps as score and value
    """
    
    def __init__(self, db_url: str = None, redis_url: str = None):
        # SQLite for persistent data
        self.db_url = db_url or ALERTS_DB_URL
        self.engine = create_engine(self.db_url)
        
        # Redis for sliding window data
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_client: Optional[redis.Redis] = None
        self._redis_available = False
        
        self._stop_event = Event()
        self._engine_thread: Optional[Thread] = None
        self._last_processed_id: int = 0
        self._engine_status: str = "stopped"
        
        # Optional short TTL cache for failure spike summary
        self._failure_spike_cache: Optional[Dict[str, Any]] = None
        self._failure_spike_cache_ts: float = 0
        self.FAILURE_SPIKE_CACHE_TTL_SEC: float = 30.0
        
        # Initialize Redis connection
        self._init_redis()
        
        print(f"[AlertEngine] Initialized with database: {self.db_url}")
        print(f"[AlertEngine] Redis: {'connected' if self._redis_available else 'not available (using fallback)'}")
    
    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self._redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self._redis_client.ping()
            self._redis_available = True
            print(f"[AlertEngine] Connected to Redis: {self.redis_url}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            print(f"[AlertEngine] Redis connection failed: {e}")
            print("[AlertEngine] Falling back to SQLite for metric windows")
            self._redis_available = False
            self._redis_client = None
    
    @property
    def redis(self) -> Optional[redis.Redis]:
        """Get Redis client, attempt reconnect if disconnected."""
        if self._redis_client is None:
            self._init_redis()
        return self._redis_client
    
    # ==================== DATABASE HELPERS ====================
    
    def execute(self, sql: str, params: dict = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results."""
        try:
            with self.engine.connect() as conn:
                if params:
                    result = conn.execute(text(sql), params)
                else:
                    result = conn.execute(text(sql))
                
                if result.returns_rows:
                    return [dict(row) for row in result.mappings()]
                else:
                    conn.commit()
                    return [{"rows_affected": result.rowcount}]
        except Exception as e:
            print(f"[AlertEngine] Database error: {e}")
            return []
    
    def initialize_db(self, schema_path: str = None):
        """Initialize the alerts database with schema."""
        if schema_path is None:
            schema_path = os.path.join(os.path.dirname(__file__), "..", "files", "alerts_schema.sql")
        
        if not os.path.exists(schema_path):
            print(f"[AlertEngine] Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, 'r') as f:
            sql_content = f.read()
        
        statements = sql_content.split(';')
        
        with self.engine.connect() as conn:
            for statement in statements:
                if statement.strip():
                    try:
                        conn.execute(text(statement))
                    except Exception as e:
                        print(f"[AlertEngine] Schema error: {e}")
            conn.commit()
        
        print("[AlertEngine] Database initialized successfully")
        return True
    
    def ensure_anomaly_history_table(self):
        """Create anomaly_history table and indexes if they do not exist (for existing DBs)."""
        sqls = [
            """
            CREATE TABLE IF NOT EXISTS anomaly_history (
                metric_id INTEGER PRIMARY KEY,
                metric_name TEXT NOT NULL,
                severity TEXT DEFAULT 'medium',
                alert_count INTEGER NOT NULL DEFAULT 0,
                detected_at TIMESTAMP,
                last_seen_at TIMESTAMP,
                last_resolved_at TIMESTAMP,
                current_status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (metric_id) REFERENCES metric_specs(metric_id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_anomaly_history_current_status ON anomaly_history(current_status)",
            "CREATE INDEX IF NOT EXISTS idx_anomaly_history_updated_at ON anomaly_history(updated_at)",
        ]
        for sql in sqls:
            try:
                self.execute(sql.strip())
            except Exception as e:
                print(f"[AlertEngine] ensure_anomaly_history_table: {e}")
    
    # ==================== EVENT OPERATIONS ====================
    
    def insert_event(self, table_name: str, payload: dict) -> int:
        """Insert a new event into the events table."""
        payload_json = json.dumps(payload)
        sql = """
            INSERT INTO events (table_name, payload_json, created_at, processed)
            VALUES (:table_name, :payload_json, :created_at, 0)
        """
        self.execute(sql, {
            "table_name": table_name,
            "payload_json": payload_json,
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Get the last inserted ID
        result = self.execute("SELECT last_insert_rowid() as id")
        event_id = result[0]["id"] if result else 0
        print(f"[Event] Inserted: {table_name} (id={event_id})")
        return event_id
    
    def fetch_new_events(self, last_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch new events after the last processed ID."""
        sql = """
            SELECT id, table_name, payload_json, created_at
            FROM events
            WHERE id > :last_id
            ORDER BY id ASC
            LIMIT :limit
        """
        return self.execute(sql, {"last_id": last_id, "limit": limit})
    
    # ==================== METRIC OPERATIONS ====================
    
    def get_metrics_for_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all metric specs that apply to a given table/event type."""
        sql = """
            SELECT metric_id, name, table_name, filter_json, window_sec, threshold, is_active, severity
            FROM metric_specs
            WHERE table_name = :table_name
        """
        return self.execute(sql, {"table_name": table_name})
    
    def get_all_metrics(self) -> List[Dict[str, Any]]:
        """Get all metric specs."""
        sql = "SELECT * FROM metric_specs"
        return self.execute(sql)
    
    def create_metric(self, name: str, description: str, table_name: str, 
                      filter_json: dict, window_sec: int, threshold: int, 
                      severity: str = "medium") -> int:
        """Create a new metric spec (alert definition)."""
        sql = """
            INSERT INTO metric_specs (name, description, table_name, filter_json, window_sec, threshold, severity)
            VALUES (:name, :description, :table_name, :filter_json, :window_sec, :threshold, :severity)
        """
        self.execute(sql, {
            "name": name,
            "description": description,
            "table_name": table_name,
            "filter_json": json.dumps(filter_json),
            "window_sec": window_sec,
            "threshold": threshold,
            "severity": severity
        })
        
        result = self.execute("SELECT last_insert_rowid() as id")
        metric_id = result[0]["id"] if result else 0
        print(f"[Metric] Created: {name} (id={metric_id})")
        return metric_id
    
    def update_metric(self, metric_id: int, **kwargs) -> bool:
        """Update a metric spec."""
        allowed_fields = ["name", "description", "table_name", "filter_json", "window_sec", "threshold", "severity"]
        updates = []
        params = {"metric_id": metric_id}
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == "filter_json" and isinstance(value, dict):
                    value = json.dumps(value)
                updates.append(f"{field} = :{field}")
                params[field] = value
        
        if not updates:
            return False
        
        updates.append("updated_at = :updated_at")
        params["updated_at"] = datetime.utcnow().isoformat()
        
        sql = f"UPDATE metric_specs SET {', '.join(updates)} WHERE metric_id = :metric_id"
        self.execute(sql, params)
        print(f"[Metric] Updated: metric_id={metric_id}")
        return True
    
    def delete_metric(self, metric_id: int) -> bool:
        """Delete a metric spec and its window data."""
        # Clear Redis window data
        if self._redis_available and self.redis:
            try:
                self.redis.delete(self._get_metric_key(metric_id))
            except redis.RedisError as e:
                print(f"[AlertEngine] Redis error deleting metric window: {e}")
        
        # Fallback: also delete from SQLite if table exists
        self.execute("DELETE FROM metric_windows WHERE metric_id = :metric_id", {"metric_id": metric_id})
        self.execute("DELETE FROM metric_specs WHERE metric_id = :metric_id", {"metric_id": metric_id})
        print(f"[Metric] Deleted: metric_id={metric_id}")
        return True
    
    # ==================== FILTER MATCHING ====================
    
    def matches_filter(self, payload: dict, filter_json: str) -> bool:
        """
        Check if event payload matches the metric filter.
        
        Filter examples:
        - '{}' or '' -> matches everything
        - '{"status": "failed"}' -> matches if payload["status"] == "failed"
        - '{"status": "failed", "amount_gt": 1000}' -> compound conditions
        """
        if not filter_json or filter_json == '{}':
            return True
        
        try:
            filter_dict = json.loads(filter_json) if isinstance(filter_json, str) else filter_json
        except json.JSONDecodeError:
            return True
        
        if not filter_dict:
            return True
        
        for key, expected_value in filter_dict.items():
            # Handle special operators
            if key.endswith("_gt"):
                actual_key = key[:-3]
                if actual_key not in payload or payload[actual_key] <= expected_value:
                    return False
            elif key.endswith("_lt"):
                actual_key = key[:-3]
                if actual_key not in payload or payload[actual_key] >= expected_value:
                    return False
            elif key.endswith("_gte"):
                actual_key = key[:-4]
                if actual_key not in payload or payload[actual_key] < expected_value:
                    return False
            elif key.endswith("_lte"):
                actual_key = key[:-4]
                if actual_key not in payload or payload[actual_key] > expected_value:
                    return False
            elif key.endswith("_in"):
                actual_key = key[:-3]
                if actual_key not in payload or payload[actual_key] not in expected_value:
                    return False
            else:
                # Exact match
                if key not in payload or payload[key] != expected_value:
                    return False
        
        return True
    
    # ==================== REDIS SLIDING WINDOW OPERATIONS ====================
    
    def _get_metric_key(self, metric_id: int) -> str:
        """Get Redis key for a metric's sliding window."""
        return f"metric:{metric_id}"
    
    def update_metric_window(self, metric_id: int, event_timestamp: str, window_sec: int):
        """
        Update the sliding window for a metric using Redis ZSET.
        
        Redis operations:
        - ZADD: Add event timestamp (score = unix timestamp, member = unique id)
        - ZREMRANGEBYSCORE: Remove events outside the window
        """
        if self._redis_available and self.redis:
            try:
                self._update_metric_window_redis(metric_id, event_timestamp, window_sec)
                return
            except redis.RedisError as e:
                print(f"[AlertEngine] Redis error, falling back to SQLite: {e}")
                self._redis_available = False
        
        # Fallback to SQLite
        self._update_metric_window_sqlite(metric_id, event_timestamp, window_sec)
    
    def _update_metric_window_redis(self, metric_id: int, event_timestamp: str, window_sec: int):
        """Update sliding window using Redis."""
        key = self._get_metric_key(metric_id)
        
        # Convert timestamp to unix timestamp for scoring
        try:
            if isinstance(event_timestamp, str):
                dt = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
            else:
                dt = event_timestamp
            timestamp_score = dt.timestamp()
        except:
            timestamp_score = time.time()
        
        # Create unique member (timestamp + random suffix to allow duplicates)
        member = f"{timestamp_score}:{time.time_ns()}"
        
        # Add to sorted set (ZADD)
        self.redis.zadd(key, {member: timestamp_score})
        
        # Remove old entries outside the window (ZREMRANGEBYSCORE)
        window_start = time.time() - window_sec
        self.redis.zremrangebyscore(key, 0, window_start)
        
        # Set TTL on key to auto-expire (window_sec + buffer)
        self.redis.expire(key, window_sec + 60)
    
    def _update_metric_window_sqlite(self, metric_id: int, event_timestamp: str, window_sec: int):
        """Fallback: Update sliding window using SQLite."""
        # Add new timestamp
        sql = """
            INSERT INTO metric_windows (metric_id, event_timestamp)
            VALUES (:metric_id, :event_timestamp)
        """
        self.execute(sql, {"metric_id": metric_id, "event_timestamp": event_timestamp})
        
        # Remove old timestamps outside the window
        window_start = (datetime.utcnow() - timedelta(seconds=window_sec)).isoformat()
        sql = """
            DELETE FROM metric_windows
            WHERE metric_id = :metric_id AND event_timestamp < :window_start
        """
        self.execute(sql, {"metric_id": metric_id, "window_start": window_start})
    
    def get_window_count(self, metric_id: int, window_sec: int) -> int:
        """
        Get the count of events in the current window for a metric.
        
        Redis: ZCOUNT or ZCARD after cleanup
        """
        if self._redis_available and self.redis:
            try:
                return self._get_window_count_redis(metric_id, window_sec)
            except redis.RedisError as e:
                print(f"[AlertEngine] Redis error, falling back to SQLite: {e}")
                self._redis_available = False
        
        # Fallback to SQLite
        return self._get_window_count_sqlite(metric_id, window_sec)
    
    def _get_window_count_redis(self, metric_id: int, window_sec: int) -> int:
        """Get window count using Redis."""
        key = self._get_metric_key(metric_id)
        
        # Get current time and window start
        now = time.time()
        window_start = now - window_sec
        
        # Count entries within the window (ZCOUNT)
        count = self.redis.zcount(key, window_start, now)
        return count
    
    def _get_window_count_sqlite(self, metric_id: int, window_sec: int) -> int:
        """Fallback: Get window count using SQLite."""
        window_start = (datetime.utcnow() - timedelta(seconds=window_sec)).isoformat()
        sql = """
            SELECT COUNT(*) as count
            FROM metric_windows
            WHERE metric_id = :metric_id AND event_timestamp >= :window_start
        """
        result = self.execute(sql, {"metric_id": metric_id, "window_start": window_start})
        return result[0]["count"] if result else 0
    
    def clear_metric_window(self, metric_id: int):
        """Clear all window data for a metric."""
        if self._redis_available and self.redis:
            try:
                self.redis.delete(self._get_metric_key(metric_id))
            except redis.RedisError:
                pass
        
        # Also clear SQLite fallback
        self.execute("DELETE FROM metric_windows WHERE metric_id = :metric_id", {"metric_id": metric_id})
    
    def clear_all_windows(self):
        """Clear all metric window data from Redis."""
        if self._redis_available and self.redis:
            try:
                # Find all metric keys
                keys = self.redis.keys("metric:*")
                if keys:
                    self.redis.delete(*keys)
                print(f"[AlertEngine] Cleared {len(keys)} metric windows from Redis")
            except redis.RedisError as e:
                print(f"[AlertEngine] Redis error clearing windows: {e}")
        
        # Also clear SQLite fallback
        self.execute("DELETE FROM metric_windows")
    
    # ==================== ALERT EVALUATION ====================
    
    def evaluate_alert(self, metric: Dict[str, Any]):
        """
        Evaluate if an alert should be triggered or resolved.
        
        - If count > threshold AND not active -> trigger alert
        - If count <= threshold AND active -> resolve alert
        """
        metric_id = metric["metric_id"]
        threshold = metric["threshold"]
        is_active = metric["is_active"]
        window_sec = metric["window_sec"]
        
        count = self.get_window_count(metric_id, window_sec)
        
        if count > threshold and not is_active:
            self._trigger_alert(metric, count)
        elif count <= threshold and is_active:
            self._resolve_alert(metric, count)
    
    def _upsert_anomaly_history(self, metric: Dict[str, Any], action: str):
        """
        Update anomaly_history whenever alert_history is updated for this metric.
        - detected_at: set when alert becomes active and (no row or current_status was 'resolved').
        - last_seen_at: updated on every trigger.
        - last_resolved_at: updated on every resolve.
        - alert_count: total number of 'triggered' rows in alert_history for this metric.
        - current_status: 'active' on trigger, 'resolved' on resolve.
        """
        metric_id = metric["metric_id"]
        now_iso = datetime.utcnow().isoformat()
        # Alert count = total triggers for this metric
        ac = self.execute(
            "SELECT COUNT(*) as c FROM alert_history WHERE metric_id = :mid AND action = 'triggered'",
            {"mid": metric_id},
        )
        alert_count = ac[0]["c"] if ac else 0
        existing = self.execute(
            "SELECT detected_at, last_seen_at, last_resolved_at, current_status FROM anomaly_history WHERE metric_id = :mid",
            {"mid": metric_id},
        )
        existing = existing[0] if existing else None
        metric_name = metric.get("name", "")
        severity = metric.get("severity", "medium")
        if action == "triggered":
            detected_at = now_iso if (not existing or existing.get("current_status") == "resolved") else (existing.get("detected_at") or now_iso)
            last_seen_at = now_iso
            last_resolved_at = existing.get("last_resolved_at") if existing else None
            current_status = "active"
        else:
            detected_at = existing.get("detected_at") if existing else None
            last_seen_at = existing.get("last_seen_at") if existing else None
            last_resolved_at = now_iso
            current_status = "resolved"
        sql = """
            INSERT INTO anomaly_history (metric_id, metric_name, severity, alert_count, detected_at, last_seen_at, last_resolved_at, current_status, updated_at)
            VALUES (:metric_id, :metric_name, :severity, :alert_count, :detected_at, :last_seen_at, :last_resolved_at, :current_status, :updated_at)
            ON CONFLICT(metric_id) DO UPDATE SET
                metric_name = excluded.metric_name,
                severity = excluded.severity,
                alert_count = excluded.alert_count,
                detected_at = excluded.detected_at,
                last_seen_at = excluded.last_seen_at,
                last_resolved_at = excluded.last_resolved_at,
                current_status = excluded.current_status,
                updated_at = excluded.updated_at
        """
        self.execute(sql, {
            "metric_id": metric_id,
            "metric_name": metric_name,
            "severity": severity,
            "alert_count": alert_count,
            "detected_at": detected_at,
            "last_seen_at": last_seen_at,
            "last_resolved_at": last_resolved_at,
            "current_status": current_status,
            "updated_at": now_iso,
        })
    
    def _trigger_alert(self, metric: Dict[str, Any], count: int):
        """Trigger an alert."""
        metric_id = metric["metric_id"]
        message = f"🚨 ALERT TRIGGERED: {metric['name']} - Count {count} exceeds threshold {metric['threshold']}"
        
        # Log to alert history
        sql = """
            INSERT INTO alert_history (metric_id, action, event_count, threshold, message)
            VALUES (:metric_id, 'triggered', :count, :threshold, :message)
        """
        self.execute(sql, {
            "metric_id": metric_id,
            "count": count,
            "threshold": metric["threshold"],
            "message": message
        })
        
        # Mark metric as active
        self.execute("UPDATE metric_specs SET is_active = 1 WHERE metric_id = :metric_id", {"metric_id": metric_id})
        
        # Keep anomaly_history in sync
        self._upsert_anomaly_history(metric, "triggered")
        
        print(f"\n{message}")
        print(f"   Severity: {metric.get('severity', 'medium').upper()}")
        print(f"   Window: {metric['window_sec']}s | Table: {metric['table_name']}\n")
    
    def _resolve_alert(self, metric: Dict[str, Any], count: int):
        """Resolve an active alert."""
        metric_id = metric["metric_id"]
        message = f"✅ ALERT RESOLVED: {metric['name']} - Count {count} now below threshold {metric['threshold']}"
        
        # Log to alert history
        sql = """
            INSERT INTO alert_history (metric_id, action, event_count, threshold, message)
            VALUES (:metric_id, 'resolved', :count, :threshold, :message)
        """
        self.execute(sql, {
            "metric_id": metric_id,
            "count": count,
            "threshold": metric["threshold"],
            "message": message
        })
        
        # Mark metric as inactive
        self.execute("UPDATE metric_specs SET is_active = 0 WHERE metric_id = :metric_id", {"metric_id": metric_id})
        
        # Keep anomaly_history in sync
        self._upsert_anomaly_history(metric, "resolved")
        
        print(f"\n{message}\n")
    
    # ==================== ENGINE STATE ====================
    # last_processed_id: Redis (key alert_engine:last_processed_id), fallback in-memory
    LAST_PROCESSED_ID_KEY = "alert_engine:last_processed_id"
    
    def get_last_processed_id(self) -> int:
        """Get the last processed event ID (from Redis, or in-memory fallback)."""
        if self._redis_available and self.redis:
            try:
                val = self.redis.get(self.LAST_PROCESSED_ID_KEY)
                if val is not None:
                    return int(val)
            except (redis.RedisError, ValueError):
                pass
        return self._last_processed_id
    
    def save_last_processed_id(self, event_id: int):
        """Save the last processed event ID to Redis and in-memory fallback."""
        self._last_processed_id = event_id
        if self._redis_available and self.redis:
            try:
                self.redis.set(self.LAST_PROCESSED_ID_KEY, str(event_id))
            except redis.RedisError:
                pass
    
    def set_engine_status(self, status: str):
        """Set the engine status (running/stopped)."""
        self._engine_status = status
    
    def get_engine_status(self) -> str:
        """Get the current engine status."""
        return self._engine_status
    
    # ==================== CORE EVENT PROCESSING ====================
    
    def process_event(self, event: Dict[str, Any]):
        """
        Process a single event:
        1. Load metrics for this table
        2. Check filter condition for each metric
        3. Update sliding window if filter matches (Redis)
        4. Evaluate alert
        """
        table_name = event["table_name"]
        
        try:
            payload = json.loads(event["payload_json"]) if isinstance(event["payload_json"], str) else event["payload_json"]
        except json.JSONDecodeError:
            payload = {}
        
        event_timestamp = event.get("created_at", datetime.utcnow().isoformat())
        
        # Get metrics for this table
        metrics = self.get_metrics_for_table(table_name)
        
        for metric in metrics:
            # Check if event matches the filter
            if self.matches_filter(payload, metric.get("filter_json", "{}")):
                # Update sliding window (Redis)
                self.update_metric_window(metric["metric_id"], event_timestamp, metric["window_sec"])
                
                # Evaluate alert
                self.evaluate_alert(metric)
    
    # ==================== MAIN ENGINE LOOP ====================
    
    def run_engine(self, tick_interval: float = 1.0):
        """
        Main engine loop (blocking).
        Continuously fetches and processes new events.
        """
        print("[AlertEngine] Starting engine...")
        self.set_engine_status("running")
        last_processed_id = self.get_last_processed_id()
        
        print(f"[AlertEngine] Resuming from event ID: {last_processed_id}")
        
        while not self._stop_event.is_set():
            try:
                events = self.fetch_new_events(last_processed_id)
                
                for event in events:
                    self.process_event(event)
                    last_processed_id = event["id"]
                
                if events:
                    self.save_last_processed_id(last_processed_id)
                    print(f"[AlertEngine] Processed {len(events)} events. Last ID: {last_processed_id}")
                
                time.sleep(tick_interval)
                
            except Exception as e:
                print(f"[AlertEngine] Error in main loop: {e}")
                time.sleep(tick_interval)
        
        self.set_engine_status("stopped")
        print("[AlertEngine] Engine stopped.")
    
    def start_background(self, tick_interval: float = 1.0):
        """Start the engine in a background thread."""
        if self._engine_thread and self._engine_thread.is_alive():
            print("[AlertEngine] Engine already running")
            return
        
        self._stop_event.clear()
        self._engine_thread = Thread(target=self.run_engine, args=(tick_interval,), daemon=True)
        self._engine_thread.start()
        print("[AlertEngine] Engine started in background")
    
    def stop(self):
        """Stop the engine."""
        print("[AlertEngine] Stopping engine...")
        self._stop_event.set()
        if self._engine_thread:
            self._engine_thread.join(timeout=5.0)
    
    # ==================== ALERT HISTORY ====================
    
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alert history."""
        sql = """
            SELECT ah.*, ms.name as metric_name, ms.table_name, ms.severity
            FROM alert_history ah
            JOIN metric_specs ms ON ah.metric_id = ms.metric_id
            ORDER BY ah.created_at DESC
            LIMIT :limit
        """
        return self.execute(sql, {"limit": limit})
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all currently active alerts."""
        sql = """
            SELECT metric_id, name, table_name, filter_json, window_sec, threshold, severity
            FROM metric_specs
            WHERE is_active = 1
        """
        return self.execute(sql)
    
    def get_anomaly_history(
        self,
        limit: int = 100,
        current_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List anomaly_history rows, optionally filtered by current_status ('active' | 'resolved').
        """
        if current_status and current_status not in ("active", "resolved"):
            current_status = None
        if current_status:
            sql = """
                SELECT metric_id, metric_name, severity, alert_count, detected_at,
                       last_seen_at, last_resolved_at, current_status, created_at, updated_at
                FROM anomaly_history
                WHERE current_status = :current_status
                ORDER BY updated_at DESC
                LIMIT :limit
            """
            return self.execute(sql, {"current_status": current_status, "limit": limit})
        sql = """
            SELECT metric_id, metric_name, severity, alert_count, detected_at,
                   last_seen_at, last_resolved_at, current_status, created_at, updated_at
            FROM anomaly_history
            ORDER BY updated_at DESC
            LIMIT :limit
        """
        return self.execute(sql, {"limit": limit})
    
    def get_anomaly_history_summary(self) -> Dict[str, int]:
        """
        Aggregate counts from anomaly_history for dashboard header:
        - active: count where current_status = 'active'
        - critical: count where current_status = 'active' AND severity = 'critical'
        - resolved_today: count where current_status = 'resolved' AND date(last_resolved_at) = date('now')
        """
        active = self.execute(
            "SELECT COUNT(*) as c FROM anomaly_history WHERE current_status = 'active'"
        )
        critical = self.execute(
            "SELECT COUNT(*) as c FROM anomaly_history WHERE current_status = 'active' AND severity = 'critical'"
        )
        resolved_today = self.execute(
            "SELECT COUNT(*) as c FROM anomaly_history WHERE current_status = 'resolved' AND date(last_resolved_at) = date('now')"
        )
        return {
            "active": active[0]["c"] if active else 0,
            "critical": critical[0]["c"] if critical else 0,
            "resolved_today": resolved_today[0]["c"] if resolved_today else 0,
        }
    
    def get_events_count_in_window(self, table_name: str, window_sec: int) -> int:
        """Count total events in the events table for the given table_name in the last window_sec."""
        window_start = (datetime.utcnow() - timedelta(seconds=window_sec)).isoformat()
        sql = """
            SELECT COUNT(*) as count
            FROM events
            WHERE table_name = :table_name AND created_at >= :window_start
        """
        result = self.execute(sql, {"table_name": table_name, "window_start": window_start})
        return result[0]["count"] if result else 0
    
    def _get_failure_count_in_events_window(
        self, table_name: str, filter_json: str, since_iso: str, until_iso: str
    ) -> int:
        """Count events matching the metric filter in events table within a time range."""
        try:
            filter_dict = json.loads(filter_json) if isinstance(filter_json, str) else filter_json
        except (json.JSONDecodeError, TypeError):
            filter_dict = {}
        if not filter_dict:
            sql = """
                SELECT COUNT(*) as count FROM events
                WHERE table_name = :table_name AND created_at >= :since AND created_at <= :until
            """
            result = self.execute(sql, {"table_name": table_name, "since": since_iso, "until": until_iso})
            return result[0]["count"] if result else 0
        # Simple case: single key like {"status": "failed"} or {"kyc_status": "rejected"}
        key = next(iter(filter_dict))
        val = filter_dict[key]
        if isinstance(val, str) and key.replace("_", "").isalnum():
            # Path as literal (key restricted to alphanumeric + underscore)
            path_literal = f"$.{key}"
            sql = f"""
                SELECT COUNT(*) as count FROM events
                WHERE table_name = :table_name AND created_at >= :since AND created_at <= :until
                AND json_extract(payload_json, '{path_literal}') = :val
            """
            result = self.execute(
                sql, {
                    "table_name": table_name,
                    "since": since_iso,
                    "until": until_iso,
                    "val": val,
                }
            )
            return result[0]["count"] if result else 0
        # Fallback: fetch and filter in Python (for complex filters)
        sql = """
            SELECT id, payload_json FROM events
            WHERE table_name = :table_name AND created_at >= :since AND created_at <= :until
        """
        rows = self.execute(sql, {"table_name": table_name, "since": since_iso, "until": until_iso})
        count = 0
        for row in rows:
            try:
                payload = json.loads(row["payload_json"]) if isinstance(row["payload_json"], str) else row["payload_json"]
                if self.matches_filter(payload, filter_json):
                    count += 1
            except (json.JSONDecodeError, TypeError):
                pass
        return count
    
    def get_failure_spike_summary(
        self,
        use_cache: bool = True,
        skip_baseline_lookup: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Build failure spike card summaries from anomaly_history (current_status='active')
        and metric_specs. Enriches with current rate from window; optional baseline from
        last resolved window.
        """
        now_ts = time.time()
        if use_cache and self._failure_spike_cache is not None:
            if (now_ts - self._failure_spike_cache_ts) < self.FAILURE_SPIKE_CACHE_TTL_SEC:
                return self._failure_spike_cache.get("summaries", [])
        # Active anomalies only; join metric_specs for table_name, window_sec, threshold, filter_json
        sql = """
            SELECT ah.metric_id, ah.metric_name, ah.severity, ah.alert_count, ah.detected_at,
                   ah.last_seen_at, ah.last_resolved_at, ah.current_status,
                   ms.table_name, ms.window_sec, ms.threshold, ms.filter_json
            FROM anomaly_history ah
            JOIN metric_specs ms ON ah.metric_id = ms.metric_id
            WHERE ah.current_status = 'active'
            ORDER BY ah.last_seen_at DESC
        """
        rows = self.execute(sql)
        # Optional: only failure-related metrics for "failure spike" card
        failure_rows = [
            r for r in rows
            if "fail" in (r.get("metric_name") or "").lower()
            or "failed" in (r.get("filter_json") or "{}").lower()
        ]
        if not failure_rows:
            if use_cache:
                self._failure_spike_cache = {"summaries": []}
                self._failure_spike_cache_ts = now_ts
            return []
        table_window_pairs = {(r["table_name"], r["window_sec"]) for r in failure_rows}
        events_count_cache = {}
        for (tname, wsec) in table_window_pairs:
            events_count_cache[(tname, wsec)] = self.get_events_count_in_window(tname, wsec)
        now = datetime.utcnow()
        out = []
        for r in failure_rows:
            metric_id = r["metric_id"]
            name = r["metric_name"]
            table_name = r["table_name"]
            window_sec = r["window_sec"]
            threshold = r["threshold"]
            filter_json = r.get("filter_json") or "{}"
            severity = r.get("severity", "medium")
            detected_at_iso = r.get("detected_at") or r.get("last_seen_at")
            if not detected_at_iso:
                continue
            try:
                detected_at = datetime.fromisoformat(detected_at_iso.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                detected_at = now
            if detected_at.tzinfo:
                now_local = datetime.now(detected_at.tzinfo)
            else:
                now_local = now
            detected_mins_ago = max(0, int((now_local - detected_at).total_seconds() / 60))
            duration_mins = max(0, int((now_local - detected_at).total_seconds() / 60))
            current_failed = self.get_window_count(metric_id, window_sec)
            total_in_window = events_count_cache.get((table_name, window_sec), 0)
            current_rate_pct = round((current_failed / total_in_window) * 100, 1) if total_in_window else 0.0
            baseline_rate_pct = 0.7
            if not skip_baseline_lookup and r.get("last_resolved_at"):
                resolved_at_iso = r["last_resolved_at"]
                try:
                    resolved_at = datetime.fromisoformat(resolved_at_iso.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    resolved_at = now_local
                window_start_dt = resolved_at - timedelta(seconds=window_sec)
                since_iso = window_start_dt.isoformat()
                until_iso = resolved_at.isoformat()
                total_then_row = self.execute(
                    "SELECT COUNT(*) as count FROM events WHERE table_name = :tn AND created_at >= :since AND created_at <= :until",
                    {"tn": table_name, "since": since_iso, "until": until_iso},
                )
                total_then = total_then_row[0]["count"] if total_then_row else 0
                if total_then > 0:
                    failed_then = self._get_failure_count_in_events_window(
                        table_name, filter_json, since_iso, until_iso
                    )
                    baseline_rate_pct = round((failed_then / total_then) * 100, 1)
            out.append({
                "title": "Failure Spike Detected",
                "severity_label": "Critical" if severity == "critical" else "High",
                "status": "Active",
                "metric_name": name,
                "metric": "Failure Rate",
                "current_rate_pct": current_rate_pct,
                "baseline_rate_pct": baseline_rate_pct,
                "current_vs_baseline": f"{current_rate_pct}% vs {baseline_rate_pct}%",
                "current_count": current_failed,
                "threshold": threshold,
                "detected_at": detected_at_iso,
                "detected_mins_ago": detected_mins_ago,
                "duration_mins": duration_mins,
                "duration_ongoing": True,
                "summary": "Failure rate crossed expected threshold significantly.",
                "actions": ["open_dashboard", "acknowledge", "snooze"],
                "metric_id": metric_id,
                "table_name": table_name,
            })
        if use_cache:
            self._failure_spike_cache = {"summaries": out}
            self._failure_spike_cache_ts = now_ts
        return out
    
    # ==================== STATS ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        total_events = self.execute("SELECT COUNT(*) as count FROM events")
        total_metrics = self.execute("SELECT COUNT(*) as count FROM metric_specs")
        active_alerts = self.execute("SELECT COUNT(*) as count FROM metric_specs WHERE is_active = 1")
        total_triggered = self.execute("SELECT COUNT(*) as count FROM alert_history WHERE action = 'triggered'")
        
        return {
            "total_events": total_events[0]["count"] if total_events else 0,
            "total_metrics": total_metrics[0]["count"] if total_metrics else 0,
            "active_alerts": active_alerts[0]["count"] if active_alerts else 0,
            "total_alerts_triggered": total_triggered[0]["count"] if total_triggered else 0,
            "last_processed_id": self.get_last_processed_id(),
            "engine_status": self.get_engine_status(),
            "redis_available": self._redis_available
        }
    
    def get_redis_stats(self) -> Dict[str, Any]:
        """Get Redis-specific statistics."""
        if not self._redis_available or not self.redis:
            return {"available": False, "message": "Redis not connected"}
        
        try:
            # Get all metric keys
            keys = self.redis.keys("metric:*")
            
            window_stats = {}
            for key in keys:
                metric_id = key.split(":")[1]
                count = self.redis.zcard(key)
                ttl = self.redis.ttl(key)
                window_stats[f"metric_{metric_id}"] = {
                    "count": count,
                    "ttl": ttl
                }
            
            return {
                "available": True,
                "total_metric_keys": len(keys),
                "windows": window_stats
            }
        except redis.RedisError as e:
            return {"available": False, "error": str(e)}


# Singleton instance
alert_engine = AlertEngineService()
