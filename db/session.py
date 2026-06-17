from sqlmodel import create_engine, Session, SQLModel
import os
from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.getenv("DB_URL")

engine = create_engine(DATABASE_URL)

def get_session() -> Session:
    with Session(engine) as session:
        yield session