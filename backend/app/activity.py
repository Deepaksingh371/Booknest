from sqlalchemy.orm import Session
from . import models
from .ws_manager import manager


async def log_activity(
    db: Session,
    user_id: str,
    event_type: str,
    message: str,
    shelf_id: str | None = None,
    book_id: str | None = None,
    notify_user_ids: set[str] | None = None,
):
    """Persist an activity row in each affected user's own feed and push it
    live to them. `user_id` is the actor; `notify_user_ids` (defaulting to
    just the actor) is everyone entitled to see the event."""
    targets = notify_user_ids if notify_user_ids is not None else {user_id}
    entries = []
    for target in targets:
        entry = models.ActivityLog(
            user_id=target,
            event_type=event_type,
            message=message,
            shelf_id=shelf_id,
            book_id=book_id,
        )
        db.add(entry)
        entries.append(entry)
    db.commit()

    for entry in entries:
        db.refresh(entry)
        await manager.send_to_user(
            entry.user_id,
            {
                "type": "activity",
                "data": {
                    "id": entry.id,
                    "event_type": entry.event_type,
                    "message": entry.message,
                    "created_at": entry.created_at.isoformat(),
                },
            },
        )
    return entries
