# === File: main.py ===

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from src.database import get_db, test_connection
from src.schemas import HealthResponse
from config import DEBUG
from src.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Digital Marketing Analysis Agent",
    description="AI-powered backend for Facebook Ads performance analysis using LangChain",
    version="1.0.0",
    debug=DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=dict)
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "message": "Digital Marketing Analysis Agent API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify service and database status.
    Returns service status and database connection status.
    """
    try:
        # Test database connection
        db_connected = test_connection()
        
        return HealthResponse(
            status="ok" if db_connected else "degraded",
            database_connected=db_connected
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )

@app.get("/health/db")
async def database_health_check(db: Session = Depends(get_db)):
    """
    Detailed database health check endpoint.
    Tests database connection and basic operations.
    """
    try:
        # Test basic database operation
        result = db.execute("SELECT 1 as test")
        test_value = result.scalar()
        
        if test_value == 1:
            return {
                "status": "healthy",
                "database": "connected",
                "test_query": "successful"
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Database test query failed"
            )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database unhealthy: {str(e)}"
        )

# Placeholder for future endpoints
# TODO: Add /chat endpoint in Etapa 4
# TODO: Add /accounts endpoint for Facebook account management
# TODO: Add /analytics endpoint for campaign analysis

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
        log_level="info"
    )