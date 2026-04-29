"""
Quick test for the Slack notifier.
Sends a fake HIGH-severity detection to verify webhook connectivity.
"""
import asyncio
from app.services.slack_notifier import notify_slack, notify_slack_narrative
from app.core.config import settings


async def test():
    print(f"Webhook URL: {settings.SLACK_WEBHOOK_URL[:60]}...")
    print(f"Min severity: {settings.SLACK_ALERT_MIN_SEVERITY}")
    print()

    # Test 1: A HIGH severity detection (should be sent)
    fake_detection = {
        "severity": "HIGH",
        "domain": "security",
        "risk_score": 78,
        "mission_name": "TEST - Slack Integration Check",
        "data_count": 5,
        "insight": "This is a test alert to verify Slack webhook connectivity. If you see this in Slack, the integration is working.",
        "recommendation": "No action needed - this is a test.",
        "sql": "SELECT 'hello' AS test;",
    }

    print("[Test 1] Sending HIGH severity detection...")
    result = await notify_slack(fake_detection)
    print(f"  Result: {'SUCCESS' if result else 'FAILED'}")
    print()

    # Test 2: A LOW severity detection (should be skipped by severity filter)
    fake_low = {
        "severity": "LOW",
        "domain": "general",
        "risk_score": 10,
        "mission_name": "TEST - Low Severity (should be skipped)",
        "data_count": 1,
        "insight": "This should NOT be sent to Slack.",
    }

    print("[Test 2] Sending LOW severity detection (should be filtered out)...")
    result2 = await notify_slack(fake_low)
    print(f"  Result: {'SUCCESS (unexpected!)' if result2 else 'FILTERED (correct - below min severity)'}")
    print()

    # Test 3: Narrative brief
    fake_narrative = {
        "overall_risk": 72,
        "overall_severity": "HIGH",
        "executive_summary": "Test narrative: Slack integration check. No real findings.",
        "immediate_actions": ["Verify Slack channel receives this message", "Confirm formatting looks correct"],
    }

    print("[Test 3] Sending narrative brief...")
    result3 = await notify_slack_narrative(fake_narrative)
    print(f"  Result: {'SUCCESS' if result3 else 'FAILED'}")
    print()

    if not result and not result3:
        print("=" * 60)
        print("Both HIGH tests failed. Check logs/app.log for details.")
        print("Common issues:")
        print("  - 'workflow_not_published': Publish the workflow in Slack")
        print("  - 'invalid_payload': Payload format mismatch")
        print("  - Connection error: Network / URL issue")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test())
