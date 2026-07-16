from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger
from config import DB_PATH
from models import Base

DATABASE_URL = f"sqlite:///{DB_PATH}"

logger.info(f"Database URL: {DATABASE_URL}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # Set to True for SQL debug logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all tables."""
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")

def get_db():
    """Get database session (for dependency injection in FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
