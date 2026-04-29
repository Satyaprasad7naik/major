"""
DerivInsight - Mock Data Generator
Deriv Hackathon 2026

Generates realistic synthetic data for all tables.
Run: python generate_mock_data.py

Output: derivinsight_mock_data.sql (INSERT statements)
"""

import random
import uuid
from datetime import datetime, timedelta
import json

# ============================================================
# CONFIGURATION
# ============================================================

NUM_USERS = 500
NUM_TRANSACTIONS = 50000
NUM_LOGIN_EVENTS = 20000
NUM_ALERTS = 200
NUM_AUDIT_LOGS = 10000

# Date range: last 6 months
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=180)

# ============================================================
# REFERENCE DATA
# ============================================================

# Country distribution (weighted towards UAE)
COUNTRIES = {
    'AE': 25,  # UAE - Primary market
    'GB': 15,  # United Kingdom
    'US': 12,  # United States
    'DE': 8,   # Germany
    'SG': 8,   # Singapore
    'IN': 7,   # India
    'FR': 5,   # France
    'HK': 5,   # Hong Kong
    'AU': 5,   # Australia
    'JP': 4,   # Japan
    'CA': 2,   # Canada
    'CH': 2,   # Switzerland
    'NL': 1,   # Netherlands
    'SE': 1,   # Sweden
    'NO': 0,   # Norway (remainder)
}

# FATF High-risk countries (for alerts)
HIGH_RISK_COUNTRIES = ['AF', 'IR', 'KP', 'SY', 'YE', 'MM', 'PK']

FIRST_NAMES = [
    'Ahmed', 'Mohammed', 'Fatima', 'Aisha', 'Omar', 'Khalid', 'Sara', 'Layla',
    'James', 'Emma', 'Oliver', 'Sophia', 'William', 'Isabella', 'Benjamin', 'Mia',
    'Hans', 'Anna', 'Felix', 'Marie', 'Pierre', 'Claire', 'Jean', 'Sophie',
    'Raj', 'Priya', 'Arjun', 'Ananya', 'Wei', 'Mei', 'Yuki', 'Hana',
    'Michael', 'Jennifer', 'David', 'Sarah', 'Robert', 'Emily', 'John', 'Lisa'
]

LAST_NAMES = [
    'Al-Rashid', 'Khan', 'Ahmed', 'Hassan', 'Ali', 'Ibrahim', 'Abdullah', 'Mahmoud',
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Miller', 'Davis', 'Wilson',
    'Mueller', 'Schmidt', 'Weber', 'Fischer', 'Martin', 'Bernard', 'Dubois', 'Laurent',
    'Sharma', 'Patel', 'Singh', 'Kumar', 'Wang', 'Li', 'Zhang', 'Chen',
    'Tanaka', 'Yamamoto', 'Suzuki', 'Nakamura', 'Thompson', 'Anderson', 'Taylor', 'Lee'
]

INSTRUMENTS = ['EUR/USD', 'GBP/USD', 'BTC/USD', 'ETH/USD', 'GOLD', 'OIL', 'AAPL', 'TSLA', 'AED/USD', 'USD/JPY']
TXN_TYPES = ['DEPOSIT', 'WITHDRAWAL', 'TRADE', 'FEE', 'BONUS']
TXN_TYPE_WEIGHTS = [20, 15, 55, 8, 2]  # Trade-heavy distribution

PAYMENT_METHODS = ['CARD', 'BANK_TRANSFER', 'CRYPTO', 'EWALLET']
DEVICE_TYPES = ['MOBILE', 'DESKTOP', 'TABLET']
DEVICE_WEIGHTS = [45, 45, 10]

ALERT_RULES = [
    ('Large Transaction', 'HIGH'),
    ('Velocity Alert', 'MEDIUM'),
    ('Off-Hours Activity', 'LOW'),
    ('New Geo Login', 'MEDIUM'),
    ('Failed Auth Spike', 'HIGH'),
    ('Withdrawal Pattern', 'HIGH'),
    ('Structuring Detection', 'CRITICAL'),
    ('Dormant Account Activity', 'MEDIUM'),
    ('High Risk Country', 'HIGH'),
    ('Rapid Fund Movement', 'HIGH'),
]

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def generate_uuid(prefix=''):
    """Generate a prefixed UUID"""
    uid = str(uuid.uuid4())[:8].upper()
    return f"{prefix}{uid}" if prefix else uid

def weighted_choice(choices, weights):
    """Select from choices based on weights"""
    total = sum(weights)
    r = random.uniform(0, total)
    cumulative = 0
    for choice, weight in zip(choices, weights):
        cumulative += weight
        if r <= cumulative:
            return choice
    return choices[-1]

def random_date(start, end):
    """Generate random datetime between start and end"""
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86400)
    return start + timedelta(days=random_days, seconds=random_seconds)

def random_ip():
    """Generate random IP address"""
    return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def escape_sql(value):
    """Escape single quotes for SQL"""
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (int, float)):
        return str(value)
    return f"'{str(value).replace(chr(39), chr(39)+chr(39))}'"

def format_timestamp(dt):
    """Format datetime for SQL"""
    return dt.strftime('%Y-%m-%d %H:%M:%S')

# ============================================================
# DATA GENERATORS
# ============================================================

def generate_users():
    """Generate user records"""
    users = []
    country_list = []
    for country, weight in COUNTRIES.items():
        country_list.extend([country] * weight)
    
    for i in range(NUM_USERS):
        user_id = f"USR-{str(i+1).zfill(4)}"
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1,999)}@example.com"
        country = random.choice(country_list)
        
        # KYC status distribution
        kyc_rand = random.random()
        if kyc_rand < 0.75:
            kyc_status = 'VERIFIED'
        elif kyc_rand < 0.93:
            kyc_status = 'PENDING'
        elif kyc_rand < 0.98:
            kyc_status = 'REJECTED'
        else:
            kyc_status = 'EXPIRED'
        
        # Risk level distribution
        risk_rand = random.random()
        if risk_rand < 0.60:
            risk_level = 'LOW'
            risk_score = random.randint(0, 30)
        elif risk_rand < 0.90:
            risk_level = 'MEDIUM'
            risk_score = random.randint(31, 60)
        else:
            risk_level = 'HIGH'
            risk_score = random.randint(61, 100)
        
        # High-risk country users are automatically HIGH risk
        if country in HIGH_RISK_COUNTRIES:
            risk_level = 'HIGH'
            risk_score = random.randint(70, 100)
        
        created_at = random_date(START_DATE, END_DATE - timedelta(days=30))
        kyc_verified_at = created_at + timedelta(days=random.randint(1, 7)) if kyc_status == 'VERIFIED' else None
        
        is_pep = random.random() < 0.02  # 2% PEP
        
        users.append({
            'user_id': user_id,
            'email': email,
            'full_name': full_name,
            'country': country,
            'phone': f"+{random.randint(1,99)}{random.randint(1000000000, 9999999999)}",
            'date_of_birth': (datetime.now() - timedelta(days=random.randint(18*365, 70*365))).strftime('%Y-%m-%d'),
            'kyc_status': kyc_status,
            'kyc_verified_at': format_timestamp(kyc_verified_at) if kyc_verified_at else None,
            'kyc_expiry_date': (kyc_verified_at + timedelta(days=365*3)).strftime('%Y-%m-%d') if kyc_verified_at else None,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'is_pep': is_pep,
            'account_status': 'ACTIVE' if random.random() < 0.95 else random.choice(['SUSPENDED', 'FROZEN']),
            'created_at': format_timestamp(created_at),
            'updated_at': format_timestamp(created_at + timedelta(days=random.randint(0, 30)))
        })
    
    return users

def generate_transactions(users):
    """Generate transaction records"""
    transactions = []
    user_ids = [u['user_id'] for u in users]
    
    for i in range(NUM_TRANSACTIONS):
        txn_id = f"TXN-{str(i+1).zfill(6)}"
        user_id = random.choice(user_ids)
        txn_type = weighted_choice(TXN_TYPES, TXN_TYPE_WEIGHTS)
        
        # Amount distribution
        amount_rand = random.random()
        if amount_rand < 0.70:
            amount = round(random.uniform(100, 5000), 2)
        elif amount_rand < 0.90:
            amount = round(random.uniform(5000, 25000), 2)
        elif amount_rand < 0.98:
            amount = round(random.uniform(25000, 50000), 2)
        else:
            amount = round(random.uniform(50000, 150000), 2)  # Flaggable
        
        # Status distribution
        if amount > 50000 and random.random() < 0.6:
            status = 'FLAGGED'
            flag_reason = random.choice(['Large amount', 'Unusual pattern', 'Risk threshold exceeded'])
        else:
            status_rand = random.random()
            if status_rand < 0.85:
                status = 'COMPLETED'
            elif status_rand < 0.93:
                status = 'PENDING'
            elif status_rand < 0.97:
                status = 'FAILED'
            else:
                status = 'FLAGGED'
            flag_reason = 'Automated screening' if status == 'FLAGGED' else None
        
        # Time distribution (80% business hours)
        created_at = random_date(START_DATE, END_DATE)
        if random.random() < 0.80:
            # Business hours: 8 AM - 8 PM
            created_at = created_at.replace(hour=random.randint(8, 19))
        else:
            # Off-hours
            created_at = created_at.replace(hour=random.choice([0,1,2,3,4,5,6,7,20,21,22,23]))
        
        instrument = random.choice(INSTRUMENTS) if txn_type == 'TRADE' else None
        
        transactions.append({
            'txn_id': txn_id,
            'user_id': user_id,
            'txn_type': txn_type,
            'instrument': instrument,
            'amount': amount,
            'currency': 'USD',
            'amount_usd': amount,
            'status': status,
            'flag_reason': flag_reason,
            'payment_method': random.choice(PAYMENT_METHODS) if txn_type in ['DEPOSIT', 'WITHDRAWAL'] else None,
            'external_ref': f"EXT-{random.randint(100000, 999999)}" if random.random() < 0.5 else None,
            'ip_address': random_ip(),
            'created_at': format_timestamp(created_at),
            'processed_at': format_timestamp(created_at + timedelta(seconds=random.randint(1, 300))) if status == 'COMPLETED' else None
        })
    
    return transactions

def generate_login_events(users):
    """Generate login event records"""
    events = []
    user_data = {u['user_id']: u for u in users}
    user_ids = list(user_data.keys())
    
    # Create some suspicious IPs (shared across multiple users)
    suspicious_ips = [random_ip() for _ in range(10)]
    
    for i in range(NUM_LOGIN_EVENTS):
        event_id = f"EVT-{str(i+1).zfill(5)}"
        
        # 95% are for known users
        if random.random() < 0.95:
            user_id = random.choice(user_ids)
            email_attempted = user_data[user_id]['email']
        else:
            user_id = None
            email_attempted = f"unknown{random.randint(1,1000)}@example.com"
        
        # IP address (5% use suspicious shared IPs)
        if random.random() < 0.05:
            ip_address = random.choice(suspicious_ips)
        else:
            ip_address = random_ip()
        
        # Status distribution
        status_rand = random.random()
        if status_rand < 0.85:
            status = 'SUCCESS'
            failure_reason = None
        elif status_rand < 0.97:
            status = 'FAILED'
            failure_reason = random.choice(['WRONG_PASSWORD', 'ACCOUNT_LOCKED', 'MFA_FAILED'])
        else:
            status = 'BLOCKED'
            failure_reason = random.choice(['IP_BLOCKED', 'SUSPICIOUS_ACTIVITY', 'GEO_BLOCKED'])
        
        country = user_data[user_id]['country'] if user_id and random.random() < 0.9 else random.choice(list(COUNTRIES.keys()))
        
        events.append({
            'event_id': event_id,
            'user_id': user_id,
            'email_attempted': email_attempted,
            'ip_address': ip_address,
            'country': country,
            'city': None,  # Optional
            'device_type': weighted_choice(DEVICE_TYPES, DEVICE_WEIGHTS),
            'device_fingerprint': generate_uuid() if random.random() < 0.7 else None,
            'user_agent': 'Mozilla/5.0 (compatible; DerivInsight/1.0)',
            'status': status,
            'failure_reason': failure_reason,
            'created_at': format_timestamp(random_date(START_DATE, END_DATE))
        })
    
    return events

def generate_alerts(users, transactions):
    """Generate alert records"""
    alerts = []
    user_ids = [u['user_id'] for u in users]
    flagged_txns = [t for t in transactions if t['status'] == 'FLAGGED']
    
    for i in range(NUM_ALERTS):
        alert_id = f"ALR-{str(i+1).zfill(4)}"
        rule_name, severity = random.choice(ALERT_RULES)
        
        # 80% of alerts are linked to users
        user_id = random.choice(user_ids) if random.random() < 0.8 else None
        
        # Link to transaction if relevant
        txn_id = None
        if rule_name in ['Large Transaction', 'Structuring Detection', 'Rapid Fund Movement'] and flagged_txns:
            txn = random.choice(flagged_txns)
            txn_id = txn['txn_id']
            user_id = txn['user_id']
        
        # Status distribution
        status_rand = random.random()
        if status_rand < 0.35:
            status = 'OPEN'
        elif status_rand < 0.50:
            status = 'INVESTIGATING'
        elif status_rand < 0.85:
            status = 'RESOLVED'
        else:
            status = 'DISMISSED'
        
        created_at = random_date(END_DATE - timedelta(days=30), END_DATE)
        
        alerts.append({
            'alert_id': alert_id,
            'rule_name': rule_name,
            'rule_id': f"RULE-{str(ALERT_RULES.index((rule_name, severity)) + 1).zfill(3)}",
            'user_id': user_id,
            'txn_id': txn_id,
            'severity': severity,
            'status': status,
            'details': json.dumps({'generated': 'mock_data', 'timestamp': format_timestamp(created_at)}),
            'assigned_to': None,
            'resolved_at': format_timestamp(created_at + timedelta(hours=random.randint(1, 72))) if status in ['RESOLVED', 'DISMISSED'] else None,
            'resolution_notes': 'Reviewed and cleared' if status == 'RESOLVED' else ('False positive' if status == 'DISMISSED' else None),
            'created_at': format_timestamp(created_at)
        })
    
    return alerts

def generate_audit_logs(users):
    """Generate audit log records"""
    logs = []
    user_ids = [u['user_id'] for u in users]
    actions = ['QUERY', 'VIEW', 'EXPORT', 'LOGIN', 'UPDATE']
    resources = ['USER', 'TRANSACTION', 'ALERT', 'DASHBOARD', 'REPORT']
    
    for i in range(NUM_AUDIT_LOGS):
        log_id = generate_uuid('LOG-')
        action = random.choice(actions)
        
        logs.append({
            'log_id': log_id,
            'actor_id': random.choice(user_ids),
            'action': action,
            'resource_type': random.choice(resources),
            'resource_id': generate_uuid() if random.random() < 0.7 else None,
            'query_text': 'SELECT * FROM transactions WHERE status = \'FLAGGED\'' if action == 'QUERY' else None,
            'ip_address': random_ip(),
            'created_at': format_timestamp(random_date(START_DATE, END_DATE))
        })
    
    return logs

def generate_dashboards(users):
    """Generate dashboard records"""
    dashboards = []
    user_ids = [u['user_id'] for u in users]
    
    dashboard_names = [
        "Compliance Overview", "High Risk Activity", "Transaction Volume", 
        "User Growth", "Alerts Summary", "Fraud Detection Matrix",
        "Geographic Distribution", "KYC Funnel", "Financial Operations",
        "System Health"
    ]
    
    for i in range(50):
        dashboard_id = generate_uuid('DSH-')
        owner_id = random.choice(user_ids)
        name = f"{random.choice(dashboard_names)} {random.randint(2025, 2026)}"
        
        # Mock widgets configuration
        widgets = []
        for j in range(random.randint(3, 8)):
            widgets.append({
                "id": f"widget_{j}",
                "type": random.choice(["LineChart", "BarChart", "PieChart", "Table", "MetricCard"]),
                "title": f"Widget {j+1}",
                "data_source": random.choice(["transactions", "users", "alerts"])
            })
            
        # Mock layout configuration
        layout = []
        for j, widget in enumerate(widgets):
            layout.append({
                "i": widget["id"],
                "x": (j % 3) * 4,
                "y": (j // 3) * 4,
                "w": 4,
                "h": 4
            })
            
        is_deployed = random.random() < 0.3
        created_at = random_date(START_DATE, END_DATE)
        
        dashboards.append({
            'dashboard_id': dashboard_id,
            'name': name,
            'owner_id': owner_id,
            'widgets': json.dumps(widgets),
            'layout': json.dumps(layout),
            'is_deployed': is_deployed,
            'deploy_url': f"https://analytics.derivinsight.com/d/{dashboard_id}" if is_deployed else None,
            'refresh_interval': random.choice([60, 300, 600, 1800, 3600]),
            'created_at': format_timestamp(created_at),
            'deployed_at': format_timestamp(created_at + timedelta(days=random.randint(0, 10))) if is_deployed else None
        })
        
    return dashboards

# ============================================================
# SQL OUTPUT
# ============================================================

def generate_insert_sql(table_name, records):
    """Generate INSERT statements for records"""
    if not records:
        return ''
    
    columns = list(records[0].keys())
    sql_lines = [f"\n-- {table_name.upper()} ({len(records)} records)"]
    
    for record in records:
        values = [escape_sql(record[col]) for col in columns]
        sql_lines.append(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});")
    
    return '\n'.join(sql_lines)

def main():
    print("DerivInsight Mock Data Generator")
    print("=" * 40)
    
    print(f"Generating {NUM_USERS} users...")
    users = generate_users()
    
    print(f"Generating {NUM_TRANSACTIONS} transactions...")
    transactions = generate_transactions(users)
    
    print(f"Generating {NUM_LOGIN_EVENTS} login events...")
    login_events = generate_login_events(users)
    
    print(f"Generating {NUM_ALERTS} alerts...")
    alerts = generate_alerts(users, transactions)
    
    print(f"Generating {NUM_AUDIT_LOGS} audit logs...")
    audit_logs = generate_audit_logs(users)

    print(f"Generating 50 dashboards...")
    dashboards = generate_dashboards(users)
    
    # Generate SQL file
    print("\nWriting SQL file...")
    
    with open('derivinsight_mock_data.sql', 'w') as f:
        f.write("-- DerivInsight Mock Data\n")
        f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-- ============================================================\n")
        
        f.write(generate_insert_sql('users', users))
        f.write(generate_insert_sql('transactions', transactions))
        f.write(generate_insert_sql('login_events', login_events))
        f.write(generate_insert_sql('alerts', alerts))
        f.write(generate_insert_sql('audit_logs', audit_logs))
        f.write(generate_insert_sql('dashboards', dashboards))
        
        f.write("\n\n-- END OF DATA\n")
    
    print("\n✅ Generated: derivinsight_mock_data.sql")
    print(f"   - {NUM_USERS} users")
    print(f"   - {NUM_TRANSACTIONS} transactions")
    print(f"   - {NUM_LOGIN_EVENTS} login events")
    print(f"   - {NUM_ALERTS} alerts")
    print(f"   - {NUM_AUDIT_LOGS} audit logs")
    print(f"   - 50 dashboards")
    print("\nRun: sqlite3 derivinsight.db < derivinsight_schema.sql")
    print("     sqlite3 derivinsight.db < derivinsight_mock_data.sql")

if __name__ == '__main__':
    main()
