import pytest
import sqlite3
import json
from unittest.mock import MagicMock, patch
from app.services.alert_engine import AlertEngineService

def test_matches_filter_basic(alert_engine):
    """Test standard equality filters."""
    payload = {"status": "failed", "user_id": 123}
    
    # Exact match
    assert alert_engine.matches_filter(payload, '{"status": "failed"}') is True
    # Mismatch
    assert alert_engine.matches_filter(payload, '{"status": "success"}') is False
    # Compound match
    assert alert_engine.matches_filter(payload, '{"status": "failed", "user_id": 123}') is True
    # Empty filter matches all
    assert alert_engine.matches_filter(payload, '{}') is True

def test_matches_filter_operators(alert_engine):
    """Test operator filters (_gt, _lt, etc.)."""
    payload = {"amount": 500, "age": 25}
    
    assert alert_engine.matches_filter(payload, '{"amount_gt": 400}') is True
    assert alert_engine.matches_filter(payload, '{"amount_lt": 400}') is False
    assert alert_engine.matches_filter(payload, '{"age_gte": 25}') is True
    assert alert_engine.matches_filter(payload, '{"amount_lte": 500}') is True
    assert alert_engine.matches_filter(payload, '{"amount_in": [100, 500, 1000]}') is True

def test_insert_and_fetch_events(alert_engine):
    """Test event persistence."""
    alert_engine.insert_event("transactions", {"id": 1, "status": "failed"})
    alert_engine.insert_event("transactions", {"id": 2, "status": "success"})
    
    events = alert_engine.fetch_new_events(0)
    assert len(events) == 2
    assert events[0]["table_name"] == "transactions"
    assert "failed" in events[0]["payload_json"]

def test_alert_triggering(alert_engine):
    """Test that alerts trigger when threshold is exceeded."""
    # 1. Create a metric: trigger if > 2 failed logins in 60s
    metric_id = alert_engine.create_metric(
        name="High Failures",
        description="Too many failed logins",
        table_name="login_events",
        filter_json={"status": "failed"},
        window_sec=60,
        threshold=2
    )
    
    # 2. Insert 3 events that match
    for _ in range(3):
        alert_engine.insert_event("login_events", {"status": "failed"})
    
    # 3. Process events
    events = alert_engine.fetch_new_events(0)
    for event in events:
        alert_engine.process_event(event)

    # 4. Check if alert is active
    metrics = alert_engine.get_active_alerts()
    assert len(metrics) == 1
    assert metrics[0]["metric_id"] == metric_id
    
    # 5. Check alert history
    history = alert_engine.get_alert_history()
    assert len(history) == 1
    assert history[0]["action"] == "triggered"

def test_alert_resolution(alert_engine):
    """Test that active alerts resolve when count drops below threshold."""
    # 1. Create an active alert
    metric_id = alert_engine.create_metric("Test", "D", "t", {}, 60, 5)
    alert_engine.execute("UPDATE metric_specs SET is_active = 1 WHERE metric_id = :id", {"id": metric_id})
    
    # 2. Evaluate with 0 events in window (should resolve)
    metric = alert_engine.get_all_metrics()[0]
    alert_engine.evaluate_alert(metric)
    
    # 3. Check if resolved
    metric_updated = alert_engine.get_all_metrics()[0]
    assert metric_updated["is_active"] == 0
    
    history = alert_engine.get_alert_history()
    assert history[0]["action"] == "resolved"
