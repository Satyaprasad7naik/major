from typing import List, Dict, Any
from app.services.vector_store import VectorStoreFactory
from app.modules.preprocessing.assets.domain_config import get_domain_few_shots

class FewShotRetriever:
    def __init__(self):
        # We perform on-the-fly ranking
        pass

    async def retrieve(self, query: str, domain: str = "general", top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves similar past query-SQL pairs, filtered by domain.
        Uses Jaccard Similarity to rank examples dynamically.
        """
        from app.modules.learning import learning_service
        
        # 1. Get all examples for the domain
        config = learning_service.get_domain_config(domain)
        all_examples = config.get("few_shots", [])
        
        if not all_examples:
            return []
            
        # 2. Tokenize user query
        user_tokens = set(query.lower().split())
        
        # 3. Score examples
        scored_examples = []
        for ex in all_examples:
            ex_q = ex.get("question", "")
            ex_tokens = set(ex_q.lower().split())
            
            # Calculate Jaccard Similarity
            intersection = len(user_tokens.intersection(ex_tokens))
            union = len(user_tokens.union(ex_tokens))
            score = intersection / union if union > 0 else 0
            
            scored_examples.append((score, ex))
            
        # 4. Sort by score (descending)
        scored_examples.sort(key=lambda x: x[0], reverse=True)
        
        # 5. Return top_k
        top_examples = [ex for score, ex in scored_examples[:top_k]]
        
        return top_examples
