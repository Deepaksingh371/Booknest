from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..activity import log_activity
from .books import _serialize

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("", response_model=schemas.PaginatedCatalog)
def browse_catalog(
    search: Optional[str] = None,
    genre: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(models.CatalogBook)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(models.CatalogBook.title.ilike(like), models.CatalogBook.author.ilike(like)))
    if genre:
        q = q.filter(models.CatalogBook.genre == genre)

    total = q.count()
    items = q.order_by(models.CatalogBook.title.asc()).offset((page - 1) * page_size).limit(page_size).all()

    owned = {
        (b.title.strip().lower(), b.author.strip().lower())
        for b in db.query(models.Book).filter(models.Book.owner_id == current_user.id).all()
    }
    out_items = []
    for c in items:
        out = schemas.CatalogBookOut.model_validate(c)
        out.in_library = (c.title.strip().lower(), c.author.strip().lower()) in owned
        out_items.append(out)

    genres = [g[0] for g in db.query(models.CatalogBook.genre).distinct().all() if g[0]]

    return schemas.PaginatedCatalog(
        items=out_items, total=total, page=page, page_size=page_size, genres=sorted(genres)
    )


@router.post("/{catalog_id}/add", response_model=schemas.BookOut, status_code=201)
async def add_from_catalog(
    catalog_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(models.CatalogBook).filter(models.CatalogBook.id == catalog_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="This book isn't in the pool")

    existing = db.query(models.Book).filter(
        models.Book.owner_id == current_user.id,
        models.Book.title.ilike(entry.title),
        models.Book.author.ilike(entry.author),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This book is already in your library")

    book = models.Book(
        owner_id=current_user.id,
        title=entry.title,
        author=entry.author,
        status=models.BookStatus.WANT_TO_READ,
        total_pages=entry.total_pages,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    await log_activity(
        db, current_user.id, "book_added", f'Added "{book.title}" from the book pool', book_id=book.id
    )
    return _serialize(book, db)
