from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
from app.orchestration.scan_memory import scan_memory
import json

class SentinelBrainstormer:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.DISCOVERY_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.8
        )

        self.schema_context = """
        ACTUAL TABLES:
        - users (user_id, username, age, kyc_status, risk_level, risk_score, is_pep, account_status)
        - transactions (txn_id, user_id, txn_type, instrument, amount, currency, amount_usd, status, flag_reason, payment_method)
        - login_events (event_id, user_id, email_attempted, status, country, city, device_type, failure_reason)
        """

    async def brainstorm_missions(self, count_per_domain=2):
        # Get adaptive context from scan memory
        adaptive = scan_memory.get_adaptive_context()

        if settings.ADAPTIVE_ENABLED and adaptive["scan_count"] > 0:
            domain_weights = adaptive["domain_weights"]
        else:
            domain_weights = {"security": count_per_domain, "compliance": count_per_domain,
                              "risk": count_per_domain, "operations": count_per_domain}

        total_count = sum(domain_weights.values())

        prompt = ChatPromptTemplate.from_template("""
            You are the "Sentinel Brain", an autonomous security and compliance agent for a financial platform.
            Your task is to brainstorm dynamic, high-impact "Deep Audit Missions" based on the database schema.

            SCHEMA:
            {schema}

            MISSION ALLOCATION BY DOMAIN:
            - security: {sec_count} missions (threats, fraud, unusual logins, account takeovers)
            - compliance: {comp_count} missions (regulatory violations, KYC gaps, PEP monitoring, AML)
            - operations: {ops_count} missions (payment failures, system health, user performance)
            - risk: {risk_count} missions (high-risk exposure, portfolio imbalances)

            SCAN INTELLIGENCE (from {scan_count} previous scans):

            FOCUS AREAS (generate DEEPER missions on these — they were critical last scan):
            {focus_areas}

            QUERIES TO AVOID (already explored recently — generate NEW angles):
            {avoid_queries}

            GOAL:
            Generate exactly {total_count} distinct audit questions (missions).
            The questions should be sophisticated, seeking hidden patterns or critical risks.
            DIVERSIFY: Do NOT repeat previous queries. Explore new angles each scan.

            RESPONSE FORMAT:
            Provide ONLY a JSON list of objects:
            [
                {{
                    "id": "unique_string",
                    "name": "Short Mission Name",
                    "query": "The natural language question for the AI to solve",
                    "domain": "one of the domains above",
                    "severity": "CRITICAL, HIGH, or MEDIUM"
                }}
            ]
        """)

        chain = prompt | self.llm
        response = await chain.ainvoke({
            "schema": self.schema_context,
            "sec_count": domain_weights.get("security", 2),
            "comp_count": domain_weights.get("compliance", 2),
            "ops_count": domain_weights.get("operations", 2),
            "risk_count": domain_weights.get("risk", 2),
            "total_count": total_count,
            "scan_count": adaptive["scan_count"],
            "focus_areas": "\n".join(adaptive["focus_areas"]) or "No previous data. This is the first scan.",
            "avoid_queries": "\n".join(f"- {q}" for q in adaptive["avoid_queries"]) or "None — first scan."
        })

        try:
            text = response.content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return json.loads(text)
        except Exception as e:
            print(f"Failed to parse brainstormed missions: {e}")
            return []
