from fastapi import APIRouter, HTTPException
from app.models.state import QueryRequest, QueryResponse
from app.alert_system.metric_models import MetricRequest, MetricResponse
from app.alert_system.metric_workflow import metric_app_graph
from app.orchestration.workflow import app_graph
from app.core.logger import logger

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query_database(request: QueryRequest):
    """
    Process a natural language query through the NL2SQL pipeline.
    Supports conversational clarification flow.
    """
    logger.info(f"Incoming query: {request.query} | Domain: {request.domain}")
    initial_state = {
        "user_question": request.query,
        "domain": request.domain,
        "conversation_history": request.conversation_history,
        "retry_count": 0
    }
    
    # Run the graph
    result = await app_graph.ainvoke(initial_state)
    logger.info(f"Graph execution status: {result.get('status')} for query: {request.query}")
    
    # Check if clarification is needed
    if result.get("status") == "needs_clarification":
        return QueryResponse(
            sql=None,
            results=None,
            status="needs_clarification",
            clarification_question=result.get("clarification_question"),
            is_final=False
        )
    
    # Check for validation errors
    if result.get("validation_error") and not result.get("query_result"):
        logger.warning(f"Validation failure for query: {request.query} | Error: {result['validation_error']}")
        return QueryResponse(
            sql=result.get("generated_sql"),
            results=None,
            status="failed",
            error=result["validation_error"],
            is_final=True
        )
    
    # Success - SQL generated and executed
    logger.info(f"Query success! {len(result.get('query_result', []))} rows returned.")
    return QueryResponse(
        sql=result.get("generated_sql"),
        results=result.get("query_result"),
        visualization_config=result.get("visualization_config"),
        insight=result.get("insight"),
        recommendation=result.get("recommendation"),
        status="success",
        is_final=True
    )

@router.post("/alert", response_model=MetricResponse)
async def create_alert(request: MetricRequest):
    """
    Process a request to create a data metric/alert.
    """
    logger.info(f"Relaying alert request to Metric Workflow: {request.query}")
    
    initial_state = {
        "user_query": request.query,
        "domain": request.domain,
        "conversation_history": request.conversation_history,
        "metric": {},
        "status": "pending",
        "explanation": ""
    }
    
    result = await metric_app_graph.ainvoke(initial_state)
    
    return MetricResponse(
        status=result.get("status", "failed"),
        metric=result.get("metric"),
        explanation=result.get("explanation", ""),
        clarification_question=result.get("clarification_question")
    )
