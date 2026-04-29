import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock
from app.core.config import settings

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_db(monkeypatch):
    """Fixture to provide an in-memory test database."""
    # Patch settings
    monkeypatch.setattr(settings, "DATABASE_URL", "sqlite://")
    
    from app.services.database import DatabaseService
    db = DatabaseService()
    
    # Setup test schema
    with db.engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("DROP TABLE IF EXISTS users"))
        conn.execute(text("CREATE TABLE users (user_id INTEGER PRIMARY KEY, username TEXT, risk_level TEXT, account_status TEXT)"))
        conn.execute(text("INSERT INTO users (user_id, username, risk_level, account_status) VALUES (1, 'test_user', 'LOW', 'ACTIVE')"))
        conn.commit()
    
    return db

@pytest.fixture
def alert_engine():
    """Fixture to provide a test AlertEngineService with in-memory DB."""
    from app.services.alert_engine import AlertEngineService
    ae = AlertEngineService(db_url="sqlite:///:memory:")
    
    # Initialize basic schema for tests
    ae.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            processed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    ae.execute("""
        CREATE TABLE IF NOT EXISTS metric_specs (
            metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            table_name TEXT NOT NULL,
            filter_json TEXT NOT NULL,
            window_sec INTEGER NOT NULL,
            threshold INTEGER NOT NULL,
            severity TEXT DEFAULT 'medium',
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    ae.execute("""
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_id INTEGER,
            action TEXT NOT NULL,
            event_count INTEGER,
            threshold INTEGER,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (metric_id) REFERENCES metric_specs(metric_id)
        )
    """)
    ae.execute("""
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
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Force redis disable for tests
    ae._redis_available = False
    ae.execute("CREATE TABLE IF NOT EXISTS metric_windows (metric_id INTEGER, event_timestamp TIMESTAMP)")
    
    return ae
