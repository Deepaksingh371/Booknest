import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, ForeignKey, DateTime, Enum, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from .database import Base


def gen_id():
    return str(uuid.uuid4())


class BookStatus(str, enum.Enum):
    WANT_TO_READ = "want_to_read"
    READING = "reading"
    FINISHED = "finished"


class ShelfRole(str, enum.Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    books = relationship("Book", back_populates="owner", cascade="all, delete-orphan")
    shelves = relationship("Shelf", back_populates="owner", cascade="all, delete-orphan")


class Book(Base):
    __tablename__ = "books"

    id = Column(String, primary_key=True, default=gen_id)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    status = Column(Enum(BookStatus), nullable=False, default=BookStatus.WANT_TO_READ)
    total_pages = Column(Integer, nullable=True)
    current_page = Column(Integer, nullable=True, default=0)
    rating = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    finished_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="books")
    shelf_links = relationship("ShelfBook", back_populates="book", cascade="all, delete-orphan")
    lending = relationship("Lending", back_populates="book", uselist=False, cascade="all, delete-orphan")


class Shelf(Base):
    __tablename__ = "shelves"

    id = Column(String, primary_key=True, default=gen_id)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="shelves")
    book_links = relationship("ShelfBook", back_populates="shelf", cascade="all, delete-orphan")
    shares = relationship("ShelfShare", back_populates="shelf", cascade="all, delete-orphan")


class ShelfBook(Base):
    """Many-to-many join between shelves and books."""
    __tablename__ = "shelf_books"
    __table_args__ = (UniqueConstraint("shelf_id", "book_id", name="uq_shelf_book"),)

    id = Column(String, primary_key=True, default=gen_id)
    shelf_id = Column(String, ForeignKey("shelves.id"), nullable=False, index=True)
    book_id = Column(String, ForeignKey("books.id"), nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    shelf = relationship("Shelf", back_populates="book_links")
    book = relationship("Book", back_populates="shelf_links")


class ShelfShare(Base):
    """A user's role on a shelf that is not theirs. Owner is implicit via Shelf.owner_id."""
    __tablename__ = "shelf_shares"
    __table_args__ = (UniqueConstraint("shelf_id", "user_id", name="uq_shelf_user"),)

    id = Column(String, primary_key=True, default=gen_id)
    shelf_id = Column(String, ForeignKey("shelves.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(Enum(ShelfRole), nullable=False, default=ShelfRole.VIEWER)
    created_at = Column(DateTime, default=datetime.utcnow)

    shelf = relationship("Shelf", back_populates="shares")
    user = relationship("User")


class Lending(Base):
    __tablename__ = "lending"

    id = Column(String, primary_key=True, default=gen_id)
    book_id = Column(String, ForeignKey("books.id"), nullable=False, unique=True, index=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    borrower_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    lent_at = Column(DateTime, default=datetime.utcnow)
    returned_at = Column(DateTime, nullable=True)

    book = relationship("Book", back_populates="lending")


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    message = Column(String, nullable=False)
    shelf_id = Column(String, ForeignKey("shelves.id"), nullable=True)
    book_id = Column(String, ForeignKey("books.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class CatalogBook(Base):
    """A shared, curated pool of books any user can browse and add a copy of
    to their own library. Adding one creates an independent `Book` row owned
    by that user - the catalog entry itself is never owned by anyone and
    isn't affected by what users do with their copies."""
    __tablename__ = "catalog_books"

    id = Column(String, primary_key=True, default=gen_id)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    genre = Column(String, nullable=True, index=True)
    total_pages = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    cover_color = Column(String, nullable=True)  # hex accent used by the UI


class RefreshToken(Base):
    """Stored so refresh tokens can be revoked/rotated server-side."""
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
