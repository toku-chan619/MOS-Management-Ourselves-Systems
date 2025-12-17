from app.schemas.draft import ExtractedDraft
from app.services.llm import call_llm_json
from app.core.config import settings

SYSTEM_PROMPT = f"""
You are an assistant that extracts actionable tasks from a user's message.
Return ONLY valid JSON.

Rules:
- Output schema: {{
  "tasks": [{{"temp_id": "...", "parent_temp_id": null or "...", "title": "...", "description": "...",
             "project_suggestion": null or "...",
             "due_date": "YYYY-MM-DD" or null,
             "due_time": "HH:MM:SS" or null,
             "priority": "low|normal|high|urgent",
             "status": "backlog|doing|waiting",
             "assumptions": [...],
             "questions": [...],
             "confidence": 0.0-1.0
  }}],
  "questions": [...]
}}
- Prefer due_date (date). due_time is optional extra detail.
- Use parent_temp_id to represent hierarchy. Keep depth <= 3.
- If unclear, put due_date=null and add a short question.
PromptVersion: {settings.PROMPT_VERSION}
""".strip()

async def extract_draft(user_text: str) -> ExtractedDraft:
    raw = await call_llm_json(SYSTEM_PROMPT, user_text)
    # ここでPydantic検証（壊れてたら例外→リトライ/フォールバック）
    return ExtractedDraft.model_validate(raw)
