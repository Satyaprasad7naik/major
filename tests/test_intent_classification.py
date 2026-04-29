import pytest
from unittest.mock import AsyncMock, patch
from app.modules.intent_classification import IntentClassificationModule

@pytest.mark.asyncio
async def test_classify_intent_success():
    """Test that intent is correctly classified for a standard query."""
    module = IntentClassificationModule()
    
    # Mock LLM response JSON
    mock_json = {
        "intent": "SELECT",
        "confidence": 0.95,
        "complexity": "Simple",
        "needs_clarification": False,
        "clarity_score": 0.9
    }
    
    import json
    with patch("app.services.llm.llm_service.generate_response", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = json.dumps(mock_json)
        
        # classify returns a tuple (intent, confidence, complexity, needs_clarification)
        intent, conf, comp, clarifies = await module.classify("What is the transaction volume?", domain="operations")
        
        assert intent == "SELECT"
        assert conf == 0.95
        assert comp == "Simple"
        assert clarifies is False

@pytest.mark.asyncio
async def test_classify_intent_clarification():
    """Test that ambiguous queries trigger clarification."""
    module = IntentClassificationModule()
    
    mock_json = {
        "intent": "SELECT",
        "confidence": 0.4,
        "complexity": "Simple",
        "needs_clarification": True,
        "clarity_score": 0.3
    }
    
    import json
    with patch("app.services.llm.llm_service.generate_response", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = json.dumps(mock_json)
        
        intent, conf, comp, clarifies = await module.classify("Show me data", domain="general")
        
        assert clarifies is True
