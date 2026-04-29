import json
from typing import Dict, Any, List
from app.services.llm import llm_service
from app.core.logger import logger

class InsightGenerationModule:
    """
    HLD Section 5: Decision Support & Action Recommendations
    Analyzes query results to provide executive-level insights and actionable recommendations.
    """
    
    async def generate(self, query: str, results: List[Dict[str, Any]], domain: str = "general") -> Dict[str, str]:
        """
        Generates insight and recommendation based on data.
        """
        logger.info(f"Generating insights for {len(results)} rows in domain: {domain}")
        if not results:
            return {
                "insight": "No data found to analyze.",
                "recommendation": "Try broadening your search criteria or checking if the data for this period is available."
            }

        # Truncate results for prompt context if too large
        sample_results = results[:20] 
        results_str = json.dumps(sample_results, indent=2)

        prompt = f"""
You are the Chief Intelligence Officer (CIO) for a major enterprise.
You have just received the results of a data query in the "{domain}" domain.

User's Question: "{query}"

Query Results (Sample of {len(sample_results)} rows out of {len(results)}):
{results_str}

Your Task:
1. **Insight**: Provide a high-level, real-time business insight from this data. What does this MEAN for the company? Connect the dots (e.g., if failures are high, mention operational risk).
2. **Recommendation**: Suggest 1-2 specific, actionable steps the executive should take based on this data. Proactive over reactive.

Format your response as a JSON object:
{{
  "insight": "Detailed business insight...",
  "recommendation": "Specific actionable steps..."
}}

Use executive language: professional, data-driven, and concise.
"""
        try:
            from app.core.config import settings
            response = await llm_service.generate_response(prompt, model_name=settings.DISCOVERY_MODEL)
            # Cleanup potential markdown
            response = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(response)
            
            return {
                "insight": data.get("insight", "Insight generated based on data metrics."),
                "recommendation": data.get("recommendation", "Continue monitoring these trends.")
            }
        except Exception as e:
            logger.error(f"Insight Generation Error: {e}")
            return {
                "insight": "Data analysis complete. Results retrieved.",
                "recommendation": "Review the returned data for specific patterns."
            }

insight_module = InsightGenerationModule()
