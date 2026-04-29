"""
Cross-Domain Correlation Engine.
Analyzes ALL completed mission results across domains to find connected threats —
entities (user_ids, IPs, countries) appearing in multiple findings.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
import json


class CorrelationEngine:

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.DISCOVERY_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.4,
        )

    async def correlate(self, all_detections: list) -> list:
        """
        Input: All completed mission results (including sub-findings).
        Output: List of threat clusters with narratives.
        """
        entity_map = self._build_entity_map(all_detections)
        overlapping = self._find_overlaps(entity_map)

        if not overlapping:
            return []

        clusters = await self._llm_correlate(all_detections, overlapping)
        return clusters

    def _build_entity_map(self, detections: list) -> dict:
        entity_map = {}
        entity_keys = ["user_id", "country", "ip_address", "email", "email_attempted"]

        for det in detections:
            mid = det.get("mission_id", "")
            domain = det.get("domain", "")
            for row in det.get("results") or []:
                for key in entity_keys:
                    if key in row and row[key]:
                        entity_ref = f"{key}:{row[key]}"
                        if entity_ref not in entity_map:
                            entity_map[entity_ref] = []
                        entry = {"mission_id": mid, "domain": domain, "mission_name": det.get("mission_name", "")}
                        if entry not in entity_map[entity_ref]:
                            entity_map[entity_ref].append(entry)

        return entity_map

    def _find_overlaps(self, entity_map: dict) -> list:
        overlaps = []
        for entity_ref, missions in entity_map.items():
            unique_missions = set(m["mission_id"] for m in missions)
            unique_domains = set(m["domain"] for m in missions)

            if len(unique_missions) >= 2:
                overlaps.append(
                    {
                        "entity": entity_ref,
                        "domains": list(unique_domains),
                        "missions": missions,
                        "cross_domain": len(unique_domains) >= 2,
                    }
                )

        overlaps.sort(key=lambda x: (-int(x["cross_domain"]), -len(x["missions"])))
        return overlaps[:10]

    async def _llm_correlate(self, detections, overlaps) -> list:
        det_summaries = []
        for d in detections:
            det_summaries.append(
                {
                    "id": d.get("mission_id"),
                    "name": d.get("mission_name"),
                    "domain": d.get("domain"),
                    "severity": d.get("severity"),
                    "risk_score": d.get("risk_score", 0),
                    "data_count": d.get("data_count", 0),
                    "insight": str(d.get("insight") or "")[:200],
                }
            )

        prompt = ChatPromptTemplate.from_template(
            """You are a threat intelligence analyst performing cross-domain correlation.

COMPLETED MISSION SUMMARIES:
{detection_summaries}

ENTITY OVERLAPS DETECTED (entities appearing across multiple missions):
{overlaps}

Group overlapping entities into THREAT CLUSTERS — related findings that together suggest a coordinated threat.

For each cluster:
1. Name the threat pattern
2. List connected mission IDs
3. List shared entities
4. Write a brief threat narrative connecting the dots
5. Recommend immediate action

RESPONSE FORMAT (JSON array only, no markdown):
[
  {{
    "cluster_id": "TC-001",
    "threat_name": "Name of the threat pattern",
    "severity": "CRITICAL or HIGH or MEDIUM",
    "connected_missions": ["mission-id-1", "mission-id-2"],
    "shared_entities": {{"user_ids": [], "countries": [], "ip_addresses": []}},
    "narrative": "Connecting narrative...",
    "recommended_action": "Specific action..."
  }}
]

Only create clusters where there is a MEANINGFUL connection. Return empty array [] if none exist."""
        )

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "detection_summaries": json.dumps(det_summaries, indent=2, default=str),
                    "overlaps": json.dumps(overlaps, indent=2, default=str),
                }
            )

            text = response.content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return json.loads(text)
        except Exception as e:
            print(f"Correlation LLM failed: {e}")
            return []


correlation_engine = CorrelationEngine()
