import React, { useState, useEffect } from 'react';

interface Props {
    onFinish: (duration: number, wordCount: number) => void;
    initialDurationSeconds?: number;
}

const BlankEditor: React.FC<Props> = ({ onFinish, initialDurationSeconds = 600 }) => {
    const [text, setText] = useState('');
    const [timeLeft, setTimeLeft] = useState(initialDurationSeconds);
    const [isActive, setIsActive] = useState(true);

    useEffect(() => {
        let interval: any = null;
        if (isActive && timeLeft > 0) {
            interval = setInterval(() => {
                setTimeLeft((seconds) => seconds - 1);
            }, 1000);
        } else if (timeLeft === 0) {
            if (interval) clearInterval(interval);
            // Timer finished - auto finish or just stop? MVP: just stop and let user finish.
            setIsActive(false);
        }
        return () => {
            if (interval) clearInterval(interval);
        };
    }, [isActive, timeLeft]);

    const formatTime = (seconds: number) => {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    };

    const wordCount = text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
    const elapsed = initialDurationSeconds - timeLeft;

    return (
        <div className="editor-container">
            <div className="editor-header">
                <div>
                    <span style={{ fontWeight: 'bold', marginRight: '1rem' }}>{formatTime(timeLeft)}</span>
                    <span style={{ color: '#888' }}>{wordCount} words</span>
                </div>
                <button className="btn-primary" onClick={() => onFinish(elapsed, wordCount)}>Finish Session</button>
            </div>
            <textarea
                className="editor-textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Start writing..."
                autoFocus
            />
        </div>
    );
};

export default BlankEditor;
