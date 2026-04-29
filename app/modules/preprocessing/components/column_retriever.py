from typing import List
from app.services.vector_store import VectorStoreFactory
from app.services.database import db_service

class ColumnRetriever:
    def __init__(self):
        self.vector_store = VectorStoreFactory.get_store("column_descriptions")

    async def retrieve(self, query: str, top_k: int = 20) -> List[str]:
        """
        Identifies relevant columns using semantic search, 
        or returns all available columns as a robust fallback.
        """
        try:
            # 1. Try semantic search first for relevance
            results = await self.vector_store.search(query, top_k=top_k)
            if results:
                return [res["content"] for res in results]
        except Exception:
            pass

        # 2. Dynamic Fallback: Get all column names directly from the DB
        # This ensures the prompt always has the CORRECT current schema.
        db_columns = db_service.get_schema_info()
        
        if db_columns:
            return db_columns

        # 3. Static Fallback (if DB is empty/fails)
        return [
            "users.user_id", "users.username", "users.age", "users.kyc_status", "users.risk_level", "users.account_status",
            "transactions.txn_id", "transactions.user_id", "transactions.txn_type", "transactions.amount_usd", "transactions.status",
            "login_events.event_id", "login_events.user_id", "login_events.status", "login_events.country", "login_events.city"
        ]
