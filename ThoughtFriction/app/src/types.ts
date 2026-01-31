export type SessionMode = 'decision' | 'blank' | 'ai-guidance' | 'ai-results' | 'reflection';

export interface IdeaRequest {
    topic: string;
    goal: string;
    hypothesis: string;
    uncertainty: string;
    constraints?: string;
    max_bullets: number;
}

export interface IdeaResponse {
    bullets: string[];
    counterpoints: string[];
    questions: string[];
}

export interface SessionLog {
    timestamp: string;
    mode: 'blank' | 'ai';
    duration_seconds: number;
    word_count: number;
    reflection?: string;
}
