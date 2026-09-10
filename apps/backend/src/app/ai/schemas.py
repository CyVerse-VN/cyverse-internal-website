from pydantic import BaseModel


class AIMessage(BaseModel):
    role: str
    content: str

