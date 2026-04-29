from typing import List, Dict, Any, Optional, Union, TypedDict, Literal
from pydantic import BaseModel, Field

# Domain types for the NL2SQL pipeline
DomainType = Literal["security", "compliance", "risk", "operations", "general"]

# HLD Section 4.2: Graph State Definition
class GraphState(TypedDict):
    user_question: str
    domain: str  # security | compliance | risk | operations | general
    conversation_history: List[Dict[str, str]]
    intent: Optional[str]
    confidence: float
    needs_clarification: bool  # True if query needs more info
    clarification_question: Optional[str]  # Question to ask user
    relevant_columns: List[str]
    few_shot_examples: List[Dict[str, Any]]
    generated_sql: Optional[str]
    validation_error: Optional[str]
    retry_count: int
    query_result: Optional[List[Dict[str, Any]]]
    visualization_config: Optional[Dict[str, Any]]  # Chart type, axis info, etc.
    insight: Optional[Union[str, List[str]]]  # AI-generated business insight
    recommendation: Optional[Union[str, List[str]]]  # Actionable business recommendation
    status: str  # success | failed | needs_clarification

# API Models
class QueryRequest(BaseModel):
    query: str
    domain: DomainType = "general"  # Default to general if not specified
    conversation_id: Optional[str] = None
    conversation_history: List[Dict[str, str]] = []  # Previous messages

class QueryResponse(BaseModel):
    sql: Optional[str]
    results: Optional[List[Dict[str, Any]]]
    visualization_config: Optional[Dict[str, Any]] = None
    insight: Optional[Union[str, List[str]]] = None
    recommendation: Optional[Union[str, List[str]]] = None
    status: str
    error: Optional[str] = None
    clarification_question: Optional[str] = None  # Set if needs clarification
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_final: bool = False  # True if SQL was generated, False if asking for clarification

