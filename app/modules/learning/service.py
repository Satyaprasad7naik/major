import json
import os
from typing import Dict, List, Any, Optional

class LearningService:
    """
    Independent module to manage domain-specific configurations (Prompts, Schema, Few-Shots).
    Allows 'teaching' the system new domains without code changes.
    """
    
    def __init__(self, storage_path: str = "app/data/domains"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        
    def _get_file_path(self, domain: str) -> str:
        return os.path.join(self.storage_path, f"{domain.lower()}.json")

    def get_domain_config(self, domain: str) -> Dict[str, Any]:
        """Load configuration for a specific domain."""
        file_path = self._get_file_path(domain)
        if not os.path.exists(file_path):
            return self._get_default_config(domain)
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading domain config for {domain}: {e}")
            return self._get_default_config(domain)

    def update_domain_config(self, domain: str, 
                           description: str = None,
                           schema_context: str = None,
                           intent_prompt: str = None,
                           sql_prompt: str = None,
                           few_shots: List[Dict] = None,
                           db_profile: Dict[str, Any] = None) -> bool:
        """
        Update specific fields of a domain configuration.
        """
        config = self.get_domain_config(domain)
        
        if description: config["description"] = description
        if schema_context: config["schema_context"] = schema_context
        if intent_prompt: config["prompts"]["intent"] = intent_prompt
        if sql_prompt: config["prompts"]["sql"] = sql_prompt
        if few_shots is not None: config["few_shots"] = few_shots
        if db_profile is not None: config["db_profile"] = db_profile

        return self._save_config(domain, config)

    def add_few_shot_example(self, domain: str, question: str, sql: str, explanation: str = ""):
        """Add a new training example to the domain."""
        config = self.get_domain_config(domain)
        
        new_example = {
            "question": question,
            "sql": sql,
            "explanation": explanation
        }
        
        if new_example not in config["few_shots"]:
            config["few_shots"].append(new_example)
            self._save_config(domain, config)

    async def discover_and_learn(self, domain: str):
        """
        Autonomous Discovery Agent:
        1. Scans database for actual data patterns (Values, Distributions).
        2. Generates synthetic 'User Questions' based on real data.
        3. Refines the domain configuration (Prompts, Schema Context, Few-Shots) using these insights.
        """
        from app.services.llm import llm_service
        from app.services.database import db_service
        
        print(f" Starting discovery for domain: {domain}...")
        
        try:
            tables_res = db_service.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row['name'] for row in tables_res]
            
            db_profile = {}
            for table in tables:
                cols_res = db_service.execute(f"PRAGMA table_info({table});")
                columns = [row['name'] for row in cols_res]
                table_data = {"columns": columns, "unique_values": {}}
                
                for col in columns:
                    try:
                        unique_values_res = db_service.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL LIMIT 20")
                        vals = [list(row.values())[0] for row in unique_values_res]
                        table_data["unique_values"][col] = vals
                    except Exception as e:
                        print(f"Warning: Could not get unique values for {table}.{col}: {e}")
                db_profile[table] = table_data
                
        except Exception as e:
            print(f"Profiling failed: {e}")
            return False, f"Database profiling failed: {e}"

        config = self.get_domain_config(domain)
        config["db_profile"] = db_profile
        self._save_config(domain, config)

        print(f" Profiled {len(db_profile)} tables. Generating insights...")
        
        truncated_db_profile = {}
        for table, data in db_profile.items():
            truncated_db_profile[table] = {
                "columns": data["columns"],
                "unique_values": {col: values[:5] for col, values in data["unique_values"].items()}
            }
        
        profile_str = json.dumps(truncated_db_profile, indent=2)
        
        learning_prompt = f"""
You are an expert Data Scientist and System Architect.
You are tasked with "Teaching" an NL2SQL system about a specific database domain: "{domain}".

Here is the ACTUAL DATA extracted from the database (Tables, Columns, and Unique Values for Entity Matching):
{profile_str}

Your Task:
1. Analyze the unique values to understand the "Entities".
2. Generate 5 REALISTIC user questions that someone would ask based on this data. 
3. Determine the best "Schema Context" description to help an AI understand these tables.
4. Suggest a specific "Intent Classification" prompt that highlights specific jargon found in this data.

Return JSON:
{{
  "refined_schema_context": "Detailed description...",
  "synthetic_few_shots": [
      {{"question": "Generated question", "sql": "Logical SQL", "explanation": "..."}}
  ],
  "intent_prompt_tuning": "Add this instruction to the system prompt: ..."
}}
"""
        try:
            from app.core.config import settings
            response = await llm_service.generate_response(learning_prompt, model_name=settings.DISCOVERY_MODEL)
            data = json.loads(response.replace("```json", "").replace("```", "").strip())
            
            config = self.get_domain_config(domain) 
            
            if data.get("refined_schema_context"):
                config["schema_context"] = data["refined_schema_context"]
                
            if data.get("synthetic_few_shots"):
                current_qs = [fs["question"] for fs in config["few_shots"]]
                for fs in data["synthetic_few_shots"]:
                    if fs["question"] not in current_qs:
                        config["few_shots"].append(fs)
            
            suggestion = data.get("intent_prompt_tuning")
            if suggestion:
                base_prompt = config["prompts"].get("intent") or "You are an AI assistant..."
                if suggestion not in base_prompt:
                    config["prompts"]["intent"] = base_prompt + "\n\nDOMAIN SPECIFIC INSTRUCTION:\n" + suggestion
            
            self._save_config(domain, config)
            return True, f"Discovery complete for {domain}!"
            
        except Exception as e:
            print(f"Learning failed for {domain}: {e}")
            return False, str(e)

    def _save_config(self, domain: str, config: Dict) -> bool:
        try:
            with open(self._get_file_path(domain), 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save domain config: {e}")
            return False

    def _get_default_config(self, domain: str) -> Dict[str, Any]:
        return {
            "domain": domain,
            "description": f"Configuration for {domain} domain",
            "schema_context": "Standard database tables.",
            "prompts": {"intent": None, "sql": None},
            "few_shots": [],
            "db_profile": {}
        }

learning_service = LearningService()
