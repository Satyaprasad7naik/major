"""
Database Test Endpoints
REST API endpoints to test connectivity and query all tables in the database.
Supports MySQL (AWS RDS) via SQLAlchemy.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

router = APIRouter(prefix="/api/db-test", tags=["Database Testing"])

# Create SQLAlchemy engine from DATABASE_URL
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)


class QueryRequest(BaseModel):
    """Request model for executing custom queries."""
    query: str
    table_name: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for query results."""
    success: bool
    table_name: Optional[str] = None
    row_count: int
    data: List[Dict[str, Any]]
    error: Optional[str] = None


def execute_query(query: str, table_name: Optional[str] = None) -> QueryResponse:
    """Execute a query on the database."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in rows]

        return QueryResponse(
            success=True,
            table_name=table_name,
            row_count=len(data),
            data=data
        )
    except SQLAlchemyError as e:
        return QueryResponse(
            success=False,
            table_name=table_name,
            row_count=0,
            data=[],
            error=str(e)
        )


# ==================== Health Check Endpoints ====================

@router.get("/health")
def db_health_check() -> Dict[str, Any]:
    """Check connectivity to the database."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database_url": settings.DATABASE_URL.replace(
                settings.DATABASE_URL.split("@")[0].split(":")[-1], "****"
            ) if "@" in settings.DATABASE_URL else settings.DATABASE_URL
        }
    except SQLAlchemyError as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ==================== Schema Endpoints ====================

@router.get("/schema")
def get_database_schema() -> Dict[str, Any]:
    """Get the schema (all tables and columns) for the database."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        schema = {}
        for table in tables:
            columns = inspector.get_columns(table)
            schema[table] = [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "default": str(col.get("default")) if col.get("default") else None,
                    "primary_key": col.get("primary_key", False)
                }
                for col in columns
            ]

        return {
            "tables": list(schema.keys()),
            "table_count": len(schema),
            "schema": schema
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/{table_name}")
def get_table_schema(table_name: str) -> Dict[str, Any]:
    """Get the schema for a specific table."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if table_name not in tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = pk_constraint.get("constrained_columns", []) if pk_constraint else []

        schema = [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": str(col.get("default")) if col.get("default") else None,
                "primary_key": col["name"] in pk_columns
            }
            for col in columns
        ]

        return {
            "table_name": table_name,
            "column_count": len(schema),
            "columns": schema
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Generic Table Endpoints ====================

@router.get("/tables")
def get_all_tables() -> Dict[str, Any]:
    """Get list of all tables with row counts."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        table_info = {}
        with engine.connect() as conn:
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                table_info[table] = result.scalar()

        return {
            "tables": table_info,
            "table_count": len(table_info),
            "total_rows": sum(table_info.values())
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/table/{table_name}")
def get_table_data(table_name: str, limit: int = 10, offset: int = 0) -> QueryResponse:
    """Get data from any table by name."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if table_name not in tables:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    return execute_query(f"SELECT * FROM `{table_name}` LIMIT {limit} OFFSET {offset}", table_name)


@router.get("/table/{table_name}/count")
def get_table_row_count(table_name: str) -> Dict[str, Any]:
    """Get row count for a specific table."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if table_name not in tables:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
            count = result.scalar()

        return {
            "table_name": table_name,
            "row_count": count
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Users Table ====================

@router.get("/users")
def get_users(limit: int = 10) -> QueryResponse:
    """Get users from the users table."""
    return execute_query(f"SELECT * FROM users LIMIT {limit}", "users")


@router.get("/users/{user_id}")
def get_user_by_id(user_id: str) -> QueryResponse:
    """Get a specific user by ID."""
    return execute_query(f"SELECT * FROM users WHERE user_id = '{user_id}'", "users")


# ==================== Transactions Table ====================

@router.get("/transactions")
def get_transactions(limit: int = 10) -> QueryResponse:
    """Get transactions."""
    return execute_query(f"SELECT * FROM transactions LIMIT {limit}", "transactions")


@router.get("/transactions/user/{user_id}")
def get_user_transactions(user_id: str, limit: int = 10) -> QueryResponse:
    """Get transactions for a specific user."""
    return execute_query(f"SELECT * FROM transactions WHERE user_id = '{user_id}' LIMIT {limit}", "transactions")


# ==================== Login Events Table ====================

@router.get("/login-events")
def get_login_events(limit: int = 10) -> QueryResponse:
    """Get login events."""
    return execute_query(f"SELECT * FROM login_events LIMIT {limit}", "login_events")


@router.get("/login-events/user/{user_id}")
def get_user_login_events(user_id: str, limit: int = 10) -> QueryResponse:
    """Get login events for a specific user."""
    return execute_query(f"SELECT * FROM login_events WHERE user_id = '{user_id}' LIMIT {limit}", "login_events")


# ==================== Metric Specs Table (Alerts) ====================

@router.get("/metric-specs")
def get_metric_specs() -> QueryResponse:
    """Get all metric specifications (alert configurations)."""
    return execute_query("SELECT * FROM metric_specs", "metric_specs")


@router.get("/metric-specs/{metric_id}")
def get_metric_spec_by_id(metric_id: int) -> QueryResponse:
    """Get a specific metric specification by ID."""
    return execute_query(f"SELECT * FROM metric_specs WHERE metric_id = {metric_id}", "metric_specs")


# ==================== Alert History Table ====================

@router.get("/alert-history")
def get_alert_history(limit: int = 20) -> QueryResponse:
    """Get alert history."""
    return execute_query(f"SELECT * FROM alert_history ORDER BY created_at DESC LIMIT {limit}", "alert_history")


@router.get("/alert-history/metric/{metric_id}")
def get_alert_history_by_metric(metric_id: int, limit: int = 10) -> QueryResponse:
    """Get alert history for a specific metric."""
    return execute_query(f"SELECT * FROM alert_history WHERE metric_id = {metric_id} ORDER BY created_at DESC LIMIT {limit}", "alert_history")


# ==================== Anomaly History Table ====================

@router.get("/anomaly-history")
def get_anomaly_history() -> QueryResponse:
    """Get anomaly history."""
    return execute_query("SELECT * FROM anomaly_history ORDER BY updated_at DESC", "anomaly_history")


# ==================== Events Table (Alerts) ====================

@router.get("/events")
def get_events(limit: int = 10) -> QueryResponse:
    """Get events."""
    return execute_query(f"SELECT * FROM events ORDER BY created_at DESC LIMIT {limit}", "events")


# ==================== Dashboards Table ====================

@router.get("/dashboards")
def get_dashboards(limit: int = 10) -> QueryResponse:
    """Get dashboards."""
    return execute_query(f"SELECT * FROM dashboards LIMIT {limit}", "dashboards")


@router.get("/dashboards/{dashboard_id}")
def get_dashboard_by_id(dashboard_id: str) -> QueryResponse:
    """Get a specific dashboard by ID."""
    return execute_query(f"SELECT * FROM dashboards WHERE dashboard_id = '{dashboard_id}'", "dashboards")


@router.get("/dashboards/deployed")
def get_deployed_dashboards() -> QueryResponse:
    """Get all deployed dashboards."""
    return execute_query("SELECT * FROM dashboards WHERE is_deployed = 1", "dashboards")


# ==================== Statistics Endpoint ====================

@router.get("/stats")
def get_database_stats() -> Dict[str, Any]:
    """Get statistics for all tables in the database."""
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        table_stats = {}
        with engine.connect() as conn:
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM `{table}`"))
                table_stats[table] = {"row_count": result.scalar()}

        return {
            "tables": table_stats,
            "total_tables": len(table_stats),
            "total_rows": sum(t["row_count"] for t in table_stats.values())
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Custom Query Endpoint ====================

@router.post("/query")
def execute_custom_query(request: QueryRequest) -> QueryResponse:
    """
    Execute a custom SQL query on the database.

    WARNING: This endpoint is for testing purposes only.
    In production, you should validate and sanitize all inputs.
    """
    # Basic safety check - only allow SELECT queries
    query_upper = request.query.strip().upper()
    if not query_upper.startswith("SELECT"):
        raise HTTPException(
            status_code=400,
            detail="Only SELECT queries are allowed for safety. Use specific endpoints for modifications."
        )

    return execute_query(request.query, request.table_name)
