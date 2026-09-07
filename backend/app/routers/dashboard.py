from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardOut)
def get_dashboard(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    books = db.query(models.Book).filter(models.Book.owner_id == current_user.id).all()

    counts_by_status = {"want_to_read": 0, "reading": 0, "finished": 0}
    for b in books:
        counts_by_status[b.status.value] += 1

    this_year = datetime.utcnow().year
    finished_this_year = sum(
        1 for b in books if b.finished_date and b.finished_date.year == this_year
    )

    rated = [b.rating for b in books if b.rating is not None]
    average_rating = round(sum(rated) / len(rated), 2) if rated else None

    shelves = db.query(models.Shelf).filter(models.Shelf.owner_id == current_user.id).all()
    top_shelf = None
    top_count = -1
    for shelf in shelves:
        count = db.query(models.ShelfBook).filter(models.ShelfBook.shelf_id == shelf.id).count()
        if count > top_count:
            top_count = count
            top_shelf = shelf.name if count > 0 else top_shelf

    books_lent_out = db.query(models.Lending).filter(
        models.Lending.owner_id == current_user.id, models.Lending.returned_at.is_(None)
    ).count()

    shelves_shared_with_me = db.query(models.ShelfShare).filter(
        models.ShelfShare.user_id == current_user.id
    ).count()

    recent_activity = (
        db.query(models.ActivityLog)
        .filter(models.ActivityLog.user_id == current_user.id)
        .order_by(models.ActivityLog.created_at.desc())
        .limit(10)
        .all()
    )

    return schemas.DashboardOut(
        counts_by_status=counts_by_status,
        finished_this_year=finished_this_year,
        average_rating=average_rating,
        top_shelf=top_shelf,
        books_lent_out=books_lent_out,
        shelves_shared_with_me=shelves_shared_with_me,
        recent_activity=recent_activity,
    )
