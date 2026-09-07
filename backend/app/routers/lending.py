from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..activity import log_activity
from .books import _serialize

router = APIRouter(tags=["lending"])


@router.post("/books/{book_id}/lend", response_model=schemas.BookOut)
async def lend_book(
    book_id: str, payload: schemas.LendIn,
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book or book.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found in your library")

    if payload.borrower_email == current_user.email:
        raise HTTPException(status_code=400, detail="You cannot lend a book to yourself")

    borrower = db.query(models.User).filter(models.User.email == payload.borrower_email).first()
    if not borrower:
        raise HTTPException(status_code=404, detail="No registered user with that email")

    active = db.query(models.Lending).filter(
        models.Lending.book_id == book_id, models.Lending.returned_at.is_(None)
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="This book is already lent out to someone else")

    lending = models.Lending(book_id=book_id, owner_id=current_user.id, borrower_id=borrower.id)
    db.add(lending)
    db.commit()

    await log_activity(
        db, current_user.id, "book_lent", f'Lent "{book.title}" to {borrower.email}',
        book_id=book.id, notify_user_ids={current_user.id, borrower.id},
    )
    return _serialize(book, db)


@router.post("/books/{book_id}/return", response_model=schemas.BookOut)
async def return_book(
    book_id: str,
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book or book.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Book not found in your library")

    active = db.query(models.Lending).filter(
        models.Lending.book_id == book_id, models.Lending.returned_at.is_(None)
    ).first()
    if not active:
        raise HTTPException(status_code=400, detail="This book is not currently lent out")

    active.returned_at = datetime.utcnow()
    db.commit()

    await log_activity(
        db, current_user.id, "book_returned", f'"{book.title}" marked as returned',
        book_id=book.id, notify_user_ids={current_user.id, active.borrower_id},
    )
    return _serialize(book, db)


@router.get("/borrowed", response_model=list[schemas.BookOut])
def borrowed_from_others(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    active_lendings = db.query(models.Lending).filter(
        models.Lending.borrower_id == current_user.id, models.Lending.returned_at.is_(None)
    ).all()
    out = []
    for lending in active_lendings:
        book = db.query(models.Book).filter(models.Book.id == lending.book_id).first()
        if not book:
            continue
        owner = db.query(models.User).filter(models.User.id == lending.owner_id).first()
        serialized = _serialize(book, db)
        serialized.owner_email = owner.email if owner else None
        serialized.owner_name = owner.name if owner else None
        out.append(serialized)
    return out
