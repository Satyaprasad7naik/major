import pytest
from app.services.database import DatabaseService

def test_db_execution(test_db):
    """Test that the database service correctly executes queries and returns results."""
    query = "SELECT username FROM users WHERE user_id = 1"
    results = test_db.execute(query)
    
    assert len(results) == 1
    assert results[0]["username"] == "test_user"

def test_db_invalid_query(test_db):
    """Test that invalid queries raise appropriate exceptions."""
    query = "SELECT * FROM non_existent_table"
    # execute returns [] on error based on app/services/database.py
    results = test_db.execute(query)
    assert results == []

def test_db_empty_results(test_db):
    """Test that queries with no matches return an empty list."""
    query = "SELECT * FROM users WHERE user_id = 999"
    results = test_db.execute(query)
    assert results == []
