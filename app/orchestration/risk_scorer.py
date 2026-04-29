"""
Dynamic Risk Scorer - Computes data-driven 0-100 risk scores from actual query results.
Replaces static LLM-assigned severity with quantitative, factor-based scoring.
"""


class DynamicRiskScorer:

    FACTOR_WEIGHTS = {
        "affected_entities": 0.20,
        "dollar_exposure": 0.25,
        "velocity": 0.15,
        "pep_involvement": 0.15,
        "kyc_gaps": 0.10,
        "severity_escalation": 0.15,
    }

    def score(self, mission: dict, results: list) -> dict:
        if not results:
            return {"risk_score": 0, "severity": "LOW", "factors": {}}

        factors = {}
        factors["affected_entities"] = self._score_affected_entities(results)
        factors["dollar_exposure"] = self._score_dollar_exposure(results)
        factors["velocity"] = self._score_velocity(results)
        factors["pep_involvement"] = self._score_pep(results)
        factors["kyc_gaps"] = self._score_kyc(results)
        factors["severity_escalation"] = self._score_escalation(mission)

        weighted_score = sum(
            factors[k]["score"] * self.FACTOR_WEIGHTS[k] for k in self.FACTOR_WEIGHTS
        )
        risk_score = min(100, max(0, round(weighted_score)))

        return {
            "risk_score": risk_score,
            "severity": self._severity_from_score(risk_score),
            "factors": factors,
        }

    def _score_affected_entities(self, results):
        user_ids = set()
        for row in results:
            if "user_id" in row and row["user_id"]:
                user_ids.add(row["user_id"])
        count = len(user_ids) or len(results)
        score = min(100, count * 10)
        return {"value": count, "score": score, "detail": f"{count} unique entities"}

    def _score_dollar_exposure(self, results):
        total = 0
        for row in results:
            for key in ["amount_usd", "total_volume", "amount", "total_amount", "total_usd"]:
                if key in row and row[key] is not None:
                    try:
                        total += abs(float(row[key]))
                    except (ValueError, TypeError):
                        pass
        score = min(100, int(total / 1000))
        return {"value": total, "score": score, "detail": f"${total:,.0f} exposure"}

    def _score_velocity(self, results):
        count = len(results)
        score = min(100, count * 5)
        return {"value": count, "score": score, "detail": f"{count} events"}

    def _score_pep(self, results):
        pep_count = sum(
            1 for r in results if r.get("is_pep") in [True, 1, "1", "TRUE", "True", "true"]
        )
        score = min(100, pep_count * 30)
        return {"value": pep_count, "score": score, "detail": f"{pep_count} PEP accounts"}

    def _score_kyc(self, results):
        gap_count = sum(
            1 for r in results if r.get("kyc_status") in ["EXPIRED", "PENDING", "REJECTED"]
        )
        score = min(100, gap_count * 15)
        return {"value": gap_count, "score": score, "detail": f"{gap_count} KYC gaps"}

    def _score_escalation(self, mission):
        base = {"CRITICAL": 80, "HIGH": 50, "MEDIUM": 25}.get(
            mission.get("severity", "MEDIUM"), 25
        )
        return {
            "value": mission.get("severity", "MEDIUM"),
            "score": base,
            "detail": f"Base: {mission.get('severity', 'MEDIUM')}",
        }

    def _severity_from_score(self, score):
        if score >= 75:
            return "CRITICAL"
        if score >= 50:
            return "HIGH"
        if score >= 25:
            return "MEDIUM"
        return "LOW"


risk_scorer = DynamicRiskScorer()
