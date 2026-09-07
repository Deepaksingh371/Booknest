import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_MAX_AGE = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")) * 24 * 60 * 60


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/auth",
    )


def _issue_tokens(db: Session, user: models.User, response: Response) -> schemas.TokenOut:
    access_token = security.create_access_token(user.id)
    refresh_token, expires_at = security.create_refresh_token(user.id)
    db.add(models.RefreshToken(
        user_id=user.id,
        token_hash=security.hash_token(refresh_token),
        expires_at=expires_at,
    ))
    db.commit()
    _set_refresh_cookie(response, refresh_token)
    return schemas.TokenOut(access_token=access_token, user=schemas.UserOut.model_validate(user))


@router.post("/signup", response_model=schemas.TokenOut, status_code=status.HTTP_201_CREATED)
def signup(payload: schemas.SignupIn, response: Response, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=security.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_tokens(db, user, response)


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return _issue_tokens(db, user, response)


@router.post("/refresh", response_model=schemas.TokenOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    """Rotates the refresh token: the old one is revoked and a new pair is
    issued. This limits the blast radius if a refresh token is ever stolen -
    reuse of a revoked token is detectable."""
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided")

    user_id = security.decode_refresh_token(raw_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    token_hash = security.hash_token(raw_token)
    stored = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == token_hash
    ).first()
    if not stored or stored.revoked or stored.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is no longer valid")

    stored.revoked = True
    db.commit()

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")

    return _issue_tokens(db, user, response)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token:
        token_hash = security.hash_token(raw_token)
        stored = db.query(models.RefreshToken).filter(
            models.RefreshToken.token_hash == token_hash
        ).first()
        if stored:
            stored.revoked = True
            db.commit()
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/auth")


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
