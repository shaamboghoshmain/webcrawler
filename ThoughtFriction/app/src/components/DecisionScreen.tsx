import React from 'react';

interface Props {
    onChooseBlank: () => void;
    onChooseAI: () => void;
    onViewInsights: () => void;
}

const DecisionScreen: React.FC<Props> = ({ onChooseBlank, onChooseAI, onViewInsights }) => {
    return (
        <div className="decision-screen">
            <div className="decision-card" onClick={onChooseBlank} style={{ cursor: 'pointer' }}>
                <h2>Blank Page</h2>
                <p>Start with your own thinking.</p>
            </div>
            <div className="decision-card" onClick={onChooseAI} style={{ cursor: 'pointer', background: '#252525' }}>
                <h2>AI First</h2>
                <p>Explore ideas, then write solo.</p>
            </div>
            <div style={{ position: 'absolute', bottom: '2rem', right: '2rem' }}>
                <button className="btn-secondary" onClick={onViewInsights} style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}>Stats</button>
            </div>
        </div>
    );
};

export default DecisionScreen;
