from typing import List, Dict, Any, Optional
from app.services.llm import llm_service
import json

class VisualizationModule:
    """
    Analyzes query results and recommends the best visualization type.
    """
    
    async def recommend(self, query: str, sql: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Determines the best chart type and configuration.
        """
        if not results:
            return None
            
        # Take a sample of data to analyze (don't send huge datasets to LLM)
        sample_data = results[:3]
        columns = list(results[0].keys())
        
        prompt = f"""
You are a data visualization expert. Recommend the best chart type for the following data query.

User Query: "{query}"
SQL Query: "{sql}"
Columns: {columns}
Sample Data (first 3 rows):
{json.dumps(sample_data, indent=2)}

analyze the data and user intent. Return a JSON object with:
- "chart_type": One of ["bar", "line", "pie", "doughnut", "scatter", "table", "box"] (Use "table" if no visualization is appropriate)
- "title": A clear, descriptive title for the chart
- "x_axis_key": The column name to use for the X-axis (labels)
- "y_axis_key": The column name(s) to use for the Y-axis (values). Can be a single string or list of strings.
- "label": Label for the dataset (e.g. "Revenue", "Count")
- "description": Brief reason for choosing this chart

Rules:
- If comparing categories (e.g., count by status, sales by country), use "bar" or "pie".
- If showing trends over time (e.g., daily active users), use "line".
- If distribution of values, use "box" or "scatter".
- If the data is just a list of unrelated items or details, use "table".
- Ensure "x_axis_key" and "y_axis_key" EXACTLY match the column names in the Sample Data.

Return ONLY the JSON object.
"""
        
        try:
            response = await llm_service.generate_response(prompt)
            # Cleanup markdown
            response = response.replace("```json", "").replace("```", "").strip()
            config = json.loads(response)
            return config
        except Exception as e:
            print(f"Visualization recommendation error: {e}")
            # Fallback heuristic
            return self._heuristic_fallback(columns, results)
            
    def _heuristic_fallback(self, columns: List[str], results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simple heuristic if LLM fails"""
        # Detect numeric columns
        numeric_cols = [c for c in columns if isinstance(results[0][c], (int, float))]
        date_cols = [c for c in columns if "date" in c.lower() or "time" in c.lower() or "at" in c.lower()]
        label_cols = [c for c in columns if c not in numeric_cols]
        
        if not numeric_cols:
            return {"chart_type": "table", "title": "Data Results"}
            
        x_key = date_cols[0] if date_cols else (label_cols[0] if label_cols else columns[0])
        y_key = numeric_cols[0]
        
        chart_type = "line" if date_cols else "bar"
        
        return {
            "chart_type": chart_type,
            "title": f"{y_key} by {x_key}",
            "x_axis_key": x_key,
            "y_axis_key": y_key,
            "label": y_key,
            "description": "Auto-generated fallback chart"
        }

visualization_module = VisualizationModule()
