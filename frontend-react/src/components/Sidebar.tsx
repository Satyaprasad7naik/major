import './Sidebar.css';

const DOMAINS = [
    { id: 'general', label: 'General', icon: '🌐' },
    { id: 'security', label: 'Security', icon: '🔒' },
    { id: 'compliance', label: 'Compliance', icon: '📋' },
    { id: 'risk', label: 'Risk', icon: '⚠️' },
    { id: 'operations', label: 'Operations', icon: '⚙️' },
];

const EXAMPLE_QUERIES = [
    'Show me all high severity incidents',
    'What are the compliance violations in the last 30 days?',
    'List all open security risks',
    'Show operational metrics for last quarter',
];

const SENTINEL_DOMAINS = [
    { icon: '🛡️', label: 'Security & Risk', desc: 'Login anomalies, suspicious transactions, high-risk users' },
    { icon: '📜', label: 'Compliance', desc: 'PEP violations, KYC gaps, regulatory breaches' },
    { icon: '⚙️', label: 'Operations', desc: 'Payment failures, system errors, performance issues' },
];

interface SidebarProps {
    mode: string;
    setMode: (mode: string) => void;
    selectedDomain: string;
    setSelectedDomain: (domain: string) => void;
    onOpenHistory?: () => void;
}

export default function Sidebar({ mode, setMode, selectedDomain, setSelectedDomain, onOpenHistory }: SidebarProps) {
    return (
        <aside className="sidebar">
            {/* Mode Toggle */}
            <div className="sidebar-section">
                <button
                    className={`mode-toggle-btn ${mode === 'sentinel' ? 'active' : ''}`}
                    onClick={() => setMode(mode === 'sentinel' ? 'chat' : 'sentinel')}
                >
                    <span className="pulse-ring"></span>
                    <span className="icon">{mode === 'sentinel' ? '💬' : '🛰️'}</span>
                    {mode === 'sentinel' ? 'QUERY CHAT' : 'SENTINEL MODE'}
                </button>
            </div>

            {/* Scan History (sentinel mode only) */}
            {mode === 'sentinel' && onOpenHistory && (
                <div className="sidebar-section">
                    <button className="history-btn" onClick={onOpenHistory}>
                        <span className="icon">📋</span>
                        Scan History
                    </button>
                </div>
            )}

            {/* Sentinel: Domain Monitoring Legend */}
            {mode === 'sentinel' && (
                <div className="sidebar-section">
                    <h3>Monitoring Domains</h3>
                    <div className="sentinel-domain-list">
                        {SENTINEL_DOMAINS.map((d, i) => (
                            <div key={i} className="sentinel-domain-item">
                                <span className="sentinel-domain-icon">{d.icon}</span>
                                <div>
                                    <div className="sentinel-domain-label">{d.label}</div>
                                    <div className="sentinel-domain-desc">{d.desc}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Sentinel: Severity Legend */}
            {mode === 'sentinel' && (
                <div className="sidebar-section">
                    <h3>Severity Levels</h3>
                    <div className="severity-legend">
                        <div className="severity-legend-item">
                            <span className="severity-dot critical"></span>
                            <span>Critical</span>
                            <span className="severity-legend-hint">Immediate action</span>
                        </div>
                        <div className="severity-legend-item">
                            <span className="severity-dot high"></span>
                            <span>High</span>
                            <span className="severity-legend-hint">Urgent review</span>
                        </div>
                        <div className="severity-legend-item">
                            <span className="severity-dot medium"></span>
                            <span>Medium</span>
                            <span className="severity-legend-hint">Monitor closely</span>
                        </div>
                        <div className="severity-legend-item">
                            <span className="severity-dot low"></span>
                            <span>Low</span>
                            <span className="severity-legend-hint">Informational</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Sentinel: Pipeline Info */}
            {mode === 'sentinel' && (
                <div className="sidebar-section">
                    <h3>Scan Pipeline</h3>
                    <div className="pipeline-steps">
                        <div className="pipeline-step"><span className="pipeline-num">1</span>AI Brainstorms Missions</div>
                        <div className="pipeline-step"><span className="pipeline-num">2</span>NL2SQL Execution</div>
                        <div className="pipeline-step"><span className="pipeline-num">3</span>Deep Dive Follow-ups</div>
                        <div className="pipeline-step"><span className="pipeline-num">4</span>Cross-Domain Correlation</div>
                        <div className="pipeline-step"><span className="pipeline-num">5</span>Intelligence Brief</div>
                    </div>
                </div>
            )}

            {/* Chat: Domain Selection */}
            {mode === 'chat' && (
                <div className="sidebar-section">
                    <h3>Domain Selection</h3>
                    <div className="domain-selector">
                        {DOMAINS.map((domain) => (
                            <button
                                key={domain.id}
                                className={`domain-btn ${selectedDomain === domain.id ? 'active' : ''}`}
                                onClick={() => setSelectedDomain(domain.id)}
                            >
                                <span className="domain-icon">{domain.icon}</span>
                                {domain.label}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Chat: Quick Examples */}
            {mode === 'chat' && (
                <div className="sidebar-section">
                    <h3>Quick Examples</h3>
                    <div className="examples-list">
                        {EXAMPLE_QUERIES.map((query, idx) => (
                            <div key={idx} className="example-item">
                                <span className="example-icon">💡</span>
                                {query}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </aside>
    );
}
