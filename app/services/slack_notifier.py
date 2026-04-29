"""
Slack Notifier — sends Sentinel alerts to Slack via chat.postMessage API (Bearer token).

Setup:
1. Set SLACK_BOT_TOKEN in .env to your bot token (xoxb-...)
2. Set SLACK_CHANNEL to the target channel name (default: sentinnelanomalies)
3. Set SLACK_ALERT_MIN_SEVERITY to "HIGH" or "CRITICAL" (default: HIGH)
"""
import httpx
from app.core.config import settings
from app.core.logger import logger

SLACK_API_URL = "https://slack.com/api/chat.postMessage"

SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _should_alert(severity: str) -> bool:
    min_sev = settings.SLACK_ALERT_MIN_SEVERITY
    return SEVERITY_ORDER.get(severity, 0) >= SEVERITY_ORDER.get(min_sev, 2)


async def _post_to_slack(channel: str, text: str) -> bool:
    """
    Post a message to Slack using the chat.postMessage API with Bearer token.
    Returns True on success, False otherwise.
    """
    token = settings.SLACK_BOT_TOKEN
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — skipping Slack notification")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "channel": channel,
        "text": text,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(SLACK_API_URL, json=payload, headers=headers)
            body = resp.json()
            if resp.status_code == 200 and body.get("ok"):
                logger.info(f"Slack message sent to #{channel}")
                return True
            else:
                error = body.get("error", resp.text)
                logger.warning(f"Slack API error ({resp.status_code}): {error}")
                return False
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")
        return False


async def notify_slack(detection: dict) -> bool:
    """
    Send a single high-severity detection to Slack.
    Returns True if sent successfully, False otherwise.
    """
    severity = detection.get("severity", "MEDIUM")
    if not _should_alert(severity):
        return False

    domain = detection.get("domain", "general")
    risk_score = detection.get("risk_score", 0)
    mission_name = detection.get("mission_name", "Unknown Mission")
    data_count = detection.get("data_count", 0)

    insight = detection.get("insight", "")
    if isinstance(insight, list):
        insight = " ".join(insight)
    insight = str(insight)[:400]

    recommendation = detection.get("recommendation", "")
    if isinstance(recommendation, list):
        recommendation = recommendation[0] if recommendation else ""
    recommendation = str(recommendation)[:250]

    sql = detection.get("sql", "")

    sev_icon = {"CRITICAL": "🚨", "HIGH": "⚠️"}.get(severity, "ℹ️")
    domain_icon = {"security": "🛡️", "compliance": "📜", "risk": "📊", "operations": "⚙️"}.get(domain, "🔍")

    lines = [
        f"{sev_icon} *SENTINEL ALERT: {mission_name}*",
        "",
        f"*Severity:* {severity}  |  *Risk Score:* {risk_score}/100  |  *Domain:* {domain_icon} {domain.title()}  |  *Records:* {data_count}",
    ]

    if insight:
        lines.append(f"\n*Insight:*\n{insight}")
    if recommendation:
        lines.append(f"\n*Recommended Action:*\n{recommendation}")
    if sql:
        lines.append(f"\n*SQL:*\n```{sql}```")

    text = "\n".join(lines)
    channel = settings.SLACK_CHANNEL

    return await _post_to_slack(channel, text)


async def notify_slack_narrative(narrative: dict) -> bool:
    """
    Send the executive intelligence brief to Slack after every scan.
    Always sends regardless of severity — this is the scan summary.
    """
    overall_risk = narrative.get("overall_risk", 0)
    overall_severity = narrative.get("overall_severity", "LOW")

    summary = str(narrative.get("executive_summary", ""))[:800]
    actions = narrative.get("immediate_actions", [])
    monitoring = narrative.get("monitoring_recommendations", [])
    threat_vectors = narrative.get("threat_vectors", [])

    sev_icon = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "🔶", "LOW": "🟢"}.get(overall_severity, "ℹ️")
    risk_bar = "🟥" * (overall_risk // 20) + "⬜" * (5 - overall_risk // 20)

    lines = [
        f"{sev_icon} *SENTINEL INTELLIGENCE BRIEF*",
        "",
        f"*Overall Risk:* {risk_bar}  {overall_risk}/100  |  *Severity:* {overall_severity}",
        "",
        f"*Executive Summary:*\n{summary}",
    ]

    # Threat vectors
    if threat_vectors:
        tv_lines = []
        for tv in threat_vectors[:5]:
            tv_sev = tv.get("severity", "LOW")
            tv_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(tv_sev, "⚪")
            tv_lines.append(f"  {tv_icon} *{tv.get('name', '')}* ({tv_sev})\n      {tv.get('description', '')[:150]}")
        lines.append(f"\n*Threat Vectors:*\n" + "\n".join(tv_lines))

    # Immediate actions
    if actions:
        actions_text = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(actions[:5]))
        lines.append(f"\n*Immediate Actions:*\n{actions_text}")

    # Monitoring recommendations
    if monitoring:
        mon_text = "\n".join(f"  • {m}" for m in monitoring[:3])
        lines.append(f"\n*Monitoring:*\n{mon_text}")

    text = "\n".join(lines)
    channel = settings.SLACK_CHANNEL

    return await _post_to_slack(channel, text)
