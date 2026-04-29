# Prompts for Preprocessing Module

ENTITY_EXTRACTION_PROMPT = """
You are an expert data analyst. Extract the following entities from the user query:
1. Date ranges (start_date, end_date)
2. Specific numerical values (amounts, quantities)
3. Named entities (locations, product names, user names)
4. Statuses or Categories (e.g., 'pending', 'shipped')

Return the output as a valid JSON object with keys: 'dates', 'numbers', 'names', 'categories'.
If an entity type is not found, return an empty list for that key.

User Query: {query}
"""

TABLE_SELECTION_PROMPT = """
Given the user query, identify the most relevant database tables from the list below.
Return a list of table names that are likely to contain the data needed to answer the query.

Available Tables:
{table_list}

User Query: {query}
"""
