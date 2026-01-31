from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class IdeaRequest(BaseModel):
    topic: str
    goal: str
    hypothesis: str
    uncertainty: str
    constraints: Optional[str] = None
    max_bullets: int = 12

class IdeaResponse(BaseModel):
    bullets: List[str]
    counterpoints: List[str]
    questions: List[str]

class SessionSummaryRequest(BaseModel):
    raw_notes: str
    ai_output_used: bool
    final_text: Optional[str] = None
    duration_seconds: int

class SessionSummaryResponse(BaseModel):
    suggested_title: str
    key_thesis: str
    weak_spots: str
    next_steps: str

class SessionLog(BaseModel):
    id: Optional[int] = None
    timestamp: datetime
    mode: str  # "blank" or "ai"
    duration_seconds: int
    word_count: int
    reflection: Optional[str] = None  # "thinking", "exploring", "mixed"
