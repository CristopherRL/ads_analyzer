# === File: src/models.py ===

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base

class FacebookAccount(Base):
    """
    Model for Facebook advertising accounts associated with users.
    Stores account information and references to Azure Key Vault secrets.
    """
    __tablename__ = "facebook_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True, comment="User identifier (e.g., email)")
    ad_account_id = Column(String(255), nullable=False, unique=True, comment="Facebook Ad Account ID (e.g., act_123456)")
    account_name = Column(String(255), comment="Human-readable account name")
    key_vault_secret_name = Column(String(255), nullable=False, unique=True, comment="Azure Key Vault secret name for access token")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Account creation timestamp")
    
    # Relationships
    api_caches = relationship("ApiCache", back_populates="facebook_account")
    campaign_data = relationship("CampaignPerformanceData", back_populates="facebook_account")
    
    def __repr__(self):
        return f"<FacebookAccount(id={self.id}, user_id='{self.user_id}', ad_account_id='{self.ad_account_id}')>"

class ApiCache(Base):
    """
    Model for caching API responses to optimize performance.
    Stores cached data from Facebook API calls with expiration.
    """
    __tablename__ = "api_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    ad_account_id = Column(String(255), nullable=False, index=True, comment="Facebook Ad Account ID")
    date_period = Column(String(7), nullable=False, comment="Date period in YYYY-MM format")
    query_hash = Column(String(64), nullable=False, comment="SHA256 hash of the request")
    result_json = Column(JSON, comment="Complete API result in JSONB format")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Cache creation timestamp")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_api_cache_account_period', 'ad_account_id', 'date_period'),
        Index('idx_api_cache_hash', 'query_hash'),
    )
    
    def __repr__(self):
        return f"<ApiCache(id={self.id}, ad_account_id='{self.ad_account_id}', date_period='{self.date_period}')>"

class ConversationHistory(Base):
    """
    Model for storing conversation history between users and the AI agent.
    Enables conversation continuity and context management.
    """
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True, comment="Conversation session identifier")
    user_id = Column(String(255), nullable=False, index=True, comment="User identifier")
    user_prompt = Column(Text, comment="User message/prompt")
    full_prompt_sent = Column(Text, comment="Complete prompt sent to LLM")
    llm_response = Column(Text, comment="LLM response")
    model_params = Column(JSON, comment="Model parameters (temperature, etc.)")
    tokens_used = Column(Integer, comment="Number of tokens used")
    estimated_cost_usd = Column(Integer, comment="Estimated cost in USD (scaled by 1000000)")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), comment="Message timestamp")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_conversation_user_session', 'user_id', 'session_id'),
        Index('idx_conversation_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<ConversationHistory(id={self.id}, user_id='{self.user_id}', session_id='{self.session_id}')>"

class PromptVersion(Base):
    """
    Model for managing different versions of system prompts.
    Allows A/B testing and prompt versioning for the AI agent.
    """
    __tablename__ = "prompt_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_name = Column(String(255), nullable=False, comment="Prompt name identifier")
    version = Column(Integer, nullable=False, comment="Prompt version number")
    prompt_text = Column(Text, comment="Full prompt text")
    is_active = Column(Boolean, default=False, comment="Whether this version is currently active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Version creation timestamp")
    
    # Unique constraint for prompt_name + version combination
    __table_args__ = (
        Index('idx_prompt_name_version', 'prompt_name', 'version', unique=True),
    )
    
    def __repr__(self):
        return f"<PromptVersion(id={self.id}, prompt_name='{self.prompt_name}', version={self.version}, is_active={self.is_active})>"

class CampaignPerformanceData(Base):
    """
    Model for storing historical campaign performance data.
    Enables trend analysis and performance tracking over time.
    """
    __tablename__ = "campaign_performance_data"
    
    id = Column(Integer, primary_key=True, index=True)
    ad_account_id = Column(String(255), nullable=False, index=True, comment="Facebook Ad Account ID")
    campaign_id = Column(String(255), nullable=False, comment="Facebook Campaign ID")
    campaign_name = Column(String(500), comment="Campaign name")
    date = Column(DateTime(timezone=True), nullable=False, comment="Performance data date")
    metrics = Column(JSON, nullable=False, comment="Campaign performance metrics (JSON)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Data creation timestamp")
    
    # Foreign key relationship
    facebook_account_id = Column(Integer, nullable=True, comment="Reference to facebook_accounts.id")
    facebook_account = relationship("FacebookAccount", back_populates="campaign_data")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_campaign_account_date', 'ad_account_id', 'date'),
        Index('idx_campaign_id_date', 'campaign_id', 'date'),
    )
    
    def __repr__(self):
        return f"<CampaignPerformanceData(id={self.id}, ad_account_id='{self.ad_account_id}', campaign_id='{self.campaign_id}')>"
