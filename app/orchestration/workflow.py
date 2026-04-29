import asyncio
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from app.models.state import GraphState
from app.modules.intent_classification import intent_module
from app.modules.clarification import clarification_module
from app.modules.preprocessing import preprocessing_service
from app.modules.sql_generation import sql_generation_module
from app.modules.validation import validation_module
from app.modules.visualization import visualization_module
from app.modules.insight_generation import insight_module
from app.services.database import db_service
from app.core.logger import logger

# Node Definitions

async def classify_intent_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Node: [classify_intent]")
    query = state["user_question"]
    domain = state.get("domain", "general")
    conversation_history = state.get("conversation_history", [])
    
    # OPTIMIZATION: Run Intent Classification and Preprocessing in parallel
    # Preprocessing does NOT require intent as a pre-output, only the domain.
    logger.info(f"Starting Intent Classification and Preprocessing in parallel for domain: {domain}")
    
    task_intent = intent_module.classify(query, conversation_history, domain=domain)
    task_preproc = preprocessing_service.process(query, domain=domain)
    
    results = await asyncio.gather(task_intent, task_preproc)
    
    intent, confidence, complexity, needs_clarification = results[0]
    preproc_data = results[1]
    
    logger.info(f"Intent classified: {intent} (conf: {confidence}) | Needs Clarification: {needs_clarification}")
    
    return {
        "intent": intent,
        "confidence": confidence,
        "needs_clarification": needs_clarification,
        "relevant_columns": preproc_data["relevant_columns"],
        "few_shot_examples": preproc_data["few_shot_examples"],
        "entities": preproc_data["entities"], # Ensure entities are passed forward
        "domain": domain
    }

async def generate_clarification_node(state: GraphState) -> Dict[str, Any]:
    """Ask user for more information."""
    query = state["user_question"]
    domain = state.get("domain", "general")
    conversation_history = state.get("conversation_history", [])
    
    clarification_question = await clarification_module.generate_clarification(
        query, domain, conversation_history
    )
    
    return {
        "clarification_question": clarification_question,
        "status": "needs_clarification"
    }

async def generate_sql_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Node: [generate_sql]")
    query = state["user_question"]
    domain = state.get("domain", "general")
    context = {
        "relevant_columns": state["relevant_columns"],
        "few_shot_examples": state["few_shot_examples"],
        "entities": state.get("entities", {}), # Fixed: Pass resolved entities forward
        "domain": domain,
        "conversation_history": state.get("conversation_history", [])
    }
    sql = await sql_generation_module.generate(query, context)
    
    # If the generator returned a guidance message (Error: ...)
    if sql.startswith("Error:"):
        logger.info(f"SQL Generator returned guidance instead of SQL: {sql[:50]}...")
        return {
            "generated_sql": None,
            "clarification_question": sql.replace("Error:", "").strip(),
            "status": "needs_clarification"
        }
        
    logger.info(f"SQL Generated: {sql[:50]}...")
    return {"generated_sql": sql}

async def validate_sql_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Node: [validate_sql]")
    sql = state["generated_sql"]
    is_valid, error = validation_module.validate(sql)
    if not is_valid:
        logger.warning(f"SQL Validation Error: {error}")
    return {"validation_error": error}

async def repair_sql_node(state: GraphState) -> Dict[str, Any]:
    query = state["user_question"]
    invalid_sql = state["generated_sql"]
    error = state["validation_error"]
    
    repaired_sql = await sql_generation_module.repair(query, invalid_sql, error)
    
    return {
        "generated_sql": repaired_sql,
        "validation_error": None,
        "retry_count": state.get("retry_count", 0) + 1
    }

async def execute_query_node(state: GraphState) -> Dict[str, Any]:
    logger.info("Node: [execute_query]")
    sql = state["generated_sql"]
    try:
        results = db_service.execute(sql)
        logger.info(f"Query execution successful. Rows: {len(results)}")
        return {"query_result": results, "status": "success"}
    except Exception as e:
        logger.error(f"SQL EXECUTION ERROR: {str(e)}")
        return {"query_result": None, "status": "failed", "validation_error": str(e)}

async def recommend_visualization_node(state: GraphState) -> Dict[str, Any]:
    """Analyze results and recommend visualization."""
    logger.info("Node: [recommend_visualization]")
    query = state["user_question"]
    sql = state.get("generated_sql", "")
    results = state.get("query_result", [])
    
    if not results:
        logger.info("No results for visualization recommendation.")
        return {"visualization_config": None}

    vis_config = await visualization_module.recommend(query, sql, results)
    logger.info(f"Visualization recommended: {vis_config.get('chart_type') if vis_config else 'None'}")
    
    # If LLM generated mock data because real results were empty
    if vis_config and vis_config.get("is_mock") and "mock_data" in vis_config:
        logger.info("Injecting mock data for demonstration.")
        return {
            "visualization_config": vis_config,
            "query_result": vis_config["mock_data"] # Update results with mock data
        }
    
    return {"visualization_config": vis_config}

async def insight_recommendation_node(state: GraphState) -> Dict[str, Any]:
    """Provide executive insights and recommendations based on the results."""
    logger.info("Node: [insight_recommendation]")
    query = state["user_question"]
    results = state.get("query_result", [])
    domain = state.get("domain", "general")
    status = state.get("status", "unknown")
    
    if status != "success":
        logger.info(f"Skipping insights because status is {status}")
        return {}

    insights = await insight_module.generate(query, results, domain)
    logger.info("Insights generated successfully.")
    
    return {
        "insight": insights.get("insight"),
        "recommendation": insights.get("recommendation")
    }

async def guidance_node(state: GraphState) -> Dict[str, Any]:
    """Generate a helpful response for off-topic or schema queries."""
    from app.services.llm import llm_service
    from app.modules.schema_understanding import schema_module
    
    query = state["user_question"]
    domain = state.get("domain", "general")
    intent = state.get("intent", "OFF_TOPIC")
    
    # Get schema context to help guide the user
    schema_context = schema_module.get_schema_string(domain=domain)
    
    if intent == "SCHEMA_QUERY":
        prompt = f"""
        You are a Database Expert. The user wants to know about the system structure.
        User asked: "{query}"
        
        Database Schema Context:
        {schema_context}
        
        Task:
        Provide a very clear and helpful list of the tables and columns available. 
        Structure it so it's easy to read (use bullet points).
        Mention what kind of questions you can answer with these tables.
        """
    else:
        prompt = f"""
        You are a helpful database assistant.
        The user asked: "{query}"
        This is off-topic or cannot be answered by the database.

        Database Knowledge:
        {schema_context}

        Task:
        Write a polite, helpful response that:
        1. Validates that you cannot answer the specific question.
        2. Suggests 3 relevant things they CAN ask about instead.
        3. Be concise and friendly.
        """
    
    guidance = await llm_service.generate_response(prompt)
    
    # We use 'clarification_question' field to show this as a standard chat message
    return {
        "clarification_question": guidance,
        "status": "needs_clarification" 
    }

async def format_response_node(state: GraphState) -> Dict[str, Any]:
    # Format results if needed
    return {}

# Conditional Edges

def route_after_intent(state: GraphState):
    """Route based on whether clarification is needed."""
    if state["intent"] in ["OFF_TOPIC", "SCHEMA_QUERY"]:
        return "guidance"
    if state.get("needs_clarification", False):
        return "clarification"
    if state["confidence"] < 0.5:
        return "clarification"
    return "generate_sql"

def route_after_validation(state: GraphState):
    if state["validation_error"]:
        if state.get("retry_count", 0) < 3:
            return "repair_sql"
        else:
            return "format_response"  # Or failure node
    return "execute_query"

# Graph Construction

workflow = StateGraph(GraphState)

workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("clarification", generate_clarification_node)
workflow.add_node("guidance", guidance_node)
workflow.add_node("generate_sql", generate_sql_node)
workflow.add_node("validate_sql", validate_sql_node)
workflow.add_node("repair_sql", repair_sql_node)
workflow.add_node("execute_query", execute_query_node)
workflow.add_node("recommend_visualization", recommend_visualization_node)
workflow.add_node("insight_recommendation", insight_recommendation_node)
workflow.add_node("format_response", format_response_node)

workflow.set_entry_point("classify_intent")

workflow.add_conditional_edges(
    "classify_intent",
    route_after_intent,
    {
        "generate_sql": "generate_sql",
        "clarification": "clarification",
        "guidance": "guidance"
    }
)

# Clarification ends the conversation (user must respond)
workflow.add_edge("clarification", END)
workflow.add_edge("guidance", END)

def route_after_sql_generation(state: GraphState):
    if state.get("status") == "needs_clarification":
        return "end"
    return "validate_sql"

workflow.add_conditional_edges(
    "generate_sql",
    route_after_sql_generation,
    {
        "validate_sql": "validate_sql",
        "end": END
    }
)

workflow.add_conditional_edges(
    "validate_sql",
    route_after_validation,
    {
        "execute_query": "execute_query",
        "repair_sql": "repair_sql",
        "format_response": "format_response"
    }
)

workflow.add_edge("repair_sql", "validate_sql")
workflow.add_edge("execute_query", "recommend_visualization")
workflow.add_edge("execute_query", "insight_recommendation")

# Join parallel branches
workflow.add_edge(["recommend_visualization", "insight_recommendation"], "format_response")
workflow.add_edge("format_response", END)

app_graph = workflow.compile()
