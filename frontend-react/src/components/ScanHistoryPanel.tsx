import { useState, useEffect } from 'react';
import './ScanHistoryPanel.css';

interface ScanSummary {
    scan_id: string;
    timestamp: string;
    total_missions: number;
    critical_count: number;
    high_count: number;
    overall_risk: number;
    overall_severity: string;
}

interface ScanHistoryPanelProps {
    onClose: () => void;
    onSelectScan: (scanId: string) => void;
}

export default function ScanHistoryPanel({ onClose, onSelectScan }: ScanHistoryPanelProps) {
    const [scans, setScans] = useState<ScanSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setLoading(true);
        fetch('http://localhost:8080/api/v1/sentinel/history')
            .then(res => res.json())
            .then(data => {
                setScans(data.scans || []);
                setLoading(false);
            })
            .catch(err => {
                setError('Failed to load scan history');
                setLoading(false);
            });
    }, []);

    const formatDate = (ts: string) => {
        const d = new Date(ts + 'Z');
        return d.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        });
    };

    const severityColor = (sev: string) => {
        switch (sev) {
            case 'CRITICAL': return 'var(--danger)';
            case 'HIGH': return 'var(--warning)';
            case 'MEDIUM': return 'var(--accent)';
            default: return 'var(--success)';
        }
    };

    return (
        <div className="history-overlay" onClick={onClose}>
            <div className="history-panel" onClick={e => e.stopPropagation()}>
                <div className="history-panel-header">
                    <div>
                        <span className="history-badge">SCAN ARCHIVE</span>
                        <h3>Scan History</h3>
                    </div>
                    <button className="history-close-btn" onClick={onClose}>X</button>
                </div>

                <div className="history-panel-body">
                    {loading && (
                        <div className="history-loading">
                            <div className="history-spinner" />
                            <p>Loading scan history...</p>
                        </div>
                    )}

                    {error && <div className="history-error">{error}</div>}

                    {!loading && !error && scans.length === 0 && (
                        <div className="history-empty">
                            <p>No past scans found.</p>
                            <p className="history-empty-sub">Run a Sentinel scan to see it here.</p>
                        </div>
                    )}

                    {!loading && scans.map(scan => (
                        <button
                            key={scan.scan_id}
                            className="history-scan-card"
                            onClick={() => onSelectScan(scan.scan_id)}
                        >
                            <div className="scan-card-top">
                                <span
                                    className="scan-severity-dot"
                                    style={{ background: severityColor(scan.overall_severity) }}
                                />
                                <span className="scan-date">{formatDate(scan.timestamp)}</span>
                                <span className={`severity-pill small ${scan.overall_severity}`}>
                                    {scan.overall_severity}
                                </span>
                            </div>
                            <div className="scan-card-stats">
                                <div className="scan-stat">
                                    <span className="scan-stat-value">{scan.total_missions}</span>
                                    <span className="scan-stat-label">Missions</span>
                                </div>
                                <div className="scan-stat">
                                    <span className="scan-stat-value" style={{ color: 'var(--danger)' }}>
                                        {scan.critical_count}
                                    </span>
                                    <span className="scan-stat-label">Critical</span>
                                </div>
                                <div className="scan-stat">
                                    <span className="scan-stat-value" style={{ color: 'var(--warning)' }}>
                                        {scan.high_count}
                                    </span>
                                    <span className="scan-stat-label">High</span>
                                </div>
                                <div className="scan-stat">
                                    <span className="scan-stat-value">{scan.overall_risk}</span>
                                    <span className="scan-stat-label">Risk</span>
                                </div>
                            </div>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}
