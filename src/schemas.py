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

# === Facebook Account Schemas ===

class FacebookAccountBase(BaseModel):
    """Base schema for Facebook account data."""
    user_id: str = Field(..., description="User identifier (e.g., email)")
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
    cache_key: str = Field(..., description="Unique cache identifier")
    data: Dict[str, Any] = Field(..., description="Cached API response data")
    expires_at: datetime = Field(..., description="Cache expiration timestamp")

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
    message: str = Field(..., description="User message")

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
    message: str
    response: str
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

# === Chat API Schemas ===

class ChatRequest(BaseModel):
    """Schema for chat endpoint request."""
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Optional session identifier for conversation continuity")

class ChatResponse(BaseModel):
    """Schema for chat endpoint response."""
    response: str = Field(..., description="AI agent response")
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    user_id: str = Field(..., description="User identifier")

# === Prompt Version Schemas ===

class PromptVersionBase(BaseModel):
    """Base schema for prompt version data."""
    version: str = Field(..., description="Prompt version identifier")
    prompt_text: str = Field(..., description="Full prompt text")
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
