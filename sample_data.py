import sqlite3
import json

def get_data_samples():
    conn = sqlite3.connect('derivinsightnew.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    tables = ['users', 'transactions', 'login_events']
    samples = {}
    
    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table} LIMIT 5")
            rows = cursor.fetchall()
            samples[table] = [dict(row) for row in rows]
        except Exception as e:
            samples[table] = str(e)
            
    conn.close()
    return samples

if __name__ == "__main__":
    print(json.dumps(get_data_samples(), indent=2))
