"""
Seed script for BookNest.

Creates two test users with sample books, a shelf shared with one user as
editor and another share as viewer, and one active lending - so the sharing
and borrowing flows can be tested immediately after a clean clone.

Run with:  python seed.py   (from the backend/ directory, venv activated)
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.database import Base, engine, SessionLocal
from app import models
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

EMAIL_A = "alice@example.com"
EMAIL_B = "bob@example.com"
EMAIL_C = "carol@example.com"
PASSWORD = "Password123"


def get_or_create_user(name, email):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return user
    user = models.User(name=name, email=email, password_hash=hash_password(PASSWORD))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


CATALOG = [
    ("Dune", "Frank Herbert", "Sci-Fi", 412, "A desert planet, a doomed house, and a prophecy.", "#e07a3f"),
    ("Project Hail Mary", "Andy Weir", "Sci-Fi", 496, "A lone astronaut wakes up with no memory and a mission to save Earth.", "#2f6f9f"),
    ("The Hobbit", "J.R.R. Tolkien", "Fantasy", 310, "A reluctant burglar sets out on an adventure with thirteen dwarves.", "#4c7a3f"),
    ("Klara and the Sun", "Kazuo Ishiguro", "Sci-Fi", 303, "An artificial friend observes the world with quiet devotion.", "#c9497a"),
    ("Foundation", "Isaac Asimov", "Sci-Fi", 255, "A mathematician predicts the fall of an empire - and plans for what comes after.", "#7a5ac9"),
    ("Circe", "Madeline Miller", "Fantasy", 393, "A witch, exiled to an island, finds her own kind of power.", "#c96b3f"),
    ("The Song of Achilles", "Madeline Miller", "Fantasy", 416, "The Trojan War, retold through the eyes of Patroclus.", "#b23f5c"),
    ("Educated", "Tara Westover", "Memoir", 334, "A woman raised off the grid claws her way to a Cambridge PhD.", "#3f8fc9"),
    ("Atomic Habits", "James Clear", "Non-Fiction", 320, "Small, consistent changes and how they compound into big results.", "#3fa172"),
    ("Sapiens", "Yuval Noah Harari", "Non-Fiction", 443, "A sweeping history of how Homo sapiens came to rule the planet.", "#c9973f"),
    ("The Silent Patient", "Alex Michaelides", "Thriller", 336, "A woman stops speaking the day she's accused of murdering her husband.", "#8f3f8f"),
    ("Gone Girl", "Gillian Flynn", "Thriller", 419, "A marriage, a disappearance, and nothing is quite what it seems.", "#3f3f8f"),
    ("The Midnight Library", "Matt Haig", "Fiction", 288, "Between life and death, a library of every path not taken.", "#5c3f8f"),
    ("Where the Crawdads Sing", "Delia Owens", "Fiction", 384, "A girl raised alone in the marsh becomes the center of a murder trial.", "#3f8f6b"),
    ("Mexican Gothic", "Silvia Moreno-Garcia", "Horror", 301, "A crumbling mansion, a strange family, and a secret that won't stay buried.", "#8f3f3f"),
]


def seed_catalog(db):
    if db.query(models.CatalogBook).count() > 0:
        return
    for title, author, genre, pages, desc, color in CATALOG:
        db.add(models.CatalogBook(
            title=title, author=author, genre=genre, total_pages=pages,
            description=desc, cover_color=color,
        ))
    db.commit()


def main():
    seed_catalog(db)
    alice = get_or_create_user("Alice Anderson", EMAIL_A)
    bob = get_or_create_user("Bob Baker", EMAIL_B)
    carol = get_or_create_user("Carol Chen", EMAIL_C)

    if db.query(models.Book).filter(models.Book.owner_id == alice.id).count() == 0:
        b1 = models.Book(owner_id=alice.id, title="Dune", author="Frank Herbert",
                          status=models.BookStatus.FINISHED, total_pages=412,
                          current_page=412, rating=5, finished_date=datetime.utcnow())
        b2 = models.Book(owner_id=alice.id, title="Project Hail Mary", author="Andy Weir",
                          status=models.BookStatus.READING, total_pages=496, current_page=180)
        b3 = models.Book(owner_id=alice.id, title="The Hobbit", author="J.R.R. Tolkien",
                          status=models.BookStatus.WANT_TO_READ, total_pages=310)
        b4 = models.Book(owner_id=alice.id, title="Klara and the Sun", author="Kazuo Ishiguro",
                          status=models.BookStatus.WANT_TO_READ, total_pages=303, rating=None)
        db.add_all([b1, b2, b3, b4])
        db.commit()
        for b in (b1, b2, b3, b4):
            db.refresh(b)

        shelf = models.Shelf(owner_id=alice.id, name="Sci-Fi Favorites")
        db.add(shelf)
        db.commit()
        db.refresh(shelf)

        db.add_all([
            models.ShelfBook(shelf_id=shelf.id, book_id=b1.id),
            models.ShelfBook(shelf_id=shelf.id, book_id=b2.id),
        ])

        # Share the shelf: Bob as editor, Carol as viewer.
        db.add(models.ShelfShare(shelf_id=shelf.id, user_id=bob.id, role=models.ShelfRole.EDITOR))
        db.add(models.ShelfShare(shelf_id=shelf.id, user_id=carol.id, role=models.ShelfRole.VIEWER))
        db.commit()

        # Bob has a book of his own too, so the editor role has something to add.
        bob_book = models.Book(owner_id=bob.id, title="Foundation", author="Isaac Asimov",
                                status=models.BookStatus.WANT_TO_READ, total_pages=255)
        db.add(bob_book)
        db.commit()
        db.refresh(bob_book)

        # Active lending: Alice lends "The Hobbit" to Bob.
        db.add(models.Lending(book_id=b3.id, owner_id=alice.id, borrower_id=bob.id))
        db.commit()

        db.add(models.ActivityLog(user_id=alice.id, event_type="book_added",
                                   message='Added "Dune"'))
        db.commit()

        print("Seed data created.")
    else:
        print("Seed data already present - skipping.")

    print("\nTest accounts (all use password: Password123):")
    print(f"  {EMAIL_A}  (owns the shared shelf, lent 'The Hobbit' to Bob)")
    print(f"  {EMAIL_B}  (editor on the shared shelf, currently borrowing 'The Hobbit')")
    print(f"  {EMAIL_C}  (viewer on the shared shelf)")


if __name__ == "__main__":
    main()
    db.close()
