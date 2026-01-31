import React, { useState } from 'react';
import type { IdeaRequest, IdeaResponse } from '../types';

interface Props {
    onBack: () => void;
    onStartSolo: () => void;
}

const AIGuidance: React.FC<Props> = ({ onBack, onStartSolo }) => {
    const [step, setStep] = useState<'form' | 'loading' | 'results'>('form');
    const [formData, setFormData] = useState<IdeaRequest>({
        topic: '',
        goal: '',
        hypothesis: '',
        uncertainty: '',
        max_bullets: 12
    });
    const [results, setResults] = useState<IdeaResponse | null>(null);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async () => {
        setStep('loading');
        try {
            const res = await fetch('http://localhost:8000/api/generate_ideas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            if (!res.ok) throw new Error('API Error');
            const data = await res.json();
            setResults(data);
            setStep('results');
        } catch (err) {
            console.error(err);
            setStep('form');
            alert('Failed to generate ideas. Ensure the Python service is running.');
        }
    };

    if (step === 'loading') {
        return <div className="container"><h2>Thinking...</h2></div>;
    }

    if (step === 'results' && results) {
        return (
            <div className="container">
                <h2>Guidance</h2>
                <div style={{ display: 'flex', gap: '2rem' }}>
                    <div style={{ flex: 1 }}>
                        <h3>Ideas</h3>
                        <ul>{results.bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>
                    </div>
                    <div style={{ flex: 1 }}>
                        <h3>Counterpoints</h3>
                        <ul>{results.counterpoints.map((b, i) => <li key={i}>{b}</li>)}</ul>
                        <h3>Questions</h3>
                        <ul>{results.questions.map((b, i) => <li key={i}>{b}</li>)}</ul>
                    </div>
                </div>
                <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
                    <button className="btn-primary" onClick={onStartSolo}>Start Solo Writing (3m)</button>
                </div>
            </div>
        );
    }

    return (
        <div className="container">
            <button onClick={onBack} className="btn-secondary" style={{ marginBottom: '1rem' }}>Back</button>
            <h2>AI Guidance</h2>
            <div className="form-group">
                <label className="form-label">Topic</label>
                <input className="form-input" name="topic" value={formData.topic} onChange={handleChange} />
            </div>
            <div className="form-group">
                <label className="form-label">Goal</label>
                <input className="form-input" name="goal" value={formData.goal} onChange={handleChange} />
            </div>
            <div className="form-group">
                <label className="form-label">Hypothesis</label>
                <input className="form-input" name="hypothesis" value={formData.hypothesis} onChange={handleChange} />
            </div>
            <div className="form-group">
                <label className="form-label">Uncertainty</label>
                <input className="form-input" name="uncertainty" value={formData.uncertainty} onChange={handleChange} />
            </div>
            <button className="btn-primary" onClick={handleSubmit}>Generate Ideas</button>
        </div>
    );
};

export default AIGuidance;
