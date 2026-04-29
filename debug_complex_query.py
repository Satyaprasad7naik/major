import asyncio
from app.orchestration.workflow import app_graph

async def test_complex_query():
    # Attempting Case 3: Analyze the impact of login failures on transaction status.
    query = "Analyze the impact of login failures on transaction status. Compare the percentage of successful transactions for users with at least one failed login vs those with none."
    initial_state = {
        "user_question": query,
        "domain": "operations",
        "conversation_history": [],
        "retry_count": 0
    }
    
    try:
        result = await app_graph.ainvoke(initial_state)
        print("RESULT STATUS:", result.get("status"))
        if result.get("status") == "success":
            print("SQL:", result.get("generated_sql"))
            print("INSIGHT:", result.get("insight"))
        else:
            print("ERROR:", result.get("validation_error"))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complex_query())
