# Domain-specific prompts and few-shot examples for DerivInsight NL2SQL
# Each domain has tailored system prompts, context, and example queries

from typing import Dict, List, Any

# ============================================================
# DOMAIN-SPECIFIC SYSTEM PROMPTS
# ============================================================

DOMAIN_PROMPTS: Dict[str, str] = {
    "security": """
You are a Security Intelligence Analyst for the DerivInsight platform.
Your focus is on detecting threats, unauthorized access, and suspicious activities.

Key areas of concern:
- Login anomalies (failed attempts, unusual locations, new devices)
- IP-based threats (multiple accounts from same IP, blocked IPs)
- Account takeover patterns
- Device fingerprint analysis
- Geographic anomalies in authentication

Use tables: login_events, users
Prioritize: created_at timestamps, ip_address, device_type, status='BLOCKED' or 'FAILED'
""",

    "compliance": """
You are a Compliance Officer for the DerivInsight platform.
Your focus is on regulatory requirements, KYC/AML, and policy adherence.

Key areas of concern:
- KYC status verification (PENDING, VERIFIED, REJECTED, EXPIRED)
- PEP (Politically Exposed Person) monitoring
- Document expiry tracking
- Regulatory reporting requirements
- Transaction monitoring for compliance

Use tables: users, transactions
Prioritize: kyc_status, kyc_expiry_date, is_pep, account_status
""",

    "risk": """
You are a Risk Management Analyst for the DerivInsight platform.
Your focus is on financial risk assessment, fraud detection, and exposure management.

Key areas of concern:
- High-value transactions (>$50,000)
- Transaction velocity patterns (rapid trades)
- Structuring detection (multiple transactions just below thresholds)
- High-risk user profiles
- Country-based risk (FATF high-risk jurisdictions)

Use tables: transactions, users
Prioritize: amount_usd, risk_level, risk_score, status='FLAGGED'
""",

    "operations": """
You are an Operations Manager for the DerivInsight platform.
Your focus is on business metrics, system health, and operational efficiency.

Key areas of concern:
- Daily transaction volumes and trends
- User growth and activity patterns
- Login activity and authentication metrics
- Business performance tracking

Use tables: transactions, users, login_events
Prioritize: DATE() aggregations, COUNT(), SUM(), trends over time
""",

    "general": """
You are a SQL expert for the DerivInsight platform.
Generate accurate SQLite queries for any natural language request.

Available data domains:
- Users: KYC status, risk levels, account information
- Transactions: Trades, deposits, withdrawals, payment methods
- Login Events: Authentication attempts, device info, geo-location
"""
}

# ============================================================
# DOMAIN-SPECIFIC FEW-SHOT EXAMPLES
# ============================================================

DOMAIN_FEW_SHOTS: Dict[str, List[Dict[str, str]]] = {
    "security": [
        {
            "question": "Show failed login attempts in the last 24 hours grouped by country",
            "sql": "SELECT country, COUNT(*) as failed_count FROM login_events WHERE status = 'FAILED' AND created_at > datetime('now', '-24 hours') GROUP BY country ORDER BY failed_count DESC;"
        },
        {
            "question": "Find IPs with more than 3 failed login attempts",
            "sql": "SELECT ip_address, COUNT(*) as attempts FROM login_events WHERE status = 'FAILED' GROUP BY ip_address HAVING attempts > 3 ORDER BY attempts DESC;"
        },
        {
            "question": "List blocked login events with user details",
            "sql": "SELECT le.*, u.full_name, u.risk_level FROM login_events le LEFT JOIN users u ON le.user_id = u.user_id WHERE le.status = 'BLOCKED' ORDER BY le.created_at DESC;"
        },
        {
            "question": "Identify suspicious IPs used by multiple accounts",
            "sql": "SELECT ip_address, COUNT(DISTINCT user_id) as unique_users FROM login_events WHERE user_id IS NOT NULL GROUP BY ip_address HAVING unique_users > 1 ORDER BY unique_users DESC;"
        }
    ],

    "compliance": [
        {
            "question": "Show users with pending KYC verification",
            "sql": "SELECT user_id, full_name, email, country, created_at FROM users WHERE kyc_status = 'PENDING' ORDER BY created_at;"
        },
        {
            "question": "Find high-risk users who are not KYC verified",
            "sql": "SELECT * FROM users WHERE risk_level = 'HIGH' AND kyc_status != 'VERIFIED';"
        },
        {
            "question": "List PEP users with their transaction history",
            "sql": "SELECT u.user_id, u.full_name, u.country, COUNT(t.txn_id) as txn_count, SUM(t.amount_usd) as total_volume FROM users u LEFT JOIN transactions t ON u.user_id = t.user_id WHERE u.is_pep = 1 GROUP BY u.user_id;"
        },
        {
            "question": "Show users with expiring KYC in the next 30 days",
            "sql": "SELECT user_id, full_name, email, kyc_expiry_date FROM users WHERE kyc_expiry_date BETWEEN date('now') AND date('now', '+30 days') ORDER BY kyc_expiry_date;"
        }
    ],

    "risk": [
        {
            "question": "Show flagged transactions over $50,000",
            "sql": "SELECT t.*, u.full_name, u.risk_level FROM transactions t JOIN users u ON t.user_id = u.user_id WHERE t.status = 'FLAGGED' AND t.amount_usd > 50000 ORDER BY t.amount_usd DESC;"
        },
        {
            "question": "Find users with the highest risk scores",
            "sql": "SELECT user_id, full_name, country, risk_level, risk_score FROM users WHERE risk_level = 'HIGH' ORDER BY risk_score DESC LIMIT 20;"
        },
        {
            "question": "Detect potential structuring (multiple transactions just below $10,000)",
            "sql": "SELECT user_id, COUNT(*) as txn_count, SUM(amount_usd) as total FROM transactions WHERE amount_usd BETWEEN 9000 AND 10000 AND created_at > datetime('now', '-24 hours') GROUP BY user_id HAVING txn_count >= 3;"
        },
        {
            "question": "Show high-risk users with recent large transactions",
            "sql": "SELECT u.user_id, u.full_name, u.risk_level, t.amount_usd, t.created_at FROM users u JOIN transactions t ON u.user_id = t.user_id WHERE u.risk_level = 'HIGH' AND t.amount_usd > 50000 ORDER BY t.created_at DESC;"
        }
    ],

    "operations": [
        {
            "question": "Show daily transaction volume for the last 30 days",
            "sql": "SELECT DATE(created_at) as date, COUNT(*) as txn_count, SUM(amount_usd) as total_volume FROM transactions WHERE created_at > datetime('now', '-30 days') GROUP BY DATE(created_at) ORDER BY date DESC;"
        },
        {
            "question": "Top 10 users by transaction volume",
            "sql": "SELECT u.user_id, u.full_name, SUM(t.amount_usd) as total_volume, COUNT(*) as txn_count FROM users u JOIN transactions t ON u.user_id = t.user_id GROUP BY u.user_id ORDER BY total_volume DESC LIMIT 10;"
        },
        {
            "question": "Count users by country",
            "sql": "SELECT country, COUNT(*) as user_count FROM users GROUP BY country ORDER BY user_count DESC;"
        },
        {
            "question": "Show daily active users based on login events",
            "sql": "SELECT DATE(created_at) as date, COUNT(DISTINCT user_id) as active_users FROM login_events WHERE status = 'SUCCESS' AND created_at > datetime('now', '-30 days') GROUP BY DATE(created_at) ORDER BY date DESC;"
        }
    ],

    "general": [
        {
            "question": "Show me all high risk users from the UAE",
            "sql": "SELECT * FROM users WHERE risk_level = 'HIGH' AND country = 'AE';"
        },
        {
            "question": "Count the number of flagged transactions over $50,000",
            "sql": "SELECT COUNT(*) FROM transactions WHERE status = 'FLAGGED' AND amount_usd > 50000;"
        },
        {
            "question": "List failed login attempts in the last 24 hours",
            "sql": "SELECT * FROM login_events WHERE status = 'FAILED' AND created_at > datetime('now', '-24 hours');"
        },
        {
            "question": "Who are the users with pending KYC?",
            "sql": "SELECT user_id, full_name, email FROM users WHERE kyc_status = 'PENDING';"
        }
    ]
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_domain_prompt(domain: str) -> str:
    """Get the system prompt for a specific domain."""
    return DOMAIN_PROMPTS.get(domain, DOMAIN_PROMPTS["general"])

def get_domain_few_shots(domain: str) -> List[Dict[str, str]]:
    """Get the few-shot examples for a specific domain."""
    return DOMAIN_FEW_SHOTS.get(domain, DOMAIN_FEW_SHOTS["general"])

def format_few_shots_for_prompt(examples: List[Dict[str, str]]) -> str:
    """Format few-shot examples into a string for the prompt."""
    formatted = []
    for i, ex in enumerate(examples, 1):
        formatted.append(f"Example {i}:")
        formatted.append(f"Question: {ex['question']}")
        formatted.append(f"SQL: {ex['sql']}")
        formatted.append("")
    return "\n".join(formatted)
