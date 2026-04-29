from typing import List
import json
from app.services.llm import llm_service

class TableRetriever:
    """
    LLM-based table retriever that intelligently selects relevant tables 
    based on the user's natural language query.
    """
    
    # Available tables in the database
    AVAILABLE_TABLES = {
        "users": "Stores user profiles including ID, email, full_name, country, KYC status, risk level, PEP status, and account status",
        "transactions": "Records financial activities with transaction type, instrument, amount, currency, status, payment method, and flags",
        "login_events": "Logs user login attempts including IP address, location, device information, status, and failure reasons"
    }
    
    async def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        """
        Identifies relevant tables using LLM-based analysis.
        Returns a list of table names that are most relevant to the query.
        """
        # Build the prompt for LLM
        tables_description = "\n".join([
            f"- {table}: {desc}" 
            for table, desc in self.AVAILABLE_TABLES.items()
        ])
        
        prompt = f"""You are a database expert. Given a user's natural language query, determine which database tables are needed to answer it.

Available Tables:
{tables_description}

User Query: "{query}"

Task: Analyze the query and return ONLY the table names that are needed to answer this question.
- If the query is about users, their profiles, personal info, KYC status, risk levels, or account status → include "users"
- If the query mentions money, amounts, instruments (stocks, crypto, tickers like AMZN), trades, deposits, withdrawals, or flags/reasons → include "transactions"  
- If the query is about login attempts, user activity, authentication, IP addresses, or device information → include "login_events"
- IMPORTANT: If you need to map a name to a transaction (e.g., "John's trades"), you MUST include BOTH "users" and "transactions".

Return your answer as a JSON array of table names ONLY. Examples:
- ["users"]
- ["transactions"]
- ["users", "transactions"]
- ["login_events"]

Return ONLY the JSON array, nothing else.
"""
        
        try:
            from app.core.config import settings
            response = await llm_service.generate_response(prompt, model_name=settings.RETRIEVAL_MODEL)
            # Clean up response
            response = response.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            # Parse the JSON response
            selected_tables = json.loads(response)
            
            # Validate that only valid tables are returned
            valid_tables = [
                table for table in selected_tables 
                if table in self.AVAILABLE_TABLES
            ]
            
            # If LLM returned valid tables, use them
            if valid_tables:
                return valid_tables
            
            # Fallback if no valid tables
            return self._keyword_fallback(query)
            
        except Exception as e:
            print(f"Table retrieval error: {e}")
            # Fallback to keyword-based selection
            return self._keyword_fallback(query)
    
    def _keyword_fallback(self, query: str) -> List[str]:
        """
        Simple keyword-based fallback for table selection if LLM fails.
        """
        relevant = []
        q = query.lower()
        
        # Check for user-related keywords
        if any(keyword in q for keyword in ["user", "customer", "kyc", "risk", "pep", "account", "profile"]):
            relevant.append("users")
        
        # Check for transaction-related keywords
        if any(keyword in q for keyword in ["transaction", "deposit", "withdrawal", "trade", "payment", "amount", "transfer", "instrument", "amzn", "aapl", "tsla", "gold", "amazon", "google", "bitcoin", "flag", "reason"]):
            relevant.append("transactions")
        
        # Check for login-related keywords
        if any(keyword in q for keyword in ["login", "activity", "auth", "ip", "device", "session", "access"]):
            relevant.append("login_events")
        
        # If no keywords matched, return all tables
        return relevant if relevant else list(self.AVAILABLE_TABLES.keys())
