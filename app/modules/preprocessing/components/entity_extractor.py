from typing import Dict, Any, List
import json
import asyncio
import difflib
from app.services.llm import llm_service
from app.core.logger import logger

class EntityExtractor:
    """
    Handles extraction and normalization of entities (dates, names, categories).
    Uses Domain Context to resolve values to actual database entries.
    """
    def __init__(self):
        self.MATCH_THRESHOLD = 0.6  # difflib ratio (0 to 1)

    async def extract(self, query: str, domain: str = "general") -> Dict[str, Any]:
        """
        Extracts entities and resolves them against database values using LLM reasoning 
        informed by the domain schema context.
        """
        from app.modules.learning import learning_service
        
        # 1. Get learned domain knowledge (contains unique values and schema context)
        config = learning_service.get_domain_config(domain)
        schema_context = config.get("schema_context", "")
        db_profile = config.get("db_profile", {})
        
        unique_values_map = {
            table: {col: values for col, values in col_data.get("unique_values", {}).items()}
            for table, col_data in db_profile.items()
        }

        # 2. Build a prompt that asks the LLM to extract AND resolve
        unique_values_str = ""
        for table, cols in unique_values_map.items():
            for col, vals in cols.items():
                if vals:
                    unique_values_str += f"- {table}.{col}: {', '.join(str(v) for v in vals[:30])}\n"

        prompt = f"""
You are a Precise Entity Extractor and Resolver.
Your goal is to extract filters from the user query and map them to ACTUAL database values.

Database Schema Context:
{schema_context}

Available Database Values (Use these for resolution):
{unique_values_str}

User Query: "{query}"

Task:
1. Extract filtering entities (Names, Categories, Statuses, Dates, Numbers).
2. RESOLVE them to the exact values found in the "Available Database Values".
   - Use your knowledge to map synonyms or abbreviations (e.g., 'Amazon' -> 'AMZN', 'Gold' -> 'XAU', 'failed' -> 'FAILED').
   - If user says "verified", and the data shows 'VERIFIED', resolve it to 'VERIFIED'.
   - If user says "Germany", and data shows 'DE', resolve it to 'DE'.
3. Output the result in JSON format.

Output JSON Format:
{{
  "resolved_entities": {{
    "table_name.column_name": "actual_db_value"
  }},
  "metadata": {{
    "dates": [],
    "numbers": []
  }}
}}

IMPORTANT: 
- Try to return keys as "table_name.column_name" if you can identify the table.
- Resolve user terms like 'Amazon' to 'AMZN' if it appears in the values.

Return ONLY the JSON.
"""
        try:
            from app.core.config import settings
            response = await llm_service.generate_response(prompt, model_name=settings.EXTRACTION_MODEL)
            # Cleanup
            response = response.strip()
            if response.startswith("```json"):
                response = response.replace("```json", "").replace("```", "").strip()
            elif response.startswith("```"):
                response = response.replace("```", "").strip()
            
            # SAFE PARSING: If not JSON, return empty
            if not (response.startswith("{") and response.endswith("}")):
                logger.warning(f"EntityExtractor: LLM returned non-JSON response: {response[:100]}")
                return {"resolved_entities": {}, "metadata": {}}

            data = json.loads(response)
            
            # Post-processing: Validate and match extracted entities
            resolved_entities = data.get("resolved_entities", {})
            if not isinstance(resolved_entities, dict):
                resolved_entities = {}
                
            validated_entities = {}

            for col_name, extracted_value in resolved_entities.items():
                table_name_parts = col_name.split('.')
                extracted_table = table_name_parts[0] if len(table_name_parts) > 1 else None
                simple_col_name = table_name_parts[-1]
                
                matched_value = None
                
                # Search targets
                search_targets = []
                if extracted_table and extracted_table in unique_values_map:
                    if simple_col_name in unique_values_map[extracted_table]:
                        search_targets.append(unique_values_map[extracted_table][simple_col_name])
                else:
                    for t_name, cols in unique_values_map.items():
                        if simple_col_name in cols:
                            search_targets.append(cols[simple_col_name])
                
                if search_targets:
                    possible_values = [str(v) for target_list in search_targets for v in target_list if v is not None]
                    
                    # 1. Exact case-insensitive match
                    ext_val_lower = str(extracted_value).lower()
                    for pv in possible_values:
                        if pv.lower() == ext_val_lower:
                            matched_value = pv
                            break
                    
                    # 2. Difflib matching
                    if matched_value is None:
                        matches = difflib.get_close_matches(ext_val_lower, [v.lower() for v in possible_values], n=1, cutoff=self.MATCH_THRESHOLD)
                        if matches:
                            # Map back to original casing
                            for pv in possible_values:
                                if pv.lower() == matches[0]:
                                    matched_value = pv
                                    break
                
                if matched_value:
                    validated_entities[col_name] = matched_value
                else:
                    validated_entities[col_name] = extracted_value

            data["resolved_entities"] = validated_entities
            logger.info(f"Final Extracted/Resolved Entities: {data.get('resolved_entities')}")
            
            return data
            
        except Exception as e:
            logger.error(f"Entity Extraction Error: {e}")
            return {"resolved_entities": {}, "metadata": {}}
