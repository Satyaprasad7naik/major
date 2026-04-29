from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class AlertRequest(BaseModel):
    base_sql: str
    user_message: str
    conversation_history: List[Dict[str, str]] = []

class AlertResponse(BaseModel):
    status: str  # "created" | "needs_clarification" | "failed"
    response_message: str
    alert_sql: Optional[str] = None
    alert_config: Optional[Dict[str, Any]] = None
    clarification_question: Optional[str] = None
