import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';
import './ChatInterface.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, ArcElement, Title, Tooltip, Legend);

interface ChatInterfaceProps {
    domain: string;
}

interface Message {
    role: 'user' | 'assistant';
    content: string;
    sql?: string;
    results?: any[];
    visualization?: any;
    insight?: string;
    recommendation?: string;
}

export default function ChatInterface({ domain }: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [conversationHistory, setConversationHistory] = useState<any[]>([]);

    const queryMutation = useMutation({
        mutationFn: async (query: string) => {
            const response = await fetch('http://localhost:8080/api/v1/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    domain,
                    conversation_history: conversationHistory,
                }),
            });
            if (!response.ok) throw new Error('Query failed');
            return response.json();
        },
        onSuccess: (data) => {
            const assistantMessage: Message = {
                role: 'assistant',
                content: data.status === 'success'
                    ? `✅ Query executed successfully! Found ${data.results?.length || 0} results.`
                    : data.clarification_question || data.error || 'Query failed',
                sql: data.sql,
                results: data.results,
                visualization: data.visualization_config,
                insight: data.insight,
                recommendation: data.recommendation,
            };

            setMessages(prev => [...prev, assistantMessage]);
            setConversationHistory(prev => [
                ...prev,
                { role: 'assistant', content: assistantMessage.content }
            ]);

            if (data.status === 'success') {
                toast.success('Query executed successfully!');
            } else if (data.status === 'needs_clarification') {
                toast.info('Need more information');
            } else {
                toast.error('Query failed');
            }
        },
        onError: () => {
            toast.error('Failed to connect to API');
        },
    });

    const handleSend = () => {
        if (!input.trim() || queryMutation.isPending) return;

        const userMessage: Message = {
            role: 'user',
            content: input,
        };

        setMessages(prev => [...prev, userMessage]);
        setConversationHistory(prev => [...prev, { role: 'user', content: input }]);
        queryMutation.mutate(input);
        setInput('');
    };

    const renderChart = (results: any[], config: any) => {
        if (!results || !config || config.chart_type === 'table') return null;

        const labels = results.map(row => row[config.x_axis_key]);
        const yKey = Array.isArray(config.y_axis_key) ? config.y_axis_key[0] : config.y_axis_key;
        const data = results.map(row => parseFloat(row[yKey]) || 0);

        const chartData = {
            labels,
            datasets: [{
                label: yKey,
                data,
                backgroundColor: 'rgba(99, 102, 241, 0.6)',
                borderColor: 'rgb(99, 102, 241)',
                borderWidth: 2,
            }],
        };

        const options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true },
                title: { display: true, text: config.title || 'Data Visualization' },
            },
        };

        switch (config.chart_type) {
            case 'bar':
                return <Bar data={chartData} options={options} />;
            case 'line':
                return <Line data={chartData} options={options} />;
            case 'pie':
                return <Pie data={chartData} options={options} />;
            default:
                return null;
        }
    };

    return (
        <div className="chat-interface">
            {/* Messages */}
            <div className="messages-container">
                {messages.length === 0 ? (
                    <div className="welcome-message">
                        <h2>👋 Welcome to DerivInsight</h2>
                        <p>Ask me anything about your data in natural language. I'll convert it to SQL and show you the results!</p>
                        <div className="features">
                            <div className="feature">
                                <span className="feature-icon">🤖</span>
                                <span>AI-Powered Queries</span>
                            </div>
                            <div className="feature">
                                <span className="feature-icon">📊</span>
                                <span>Visual Analytics</span>
                            </div>
                            <div className="feature">
                                <span className="feature-icon">⚡</span>
                                <span>Real-time Results</span>
                            </div>
                        </div>
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <div key={idx} className={`message ${msg.role}`}>
                            <div className="message-content">
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>

                            {msg.sql && (
                                <div className="sql-block">
                                    <div className="sql-header">
                                        <span>Generated SQL</span>
                                        <button onClick={() => navigator.clipboard.writeText(msg.sql!)}>Copy</button>
                                    </div>
                                    <pre>{msg.sql}</pre>
                                </div>
                            )}

                            {msg.results && msg.results.length > 0 && (
                                <>
                                    {msg.visualization && (
                                        <div className="chart-container">
                                            {renderChart(msg.results, msg.visualization)}
                                        </div>
                                    )}

                                    <div className="results-table">
                                        <table>
                                            <thead>
                                                <tr>
                                                    {Object.keys(msg.results[0]).map(key => (
                                                        <th key={key}>{key}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {msg.results.slice(0, 10).map((row, i) => (
                                                    <tr key={i}>
                                                        {Object.values(row).map((val: any, j) => (
                                                            <td key={j}>{val?.toString() || 'N/A'}</td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </>
                            )}

                            {(msg.insight || msg.recommendation) && (
                                <div className="insights-box">
                                    {msg.insight && (
                                        <div className="insight-item">
                                            <div className="insight-label">💡 AI Insight</div>
                                            <ReactMarkdown>{msg.insight}</ReactMarkdown>
                                        </div>
                                    )}
                                    {msg.recommendation && (
                                        <div className="rec-item">
                                            <div className="rec-label">⚖️ Recommended Action</div>
                                            <ReactMarkdown>{Array.isArray(msg.recommendation) ? msg.recommendation.join('\n') : msg.recommendation}</ReactMarkdown>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))
                )}

                {queryMutation.isPending && (
                    <div className="loading-indicator">
                        <span>Thinking</span>
                        <div className="loading-dots">
                            <div className="dot"></div>
                            <div className="dot"></div>
                            <div className="dot"></div>
                        </div>
                    </div>
                )}
            </div>

            {/* Input */}
            <div className="input-container">
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSend();
                        }
                    }}
                    placeholder="Ask a question about your data..."
                    rows={1}
                />
                <button onClick={handleSend} disabled={queryMutation.isPending}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                </button>
            </div>
        </div>
    );
}
