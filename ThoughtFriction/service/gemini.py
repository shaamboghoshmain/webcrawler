from google import genai
from google.genai import types
import json
from .config import settings
from .models import IdeaRequest, IdeaResponse, SessionSummaryRequest, SessionSummaryResponse

class GeminiClient:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
             print("Warning: GEMINI_API_KEY not set.")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    def generate_ideas(self, req: IdeaRequest) -> IdeaResponse:
        prompt = f"""
        Topic: {req.topic}
        Goal: {req.goal}
        Hypothesis: {req.hypothesis}
        Uncertainty: {req.uncertainty}
        Constraints: {req.constraints or "None"}
        
        Generate {req.max_bullets} idea bullets, 3 counterpoints, and 3 probing questions.
        Return JSON with keys: bullets (list of strings), counterpoints (list of strings), questions (list of strings).
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=IdeaResponse
                )
            )
            return response.parsed
        except Exception as e:
            print(f"Gemini API Error: {e}")
            # Fallback or re-raise. For MVP, re-raising or returning empty might be okay, but let's return a safe failure.
            raise e

    def summarize_session(self, req: SessionSummaryRequest) -> SessionSummaryResponse:
        prompt = f"""
        Raw Notes: {req.raw_notes}
        AI Used: {req.ai_output_used}
        Final Text (Excerpt): {req.final_text[:2000] if req.final_text else "None"}
        
        Analyze this writing session.
        Return JSON regarding: suggested_title, key_thesis, weak_spots, next_steps.
        Keep it brief and constructive.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                     response_mime_type="application/json",
                     response_schema=SessionSummaryResponse
                )
            )
            return response.parsed
        except Exception as e:
            print(f"Gemini API Error: {e}")
            raise e

gemini_client = GeminiClient()
