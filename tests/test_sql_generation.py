import pytest
from unittest.mock import AsyncMock, patch
from app.modules.sql_generation import SQLGenerationModule

@pytest.mark.asyncio
async def test_generate_sql_simple():
    """Test generating a simple SQL query."""
    module = SQLGenerationModule()
    
    expected_sql = "SELECT username FROM users WHERE risk_level = 'HIGH';"
    
    # Context as required by SQLGenerationModule.generate
    context = {
        "domain": "risk",
        "entities": {"resolved_entities": {}},
        "relevant_columns": ["users.username", "users.risk_level"],
        "few_shot_examples": []
    }
    
    with patch("app.services.llm.llm_service.generate_response", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = f"```sql\n{expected_sql}\n```"
        
        with patch("app.services.database.db_service.get_schema_info") as mock_schema:
            mock_schema.return_value = ["users.user_id", "users.username", "users.risk_level"]
            
            sql = await module.generate("Show me high risk users", context=context)
            
            assert "SELECT" in sql
            assert "users" in sql
            assert "risk_level" in sql
            assert "```" not in sql

@pytest.mark.asyncio
async def test_generate_sql_error_handling():
    """Test that the module handles error responses from the LLM."""
    module = SQLGenerationModule()
    context = {"domain": "general"}
    
    with patch("app.services.llm.llm_service.generate_response", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Error: I cannot answer that."
        
        with patch("app.services.database.db_service.get_schema_info") as mock_schema:
            mock_schema.return_value = []
            
            response = await module.generate("Tell me a joke", context=context)
            assert response.startswith("Error")
