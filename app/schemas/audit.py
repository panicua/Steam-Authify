from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_type: str
    actor_id: str
    entity_type: str
    entity_id: int | None = None
    action: str
    payload: dict | None = None
    created_at: datetime
