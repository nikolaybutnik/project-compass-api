from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


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
    messages: List[dict]
    tools: List[dict] = []
    tool_choice: str = "auto"


class ProjectRequest(BaseModel):
    userId: str
    title: str
    description: Optional[str] = None
    status: str = "planning"
    kanban: Optional[dict] = None


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# date objects are Firestore Timestamps stored as dicts
class KanbanTask(BaseModel):
    id: str
    columnId: str
    title: str
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    dueDate: Optional[dict] = None
    tags: Optional[List[str]] = None
    createdAt: dict
    updatedAt: dict


class KanbanColumn(BaseModel):
    id: str
    title: str
    tasks: List[KanbanTask] = []
    taskLimit: Optional[int] = None


class Kanban(BaseModel):
    columns: List[KanbanColumn]
    columnLimit: Optional[int] = None
    totalTaskLimit: Optional[int] = None


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"
