from pydantic import BaseModel


class ChatRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[dict]
    tools: list[dict] = []
    tool_choice: str = "auto"
