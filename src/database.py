# === File: src/database.py ===

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_CONNECTION_STRING
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
if not DATABASE_CONNECTION_STRING:
    raise ValueError("DATABASE_CONNECTION_STRING environment variable is required")

try:
    engine = create_engine(
        DATABASE_CONNECTION_STRING,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,    # Recycle connections every 5 minutes
        echo=False           # Set to True for SQL query logging
    )
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

def get_db():
    """
    Dependency function to get database session.
    Used by FastAPI endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_tables():
    """
    Create all tables defined in models.
    Call this function to initialize the database schema.
    """
    try:
        # Import models to ensure they are registered with Base
        from src.models import (
            FacebookAccount, 
            ApiCache, 
            ConversationHistory, 
            PromptVersion, 
            CampaignPerformanceData
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise

def check_connection():
    """
    Test database connection.
    Returns True if connection is successful, False otherwise.
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
