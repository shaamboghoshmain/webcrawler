import React, { useState } from 'react';
import type { SessionLog } from '../types';

interface Props {
    stats: SessionLog;
    onSave: (finalLog: SessionLog) => void;
}

const SessionEndModal: React.FC<Props> = ({ stats, onSave }) => {
    const [reflection, setReflection] = useState<string>('');

    const handleSave = () => {
        onSave({ ...stats, reflection });
    };

    return (
        <div className="container" style={{ maxWidth: '500px', marginTop: '50px', background: '#252525', padding: '2rem', borderRadius: '8px' }}>
            <h2>Session Complete</h2>
            <p>Duration: {Math.floor(stats.duration_seconds / 60)}m {stats.duration_seconds % 60}s</p>
            <p>Words: {stats.word_count}</p>

            <div style={{ margin: '2rem 0' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>How was this session?</label>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    {['Thinking', 'Exploring', 'Mixed'].map((opt) => (
                        <button
                            key={opt}
                            className={reflection === opt ? 'btn-primary' : 'btn-secondary'}
                            onClick={() => setReflection(opt)}
                        >
                            {opt}
                        </button>
                    ))}
                </div>
            </div>

            <button className="btn-primary" style={{ width: '100%' }} onClick={handleSave} disabled={!reflection}>
                Save & Close
            </button>
        </div>
    );
};

export default SessionEndModal;
