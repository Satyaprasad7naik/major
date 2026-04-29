from typing import Dict, Any
import json
from app.services.llm import llm_service

class ClarificationModule:
    """
    Generates clarifying questions when user query is ambiguous or incomplete.
    Helps refine compliance rules and complex queries.
    """
    
    async def generate_clarification(self, query: str, domain: str, conversation_history: list = None) -> str:
        """
        Generates a follow-up question to clarify the user's intent.
        Uses real schema context to ensure suggestions match the database.
        """
        from app.modules.learning import learning_service
        
        # Load real domain context
        config = learning_service.get_domain_config(domain)
        schema_context = config.get("schema_context", "")
        db_profile = config.get("db_profile", {})
        
        history_context = ""
        if conversation_history:
            history_context = "\n\nConversation so far:\n"
            for msg in conversation_history[-5:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                history_context += f"{role.upper()}: {content}\n"
        
        prompt = f"""
You are a helpful assistant helping clarify database queries in the {domain.upper()} domain.

DATABASE CONTEXT (STRICT TRUTH):
{schema_context}

Available Table Insights:
{json.dumps({t: d.get('columns') for t, d in db_profile.items()}, indent=2) if db_profile else "users, transactions, login_events"}

{history_context}

Current user query: "{query}"

The query is ambiguous, asks for something not in the database (like 'rules' or 'policies'), or wants a general discussion. 

Your Task: 
1. Acknowledge what they asked (e.g., "I see you want to discuss UAE compliance rules").
2. Explain that you are a Data Assistant with access to transaction logs, user profiles, and login events, but you do NOT have a table for regulatory text/rules.
3. BRIDGE to the data: Suggest 2-3 specific things you CAN show them from our 3 tables that are relevant to their domain.

DOMAIN-SPECIFIC DATA GUIDANCE:
- COMPLIANCE: "I can show you **flagged transactions in the UAE**, **users with pending KYC status**, or **PEP users**."
- SECURITY: "I can show you **failed login attempts**, **blocked IP addresses**, or **login frequency by country**."
- RISK: "I can show you **high-value transactions (>$10k)**, **users with an elevated risk score**, or **velocity patterns**."
- OPERATIONS: "I can show you **daily transaction volumes**, **average transaction amounts**, or **active users by device type**."

Generate a conversational, helpful response that redirects them to ask about our real data.

Return ONLY the clarifying question. Be conversational and helpful. Don't include JSON or markdown.
"""
        
        try:
            from app.core.config import settings
            response = await llm_service.generate_response(prompt, model_name=settings.CLARIFICATION_MODEL)
            return response.strip()
        except Exception as e:
            print(f"Clarification generation error: {e}")
            return "Could you please provide more details about what you're looking for?"

clarification_module = ClarificationModule()
