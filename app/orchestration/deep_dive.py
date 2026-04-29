"""
Deep Dive Generator - Autonomous Investigation Chains.
When a mission finds suspicious data, this generates targeted follow-up queries
using specific entity IDs from the results, like a detective following leads.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
import json


class DeepDiveGenerator:

    MAX_DEPTH = 2
    MAX_FOLLOWUPS = 2
    TRIGGER_THRESHOLD = 1

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.DISCOVERY_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.7,
        )

    async def should_deep_dive(self, mission_result: dict) -> bool:
        if mission_result.get("error"):
            return False
        results = mission_result.get("results") or []
        risk_score = mission_result.get("risk_score", 0)
        return len(results) >= self.TRIGGER_THRESHOLD and risk_score >= 40

    async def generate_followups(self, mission_result: dict, depth: int = 0) -> list:
        if depth >= self.MAX_DEPTH:
            return []

        results_sample = (mission_result.get("results") or [])[:10]

        prompt = ChatPromptTemplate.from_template(
            """You are a forensic data analyst. A security scan mission just completed with findings.

PARENT MISSION: {mission_name}
PARENT QUERY: {mission_query}
DOMAIN: {domain}
RISK SCORE: {risk_score}/100
SEVERITY: {severity}

FINDINGS (sample):
{results_json}

INSIGHT: {insight}

DATABASE SCHEMA:
- users (user_id, username, age, kyc_status, risk_level, risk_score, is_pep, account_status)
- transactions (txn_id, user_id, txn_type, instrument, amount, currency, amount_usd, status, flag_reason, payment_method)
- login_events (event_id, user_id, email_attempted, ip_address, country, city, device_type, status, failure_reason)

Generate {max_followups} targeted follow-up investigation queries that dig deeper into the specific entities found.

Rules:
- Extract SPECIFIC entity values (user_ids, countries, amounts) from the results
- Each follow-up should investigate a DIFFERENT angle of the same finding
- Think like a detective: "We found X, now let's check Y about the same actors"
- Queries must be natural language questions the NL2SQL system can answer

RESPONSE FORMAT (JSON array only, no markdown):
[
  {{
    "name": "Short investigative name",
    "query": "Natural language question with SPECIFIC entities from findings",
    "domain": "{domain}",
    "rationale": "Why this follow-up matters"
  }}
]"""
        )

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "mission_name": mission_result.get("mission_name", ""),
                    "mission_query": mission_result.get("original_query", ""),
                    "domain": mission_result.get("domain", "security"),
                    "risk_score": mission_result.get("risk_score", 0),
                    "severity": mission_result.get("severity", "MEDIUM"),
                    "results_json": json.dumps(results_sample, indent=2, default=str),
                    "insight": str(mission_result.get("insight", ""))[:500],
                    "max_followups": self.MAX_FOLLOWUPS,
                }
            )

            text = response.content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            followups = json.loads(text)
            parent_id = mission_result.get("mission_id", "unknown")

            enriched = []
            for i, f in enumerate(followups[: self.MAX_FOLLOWUPS]):
                enriched.append(
                    {
                        "id": f"dd-{parent_id}-{depth + 1}-{i}",
                        "name": f.get("name", "Follow-up Investigation"),
                        "query": f["query"],
                        "domain": f.get("domain", mission_result.get("domain")),
                        "severity": mission_result.get("severity", "HIGH"),
                        "parent_mission_id": parent_id,
                        "depth": depth + 1,
                        "rationale": f.get("rationale", ""),
                    }
                )
            return enriched

        except Exception as e:
            print(f"Deep dive generation failed: {e}")
            return []


deep_dive_generator = DeepDiveGenerator()
