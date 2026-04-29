import sqlite3
import json

def get_full_schema():
    conn = sqlite3.connect('derivinsightnew.db')
    cursor = conn.cursor()
    
    schema = {}
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [r[1] for r in cursor.fetchall()]
        
        # Get one row to see sample data
        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
        row = cursor.fetchone()
        sample = dict(zip(columns, row)) if row else {}
        
        schema[table] = {
            "columns": columns,
            "sample": sample
        }
    
    conn.close()
    return schema

if __name__ == "__main__":
    print(json.dumps(get_full_schema(), indent=2))
