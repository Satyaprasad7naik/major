import json
from typing import List, Dict, Any, Optional, Tuple
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from app.services.llm import llm_service
from app.alert_system.metric_models import MetricDefinition
from app.core.logger import logger

class MetricGraphState(TypedDict):
    user_query: str
    domain: str
    conversation_history: List[Dict[str, str]]
    intent: Optional[str]
    relevant_tables: List[str]
    metric: Optional[Dict[str, Any]]
    status: str
    explanation: str
    clarification_question: Optional[str]
    needs_clarification: bool

async def classify_metric_intent_node(state: MetricGraphState) -> Dict[str, Any]:
    """Determines if the request is a valid alert/metric request."""
    query = state["user_query"]
    history = state.get("conversation_history", [])
    
    history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history[-3:]])
    
    prompt = f"""
You are a Monitoring System Intent Classifier.
Analyze the user's request for a data alert or metric.

History:
{history_str}

User Request: "{query}"

Tasks:
1. Is this a request to create/modify an alert or metric? (intent: "CREATE_METRIC")
2. Is it off-topic? (intent: "OFF_TOPIC")
3. Is it missing critical info like 'threshold', 'event type', or 'condition'? (needs_clarification: true/false)

Return JSON:
{{
  "intent": "CREATE_METRIC" | "OFF_TOPIC",
  "needs_clarification": boolean,
  "confidence": float
}}
"""
    try:
        res = await llm_service.generate_response(prompt)
        data = json.loads(res.replace("```json", "").replace("```", "").strip())
        return {
            "intent": data.get("intent", "CREATE_METRIC"),
            "needs_clarification": data.get("needs_clarification", False)
        }
    except:
        return {"intent": "CREATE_METRIC", "needs_clarification": False}

async def select_metric_tables_node(state: MetricGraphState) -> Dict[str, Any]:
    """Identifies which core table is relevant for the metric."""
    query = state["user_query"]
    
    prompt = f"""
Identify the core database table needed for this alert:
Tables:
- transactions: payments, trades, deposits, amounts
- login_events: login attempts, ip, device
- users: kyc, risk level, activity status

User Query: "{query}"

Return ONLY the table name in a JSON list. Example: ["transactions"]
"""
    try:
        res = await llm_service.generate_response(prompt)
        tables = json.loads(res.replace("```json", "").replace("```", "").strip())
        return {"relevant_tables": tables}
    except:
        return {"relevant_tables": ["transactions"]}

async def generate_metric_clarification_node(state: MetricGraphState) -> Dict[str, Any]:
    """Ask for missing alert parameters."""
    query = state["user_query"]
    
    prompt = f"""
The user wants an alert but some information is missing.
User: "{query}"

Task: Ask a friendly question to get missing details like:
- Threshold (e.g., "how many failures?")
- Window (e.g., "over what time period?")
- Specific condition (e.g., "which specific country or status?")

Return ONLY the question string.
"""
    question = await llm_service.generate_response(prompt)
    return {
        "clarification_question": question.strip(),
        "status": "needs_clarification"
    }

async def generate_metric_node(state: MetricGraphState) -> Dict[str, Any]:
    """Uses LLM to transform NL query into a structured Metric JSON."""
    query = state["user_query"]
    tables = state.get("relevant_tables", ["transactions"])
    history = state.get("conversation_history", [])
    
    # Use only the first table for primary event_type
    primary_table = tables[0] if tables else "transactions"
    # Mapping for consistent output format
    table_map = {"transactions": "transaction", "login_events": "login_event", "users": "user"}
    event_type = table_map.get(primary_table, "transaction")

    history_str = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-3:]])
    
    prompt = f"""
You are an expert Performance Monitoring Engineer. 
Convert the request into a "Metric Definition" JSON.

Context:
- Primary Event Type: {event_type}
- Chat History: {history_str}
- Current User Request: "{query}"

LOGIC RULES:
1. Identify if the user is asking for a COUNT, SUM, or AVG.
2. Identify the threshold (e.g., "below 50000" means threshold=50000).
3. Identify a filter if possible (e.g., status='failed'). If no specific filter is mentioned but a status is implied, add it. If NO filter is relevant, you can omit the "filter" key.
4. Set "window_sec" to 60 unless specified otherwise.

METRIC JSON STRUCTURE:
{{
  "metric_id": "m1",
  "event_type": "{event_type}",
  "filter": {{
    "field": "string_column_name",
    "operator": "==" | ">" | "<" | "!=",
    "value": "string_or_number"
  }},
  "aggregation": "count" | "sum" | "avg",
  "window_sec": 60,
  "threshold": 3
}}

Return JSON ONLY.
"""
    try:
        from app.core.config import settings
        response = await llm_service.generate_response(prompt, model_name=settings.SQL_MODEL)
        # Clean response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:-3]
        elif response.startswith("```"):
            response = response[3:-3]
            
        metric_data = json.loads(response.strip())
        
        # Ensure name consistency
        if "event_type" not in metric_data:
            metric_data["event_type"] = event_type
            
        return {
            "metric": metric_data,
            "status": "success",
            "explanation": f"Successfully created metric for: {query}"
        }
    except Exception as e:
        logger.error(f"Metric generation error: {e}")
        return {
            "status": "failed",
            "explanation": f"Error parsing metric: {str(e)}",
            "clarification_question": "I couldn't quite map that to a metric config. Could you specify the event type (transaction, login, user) and the threshold?"
        }

# Setup the graph
workflow = StateGraph(MetricGraphState)

workflow.add_node("classify_intent", classify_metric_intent_node)
workflow.add_node("select_tables", select_metric_tables_node)
workflow.add_node("clarification", generate_metric_clarification_node)
workflow.add_node("generate_metric", generate_metric_node)

workflow.set_entry_point("classify_intent")

def route_metric_intent(state: MetricGraphState):
    if state["intent"] == "OFF_TOPIC":
        return "end"
    if state["needs_clarification"]:
        return "clarification"
    return "select_tables"

workflow.add_conditional_edges(
    "classify_intent",
    route_metric_intent,
    {
        "clarification": "clarification",
        "select_tables": "select_tables",
        "end": END
    }
)

workflow.add_edge("select_tables", "generate_metric")
workflow.add_edge("generate_metric", END)
workflow.add_edge("clarification", END)

metric_app_graph = workflow.compile()
