from pydantic import BaseModel


class UserRequest(BaseModel):
    uid: str
    email: str | None = None
    displayName: str | None = None
    photoURL: str | None = None


class ActiveProjectRequest(BaseModel):
    userId: str
    projectId: str


class ChatRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[dict]
    tools: list[dict] = []
    tool_choice: str = "auto"
