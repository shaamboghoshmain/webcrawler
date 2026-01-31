import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import IdeaRequest, IdeaResponse, SessionSummaryRequest, SessionSummaryResponse, SessionLog
from .gemini import gemini_client
from .database import db

app = FastAPI(title="Friction Service")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "app://."], # app://. for Electron if needed, though usually it's file:// or http://localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate_ideas", response_model=IdeaResponse)
def generate_ideas(req: IdeaRequest):
    try:
        return gemini_client.generate_ideas(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/summarize_session", response_model=SessionSummaryResponse)
def summarize_session(req: SessionSummaryRequest):
    try:
        return gemini_client.summarize_session(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session")
def save_session(session: SessionLog):
    try:
        db.save_session(session)
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def get_stats():
    try:
         return db.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
