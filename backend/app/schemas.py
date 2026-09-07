from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator

from .models import BookStatus, ShelfRole


# ---------- Auth ----------
class SignupIn(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_rules(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Books ----------
class BookIn(BaseModel):
    title: str
    author: str
    status: BookStatus = BookStatus.WANT_TO_READ
    total_pages: Optional[int] = None
    rating: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("This field cannot be blank")
        return v.strip()

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v):
        if v is not None and not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("total_pages")
    @classmethod
    def pages_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Total pages must be a positive number")
        return v


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    status: Optional[BookStatus] = None
    total_pages: Optional[int] = None
    rating: Optional[int] = None
    notes: Optional[str] = None


class ProgressIn(BaseModel):
    current_page: int


class BookOut(BaseModel):
    id: str
    owner_id: str
    title: str
    author: str
    status: BookStatus
    total_pages: Optional[int]
    current_page: Optional[int]
    rating: Optional[int]
    notes: Optional[str]
    finished_date: Optional[datetime]
    created_at: datetime
    is_lent: bool = False
    lent_to_email: Optional[str] = None
    owner_email: Optional[str] = None
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedBooks(BaseModel):
    items: List[BookOut]
    total: int
    page: int
    page_size: int


# ---------- Catalog (book pool) ----------
class CatalogBookOut(BaseModel):
    id: str
    title: str
    author: str
    genre: Optional[str]
    total_pages: Optional[int]
    description: Optional[str]
    cover_color: Optional[str]
    in_library: bool = False

    class Config:
        from_attributes = True


class PaginatedCatalog(BaseModel):
    items: List[CatalogBookOut]
    total: int
    page: int
    page_size: int
    genres: List[str]


# ---------- Shelves ----------
class ShelfIn(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def not_blank(cls, v):
        if not v.strip():
            raise ValueError("Shelf name cannot be blank")
        return v.strip()


class ShareIn(BaseModel):
    email: EmailStr
    role: ShelfRole

    @field_validator("role")
    @classmethod
    def role_valid(cls, v):
        if v == ShelfRole.OWNER:
            raise ValueError("Cannot grant owner role via sharing")
        return v


class RoleUpdateIn(BaseModel):
    role: ShelfRole


class CollaboratorOut(BaseModel):
    user_id: str
    name: str
    email: str
    role: ShelfRole


class ShelfOut(BaseModel):
    id: str
    owner_id: str
    owner_email: str
    name: str
    created_at: datetime
    book_count: int
    my_role: ShelfRole


class SharedShelfOut(ShelfOut):
    pass


# ---------- Lending ----------
class LendIn(BaseModel):
    borrower_email: EmailStr


# ---------- Activity ----------
class ActivityOut(BaseModel):
    id: str
    event_type: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Dashboard ----------
class DashboardOut(BaseModel):
    counts_by_status: dict
    finished_this_year: int
    average_rating: Optional[float]
    top_shelf: Optional[str]
    books_lent_out: int
    shelves_shared_with_me: int
    recent_activity: List[ActivityOut]
