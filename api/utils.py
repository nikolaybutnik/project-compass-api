import uuid
from api.models import Kanban, KanbanColumn


def create_default_kanban() -> Kanban:
    """Create the default kanban board structure with standard columns"""
    return Kanban(
        columns=[
            KanbanColumn(id=str(uuid.uuid4()), title="To Do", tasks=[]),
            KanbanColumn(id=str(uuid.uuid4()), title="In Progress", tasks=[]),
            KanbanColumn(id=str(uuid.uuid4()), title="Completed", tasks=[]),
        ]
    )
