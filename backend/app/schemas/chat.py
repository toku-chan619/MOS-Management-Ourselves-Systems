from pydantic import BaseModel

class ChatPostIn(BaseModel):
    content: str
