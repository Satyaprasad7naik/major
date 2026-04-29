from typing import List, Dict, Any
from datetime import datetime
from app.services.llm import llm_service
from app.modules.schema_understanding import schema_module
from app.core.logger import logger
from app.modules.preprocessing.assets.domain_config import (
    get_domain_prompt,
    format_few_shots_for_prompt
)

class SQLGenerationModule:
    """
    HLD 3.4: SQL Generation Module
    Leverages LLMs with schema-aware prompting to produce SQL.
    Now supports domain-specific prompts for security, compliance, risk, and operations.
    """
    
    async def generate(self, query: str, context: Dict[str, Any]) -> str:
        """
        Generates SQL based on query and context (schema, few-shot, domain, etc.)
        """
        from app.modules.learning import learning_service
        
        # Get domain from context
        domain = context.get("domain", "general")
        logger.info(f"Generating SQL for domain: {domain} | Query: {query}")
        
        # 1. Get Schema Context from Domain Adapter (via Schema Module)
        schema_str = schema_module.get_schema_string(domain=domain)
        
        # 2. Get LIVE truth from DB service to prevent hallucinations
        from app.services.database import db_service
        live_schema = db_service.get_schema_info()
        
        # Group columns by table for better LLM understanding
        schema_dict = {}
        for item in live_schema:
            t, c = item.split('.')
            if t not in schema_dict:
                schema_dict[t] = []
            schema_dict[t].append(c)
            
        live_schema_str = "ACTUAL DATABASE SCHEMA (ABSOLUTE TRUTH):\n"
        for table, cols in schema_dict.items():
            live_schema_str += f"Table: {table}\nColumns: {', '.join(cols)}\n\n"

        # 3. Get Domain Prompt (SQL Specific) from Domain Adapter
        domain_config = learning_service.get_domain_config(domain)
        custom_sql_prompt = domain_config.get("prompts", {}).get("sql")
        
        if custom_sql_prompt:
            logger.info(f"Using custom SQL prompt for domain: {domain}")
            
        domain_prompt = custom_sql_prompt or f"You are an expert SQL assistant for the {domain} domain."
        
        # Format few-shot examples
        examples = context.get("few_shot_examples", [])
        few_shot_str = format_few_shots_for_prompt(examples) if examples else ""
        
        # 3. Get Resolved Entities and Columns from context
        entities = context.get("entities", {})
        resolved_vals = entities.get("resolved_entities", {})
        entity_str = ""
        if resolved_vals:
            entity_str = "Resolved Entity Mappings (Use these EXACT values in your filters):\n"
            for col, val in resolved_vals.items():
                entity_str += f"- {col}: {val}\n"

        # Add Relevant Columns for precision
        relevant_columns = context.get("relevant_columns", [])
        columns_str = ""
        if relevant_columns:
            columns_str = "Relevant Database Columns:\n" + ", ".join(relevant_columns) + "\n"

        # Get current date for temporal context
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Format conversation history for context
        history = context.get("conversation_history", [])
        history_str = ""
        if history:
            history_str = "CONVERSATION HISTORY (Use this to understand follow-up questions):\n"
            for msg in history[-5:]: # Last 5 messages
                role = msg.get('role', 'user') if isinstance(msg, dict) else getattr(msg, 'role', 'user')
                content = msg.get('content', '') if isinstance(msg, dict) else getattr(msg, 'content', '')
                history_str += f"- {role.upper()}: {content}\n"

        prompt = f"""
{domain_prompt}

{live_schema_str}

{history_str}

{columns_str}
{entity_str}

{f"Example Queries for {domain.upper()} domain:" if few_shot_str else ""}
{few_shot_str}

Guidelines:
1. Use SQLite syntax ONLY.
2. Return ONLY the SQL query. Do not include markdown formatting (```sql ... ```) or explanations.
3. Current date/time context: Today is {current_date} ({current_datetime}). 
4. **NO HALLUCINATION**: ONLY use tables listed in 'ACTUAL DATABASE SCHEMA'. NEVER use 'payments', 'flags', or 'user_instruments'.
5. **TABLE REPLACEMENT**: If the user asks for 'payments', 'debits', 'credit' or 'transfers', ALWAYS map this to the 'transactions' table.
6. **STRICT COLUMNS**: Use 'username' for names and 'user_id' for IDs. NEVER use 'name' or 'id'.
7. Respect the schema relations. JOIN users and transactions on 'user_id'.
8. MANDATORY PARTIAL MATCHING: Whenever you query a string-based column, ALWAYS use `UPPER(column) LIKE '%VALUE%'`.
9. **DATA LIMITATION**: If the query asks for concepts not in our schema (like 'regulatory rules', 'HR policies', 'legal text'), DO NOT generate SQL. Instead, return: "Error: I don't have a table for regulatory text. However, I can show you domain-relevant data like [List 3 things from schema]. Which would you like to see?"
10. If the query CANNOT be answered with users, transactions, or login_events, return an Error message starting with "Error:".

User Request: {query}

SQL Query:
"""
        from app.core.config import settings
        response = await llm_service.generate_response(prompt, model_name=settings.SQL_MODEL)
        
        # If the LLM explicitly returns an Error/Guidance message, return it as is.
        if response.startswith("Error"):
            logger.warning(f"SQL Generation guidance response for query: {query} | Msg: {response[:50]}...")
            return response

        # Clean up response
        cleaned_sql = response.replace("```sql", "").replace("```", "").strip()
        
        # Double check if cleaned result is an Error
        if cleaned_sql.startswith("Error"):
            logger.warning(f"SQL Generation guidance response (cleaned) for query: {query}")
            return cleaned_sql
            
        logger.info(f"SQL Generated and cleaned: {cleaned_sql[:50]}...")
        return cleaned_sql

    async def repair(self, query: str, invalid_sql: str, error: str) -> str:
        """
        Repairs invalid SQL based on the error message.
        """
        prompt = f"""
You are a SQL expert. The following SQLite query generated for the request "{query}" is invalid.

Invalid SQL: {invalid_sql}
Error: {error}

Please fix the SQL query to be valid SQLite syntax.
Return ONLY the corrected SQL query. No markdown, no explanations.
"""
        
        response = await llm_service.generate_response(prompt)
        
        # Clean up response
        cleaned_sql = response.replace("```sql", "").replace("```", "").strip()
        return cleaned_sql

sql_generation_module = SQLGenerationModule()
