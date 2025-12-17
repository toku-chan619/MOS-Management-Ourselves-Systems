from pydantic import BaseModel, Field
from datetime import date, time
from typing import Literal, Optional

TaskStatus = Literal["backlog","doing","waiting","done","canceled"]
TaskPriority = Literal["low","normal","high","urgent"]

class ExtractedTask(BaseModel):
    temp_id: str = Field(min_length=1)
    parent_temp_id: Optional[str] = None

    title: str
    description: str = ""

    project_suggestion: Optional[str] = None

    due_date: Optional[date] = None
    due_time: Optional[time] = None

    priority: TaskPriority = "normal"
    status: Literal["backlog","doing","waiting"] = "backlog"

    assumptions: list[str] = []
    questions: list[str] = []
    confidence: float = Field(ge=0, le=1)

class ExtractedDraft(BaseModel):
    tasks: list[ExtractedTask] = []
    questions: list[str] = []
