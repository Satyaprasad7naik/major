-- =============================================
-- DerivInsight Alerts Engine Database Schema
-- MySQL Version
-- =============================================

-- Events table: stores all incoming events from various sources
CREATE TABLE IF NOT EXISTS events (
    id INT PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(255) NOT NULL,   -- source table/event type (e.g., 'login', 'transaction', 'kyc')
    payload_json TEXT NOT NULL,         -- JSON payload containing event data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed TINYINT(1) DEFAULT 0      -- flag to track if event has been processed
);

-- Index for efficient event fetching
CREATE INDEX idx_events_table_name ON events(table_name);
CREATE INDEX idx_events_created_at ON events(created_at);
CREATE INDEX idx_events_table_name_created_at ON events(table_name, created_at);
CREATE INDEX idx_events_processed ON events(processed);

-- Metric Specs table (alerts configuration)
-- Defines what conditions trigger alerts
CREATE TABLE IF NOT EXISTS metric_specs (
    metric_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,         -- human-readable metric name
    description TEXT,                   -- description of what this metric tracks
    table_name VARCHAR(255) NOT NULL,   -- which event type this metric applies to
    filter_json TEXT,                   -- JSON filter conditions (e.g., {"status": "failed"})
    window_sec INT NOT NULL,            -- sliding window duration in seconds
    threshold INT NOT NULL,             -- count threshold to trigger alert
    is_active TINYINT(1) DEFAULT 0,     -- whether alert is currently triggered
    severity VARCHAR(50) DEFAULT 'medium', -- alert severity: low, medium, high, critical
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_metric_specs_table_name ON metric_specs(table_name);
CREATE INDEX idx_metric_specs_is_active ON metric_specs(is_active);

-- Alert History table: logs all alert triggers and resolutions
CREATE TABLE IF NOT EXISTS alert_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    metric_id INT NOT NULL,
    action VARCHAR(50) NOT NULL,        -- 'triggered' or 'resolved'
    event_count INT NOT NULL,           -- count at the time of action
    threshold INT NOT NULL,             -- threshold at the time of action
    message TEXT,                       -- alert message
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (metric_id) REFERENCES metric_specs(metric_id)
);

CREATE INDEX idx_alert_history_metric_id ON alert_history(metric_id);
CREATE INDEX idx_alert_history_created_at ON alert_history(created_at);

-- Anomaly History table: one row per metric, updated whenever alert_history is written for that metric
CREATE TABLE IF NOT EXISTS anomaly_history (
    metric_id INT PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    severity VARCHAR(50) DEFAULT 'medium',
    alert_count INT NOT NULL DEFAULT 0,
    detected_at TIMESTAMP NULL,         -- set when alert becomes active and alert_count was 0 (start of current period)
    last_seen_at TIMESTAMP NULL,        -- updated on every trigger
    last_resolved_at TIMESTAMP NULL,    -- updated on every resolve
    current_status VARCHAR(50) NOT NULL, -- 'active' | 'resolved'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (metric_id) REFERENCES metric_specs(metric_id)
);

CREATE INDEX idx_anomaly_history_current_status ON anomaly_history(current_status);
CREATE INDEX idx_anomaly_history_updated_at ON anomaly_history(updated_at);

-- Metric Windows table: stores event timestamps for sliding window calculations
-- This replaces Redis ZSET for SQLite-based implementation
CREATE TABLE IF NOT EXISTS metric_windows (
    id INT PRIMARY KEY AUTO_INCREMENT,
    metric_id INT NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (metric_id) REFERENCES metric_specs(metric_id)
);

CREATE INDEX idx_metric_windows_metric_id ON metric_windows(metric_id);
CREATE INDEX idx_metric_windows_event_timestamp ON metric_windows(event_timestamp);
CREATE INDEX idx_metric_windows_composite ON metric_windows(metric_id, event_timestamp);

-- =============================================
-- Insert default metric specs (sample alerts)
-- =============================================

-- Alert: Too many failed logins in 5 minutes
INSERT IGNORE INTO metric_specs (metric_id, name, description, table_name, filter_json, window_sec, threshold, severity)
VALUES (1, 'Failed Login Spike', 'Triggers when failed login attempts exceed threshold in time window',
        'login', '{"status": "failed"}', 300, 10, 'high');

-- Alert: Too many failed transactions in 2 minutes
INSERT IGNORE INTO metric_specs (metric_id, name, description, table_name, filter_json, window_sec, threshold, severity)
VALUES (2, 'Failed Transaction Spike', 'Triggers when failed transactions exceed threshold',
        'transaction', '{"status": "failed"}', 120, 5, 'critical');

-- Alert: High volume of KYC rejections in 10 minutes
INSERT IGNORE INTO metric_specs (metric_id, name, description, table_name, filter_json, window_sec, threshold, severity)
VALUES (3, 'KYC Rejection Spike', 'Triggers when KYC rejections exceed threshold',
        'kyc', '{"kyc_status": "rejected"}', 600, 3, 'medium');

-- Alert: High transaction volume (any status) in 1 minute
INSERT IGNORE INTO metric_specs (metric_id, name, description, table_name, filter_json, window_sec, threshold, severity)
VALUES (4, 'Transaction Volume Spike', 'Triggers when total transaction volume is high',
        'transaction', '{}', 60, 20, 'low');

-- Alert: New user registration spike in 30 minutes
INSERT IGNORE INTO metric_specs (metric_id, name, description, table_name, filter_json, window_sec, threshold, severity)
VALUES (5, 'User Registration Spike', 'Triggers when new user registrations spike',
        'user', '{}', 1800, 50, 'low');

CREATE TABLE dashboards (
    dashboard_id VARCHAR(36) PRIMARY KEY,
    name TEXT,
    owner_id TEXT,
    widgets TEXT,
    layout TEXT,
    is_deployed BOOLEAN,
    deploy_url TEXT,
    refresh_interval INTEGER,
    created_at DATETIME,
    deployed_at DATETIME
);