from typing import Dict, Any, Tuple, Optional
from app.services.llm import llm_service
import json

class AlertGenerationModule:
    """
    Independent system for creation and negotiation of data alerts based on SQL queries.
    Completely separated from the core NL2SQL pipeline.
    """
    
    async def process_alert_request(self, base_sql: str, user_message: str, history: list) -> Tuple[str, str, Optional[str], Optional[Dict[str, Any]]]:
        """
        Analyzes the user's request to create an alert.
        Returns: (status, message, alert_sql, alert_config)
        """
        
        # history content for context
        history_context = ""
        if history:
            history_context = "Chat History:\n" + "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-3:]])

        prompt = f"""
You are an expert Data Reliability Engineer. Your task is to generate a specific SQL query for a DATA ALERT system.

Context:
1. Base SQL (what the user was looking at): "{base_sql}"
2. {history_context}
3. User Instruction (how to alert): "{user_message}"

Your Goal:
1. Understand the alert condition (e.g., "count > 100", "any new row", "value increased").
2. Generate a valid SQL query (`alert_sql`) that returns RESULT ROWS only when the alert should fire.
   - If the user wants to alert on "count > 10", the SQL should return the count ONLY if it is > 10.
   - If user wants "any failed transaction", SQL should return those transactions.
   - If no condition implies, default to "if any text returned then alert".
3. Extract metadata (name, frequency, channel).

Requirements:
- The `alert_sql` must be derived from `base_sql` but modified to include the Alert Condition (WHERE clauses, HAVING clauses, etc.).
- Use SQLite syntax.
- If the instruction is ambiguous (e.g., "Alert me" without saying WHEN), return `status: "needs_clarification"` and ask a question.

Return JSON:
{{
  "status": "created" | "needs_clarification",
  "response_message": "Conversational confirmation or question",
  "alert_sql": "THE_MODIFIED_SQL_QUERY",
  "alert_config": {{
      "frequency": "hourly" | "daily" | "real-time",
      "channel": "email" | "slack",
      "alert_name": "Short descriptive title"
  }}
}}
"""
        try:
            response = await llm_service.generate_response(prompt)
            # Remove markdown code blocks if any
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:-3]
            elif response.startswith("```"):
                response = response[3:-3]
            
            data = json.loads(response.strip())
            
            status = data.get("status", "failed")
            message = data.get("response_message", "Processing...")
            sql = data.get("alert_sql")
            config = data.get("alert_config")
            
            return status, message, sql, config
            
        except Exception as e:
            print(f"Alert generation error: {e}")
            return "failed", f"Error: {str(e)}", None, None

alert_module = AlertGenerationModule()
