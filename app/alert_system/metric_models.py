from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class MetricFilter(BaseModel):
    field: str
    operator: str = "=="
    value: Any

class MetricDefinition(BaseModel):
    metric_id: str = Field(..., description="Unique identifier for the metric (e.g., m1, m2)")
    event_type: str = Field(..., description="The table/event type (e.g., transaction, login_event, user)")
    filter: Optional[MetricFilter] = None
    aggregation: str = Field(..., description="Aggregation type (e.g., count, sum, avg)")
    window_sec: int = Field(..., description="Time window in seconds")
    threshold: float = Field(..., description="The value at which to trigger an alert")

class MetricRequest(BaseModel):
    query: str
    domain: str = "general"
    conversation_history: List[Dict[str, str]] = []

class MetricResponse(BaseModel):
    status: str
    metric: Optional[MetricDefinition] = None
    explanation: str
    clarification_question: Optional[str] = None
