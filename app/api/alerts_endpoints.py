"""
Alert Engine API Endpoints
==========================
REST API endpoints for managing the alert engine.

Endpoints:
- POST   /api/v1/alerts/metrics           - Create a new metric spec
- GET    /api/v1/alerts/metrics           - List all metric specs
- GET    /api/v1/alerts/metrics/{id}      - Get a specific metric
- PUT    /api/v1/alerts/metrics/{id}      - Update a metric
- DELETE /api/v1/alerts/metrics/{id}      - Delete a metric
- GET    /api/v1/alerts/active            - Get active alerts
- GET    /api/v1/alerts/history           - Get alert history
- GET    /api/v1/alerts/failure-spike     - Get failure spike summary (from anomaly_history)
- GET    /api/v1/alerts/anomaly-history    - List anomaly history (metric_id, alert_count, status, etc.)
- GET    /api/v1/alerts/anomaly-history/summary - Aggregates: active, critical, resolved_today
- POST   /api/v1/alerts/events            - Push a new event
- GET    /api/v1/alerts/stats             - Get engine stats
- POST   /api/v1/alerts/engine/start      - Start the alert engine
- POST   /api/v1/alerts/engine/stop       - Stop the alert engine
- GET    /api/v1/alerts/engine/status     - Get engine status
- POST   /api/v1/alerts/generator/start   - Start event generator
- POST   /api/v1/alerts/generator/stop    - Stop event generator
- GET    /api/v1/alerts/generator/status  - Get generator status
- POST   /api/v1/alerts/generator/burst   - Generate burst events for testing
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json

from app.services.alert_engine import AlertEngineService, ALERTS_DB_PATH
from app.services.alert_events_generate import EventGenerator
from app.services.worker_registry import worker_registry
from app.services import task_orchestrator
import os

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

# Initialize alert engine
alert_engine = AlertEngineService()

# Initialize event generator (singleton; used for burst and in-worker container)
event_generator = EventGenerator()

# Check if DB exists and initialize if needed
if not os.path.exists(ALERTS_DB_PATH):
    schema_path = os.path.join(os.path.dirname(__file__), "..", "files", "alerts_schema.sql")
    alert_engine.initialize_db(schema_path)
else:
    alert_engine.ensure_anomaly_history_table()


# ==================== PYDANTIC MODELS ====================

class MetricCreate(BaseModel):
    """Model for creating a new metric spec."""
    name: str = Field(..., description="Human-readable metric name")
    description: Optional[str] = Field(None, description="Description of what this metric tracks")
    table_name: str = Field(..., description="Event type this metric applies to (e.g., 'login', 'transaction')")
    filter_json: Dict[str, Any] = Field(default={}, description="Filter conditions as JSON")
    window_sec: int = Field(..., description="Sliding window duration in seconds", ge=1)
    threshold: int = Field(..., description="Count threshold to trigger alert", ge=1)
    severity: str = Field(default="medium", description="Alert severity: low, medium, high, critical")


class MetricUpdate(BaseModel):
    """Model for updating a metric spec."""
    name: Optional[str] = None
    description: Optional[str] = None
    table_name: Optional[str] = None
    filter_json: Optional[Dict[str, Any]] = None
    window_sec: Optional[int] = Field(None, ge=0)
    threshold: Optional[int] = Field(None, ge=1)
    severity: Optional[str] = None


class EventCreate(BaseModel):
    """Model for creating a new event."""
    table_name: str = Field(..., description="Event type (e.g., 'login', 'transaction', 'kyc')")
    payload: Dict[str, Any] = Field(..., description="Event payload data")


class MetricResponse(BaseModel):
    """Response model for a metric."""
    metric_id: int
    name: str
    description: Optional[str]
    table_name: str
    filter_json: str
    window_sec: int
    threshold: int
    is_active: bool
    severity: str
    created_at: Optional[str]
    updated_at: Optional[str]


class GeneratorConfig(BaseModel):
    """Configuration for the event generator."""
    user_interval: float = Field(default=60, description="Interval for user events in seconds")
    login_min_interval: float = Field(default=2, description="Min interval for login events")
    login_max_interval: float = Field(default=10, description="Max interval for login events")
    txn_min_interval: float = Field(default=1, description="Min interval for transaction events")
    txn_max_interval: float = Field(default=4, description="Max interval for transaction events")
    kyc_min_interval: float = Field(default=10, description="Min interval for KYC events")
    kyc_max_interval: float = Field(default=20, description="Max interval for KYC events")


class BurstRequest(BaseModel):
    """Request model for generating burst events."""
    event_type: str = Field(..., description="Event type: 'login', 'transaction', or 'kyc'")
    count: int = Field(default=10, description="Number of events to generate", ge=1, le=100)
    status: Optional[str] = Field(default=None, description="Status for the events (e.g., 'failed', 'success')")


class WorkerStartRequest(BaseModel):
    """Optional body for engine/generator start: register an externally started task by taskArn."""
    task_arn: Optional[str] = Field(default=None, description="Task ARN of the worker (e.g. ECS task); if provided, only registers in Redis")


class GeneratorStartRequest(BaseModel):
    """Body for generator start: optional task_arn to register, optional config when API starts the task."""
    task_arn: Optional[str] = Field(default=None, description="Task ARN if registering an externally started task")
    config: Optional[GeneratorConfig] = Field(default=None, description="Generator config when API starts the task")


class StartAllRequest(BaseModel):
    """Body for start-all: optional task ARNs to register (externally started workers)."""
    engine_task_arn: Optional[str] = Field(default=None, description="Engine worker task ARN to register")
    generator_task_arn: Optional[str] = Field(default=None, description="Generator worker task ARN to register")


# ==================== METRIC ENDPOINTS ====================

@router.post("/metrics", response_model=dict)
async def create_metric(metric: MetricCreate):
    """
    Create a new metric spec (alert definition).
    
    Example:
    ```json
    {
        "name": "Failed Login Spike",
        "description": "Triggers when failed logins exceed threshold",
        "table_name": "login",
        "filter_json": {"status": "failed"},
        "window_sec": 300,
        "threshold": 10,
        "severity": "high"
    }
    ```
    """
    window_sec = metric.window_sec if (metric.window_sec is not None and metric.window_sec > 0) else 60
    metric_id = alert_engine.create_metric(
        name=metric.name,
        description=metric.description or "",
        table_name=metric.table_name,
        filter_json=metric.filter_json,
        window_sec=window_sec,
        threshold=metric.threshold,
        severity=metric.severity
    )
    
    return {
        "status": "success",
        "metric_id": metric_id,
        "message": f"Metric '{metric.name}' created successfully"
    }


@router.get("/metrics")
async def list_metrics():
    """Get all metric specs."""
    metrics = alert_engine.get_all_metrics()
    return {
        "status": "success",
        "count": len(metrics),
        "metrics": metrics
    }


@router.get("/metrics/{metric_id}")
async def get_metric(metric_id: int):
    """Get a specific metric by ID."""
    result = alert_engine.execute(
        "SELECT * FROM metric_specs WHERE metric_id = :metric_id",
        {"metric_id": metric_id}
    )
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Metric {metric_id} not found")
    
    return {
        "status": "success",
        "metric": result[0]
    }


@router.put("/metrics/{metric_id}")
async def update_metric(metric_id: int, metric: MetricUpdate):
    """Update a metric spec."""
    # Check if exists
    existing = alert_engine.execute(
        "SELECT metric_id FROM metric_specs WHERE metric_id = :metric_id",
        {"metric_id": metric_id}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail=f"Metric {metric_id} not found")
    
    # Build update dict
    updates = {}
    if metric.name is not None:
        updates["name"] = metric.name
    if metric.description is not None:
        updates["description"] = metric.description
    if metric.table_name is not None:
        updates["table_name"] = metric.table_name
    if metric.filter_json is not None:
        updates["filter_json"] = metric.filter_json
    if metric.window_sec is not None:
        updates["window_sec"] = metric.window_sec if metric.window_sec > 0 else 60
    if metric.threshold is not None:
        updates["threshold"] = metric.threshold
    if metric.severity is not None:
        updates["severity"] = metric.severity
    
    if updates:
        alert_engine.update_metric(metric_id, **updates)
    
    return {
        "status": "success",
        "message": f"Metric {metric_id} updated"
    }


@router.delete("/metrics/{metric_id}")
async def delete_metric(metric_id: int):
    """Delete a metric spec."""
    # Check if exists
    existing = alert_engine.execute(
        "SELECT metric_id FROM metric_specs WHERE metric_id = :metric_id",
        {"metric_id": metric_id}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail=f"Metric {metric_id} not found")
    
    alert_engine.delete_metric(metric_id)
    
    return {
        "status": "success",
        "message": f"Metric {metric_id} deleted"
    }


# ==================== ALERT ENDPOINTS ====================

@router.get("/active")
async def get_active_alerts():
    """Get all currently active alerts."""
    active = alert_engine.get_active_alerts()
    return {
        "status": "success",
        "count": len(active),
        "active_alerts": active
    }


@router.get("/history")
async def get_alert_history(limit: int = 50):
    """Get alert history (triggers and resolutions)."""
    history = alert_engine.get_alert_history(limit=limit)
    return {
        "status": "success",
        "count": len(history),
        "history": history
    }


@router.get("/failure-spike")
async def get_failure_spike(
    use_cache: bool = True,
    skip_baseline_lookup: bool = False,
):
    """
    Get failure spike summary from anomaly_history (current_status='active') and metric_specs.
    Returns card-ready data: title, status, metric (Failure Rate), current vs baseline %,
    detected time, duration, summary, and actions (Open Dashboard, Acknowledge, Snooze).
    - use_cache: use 30s TTL cache to reduce latency on repeated calls (default True).
    - skip_baseline_lookup: if True, use default baseline and skip extra DB queries (lower latency).
    """
    summaries = alert_engine.get_failure_spike_summary(
        use_cache=use_cache,
        skip_baseline_lookup=skip_baseline_lookup,
    )
    return {
        "status": "success",
        "count": len(summaries),
        "failure_spikes": summaries
    }


@router.get("/anomaly-history")
async def list_anomaly_history(
    limit: int = 100,
    current_status: Optional[str] = None,
):
    """
    List anomaly_history rows (one per metric, updated on every alert trigger/resolve).
    Query params:
    - limit: max rows (default 100).
    - current_status: filter by 'active' or 'resolved'.
    """
    rows = alert_engine.get_anomaly_history(limit=limit, current_status=current_status)
    return {
        "status": "success",
        "count": len(rows),
        "anomaly_history": rows
    }


@router.get("/anomaly-history/summary")
async def get_anomaly_history_summary():
    """
    Aggregate counts from anomaly_history for dashboard header:
    - active: number of anomalies currently active
    - critical: number of active anomalies with severity critical
    - resolved_today: number resolved today (by date(last_resolved_at))
    """
    summary = alert_engine.get_anomaly_history_summary()
    return {
        "status": "success",
        "active": summary["active"],
        "critical": summary["critical"],
        "resolved_today": summary["resolved_today"],
    }


# ==================== EVENT ENDPOINTS ====================

@router.post("/events")
async def create_event(event: EventCreate):
    """
    Push a new event to the events table.
    
    Example:
    ```json
    {
        "table_name": "login",
        "payload": {
            "user_id": 123,
            "status": "failed",
            "ip_address": "192.168.1.1"
        }
    }
    ```
    """
    event_id = alert_engine.insert_event(
        table_name=event.table_name,
        payload=event.payload
    )
    
    return {
        "status": "success",
        "event_id": event_id,
        "message": f"Event '{event.table_name}' created"
    }


@router.get("/events")
async def list_events(limit: int = 100, offset: int = 0):
    """Get recent events."""
    events = alert_engine.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT :limit OFFSET :offset",
        {"limit": limit, "offset": offset}
    )
    
    total = alert_engine.execute("SELECT COUNT(*) as count FROM events")
    
    return {
        "status": "success",
        "total": total[0]["count"] if total else 0,
        "count": len(events),
        "events": events
    }


# ==================== ENGINE CONTROL ====================

@router.get("/stats")
async def get_stats():
    """Get engine statistics."""
    stats = alert_engine.get_stats()
    return {
        "status": "success",
        "stats": stats
    }


@router.get("/redis/stats")
async def get_redis_stats():
    """Get Redis statistics for sliding windows."""
    stats = alert_engine.get_redis_stats()
    return {
        "status": "success",
        "redis": stats
    }


@router.post("/redis/clear")
async def clear_redis_windows():
    """Clear all metric window data from Redis."""
    alert_engine.clear_all_windows()
    return {
        "status": "success",
        "message": "All metric windows cleared"
    }


@router.post("/engine/start")
async def start_engine(body: Optional[WorkerStartRequest] = None):
    """
    Start the alert engine worker (runs in a separate container).
    If task_arn is provided in body, registers that task in Redis (task was started externally).
    Otherwise attempts to start the task via ECS (if configured) and stores taskArn in Redis.
    """
    if not worker_registry.is_available():
        raise HTTPException(status_code=503, detail="Redis unavailable; cannot register engine worker")
    task_arn = body.task_arn if body else None
    if task_arn:
        if worker_registry.get_engine_task_arn():
            return {
                "status": "warning",
                "message": "Engine worker already registered; stop it first to register a new task_arn"
            }
        if worker_registry.set_engine_task_arn(task_arn):
            return {
                "status": "success",
                "message": "Engine worker task registered",
                "task_arn": task_arn
            }
        raise HTTPException(status_code=500, detail="Failed to store task_arn in Redis")
    task_arn, err = task_orchestrator.start_engine_task()
    if err and not task_arn:
        raise HTTPException(status_code=400, detail=err)
    if not task_arn:
        raise HTTPException(status_code=500, detail="Failed to start engine task")
    if not worker_registry.set_engine_task_arn(task_arn):
        return {
            "status": "error",
            "message": "Engine task started but failed to register task_arn in Redis",
            "task_arn": task_arn
        }
    return {
        "status": "success",
        "message": "Alert engine worker started",
        "task_arn": task_arn
    }


@router.post("/engine/stop")
async def stop_engine():
    """
    Stop the alert engine worker: fetch taskArn from Redis, stop that task, then remove the key.
    """
    if not worker_registry.is_available():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    task_arn = worker_registry.get_engine_task_arn()
    if not task_arn:
        return {
            "status": "warning",
            "message": "Engine is already stopped (no task_arn in Redis)"
        }
    err = task_orchestrator.stop_engine_task(task_arn)
    worker_registry.delete_engine_task_arn()
    if err:
        return {
            "status": "success",
            "message": "Engine task unregistered from Redis; stop may have failed",
            "stop_error": err
        }
    return {
        "status": "success",
        "message": "Alert engine worker stopped"
    }


@router.get("/engine/status")
async def engine_status():
    """
    Get engine status from Redis: if task_arn key is present, engine is running.
    """
    if not worker_registry.is_available():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    task_arn = worker_registry.get_engine_task_arn()
    status = "running" if task_arn else "stopped"
    out = {"status": "success", "engine_status": status}
    if task_arn:
        out["task_arn"] = task_arn
    return out


# ==================== EVENT GENERATOR CONTROL ====================

@router.post("/generator/start")
async def start_generator(body: Optional[GeneratorStartRequest] = None):
    """
    Start the event generator worker (runs in a separate container).
    If task_arn is provided in body, registers that task in Redis (task was started externally).
    Otherwise attempts to start the task via ECS (if configured) and stores taskArn in Redis.
    Config in body is used when the API starts the task; otherwise the worker container uses its own config.
    """
    if not worker_registry.is_available():
        raise HTTPException(status_code=503, detail="Redis unavailable; cannot register generator worker")
    task_arn = body.task_arn if body else None
    config = body.config if body else None
    if task_arn:
        if worker_registry.get_generator_task_arn():
            return {
                "status": "warning",
                "message": "Generator worker already registered; stop it first to register a new task_arn"
            }
        if worker_registry.set_generator_task_arn(task_arn):
            return {
                "status": "success",
                "message": "Generator worker task registered",
                "task_arn": task_arn
            }
        raise HTTPException(status_code=500, detail="Failed to store task_arn in Redis")
    task_arn, err = task_orchestrator.start_generator_task()
    if err and not task_arn:
        raise HTTPException(status_code=400, detail=err)
    if not task_arn:
        raise HTTPException(status_code=500, detail="Failed to start generator task")
    if not worker_registry.set_generator_task_arn(task_arn):
        return {
            "status": "error",
            "message": "Generator task started but failed to register task_arn in Redis",
            "task_arn": task_arn
        }
    cfg = config or GeneratorConfig()
    return {
        "status": "success",
        "message": "Event generator worker started",
        "task_arn": task_arn,
        "config": {
            "user_interval": cfg.user_interval,
            "login_interval": [cfg.login_min_interval, cfg.login_max_interval],
            "txn_interval": [cfg.txn_min_interval, cfg.txn_max_interval],
            "kyc_interval": [cfg.kyc_min_interval, cfg.kyc_max_interval]
        }
    }


@router.post("/generator/stop")
async def stop_generator():
    """
    Stop the generator worker: fetch taskArn from Redis, stop that task, then remove the key.
    """
    if not worker_registry.is_available():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    task_arn = worker_registry.get_generator_task_arn()
    if not task_arn:
        return {
            "status": "warning",
            "message": "Generator is already stopped (no task_arn in Redis)"
        }
    err = task_orchestrator.stop_generator_task(task_arn)
    worker_registry.delete_generator_task_arn()
    if err:
        return {
            "status": "success",
            "message": "Generator task unregistered from Redis; stop may have failed",
            "stop_error": err
        }
    return {
        "status": "success",
        "message": "Event generator worker stopped"
    }


@router.get("/generator/status")
async def generator_status():
    """
    Get generator status from Redis: if task_arn key is present, generator is running.
    """
    if not worker_registry.is_available():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    task_arn = worker_registry.get_generator_task_arn()
    running = task_arn is not None
    out = {
        "status": "success",
        "generator_running": running,
    }
    if task_arn:
        out["task_arn"] = task_arn
    return out


@router.post("/generator/burst")
async def generate_burst(request: BurstRequest):
    """
    Generate a burst of events for testing alerts.
    
    This is useful for quickly testing if alerts trigger correctly.
    
    Example:
    ```json
    {
        "event_type": "login",
        "count": 15,
        "status": "failed"
    }
    ```
    
    Supported event types:
    - login: status can be "success" or "failed" (default: "failed")
    - transaction: status can be "success" or "failed" (default: "failed")
    - kyc: generates rejection events (status ignored)
    """
    event_type = request.event_type.lower()
    count = request.count
    
    if event_type == "login":
        status = request.status or "failed"
        event_generator.generate_login_burst(count=count, status=status)
        return {
            "status": "success",
            "message": f"Generated {count} {status} login events",
            "event_type": "login",
            "count": count
        }
    
    elif event_type == "transaction":
        status = request.status or "failed"
        event_generator.generate_transaction_burst(count=count, status=status)
        return {
            "status": "success",
            "message": f"Generated {count} {status} transaction events",
            "event_type": "transaction",
            "count": count
        }
    
    elif event_type == "kyc":
        event_generator.generate_kyc_rejection_burst(count=count)
        return {
            "status": "success",
            "message": f"Generated {count} KYC rejection events",
            "event_type": "kyc",
            "count": count
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event type: {event_type}. Supported: login, transaction, kyc"
        )


# ==================== COMBINED CONTROL ====================

@router.post("/start-all")
async def start_all_services(body: Optional[StartAllRequest] = None):
    """
    Start both the alert engine and event generator workers (each in a separate container).
    Uses Redis task_arn registration; pass engine_task_arn and/or generator_task_arn to register externally started tasks.
    """
    if not worker_registry.is_available():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    results = {}
    task_arn_engine = body.engine_task_arn if body else None
    task_arn_gen = body.generator_task_arn if body else None
    # Start engine: register or ECS
    if worker_registry.get_engine_task_arn():
        results["engine"] = "already running"
    elif task_arn_engine:
        worker_registry.set_engine_task_arn(task_arn_engine)
        results["engine"] = "registered"
    else:
        arn, err = task_orchestrator.start_engine_task()
        if arn:
            worker_registry.set_engine_task_arn(arn)
            results["engine"] = "started"
        else:
            results["engine"] = f"failed: {err}"
    # Start generator: register or ECS
    if worker_registry.get_generator_task_arn():
        results["generator"] = "already running"
    elif task_arn_gen:
        worker_registry.set_generator_task_arn(task_arn_gen)
        results["generator"] = "registered"
    else:
        arn, err = task_orchestrator.start_generator_task()
        if arn:
            worker_registry.set_generator_task_arn(arn)
            results["generator"] = "started"
        else:
            results["generator"] = f"failed: {err}"
    return {
        "status": "success",
        "message": "Services start requested",
        "results": results
    }


@router.post("/stop-all")
async def stop_all_services():
    """
    Stop both the alert engine and event generator workers: fetch taskArn from Redis, stop each, remove keys.
    """
    if not worker_registry.is_available():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    results = {}
    # Stop generator first
    g_arn = worker_registry.get_generator_task_arn()
    if g_arn:
        task_orchestrator.stop_generator_task(g_arn)
        worker_registry.delete_generator_task_arn()
        results["generator"] = "stopped"
    else:
        results["generator"] = "not running"
    # Stop engine
    e_arn = worker_registry.get_engine_task_arn()
    if e_arn:
        task_orchestrator.stop_engine_task(e_arn)
        worker_registry.delete_engine_task_arn()
        results["engine"] = "stopped"
    else:
        results["engine"] = "not running"
    return {
        "status": "success",
        "message": "Services stopped",
        "results": results
    }


@router.get("/status-all")
async def get_all_status():
    """
    Get status of both the alert engine and event generator from Redis and engine stats.
    """
    if not worker_registry.is_available():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    stats = alert_engine.get_stats()
    engine_task_arn = worker_registry.get_engine_task_arn()
    generator_task_arn = worker_registry.get_generator_task_arn()
    return {
        "status": "success",
        "engine": {
            "status": "running" if engine_task_arn else "stopped",
            "task_arn": engine_task_arn,
            "last_processed_id": stats["last_processed_id"],
            "total_events": stats["total_events"],
            "active_alerts": stats["active_alerts"],
            "total_alerts_triggered": stats["total_alerts_triggered"]
        },
        "generator": {
            "running": generator_task_arn is not None,
            "task_arn": generator_task_arn
        }
    }
