# === File: src/schemas.py ===

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

# === Base Schemas ===

class HealthResponse(BaseModel):
    """Schema for health check endpoint response."""
    status: str = Field(default="ok", description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    database_connected: bool = Field(description="Database connection status")

# === User Schemas ===

class UserBase(BaseModel):
    """Base schema for user data."""
    email: str = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User display name")
    password: Optional[str] = Field(None, description="User password (for future authentication)")

class UserCreate(UserBase):
    """Schema for creating a new user."""
    pass

class UserUpdate(BaseModel):
    """Schema for updating user data."""
    name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# === Authentication Schemas ===

class LoginRequest(BaseModel):
    """Schema for login request."""
    email: str = Field(..., description="User email address")

class LoginResponse(BaseModel):
    """Schema for login response."""
    success: bool = Field(..., description="Whether login was successful")
    message: str = Field(..., description="Login result message")
    user: Optional[UserResponse] = Field(None, description="User information if login successful")
    access_token: Optional[str] = Field(None, description="Access token for authenticated requests")

# === Facebook Account Schemas ===

class FacebookAccountBase(BaseModel):
    """Base schema for Facebook account data."""
    user_id: int = Field(..., description="User ID (foreign key to users table)")
    ad_account_id: str = Field(..., description="Facebook Ad Account ID (e.g., act_123456)")
    account_name: Optional[str] = Field(None, description="Human-readable account name")
    key_vault_secret_name: str = Field(..., description="Azure Key Vault secret name for access token")

class FacebookAccountCreate(FacebookAccountBase):
    """Schema for creating a new Facebook account."""
    pass

class FacebookAccountUpdate(BaseModel):
    """Schema for updating Facebook account data."""
    account_name: Optional[str] = None
    key_vault_secret_name: Optional[str] = None

class FacebookAccountResponse(FacebookAccountBase):
    """Schema for Facebook account response."""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# === API Cache Schemas ===

class ApiCacheBase(BaseModel):
    """Base schema for API cache data."""
    ad_account_id: str = Field(..., description="Facebook Ad Account ID")
    date_period: str = Field(..., description="Date period in YYYY-MM format")
    query_hash: str = Field(..., description="SHA256 hash of the request")
    result_json: Optional[Dict[str, Any]] = Field(None, description="Complete API result in JSONB format")

class ApiCacheCreate(ApiCacheBase):
    """Schema for creating new API cache entry."""
    pass

class ApiCacheResponse(ApiCacheBase):
    """Schema for API cache response."""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# === Conversation Schemas ===

class ConversationMessage(BaseModel):
    """Schema for conversation message."""
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Conversation session identifier")
    user_prompt: Optional[str] = Field(None, description="User message/prompt")
    full_prompt_sent: Optional[str] = Field(None, description="Complete prompt sent to LLM")
    llm_response: Optional[str] = Field(None, description="LLM response")
    llm_params: Optional[Dict[str, Any]] = Field(None, description="LLM model parameters")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    estimated_cost_usd: Optional[int] = Field(None, description="Estimated cost in USD (scaled by 1000000)")

class ConversationResponse(BaseModel):
    """Schema for conversation response."""
    response: str = Field(..., description="AI agent response")
    session_id: str = Field(..., description="Conversation session identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")

class ConversationHistoryResponse(BaseModel):
    """Schema for conversation history response."""
    id: int
    user_id: str
    session_id: str
    user_prompt: Optional[str]
    full_prompt_sent: Optional[str]
    llm_response: Optional[str]
    llm_params: Optional[Dict[str, Any]]
    tokens_used: Optional[int]
    estimated_cost_usd: Optional[int]
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

# === Chat API Schemas ===

class ChatRequest(BaseModel):
    """Schema for chat endpoint request."""
    user_id: int = Field(..., description="User ID (foreign key to users table)")
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Optional session identifier for conversation continuity")

class ChatResponse(BaseModel):
    """Schema for chat endpoint response."""
    response: str = Field(..., description="AI agent response")
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    user_id: int = Field(..., description="User ID (foreign key to users table)")

class SessionInfoResponse(BaseModel):
    """Schema for session information response."""
    user_id: int = Field(..., description="User ID (foreign key to users table)")
    session_id: str = Field(..., description="Session identifier")
    message_count: int = Field(..., description="Number of messages in session")
    has_summary: bool = Field(..., description="Whether session has conversation summary")
    created_at: Optional[datetime] = Field(None, description="Session creation timestamp")

class ClearSessionRequest(BaseModel):
    """Schema for clearing session request."""
    user_id: str = Field(..., description="User identifier")
    session_id: Optional[str] = Field(None, description="Optional specific session to clear")

class ClearSessionResponse(BaseModel):
    """Schema for clearing session response."""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Operation result message")
    cleared_sessions: int = Field(..., description="Number of sessions cleared")

# === Prompt Version Schemas ===

class PromptVersionBase(BaseModel):
    """Base schema for prompt version data."""
    prompt_name: str = Field(..., description="Prompt name identifier")
    version: int = Field(..., description="Prompt version number")
    prompt_text: Optional[str] = Field(None, description="Full prompt text")
    is_active: bool = Field(default=False, description="Whether this version is currently active")

class PromptVersionCreate(PromptVersionBase):
    """Schema for creating new prompt version."""
    pass

class PromptVersionUpdate(BaseModel):
    """Schema for updating prompt version."""
    prompt_text: Optional[str] = None
    is_active: Optional[bool] = None

class PromptVersionResponse(PromptVersionBase):
    """Schema for prompt version response."""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# === Campaign Performance Schemas ===

class CampaignPerformanceBase(BaseModel):
    """Base schema for campaign performance data."""
    ad_account_id: str = Field(..., description="Facebook Ad Account ID")
    campaign_id: str = Field(..., description="Facebook Campaign ID")
    campaign_name: Optional[str] = Field(None, description="Campaign name")
    date: datetime = Field(..., description="Performance data date")
    metrics: Dict[str, Any] = Field(..., description="Campaign performance metrics")

class CampaignPerformanceCreate(CampaignPerformanceBase):
    """Schema for creating new campaign performance data."""
    pass

class CampaignPerformanceResponse(CampaignPerformanceBase):
    """Schema for campaign performance response."""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# === Error Schemas ===

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
