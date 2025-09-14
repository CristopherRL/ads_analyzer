# === File: main.py ===

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from src.database import get_db, test_connection
from src.schemas import (
    HealthResponse, ChatRequest, ChatResponse, SessionInfoResponse, 
    ClearSessionRequest, ClearSessionResponse, ErrorResponse,
    LoginRequest, LoginResponse, UserResponse
)
from src.models import User
from src.agent.agent_executor import DigitalMarketingAgent
from config import DEBUG
from src.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Setup rate limiting
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI application
app = FastAPI(
    title="Digital Marketing Analysis Agent",
    description="AI-powered backend for Facebook Ads performance analysis using LangChain",
    version="1.0.0",
    debug=DEBUG
)

# Add rate limiting to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
@limiter.limit("30/minute")  # 30 health checks per minute
async def health_check(request: Request):
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

# === Authentication Endpoints ===

@app.post("/auth/login", response_model=LoginResponse)
@limiter.limit("10/minute")  # 10 login attempts per minute
async def login(request: Request, login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Simple login endpoint that verifies if email exists in users table.
    For MVP: only checks if email exists, no password validation yet.
    """
    try:
        logger.info(f"Login attempt for email: {login_data.email}")
        
        # Check if user exists in database
        user = db.query(User).filter(
            User.email == login_data.email,
            User.is_active == True
        ).first()
        
        if user:
            logger.info(f"Successful login for user: {user.email}")
            return LoginResponse(
                success=True,
                message="Login successful",
                user=UserResponse(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    password=None,  # Never return password
                    is_active=user.is_active,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                ),
                access_token=f"user_{user.id}_{user.email}"  # Simple token for MVP
            )
        else:
            logger.warning(f"Login failed - user not found: {login_data.email}")
            return LoginResponse(
                success=False,
                message="User not found or inactive",
                user=None,
                access_token=None
            )
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )

@app.get("/auth/verify/{email}")
@limiter.limit("20/minute")  # 20 verification attempts per minute
async def verify_user(request: Request, email: str, db: Session = Depends(get_db)):
    """
    Verify if a user email exists in the system.
    Useful for frontend to check if user can login.
    """
    try:
        user = db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()
        
        return {
            "email": email,
            "exists": user is not None,
            "user_id": user.id if user else None
        }
        
    except Exception as e:
        logger.error(f"User verification error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )

# === Chat Endpoints ===

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")  # 20 chat messages per minute
async def chat_with_agent(request: Request, chat_request: ChatRequest):
    """
    Chat endpoint for conversation with the Digital Marketing Agent.
    Processes user messages and returns AI agent responses.
    """
    try:
        logger.info(f"Chat request from user {chat_request.user_id}")
        
        # Create or get agent instance
        agent = DigitalMarketingAgent(
            user_id=chat_request.user_id,
            session_id=chat_request.session_id
        )
        
        # Process message with agent
        response_text = agent.process_message(chat_request.message)
        
        # Return response
        return ChatResponse(
            response=response_text,
            session_id=agent.session_id,
            user_id=chat_request.user_id
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )

@app.get("/chat/session/{session_id}", response_model=SessionInfoResponse)
@limiter.limit("30/minute")  # 30 session info requests per minute
async def get_session_info(request: Request, session_id: str):
    """
    Get information about a specific chat session.
    """
    try:
        logger.info(f"Getting session info for {session_id}")
        
        # Extract user_id from session_id (format: timestamp_userid)
        if "_" in session_id:
            user_id = "_".join(session_id.split("_")[1:]).replace("_at_", "@").replace("_", ".")
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID format"
            )
        
        # Create agent to get session info
        agent = DigitalMarketingAgent(
            user_id=user_id,
            session_id=session_id
        )
        
        # Get session information
        session_info = agent.get_session_info()
        
        return SessionInfoResponse(
            user_id=session_info["user_id"],
            session_id=session_info["session_id"],
            message_count=session_info["message_count"],
            has_summary=session_info["has_summary"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving session information: {str(e)}"
        )

@app.delete("/chat/session/{session_id}", response_model=ClearSessionResponse)
@limiter.limit("10/minute")  # 10 session clear requests per minute
async def clear_session(request: Request, session_id: str):
    """
    Clear a specific chat session.
    """
    try:
        logger.info(f"Clearing session {session_id}")
        
        # Extract user_id from session_id
        if "_" in session_id:
            user_id = "_".join(session_id.split("_")[1:]).replace("_at_", "@").replace("_", ".")
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid session ID format"
            )
        
        # Create agent and clear session
        agent = DigitalMarketingAgent(
            user_id=user_id,
            session_id=session_id
        )
        
        agent.clear_session()
        
        return ClearSessionResponse(
            success=True,
            message=f"Session {session_id} cleared successfully",
            cleared_sessions=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing session: {str(e)}"
        )

@app.post("/chat/clear", response_model=ClearSessionResponse)
@limiter.limit("5/minute")  # 5 clear all sessions requests per minute
async def clear_user_sessions(request: Request, clear_request: ClearSessionRequest):
    """
    Clear all sessions for a specific user or a specific session.
    """
    try:
        logger.info(f"Clear sessions request for user {clear_request.user_id}")
        
        if clear_request.session_id:
            # Clear specific session
            agent = DigitalMarketingAgent(
                user_id=clear_request.user_id,
                session_id=clear_request.session_id
            )
            agent.clear_session()
            
            return ClearSessionResponse(
                success=True,
                message=f"Session {clear_request.session_id} cleared successfully",
                cleared_sessions=1
            )
        else:
            # Clear all sessions for user (placeholder - would need database query)
            # For now, we'll return a message indicating this feature needs implementation
            return ClearSessionResponse(
                success=False,
                message="Clearing all user sessions not yet implemented. Please specify a session_id.",
                cleared_sessions=0
            )
        
    except Exception as e:
        logger.error(f"Error clearing user sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing sessions: {str(e)}"
        )

# === Future Endpoints (Placeholders) ===
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