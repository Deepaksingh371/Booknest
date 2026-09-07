from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..activity import log_activity

router = APIRouter(prefix="/books", tags=["books"])


def _serialize(book: models.Book, db: Session) -> schemas.BookOut:
    out = schemas.BookOut.model_validate(book)
    active_lending = (
        db.query(models.Lending)
        .filter(models.Lending.book_id == book.id, models.Lending.returned_at.is_(None))
        .first()
    )
    if active_lending:
        borrower = db.query(models.User).filter(models.User.id == active_lending.borrower_id).first()
        out.is_lent = True
        out.lent_to_email = borrower.email if borrower else None
    return out


@router.get("", response_model=schemas.PaginatedBooks)
def list_books(
    status: Optional[models.BookStatus] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(rating|title|created_at)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.Book).filter(models.Book.owner_id == current_user.id)

    if status is not None:
        q = q.filter(models.Book.status == status)

    if search:
        like = f"%{search}%"
        q = q.filter(or_(models.Book.title.ilike(like), models.Book.author.ilike(like)))

    sort_col = getattr(models.Book, sort_by)
    q = q.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return schemas.PaginatedBooks(
        items=[_serialize(b, db) for b in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=schemas.BookOut, status_code=201)
async def create_book(
    payload: schemas.BookIn,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    book = models.Book(owner_id=current_user.id, **payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    await log_activity(db, current_user.id, "book_added", f'Added "{book.title}"', book_id=book.id)
    return _serialize(book, db)


def _get_owned_book(book_id: str, current_user: models.User, db: Session) -> models.Book:
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this book")
    return book


@router.get("/{book_id}", response_model=schemas.BookOut)
def get_book(book_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _get_owned_book(book_id, current_user, db)
    return _serialize(book, db)


@router.patch("/{book_id}", response_model=schemas.BookOut)
async def update_book(
    book_id: str,
    payload: schemas.BookUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    book = _get_owned_book(book_id, current_user, db)
    data = payload.model_dump(exclude_unset=True)

    if "rating" in data and data["rating"] is not None and not (1 <= data["rating"] <= 5):
        raise HTTPException(status_code=422, detail="Rating must be between 1 and 5")
    if "total_pages" in data and data["total_pages"] is not None and data["total_pages"] <= 0:
        raise HTTPException(status_code=422, detail="Total pages must be a positive number")

    old_status = book.status
    for field, value in data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)

    if "status" in data and data["status"] != old_status:
        await log_activity(
            db, current_user.id, "status_changed",
            f'"{book.title}" status changed to {book.status.value}', book_id=book.id,
        )
    return _serialize(book, db)


@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _get_owned_book(book_id, current_user, db)
    # Cleaning shelf_links and lending happens automatically via cascade,
    # so deleting a book never leaves orphaned shelf references.
    title = book.title
    db.delete(book)
    db.commit()
    await log_activity(db, current_user.id, "book_deleted", f'Deleted "{title}"')


@router.post("/{book_id}/progress", response_model=schemas.BookOut)
async def log_progress(
    book_id: str,
    payload: schemas.ProgressIn,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    book = _get_owned_book(book_id, current_user, db)

    if book.total_pages is None:
        raise HTTPException(status_code=422, detail="Set total pages before logging progress")
    if payload.current_page < 0:
        raise HTTPException(status_code=422, detail="Current page cannot be negative")
    if payload.current_page > book.total_pages:
        raise HTTPException(status_code=422, detail="Current page cannot exceed total pages")

    book.current_page = payload.current_page
    if book.status != models.BookStatus.FINISHED:
        book.status = models.BookStatus.READING

    just_finished = payload.current_page == book.total_pages and book.status != models.BookStatus.FINISHED
    if payload.current_page == book.total_pages:
        book.status = models.BookStatus.FINISHED
        book.finished_date = datetime.utcnow()

    db.commit()
    db.refresh(book)

    if just_finished:
        await log_activity(db, current_user.id, "status_changed", f'Finished "{book.title}"', book_id=book.id)

    return _serialize(book, db)
