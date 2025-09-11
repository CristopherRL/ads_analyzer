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
    cache_key = Column(String(500), nullable=False, comment="Unique cache identifier")
    data = Column(JSON, nullable=False, comment="Cached API response data")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Cache creation timestamp")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="Cache expiration timestamp")
    
    # Foreign key relationship
    facebook_account_id = Column(Integer, nullable=True, comment="Reference to facebook_accounts.id")
    facebook_account = relationship("FacebookAccount", back_populates="api_caches")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_api_cache_account_expires', 'ad_account_id', 'expires_at'),
        Index('idx_api_cache_key', 'cache_key'),
    )
    
    def __repr__(self):
        return f"<ApiCache(id={self.id}, ad_account_id='{self.ad_account_id}', cache_key='{self.cache_key}')>"

class ConversationHistory(Base):
    """
    Model for storing conversation history between users and the AI agent.
    Enables conversation continuity and context management.
    """
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True, comment="User identifier")
    session_id = Column(String(255), nullable=False, index=True, comment="Conversation session identifier")
    message = Column(Text, nullable=False, comment="User message")
    response = Column(Text, nullable=False, comment="AI agent response")
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
    version = Column(String(50), nullable=False, unique=True, comment="Prompt version identifier")
    prompt_text = Column(Text, nullable=False, comment="Full prompt text")
    is_active = Column(Boolean, default=False, comment="Whether this version is currently active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Version creation timestamp")
    
    def __repr__(self):
        return f"<PromptVersion(id={self.id}, version='{self.version}', is_active={self.is_active})>"

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
