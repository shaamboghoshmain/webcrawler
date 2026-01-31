import { useState } from 'react';
import DecisionScreen from './components/DecisionScreen';
import BlankEditor from './components/BlankEditor';
import AIGuidance from './components/AIGuidance';
import SessionEndModal from './components/SessionEndModal';
import InsightsModal from './components/InsightsModal';
import type { SessionMode, SessionLog } from './types';
import './index.css';

function App() {
  const [mode, setMode] = useState<SessionMode>('decision');
  const [sessionType, setSessionType] = useState<'blank' | 'ai'>('blank');
  const [sessionStats, setSessionStats] = useState<SessionLog | null>(null);
  const [showInsights, setShowInsights] = useState(false);

  const startBlank = () => {
    setSessionType('blank');
    setMode('blank');
  };

  const startAI = () => {
    setSessionType('ai');
    setMode('ai-guidance');
  };

  const handleFinishSession = (duration: number, wordCount: number) => {
    setSessionStats({
      timestamp: new Date().toISOString(),
      mode: sessionType,
      duration_seconds: duration,
      word_count: wordCount
    });
    setMode('reflection');
  };

  const handleSaveSession = async (finalLog: SessionLog) => {
    try {
      await fetch('http://localhost:8000/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(finalLog)
      });
    } catch (e) {
      console.error("Failed to save session", e);
      alert("Failed to save session: " + e);
    }
    setMode('decision');
    setSessionStats(null);
  };

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', position: 'relative' }}>
      {mode === 'decision' && (
        <DecisionScreen
          onChooseBlank={startBlank}
          onChooseAI={startAI}
          onViewInsights={() => setShowInsights(true)}
        />
      )}
      {mode === 'blank' && (
        <BlankEditor
          onFinish={handleFinishSession}
          // If coming from AI, give 3 mins (180s). Else 10 mins (600s).
          initialDurationSeconds={sessionType === 'ai' ? 180 : 600}
        />
      )}
      {mode === 'ai-guidance' && (
        <AIGuidance
          onBack={() => setMode('decision')}
          onStartSolo={() => setMode('blank')}
        />
      )}
      {mode === 'reflection' && sessionStats && (
        <SessionEndModal
          stats={sessionStats}
          onSave={handleSaveSession}
        />
      )}
      {showInsights && (
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <InsightsModal onClose={() => setShowInsights(false)} />
        </div>
      )}
    </div>
  );
}

export default App;
