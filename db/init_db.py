from sqlmodel import SQLModel

# Even though it isn't explicitly called in the function, importing Document
# registers its schema with SQLModel.metadata so create_all knows it exists.
from db.models import Document
from db.session import engine


def create_db_and_tables() -> None:
    """Initializes the database and creates all registered tables."""
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    print("Creating database and tables...")
    create_db_and_tables()
    print("Database initialization complete!")