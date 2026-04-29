import pytest
import redis
from unittest.mock import MagicMock, patch
from app.services.worker_registry import WorkerRegistry
from app.services.llm import LLMService

def test_worker_registry_init_failure():
    """Test that WorkerRegistry handles redis connection failure gracefully."""
    with patch("redis.from_url") as mock_redis:
        mock_redis.side_effect = redis.ConnectionError("Connection failed")
        registry = WorkerRegistry(redis_url="redis://invalid:6379")
        assert registry.is_available() is False
        assert registry.redis is None

def test_worker_registry_set_get():
    """Test setting and getting task ARNs in WorkerRegistry."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = "arn:aws:ecs:task/123"
    
    with patch("redis.from_url", return_value=mock_client):
        registry = WorkerRegistry(redis_url="redis://localhost:6379")
        registry._available = True # Force available for mock
        
        # Test Set
        assert registry.set_engine_task_arn("arn:aws:ecs:task/123") is True
        mock_client.set.assert_called_with("alerts:engine:task_arn", "arn:aws:ecs:task/123")
        
        # Test Get
        assert registry.get_engine_task_arn() == "arn:aws:ecs:task/123"
        mock_client.get.assert_called_with("alerts:engine:task_arn")
        
        # Test Delete
        assert registry.delete_engine_task_arn() is True
        mock_client.delete.assert_called_with("alerts:engine:task_arn")

@pytest.mark.asyncio
async def test_llm_service_retry_logic():
    """Test that LLMService retries on 429 errors."""
    from app.services.llm import LLMService
    
    with patch("app.services.llm.genai.GenerativeModel") as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # First call fails with 429, second succeeds
        mock_model.generate_content.side_effect = [
            Exception("429 Resource exhausted"),
            MagicMock(text="Success response", candidates=[MagicMock(finish_reason=1)])
        ]
        
        # Patch sleep to avoid waiting
        with patch("time.sleep"):
            service = LLMService()
            service.provider = "gemini"
            service.model = mock_model
            
            response = await service.generate_response("Hello")
            assert response == "Success response"
            assert mock_model.generate_content.call_count == 2

@pytest.mark.asyncio
async def test_llm_service_safety_block():
    """Test that LLMService handles safety blocks correctly."""
    with patch("app.services.llm.genai.GenerativeModel") as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Mock a safety block response
        mock_candidate = MagicMock()
        mock_candidate.finish_reason = 3 # SAFETY
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        
        mock_model.generate_content.return_value = mock_response
        
        service = LLMService()
        service.provider = "gemini"
        service.model = mock_model
        
        response = await service.generate_response("Harmful prompt")
        assert "blocked by safety filters" in response

def test_event_generator_insertion(alert_engine):
    """Test that EventGenerator writes correctly to AlertEngine."""
    from app.services.alert_events_generate import EventGenerator
    from app.services.alert_engine import AlertEngineService
    
    # We patch generator's engine_service to use our test alert_engine fixture
    with patch("app.services.alert_events_generate.AlertEngineService", return_value=alert_engine):
        gen = EventGenerator()
        event_id = gen.write_event("test_type", {"test": "data"})
        
        events = alert_engine.fetch_new_events(0)
        assert len(events) >= 1
        assert events[-1]["table_name"] == "test_type"

def test_task_orchestrator_config_check():
    """Test task orchestrator configuration detection."""
    from app.services.task_orchestrator import _ecs_configured
    from app.core.config import settings
    
    with patch("app.services.task_orchestrator._BOTO_AVAILABLE", True):
        with patch.object(settings, "ECS_CLUSTER", "my-cluster"):
            with patch.object(settings, "ECS_SUBNETS", "s-1,s-2"):
                with patch.object(settings, "ECS_TASK_DEFINITION", "task-def"):
                    assert _ecs_configured() is True
                
                with patch.object(settings, "ECS_TASK_DEFINITION", None):
                    with patch.object(settings, "ECS_ENGINE_TASK_DEFINITION", None):
                        assert _ecs_configured() is False

def test_start_engine_task_boto_call():
    """Test that start_engine_task makes correct boto3 calls."""
    import sys
    mock_boto = MagicMock()
    mock_client = MagicMock()
    mock_boto.client.return_value = mock_client
    mock_client.run_task.return_value = {"tasks": [{"taskArn": "arn:123"}]}
    
    with patch.dict(sys.modules, {"boto3": mock_boto}):
        from app.services.task_orchestrator import start_engine_task
        with patch("app.services.task_orchestrator._BOTO_AVAILABLE", True):
            with patch("app.services.task_orchestrator.boto3", mock_boto):
                with patch("app.services.task_orchestrator._ecs_configured", return_value=True):
                    arn, err = start_engine_task()
                    assert arn == "arn:123"
                    assert err is None
                    mock_boto.client.assert_called_with("ecs")
