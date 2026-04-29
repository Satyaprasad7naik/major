"""
Dashboard API Endpoints
=======================
REST API endpoints for managing user dashboards.

Endpoints:
- POST /api/v1/dashboards           - Create a new dashboard
- GET  /api/v1/dashboards           - Fetch all dashboards for a user
- GET  /api/v1/dashboards/{id}      - Get dashboard details by ID
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
import uuid
import sqlite3
import json

router = APIRouter(prefix="/api/v1/dashboards", tags=["dashboards"])

DATABASE_PATH = "./deriveinsights_dashboard.db"


def get_db_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ==================== PYDANTIC MODELS ====================

class DashboardCreate(BaseModel):
    """Model for creating a new dashboard - only dashboardName is required."""
    dashboardName: str = Field(..., min_length=1, description="Name of the dashboard (required)")
    userId: Optional[str] = None
    domainType: Optional[str] = None
    graphsArray: Optional[List[Any]] = None


class DashboardResponse(BaseModel):
    """Response model for dashboard creation."""
    status: str
    dashboardId: str
    name: str


class DashboardListItem(BaseModel):
    """Model for dashboard list item."""
    dashboardName: str
    dashboardId: str
    createdAt: str


class DashboardListResponse(BaseModel):
    """Response model for fetching all dashboards."""
    domainType: str
    dashboards: List[DashboardListItem]


class DashboardDetailResponse(BaseModel):
    """Response model for dashboard details."""
    dashboardId: str
    dashboardName: str
    domainType: Optional[str]
    graphsArray: Optional[List[Any]]


# ==================== DASHBOARD ENDPOINTS ====================

@router.post("", response_model=DashboardResponse)
async def create_dashboard(dashboard: DashboardCreate):
    """
    Create a new dashboard.
    Only dashboardName is required.
    """
    # Generate unique dashboard ID
    dashboard_id = str(uuid.uuid4().int)[:11]

    # Prepare widgets JSON (store graphsArray as widgets)
    widgets_json = json.dumps(dashboard.graphsArray) if dashboard.graphsArray else None

    # Prepare layout JSON (store domainType in layout)
    layout_json = json.dumps({"domainType": dashboard.domainType}) if dashboard.domainType else None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO dashboards (dashboard_id, name, owner_id, widgets, layout, is_deployed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dashboard_id,
                dashboard.dashboardName,
                dashboard.userId,
                widgets_json,
                layout_json,
                False,
                datetime.now().isoformat()
            )
        )
        conn.commit()
    finally:
        conn.close()

    return DashboardResponse(
        status="success",
        dashboardId=dashboard_id,
        name=dashboard.dashboardName
    )


@router.get("", response_model=DashboardListResponse)
async def fetch_all_dashboards(userId: Optional[str] = None, domainType: Optional[str] = None):
    """
    Fetch all dashboards for a user.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        if userId:
            cursor.execute(
                "SELECT dashboard_id, name, created_at, layout FROM dashboards WHERE owner_id = ?",
                (userId,)
            )
        else:
            cursor.execute("SELECT dashboard_id, name, created_at, layout FROM dashboards")

        rows = cursor.fetchall()
    finally:
        conn.close()

    dashboards = []
    for row in rows:
        layout = json.loads(row["layout"]) if row["layout"] else {}
        row_domain_type = layout.get("domainType", "")

        # Filter by domainType if specified (case-insensitive)
        if domainType and row_domain_type and row_domain_type.lower() != domainType.lower():
            continue

        created_at = row["created_at"] or ""
        if created_at and "T" in created_at:
            created_at = created_at.split("T")[0]

        dashboards.append(DashboardListItem(
            dashboardName=row["name"] or "",
            dashboardId=row["dashboard_id"],
            createdAt=created_at
        ))

    return DashboardListResponse(
        domainType=domainType or "all",
        dashboards=dashboards
    )


@router.get("/{dashboardId}", response_model=DashboardDetailResponse)
async def get_dashboard_details(dashboardId: str):
    """
    Get detailed information about a specific dashboard.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT dashboard_id, name, widgets, layout FROM dashboards WHERE dashboard_id = ?",
            (dashboardId,)
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard with ID '{dashboardId}' not found"
        )

    # Parse stored JSON
    graphs_array = json.loads(row["widgets"]) if row["widgets"] else []
    layout = json.loads(row["layout"]) if row["layout"] else {}
    domain_type = layout.get("domainType")

    return DashboardDetailResponse(
        dashboardId=row["dashboard_id"],
        dashboardName=row["name"] or "",
        domainType=domain_type,
        graphsArray=graphs_array
    )
