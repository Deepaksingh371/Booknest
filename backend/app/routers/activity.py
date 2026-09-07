from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=list[schemas.ActivityOut])
def get_activity(
    limit: int = Query(30, ge=1, le=200),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.ActivityLog)
        .filter(models.ActivityLog.user_id == current_user.id)
        .order_by(models.ActivityLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return rows
