import pytest
from app.orchestration.workflow import app_graph
from app.models.state import GraphState
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_full_workflow_success(test_db):
    """Test the full graph flow from question to insight."""
    
    initial_state = {
        "user_question": "What is the status of my transactions?",
        "domain": "operations",
        "conversation_history": [],
        "relevant_columns": [],
        "entities": {"resolved_entities": {}},
        "retry_count": 0
    }
    
    import app.orchestration.workflow as wf
    
    with pytest.MonkeyPatch.context() as mp:
        # Corrected variable names based on app/orchestration/workflow.py
        mp.setattr(wf.intent_module, "classify", 
                   AsyncMock(return_value=("SELECT", 1.0, "Simple", False)))
        
        mp.setattr(wf.sql_generation_module, "generate", 
                   AsyncMock(return_value="SELECT username FROM users"))
        
        mp.setattr(wf.insight_module, "generate", 
                   AsyncMock(return_value={
                       "insight": "Test Insight", 
                       "recommendation": "Test Recommendation"
                   }))
        
        mp.setattr(wf.visualization_module, "recommend", 
                   AsyncMock(return_value={
                       "chart_type": "table", "title": "Test"
                   }))
        
        # Inject our test_db
        mp.setattr(wf, "db_service", test_db)
        
        final_state = await app_graph.ainvoke(initial_state)
        
        assert final_state["status"] == "success"
        assert "query_result" in final_state
        assert final_state["insight"] == "Test Insight"
        assert final_state["recommendation"] == "Test Recommendation"

@pytest.mark.asyncio
async def test_workflow_clarification_node():
    """Test that the workflow routes to clarification when needed."""
    initial_state = {
        "user_question": "??",
        "domain": "general",
        "retry_count": 0
    }
    
    import app.orchestration.workflow as wf
    
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(wf.intent_module, "classify", 
                   AsyncMock(return_value=("SELECT", 0.3, "Simple", True)))
        
        mp.setattr(wf.clarification_module, "generate_clarification", 
                   AsyncMock(return_value="Could you please specify your request?"))

        final_state = await app_graph.ainvoke(initial_state)
        
        assert "clarification_question" in final_state
        assert final_state["clarification_question"] == "Could you please specify your request?"
        assert final_state["status"] == "needs_clarification"
