"""
Narrative Generator - Executive Intelligence Brief.
Weaves ALL detections and correlations into a cohesive executive summary
with threat vectors, immediate actions, and monitoring recommendations.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.core.config import settings
import json


class NarrativeGenerator:

    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.DISCOVERY_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.6,
        )

    async def generate(self, detections: list, clusters: list, scan_metadata: dict) -> dict:
        det_summaries = []
        for d in detections:
            det_summaries.append(
                {
                    "mission": d.get("mission_name"),
                    "domain": d.get("domain"),
                    "severity": d.get("severity"),
                    "risk_score": d.get("risk_score", 0),
                    "data_count": d.get("data_count", 0),
                    "insight": str(d.get("insight") or "")[:300],
                    "is_sub_finding": d.get("depth", 0) > 0,
                }
            )

        prompt = ChatPromptTemplate.from_template(
            """You are the Chief Intelligence Officer preparing a real-time threat brief for the executive board.

SCAN OVERVIEW:
- Total missions executed: {total_missions}
- Domains covered: security, compliance, risk, operations
- Timestamp: {timestamp}

DETECTION SUMMARIES:
{detection_summaries}

THREAT CLUSTERS (cross-domain correlations):
{clusters}

Write a concise executive intelligence brief. Turn raw detections into actionable intelligence.

Structure:
1. ONE paragraph executive summary (3-5 sentences) — top threat vectors
2. List 2-4 identified threat vectors with severity and description
3. 3-5 immediate action items (specific, actionable, urgent-first)
4. 2-3 monitoring recommendations for ongoing vigilance

Tone: Professional, urgent but composed. Use specific numbers. Write for a CEO.

RESPONSE FORMAT (JSON only, no markdown):
{{
    "executive_summary": "Your platform currently faces...",
    "threat_vectors": [
        {{
            "name": "Threat name",
            "severity": "CRITICAL or HIGH or MEDIUM",
            "description": "1-2 sentence description"
        }}
    ],
    "immediate_actions": ["Action 1", "Action 2"],
    "monitoring_recommendations": ["Recommendation 1"]
}}"""
        )

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke(
                {
                    "total_missions": scan_metadata.get("total_missions", len(detections)),
                    "timestamp": scan_metadata.get("timestamp", "LIVE"),
                    "detection_summaries": json.dumps(det_summaries, indent=2, default=str),
                    "clusters": json.dumps(clusters, indent=2, default=str),
                }
            )

            text = response.content
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            result = json.loads(text)

            # Compute overall risk from top detection scores
            scores = [d.get("risk_score", 0) for d in detections if d.get("risk_score")]
            top_scores = sorted(scores, reverse=True)[:5]
            overall_risk = round(sum(top_scores) / max(len(top_scores), 1)) if top_scores else 0

            result["overall_risk"] = overall_risk
            result["overall_severity"] = (
                "CRITICAL" if overall_risk >= 75 else
                "HIGH" if overall_risk >= 50 else
                "MEDIUM" if overall_risk >= 25 else "LOW"
            )
            result["title"] = f"Intelligence Brief - {scan_metadata.get('timestamp', 'LIVE')}"

            return result
        except Exception as e:
            print(f"Narrative generation failed: {e}")
            return {
                "title": "Intelligence Brief",
                "overall_risk": 0,
                "overall_severity": "LOW",
                "executive_summary": "Scan completed. Review individual findings for details.",
                "threat_vectors": [],
                "immediate_actions": ["Review detection cards for specific findings"],
                "monitoring_recommendations": ["Continue scheduled scans"],
            }


narrative_generator = NarrativeGenerator()
