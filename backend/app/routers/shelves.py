from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..activity import log_activity
from ..models import ShelfRole

router = APIRouter(prefix="/shelves", tags=["shelves"])


def _get_shelf_or_404(shelf_id: str, db: Session) -> models.Shelf:
    shelf = db.query(models.Shelf).filter(models.Shelf.id == shelf_id).first()
    if not shelf:
        raise HTTPException(status_code=404, detail="Shelf not found")
    return shelf


def _role_for(shelf: models.Shelf, user: models.User, db: Session) -> Optional[ShelfRole]:
    if shelf.owner_id == user.id:
        return ShelfRole.OWNER
    share = db.query(models.ShelfShare).filter(
        models.ShelfShare.shelf_id == shelf.id, models.ShelfShare.user_id == user.id
    ).first()
    return share.role if share else None


def _require_access(shelf: models.Shelf, user: models.User, db: Session) -> ShelfRole:
    role = _role_for(shelf, user, db)
    if role is None:
        raise HTTPException(status_code=403, detail="You do not have access to this shelf")
    return role


def _require_owner(shelf: models.Shelf, user: models.User, db: Session):
    if _role_for(shelf, user, db) != ShelfRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the shelf owner can do this")


def _collaborator_ids(shelf: models.Shelf, db: Session) -> set[str]:
    ids = {shelf.owner_id}
    shares = db.query(models.ShelfShare).filter(models.ShelfShare.shelf_id == shelf.id).all()
    ids.update(s.user_id for s in shares)
    return ids


def _shelf_out(shelf: models.Shelf, my_role: ShelfRole, db: Session) -> schemas.ShelfOut:
    book_count = db.query(models.ShelfBook).filter(models.ShelfBook.shelf_id == shelf.id).count()
    owner = db.query(models.User).filter(models.User.id == shelf.owner_id).first()
    return schemas.ShelfOut(
        id=shelf.id, owner_id=shelf.owner_id, owner_email=owner.email if owner else "",
        name=shelf.name, created_at=shelf.created_at, book_count=book_count, my_role=my_role,
    )


@router.get("", response_model=list[schemas.ShelfOut])
def list_my_shelves(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    shelves = db.query(models.Shelf).filter(models.Shelf.owner_id == current_user.id).all()
    return [_shelf_out(s, ShelfRole.OWNER, db) for s in shelves]


@router.get("/shared-with-me", response_model=list[schemas.SharedShelfOut])
def shared_with_me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    shares = db.query(models.ShelfShare).filter(models.ShelfShare.user_id == current_user.id).all()
    out = []
    for share in shares:
        shelf = db.query(models.Shelf).filter(models.Shelf.id == share.shelf_id).first()
        if shelf:
            out.append(_shelf_out(shelf, share.role, db))
    return out


@router.post("", response_model=schemas.ShelfOut, status_code=201)
async def create_shelf(payload: schemas.ShelfIn, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    shelf = models.Shelf(owner_id=current_user.id, name=payload.name)
    db.add(shelf)
    db.commit()
    db.refresh(shelf)
    return _shelf_out(shelf, ShelfRole.OWNER, db)


@router.delete("/{shelf_id}", status_code=204)
async def delete_shelf(shelf_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    shelf = _get_shelf_or_404(shelf_id, db)
    _require_owner(shelf, current_user, db)
    collaborators = _collaborator_ids(shelf, db) - {current_user.id}
    # Cascade deletes ShelfBook links and ShelfShare rows - books themselves
    # are untouched since they only ever hold a foreign key FROM the join table.
    db.delete(shelf)
    db.commit()
    if collaborators:
        await log_activity(db, current_user.id, "shelf_deleted", f'Shelf deleted', notify_user_ids=collaborators)


@router.get("/{shelf_id}/books", response_model=list[schemas.BookOut])
def list_shelf_books(shelf_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    shelf = _get_shelf_or_404(shelf_id, db)
    _require_access(shelf, current_user, db)
    links = db.query(models.ShelfBook).filter(models.ShelfBook.shelf_id == shelf_id).all()
    from .books import _serialize
    return [_serialize(link.book, db) for link in links]


@router.post("/{shelf_id}/books/{book_id}", status_code=201)
async def add_book_to_shelf(
    shelf_id: str, book_id: str,
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
):
    shelf = _get_shelf_or_404(shelf_id, db)
    role = _require_access(shelf, current_user, db)
    if role == ShelfRole.VIEWER:
        raise HTTPException(status_code=403, detail="Viewers cannot add books to this shelf")

    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    # Editors may only add books they themselves own (they can't inject someone
    # else's private book onto a shared shelf).
    if book.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only add your own books")

    existing = db.query(models.ShelfBook).filter(
        models.ShelfBook.shelf_id == shelf_id, models.ShelfBook.book_id == book_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Book is already on this shelf")

    db.add(models.ShelfBook(shelf_id=shelf_id, book_id=book_id))
    db.commit()

    collaborators = _collaborator_ids(shelf, db)
    await log_activity(
        db, current_user.id, "shelf_book_added", f'"{book.title}" added to shelf "{shelf.name}"',
        shelf_id=shelf_id, book_id=book_id, notify_user_ids=collaborators,
    )
    return {"ok": True}


@router.delete("/{shelf_id}/books/{book_id}", status_code=204)
async def remove_book_from_shelf(
    shelf_id: str, book_id: str,
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
):
    shelf = _get_shelf_or_404(shelf_id, db)
    role = _require_access(shelf, current_user, db)
    if role == ShelfRole.VIEWER:
        raise HTTPException(status_code=403, detail="Viewers cannot remove books from this shelf")

    link = db.query(models.ShelfBook).filter(
        models.ShelfBook.shelf_id == shelf_id, models.ShelfBook.book_id == book_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Book is not on this shelf")

    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    db.delete(link)
    db.commit()

    collaborators = _collaborator_ids(shelf, db)
    await log_activity(
        db, current_user.id, "shelf_book_removed",
        f'"{book.title if book else "A book"}" removed from shelf "{shelf.name}"',
        shelf_id=shelf_id, notify_user_ids=collaborators,
    )


@router.get("/{shelf_id}/collaborators", response_model=list[schemas.CollaboratorOut])
def list_collaborators(shelf_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    shelf = _get_shelf_or_404(shelf_id, db)
    _require_access(shelf, current_user, db)
    shares = db.query(models.ShelfShare).filter(models.ShelfShare.shelf_id == shelf_id).all()
    out = []
    for s in shares:
        u = db.query(models.User).filter(models.User.id == s.user_id).first()
        if u:
            out.append(schemas.CollaboratorOut(user_id=u.id, name=u.name, email=u.email, role=s.role))
    return out


@router.post("/{shelf_id}/share", status_code=201)
async def share_shelf(
    shelf_id: str, payload: schemas.ShareIn,
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
):
    shelf = _get_shelf_or_404(shelf_id, db)
    _require_owner(shelf, current_user, db)

    target = db.query(models.User).filter(models.User.email == payload.email).first()
    if not target:
        raise HTTPException(status_code=404, detail="No registered user with that email")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="You already own this shelf")

    existing = db.query(models.ShelfShare).filter(
        models.ShelfShare.shelf_id == shelf_id, models.ShelfShare.user_id == target.id
    ).first()
    if existing:
        existing.role = payload.role
    else:
        db.add(models.ShelfShare(shelf_id=shelf_id, user_id=target.id, role=payload.role))
    db.commit()

    await log_activity(
        db, current_user.id, "shelf_shared", f'Shared "{shelf.name}" with {target.email} as {payload.role.value}',
        shelf_id=shelf_id, notify_user_ids={target.id, current_user.id},
    )
    return {"ok": True}


@router.patch("/{shelf_id}/collaborators/{user_id}", status_code=200)
async def update_collaborator_role(
    shelf_id: str, user_id: str, payload: schemas.RoleUpdateIn,
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
):
    shelf = _get_shelf_or_404(shelf_id, db)
    _require_owner(shelf, current_user, db)
    if payload.role == ShelfRole.OWNER:
        raise HTTPException(status_code=400, detail="Cannot assign the owner role")

    share = db.query(models.ShelfShare).filter(
        models.ShelfShare.shelf_id == shelf_id, models.ShelfShare.user_id == user_id
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="This user is not a collaborator on this shelf")

    share.role = payload.role
    db.commit()
    await log_activity(
        db, current_user.id, "role_changed", f'Changed a collaborator role on "{shelf.name}"',
        shelf_id=shelf_id, notify_user_ids={user_id, current_user.id},
    )
    return {"ok": True}


@router.delete("/{shelf_id}/collaborators/{user_id}", status_code=204)
async def remove_collaborator(
    shelf_id: str, user_id: str,
    current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db),
):
    shelf = _get_shelf_or_404(shelf_id, db)
    _require_owner(shelf, current_user, db)

    share = db.query(models.ShelfShare).filter(
        models.ShelfShare.shelf_id == shelf_id, models.ShelfShare.user_id == user_id
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="This user is not a collaborator on this shelf")

    db.delete(share)
    db.commit()
    await log_activity(
        db, current_user.id, "collaborator_removed", f'Removed a collaborator from "{shelf.name}"',
        shelf_id=shelf_id, notify_user_ids={user_id, current_user.id},
    )
