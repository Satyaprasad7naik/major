from typing import List, Dict, Any
from app.modules.learning import learning_service

# The core tables we want to focus on
ALLOWED_TABLES = ['users', 'login_events', 'transactions']

class TableFocusedSchemaModule:
    """
    HLD 3.1 (Filtered): Schema Understanding Module
    Dynamically restricts the database schema focus to: 
    - users
    - login_events
    - transactions
    """
    
    def get_schema_string(self, relevant_columns: List[str] = None, domain: str = "general") -> str:
        """
        Generate schema representations restricted to the allowed core tables.
        This provides a cleaner context for the LLM.
        """
        # Load the full learned configuration
        config = learning_service.get_domain_config(domain)
        
        db_profile = config.get("db_profile", {})
        
        # Filter profile to only include allowed tables
        filtered_profile = {
            table: info for table, info in db_profile.items()
            if table in ALLOWED_TABLES
        }
        
        if not filtered_profile:
            # Fallback if profile is empty or doesn't have the tables yet
            return "Focused Schema: users (user_id, email, kyc_status, risk_level), login_events (id, user_id, status, ip_address), transactions (txn_id, user_id, amount_usd, status)."

        # Construct a clean schema string for the prompt
        schema_blocks = []
        for table, details in filtered_profile.items():
            cols = ", ".join(details.get("columns", []))
            schema_blocks.append(f"Table: {table}\nColumns: {cols}")
            
        return "DATABASE FOCUS (Restricted to Core Tables):\n\n" + "\n\n".join(schema_blocks)

# Create an instance that can be used as a drop-in replacement
focused_schema_module = TableFocusedSchemaModule()
