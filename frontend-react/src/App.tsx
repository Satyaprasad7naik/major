import { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import SentinelDashboard from './components/SentinelDashboard';
import ScanHistoryPanel from './components/ScanHistoryPanel';
import type { HistoricalScan } from './components/SentinelDashboard';
import './App.css';

const queryClient = new QueryClient();

function App() {
    const [mode, setMode] = useState('sentinel'); // 'chat' or 'sentinel'
    const [selectedDomain, setSelectedDomain] = useState('general');
    const [isConnected, setIsConnected] = useState(false);
    const [showHistory, setShowHistory] = useState(false);
    const [historicalScan, setHistoricalScan] = useState<HistoricalScan | null>(null);

    useEffect(() => {
        // Check API connection
        fetch('http://localhost:8080/health')
            .then(res => res.json())
            .then(() => setIsConnected(true))
            .catch(() => setIsConnected(false));
    }, []);

    const handleSelectScan = (scanId: string) => {
        fetch(`http://localhost:8080/api/v1/sentinel/history/${scanId}`)
            .then(res => res.json())
            .then(data => {
                setHistoricalScan(data);
                setShowHistory(false);
            })
            .catch(err => console.error('Failed to load scan:', err));
    };

    const handleBackToLive = () => {
        setHistoricalScan(null);
    };

    return (
        <QueryClientProvider client={queryClient}>
            <div className="app-container">
                <Toaster position="top-right" />

                {/* Header */}
                <header className="app-header">
                    <div className="logo-section">
                        <div className="logo-icon">🛰️</div>
                        <h1>DerivInsight</h1>
                        <span className="tagline">AI-Powered Intelligence Platform</span>
                    </div>

                    <div className="header-actions">
                        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
                            <span className="status-dot"></span>
                            {isConnected ? 'Connected' : 'Disconnected'}
                        </div>
                    </div>
                </header>

                <div className="app-body">
                    {/* Sidebar */}
                    <Sidebar
                        mode={mode}
                        setMode={setMode}
                        selectedDomain={selectedDomain}
                        setSelectedDomain={setSelectedDomain}
                        onOpenHistory={() => setShowHistory(true)}
                    />

                    {/* Main Content */}
                    <main className="main-content">
                        {mode === 'chat' ? (
                            <ChatInterface domain={selectedDomain} />
                        ) : (
                            <SentinelDashboard
                                historicalScan={historicalScan}
                                onBackToLive={handleBackToLive}
                            />
                        )}
                    </main>
                </div>

                {/* History Panel Overlay */}
                {showHistory && (
                    <ScanHistoryPanel
                        onClose={() => setShowHistory(false)}
                        onSelectScan={handleSelectScan}
                    />
                )}
            </div>
        </QueryClientProvider>
    );
}

export default App;
