import React, { useEffect, useState } from 'react';

interface Stats {
    total_sessions: number;
    blank_sessions: number;
    ai_sessions: number;
    avg_blank_duration: number;
}

interface Props {
    onClose: () => void;
}

const InsightsModal: React.FC<Props> = ({ onClose }) => {
    const [stats, setStats] = useState<Stats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('http://localhost:8000/api/stats')
            .then(res => res.json())
            .then(data => {
                setStats(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    if (loading) return <div className="container">Loading stats...</div>;

    if (!stats) return <div className="container">Failed to load stats. <button onClick={onClose}>Close</button></div>;

    return (
        <div className="container" style={{ maxWidth: '600px', marginTop: '50px', background: '#252525', padding: '2rem', borderRadius: '8px', position: 'relative' }}>
            <button onClick={onClose} style={{ position: 'absolute', right: '1rem', top: '1rem', background: 'transparent', border: 'none', color: '#888', cursor: 'pointer', fontSize: '1.5rem' }}>&times;</button>
            <h2>Insights</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                <div>
                    <h3>Total Sessions</h3>
                    <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.total_sessions}</p>
                </div>
                <div>
                    <h3>Blank Page Rate</h3>
                    <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                        {stats.total_sessions ? Math.round((stats.blank_sessions / stats.total_sessions) * 100) : 0}%
                    </p>
                </div>
                <div>
                    <h3>Avg Solo Duration</h3>
                    <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                        {Math.floor(stats.avg_blank_duration / 60)}m {Math.round(stats.avg_blank_duration % 60)}s
                    </p>
                </div>
            </div>
        </div>
    );
};

export default InsightsModal;
