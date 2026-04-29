import os
from typing import List, Dict, Any
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings
from app.core.logger import logger

class DatabaseService:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        logger.info(f"DatabaseService initialized with engine: {settings.DATABASE_URL.split('///')[-1]}")
        self.initialize_db()

    def initialize_db(self):
        """Initialize database schema if it doesn't exist."""
        try:
            inspector = inspect(self.engine)
            if not inspector.has_table("users"):
                print("Initializing database schema...")
                self._execute_sql_file(settings.SCHEMA_PATH)
                print("Schema initialized.")
        except Exception as e:
            print(f"Error initializing database: {e}")

    def _execute_sql_file(self, file_path: str):
        """Execute SQL commands from a file."""
        if not os.path.exists(file_path):
            # Try to resolve relative to project root if needed
            file_path = os.path.join(os.getcwd(), file_path)
            
        if not os.path.exists(file_path):
            print(f"Schema file not found at: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
            
        # Split by semicolon for SQLite execution
        # Note: This is a simple split and might fail on complex stored procs, 
        # but works for standard CREATE TABLE/INSERT statements.
        statements = sql_content.split(';')
        
        with self.engine.connect() as conn:
            for statement in statements:
                if statement.strip():
                    try:
                        conn.execute(text(statement))
                    except Exception as e:
                        print(f"Error executing statement: {statement[:50]}... -> {e}")
            conn.commit()

    def execute(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a raw SQL query and return results as a list of dicts."""
        logger.info(f"Executing SQL: {sql}")
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                # Check if it's a SELECT query (returns rows)
                if result.returns_rows:
                    data = [dict(row) for row in result.mappings()]
                    logger.info(f"Execution complete. Returned {len(data)} rows.")
                    return data
                else:
                    conn.commit()
                    logger.info(f"Execution complete. Rows affected: {result.rowcount}")
                    return [{"status": "success", "rows_affected": result.rowcount}]
        except Exception as e:
            logger.error(f"DATABASE EXECUTION ERROR: {str(e)} | Query: {sql}")
            return []

    def get_schema_info(self) -> List[str]:
        """Returns a list of 'table.column' strings for all tables in the database."""
        schema_info = []
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            for table in tables:
                columns = inspector.get_columns(table)
                for col in columns:
                    schema_info.append(f"{table}.{col['name']}")
            return schema_info
        except Exception as e:
            logger.error(f"Error fetching schema info: {e}")
            return []

db_service = DatabaseService()
