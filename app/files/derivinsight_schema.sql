-- ============================================================
-- DerivInsight Database Schema
-- Deriv Hackathon 2026
-- Version: 1.0
-- Database: SQLite (Development) / PostgreSQL (Production)
-- ============================================================

-- ============================================================
-- TABLE: users
-- Description: All registered user accounts with KYC and risk info
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(36) PRIMARY KEY,                    -- Format: USR-XXXX
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    country CHAR(2) NOT NULL,                           -- ISO 3166-1 alpha-2
    phone VARCHAR(20),
    date_of_birth DATE,
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING|VERIFIED|REJECTED|EXPIRED
    kyc_verified_at TIMESTAMP,
    kyc_expiry_date DATE,
    risk_level VARCHAR(10) NOT NULL DEFAULT 'LOW',      -- LOW|MEDIUM|HIGH
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    is_pep BOOLEAN DEFAULT FALSE,                       -- Politically Exposed Person
    account_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE|SUSPENDED|CLOSED|FROZEN
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: transactions
-- Description: All financial transactions
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
    txn_id VARCHAR(36) PRIMARY KEY,                     -- Format: TXN-XXXXXX
    user_id VARCHAR(36) NOT NULL REFERENCES users(user_id),
    txn_type VARCHAR(20) NOT NULL,                      -- DEPOSIT|WITHDRAWAL|TRADE|FEE|BONUS|TRANSFER
    instrument VARCHAR(20),                             -- EUR/USD, BTC/USD, GOLD, etc.
    amount DECIMAL(18,2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL DEFAULT 'USD',            -- ISO 4217
    amount_usd DECIMAL(18,2) NOT NULL,                  -- Converted to USD for reporting
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',      -- PENDING|COMPLETED|FAILED|FLAGGED|REVERSED
    flag_reason VARCHAR(100),
    payment_method VARCHAR(50),                         -- CARD|BANK_TRANSFER|CRYPTO|EWALLET
    external_ref VARCHAR(100),
    ip_address VARCHAR(45),                             -- IPv4 or IPv6
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- ============================================================
-- TABLE: login_events
-- Description: Authentication attempts for security monitoring
-- ============================================================
CREATE TABLE IF NOT EXISTS login_events (
    event_id VARCHAR(36) PRIMARY KEY,                   -- Format: EVT-XXXXX
    user_id VARCHAR(36) REFERENCES users(user_id),      -- NULL for unknown user attempts
    email_attempted VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    country CHAR(2),                                    -- Geo-located from IP
    city VARCHAR(100),
    device_type VARCHAR(20),                            -- MOBILE|DESKTOP|TABLET|UNKNOWN
    device_fingerprint VARCHAR(64),
    user_agent TEXT,
    status VARCHAR(20) NOT NULL,                        -- SUCCESS|FAILED|BLOCKED|MFA_REQUIRED
    failure_reason VARCHAR(50),                         -- WRONG_PASSWORD|ACCOUNT_LOCKED|IP_BLOCKED
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: alert_rules
-- Description: Configurable anomaly detection rules
-- ============================================================
CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id VARCHAR(36) PRIMARY KEY,
    rule_name VARCHAR(50) UNIQUE NOT NULL,
    rule_type VARCHAR(30) NOT NULL,                     -- THRESHOLD|VELOCITY|PATTERN|GEO|TIME
    condition JSON NOT NULL,                            -- Rule condition config
    severity VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',     -- LOW|MEDIUM|HIGH|CRITICAL
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: alerts
-- Description: System-generated alerts from anomaly detection
-- ============================================================
CREATE TABLE IF NOT EXISTS alerts (
    alert_id VARCHAR(36) PRIMARY KEY,                   -- Format: ALR-XXXX
    rule_name VARCHAR(50) NOT NULL,
    rule_id VARCHAR(36) REFERENCES alert_rules(rule_id),
    user_id VARCHAR(36) REFERENCES users(user_id),      -- NULL for system alerts
    txn_id VARCHAR(36) REFERENCES transactions(txn_id),
    severity VARCHAR(10) NOT NULL,                      -- LOW|MEDIUM|HIGH|CRITICAL
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',         -- OPEN|INVESTIGATING|RESOLVED|DISMISSED|ESCALATED
    details JSON,                                       -- Alert context payload
    assigned_to VARCHAR(36) REFERENCES users(user_id),
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: audit_logs
-- Description: Complete audit trail for compliance
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id VARCHAR(36) PRIMARY KEY,
    actor_id VARCHAR(36) REFERENCES users(user_id),
    action VARCHAR(50) NOT NULL,                        -- QUERY|EXPORT|VIEW|UPDATE|DELETE|LOGIN
    resource_type VARCHAR(30) NOT NULL,                 -- USER|TRANSACTION|ALERT|DASHBOARD|REPORT
    resource_id VARCHAR(36),
    query_text TEXT,                                    -- NL query or SQL executed
    ip_address VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE: dashboards
-- Description: Saved dashboard configurations
-- ============================================================
CREATE TABLE IF NOT EXISTS dashboards (
    dashboard_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    owner_id VARCHAR(36) NOT NULL REFERENCES users(user_id),
    widgets JSON NOT NULL,                              -- Array of widget configs
    layout JSON NOT NULL,                               -- Grid layout positions
    is_deployed BOOLEAN DEFAULT FALSE,
    deploy_url VARCHAR(255),
    refresh_interval INTEGER DEFAULT 300,               -- Auto-refresh in seconds
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deployed_at TIMESTAMP
);

-- ============================================================
-- TABLE: query_history
-- Description: Saved NL queries for replay
-- ============================================================
CREATE TABLE IF NOT EXISTS query_history (
    query_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(user_id),
    nl_query TEXT NOT NULL,                             -- Natural language query
    generated_sql TEXT NOT NULL,                        -- Generated SQL
    result_count INTEGER,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- INDEXES
-- ============================================================

-- users indexes
CREATE INDEX idx_users_country ON users(country);
CREATE INDEX idx_users_kyc_status ON users(kyc_status);
CREATE INDEX idx_users_risk_level ON users(risk_level);
CREATE INDEX idx_users_account_status ON users(account_status);
CREATE INDEX idx_users_created_at ON users(created_at);

-- transactions indexes
CREATE INDEX idx_txn_user_id ON transactions(user_id);
CREATE INDEX idx_txn_status ON transactions(status);
CREATE INDEX idx_txn_type ON transactions(txn_type);
CREATE INDEX idx_txn_amount_usd ON transactions(amount_usd);
CREATE INDEX idx_txn_created_at ON transactions(created_at);
CREATE INDEX idx_txn_user_created ON transactions(user_id, created_at);
CREATE INDEX idx_txn_instrument ON transactions(instrument);

-- login_events indexes
CREATE INDEX idx_login_user_id ON login_events(user_id);
CREATE INDEX idx_login_status ON login_events(status);
CREATE INDEX idx_login_ip ON login_events(ip_address);
CREATE INDEX idx_login_country ON login_events(country);
CREATE INDEX idx_login_created_at ON login_events(created_at);

-- alerts indexes
CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_rule_name ON alerts(rule_name);
CREATE INDEX idx_alerts_created_at ON alerts(created_at);

-- audit_logs indexes
CREATE INDEX idx_audit_actor_id ON audit_logs(actor_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at);

-- dashboards indexes
CREATE INDEX idx_dashboards_owner_id ON dashboards(owner_id);
CREATE INDEX idx_dashboards_is_deployed ON dashboards(is_deployed);


-- ============================================================
-- PRE-CONFIGURED ALERT RULES
-- ============================================================

INSERT INTO alert_rules (rule_id, rule_name, rule_type, condition, severity, is_active) VALUES
('RULE-001', 'Large Transaction', 'THRESHOLD', 
 '{"field": "amount_usd", "operator": ">", "value": 50000}', 'HIGH', TRUE),

('RULE-002', 'Velocity Alert', 'VELOCITY', 
 '{"event": "TRADE", "count": 20, "window_minutes": 5, "group_by": "user_id"}', 'MEDIUM', TRUE),

('RULE-003', 'Off-Hours Activity', 'TIME', 
 '{"outside_hours": {"start": "08:00", "end": "20:00"}, "timezone": "local"}', 'LOW', TRUE),

('RULE-004', 'New Geo Login', 'GEO', 
 '{"condition": "new_country", "lookback_days": 30}', 'MEDIUM', TRUE),

('RULE-005', 'Failed Auth Spike', 'VELOCITY', 
 '{"event": "FAILED_LOGIN", "count": 5, "window_minutes": 10, "group_by": "user_id"}', 'HIGH', TRUE),

('RULE-006', 'Withdrawal Pattern', 'PATTERN', 
 '{"event": "WITHDRAWAL", "count": 3, "window_hours": 24, "condition": "different_destinations"}', 'HIGH', TRUE),

('RULE-007', 'Structuring Detection', 'PATTERN', 
 '{"event": "DEPOSIT", "amount_range": {"min": 9000, "max": 10000}, "count": 3, "window_hours": 24}', 'CRITICAL', TRUE),

('RULE-008', 'Dormant Account Activity', 'PATTERN', 
 '{"condition": "activity_after_dormancy", "dormancy_days": 90}', 'MEDIUM', TRUE),

('RULE-009', 'High Risk Country', 'GEO', 
 '{"countries": ["AF", "IR", "KP", "SY", "YE"], "event": "TRANSACTION"}', 'HIGH', TRUE),

('RULE-010', 'Rapid Fund Movement', 'PATTERN', 
 '{"sequence": ["DEPOSIT", "WITHDRAWAL"], "window_hours": 1, "min_amount": 5000}', 'HIGH', TRUE);


-- ============================================================
-- SAMPLE DATA GENERATION HELPERS (SQLite)
-- ============================================================

-- Use this to generate UUIDs in SQLite:
-- SELECT lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || 
--        substr(lower(hex(randomblob(2))),2) || '-' || 
--        substr('89ab',abs(random()) % 4 + 1, 1) || 
--        substr(lower(hex(randomblob(2))),2) || '-' || 
--        lower(hex(randomblob(6)));

-- ============================================================
-- VIEWS (for common queries)
-- ============================================================

-- High-risk users needing attention
CREATE VIEW IF NOT EXISTS v_high_risk_users AS
SELECT u.*, 
       COUNT(DISTINCT t.txn_id) as txn_count,
       SUM(t.amount_usd) as total_volume,
       COUNT(DISTINCT a.alert_id) as alert_count
FROM users u
LEFT JOIN transactions t ON u.user_id = t.user_id
LEFT JOIN alerts a ON u.user_id = a.user_id AND a.status = 'OPEN'
WHERE u.risk_level = 'HIGH'
GROUP BY u.user_id;

-- Flagged transactions with user details
CREATE VIEW IF NOT EXISTS v_flagged_transactions AS
SELECT t.*, u.full_name, u.country as user_country, u.risk_level, u.kyc_status
FROM transactions t
JOIN users u ON t.user_id = u.user_id
WHERE t.status = 'FLAGGED';

-- Open alerts with context
CREATE VIEW IF NOT EXISTS v_open_alerts AS
SELECT a.*, u.full_name, u.email, u.risk_level, t.amount_usd as txn_amount
FROM alerts a
LEFT JOIN users u ON a.user_id = u.user_id
LEFT JOIN transactions t ON a.txn_id = t.txn_id
WHERE a.status = 'OPEN'
ORDER BY 
    CASE a.severity 
        WHEN 'CRITICAL' THEN 1 
        WHEN 'HIGH' THEN 2 
        WHEN 'MEDIUM' THEN 3 
        ELSE 4 
    END,
    a.created_at DESC;

-- Daily transaction summary
CREATE VIEW IF NOT EXISTS v_daily_summary AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_txns,
    SUM(amount_usd) as total_volume,
    AVG(amount_usd) as avg_amount,
    COUNT(CASE WHEN status = 'FLAGGED' THEN 1 END) as flagged_count,
    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_count
FROM transactions
GROUP BY DATE(created_at)
ORDER BY date DESC;


-- ============================================================
-- END OF SCHEMA
-- ============================================================
