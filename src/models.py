# === File: src/models.py ===

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Index, ForeignKey, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base

class User(Base):
    """
    Model for application users.
    Stores user information and authentication data.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True, comment="User email address")
    name = Column(String(255), comment="User display name")
    password = Column(String(255), comment="User password (for future authentication)")
    is_active = Column(Boolean, default=True, comment="Whether user account is active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="User creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="User last update timestamp")
    
    # Relationships
    user_facebook_accounts = relationship("UserFacebookAccount", foreign_keys="UserFacebookAccount.user_id", back_populates="user")
    conversations = relationship("ConversationHistory", back_populates="user")
    analysis_results = relationship("AnalysisResult", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}')>"

class FacebookAccount(Base):
    """
    Model for Facebook advertising accounts.
    Stores account information and references to Azure Key Vault secrets.
    Note: user_id removed - use UserFacebookAccount for many-to-many relationship.
    """
    __tablename__ = "facebook_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    ad_account_id = Column(String(255), nullable=False, unique=True, comment="Facebook Ad Account ID (e.g., act_123456)")
    account_name = Column(String(255), comment="Human-readable account name")
    key_vault_secret_name = Column(String(255), nullable=False, unique=True, comment="Azure Key Vault secret name for access token")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Account creation timestamp")
    
    # Relationships
    user_facebook_accounts = relationship("UserFacebookAccount", back_populates="facebook_account")
    campaign_data = relationship("CampaignPerformanceData", back_populates="facebook_account")
    analysis_results = relationship("AnalysisResult", back_populates="facebook_account")
    
    def __repr__(self):
        return f"<FacebookAccount(id={self.id}, ad_account_id='{self.ad_account_id}')>"

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
    
    # Note: facebook_account_id removed - ad_account_id is sufficient for identification
    
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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="Foreign key to users table")
    user_prompt = Column(Text, comment="User message/prompt")
    full_prompt_sent = Column(Text, comment="Complete prompt sent to LLM")
    llm_response = Column(Text, comment="LLM response")
    llm_params = Column(JSON, comment="LLM model parameters (temperature, etc.)")
    tokens_used = Column(Integer, comment="Number of tokens used")
    estimated_cost_usd = Column(DECIMAL(10,4), comment="Estimated cost in USD")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), comment="Message timestamp")
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    
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
    facebook_account_id = Column(Integer, ForeignKey("facebook_accounts.id"), nullable=True, comment="Reference to facebook_accounts.id")
    facebook_account = relationship("FacebookAccount", back_populates="campaign_data")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_campaign_account_date', 'ad_account_id', 'date'),
        Index('idx_campaign_id_date', 'campaign_id', 'date'),
    )
    
    def __repr__(self):
        return f"<CampaignPerformanceData(id={self.id}, ad_account_id='{self.ad_account_id}', campaign_id='{self.campaign_id}')>"

class ModelMapping(Base):
    """
    Model for mapping assigned model names to generic model names.
    Enables cost calculation by mapping specific deployment names to pricing models.
    """
    __tablename__ = "model_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    api_provider = Column(String(50), nullable=False, comment="API provider (e.g., azure_openai, openai)")
    assigned_model_name = Column(String(100), nullable=False, comment="Assigned model name in API (e.g., gpt-4o_analyst)")
    generic_model_name = Column(String(100), nullable=False, comment="Generic model name for pricing (e.g., gpt-4o)")
    is_active = Column(Boolean, default=True, comment="Whether this mapping is active")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Mapping creation timestamp")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_model_mapping_assigned', 'assigned_model_name'),
        Index('idx_model_mapping_generic', 'generic_model_name'),
        Index('idx_model_mapping_provider', 'api_provider'),
        Index('idx_model_mapping_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<ModelMapping(id={self.id}, assigned='{self.assigned_model_name}', generic='{self.generic_model_name}')>"

class ModelPricing(Base):
    """
    Model for storing Azure OpenAI model pricing information.
    Enables cost calculation for token usage tracking.
    """
    __tablename__ = "model_pricing"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False, comment="Model name (e.g., gpt-4-turbo)")
    input_cost_per_1k_tokens = Column(DECIMAL(10,6), nullable=False, comment="Cost per 1000 input tokens in USD")
    output_cost_per_1k_tokens = Column(DECIMAL(10,6), nullable=False, comment="Cost per 1000 output tokens in USD")
    effective_date = Column(DateTime(timezone=True), nullable=False, comment="Date when these prices become effective")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Record creation timestamp")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Record last update timestamp")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_model_pricing_model_date', 'model_name', 'effective_date'),
    )
    
    def __repr__(self):
        return f"<ModelPricing(id={self.id}, model_name='{self.model_name}', effective_date='{self.effective_date}')>"

class UserFacebookAccount(Base):
    """
    Model for many-to-many relationship between users and Facebook accounts.
    Enables multiple users to access the same Facebook account.
    """
    __tablename__ = "user_facebook_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="Foreign key to users table")
    facebook_account_id = Column(Integer, ForeignKey("facebook_accounts.id", ondelete="CASCADE"), nullable=False, comment="Foreign key to facebook_accounts table")
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Assignment timestamp")
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="User who made the assignment")
    is_active = Column(Boolean, default=True, comment="Whether the assignment is active")
    notes = Column(Text, comment="Additional notes about the assignment")
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_facebook_accounts")
    facebook_account = relationship("FacebookAccount", back_populates="user_facebook_accounts")
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])
    
    # Unique constraint and indexes
    __table_args__ = (
        Index('idx_user_facebook_accounts_user_id', 'user_id'),
        Index('idx_user_facebook_accounts_facebook_id', 'facebook_account_id'),
        Index('idx_user_facebook_accounts_active', 'is_active'),
        Index('idx_user_facebook_unique', 'user_id', 'facebook_account_id', unique=True),
    )
    
    def __repr__(self):
        return f"<UserFacebookAccount(id={self.id}, user_id='{self.user_id}', facebook_account_id='{self.facebook_account_id}')>"

class AnalysisResult(Base):
    """
    Model for storing analysis results generated by the LLM.
    Stores complete analysis text and metadata for campaign analysis.
    """
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="Foreign key to users table")
    session_id = Column(String(100), comment="Conversation session identifier")
    analysis_type = Column(String(50), nullable=False, comment="Type of analysis performed")
    facebook_account_id = Column(Integer, ForeignKey("facebook_accounts.id"), nullable=True, comment="Foreign key to facebook_accounts table")
    result_text = Column(Text, nullable=False, comment="Complete analysis text generated by LLM")
    analysis_metadata = Column(JSON, comment="Additional metadata (campaigns analyzed, dates, metrics, etc.)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Analysis creation timestamp")
    
    # Relationships
    user = relationship("User", back_populates="analysis_results")
    facebook_account = relationship("FacebookAccount", back_populates="analysis_results")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_analysis_results_user_id', 'user_id'),
        Index('idx_analysis_results_session_id', 'session_id'),
        Index('idx_analysis_results_type', 'analysis_type'),
        Index('idx_analysis_results_facebook_account', 'facebook_account_id'),
        Index('idx_analysis_results_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, user_id='{self.user_id}', analysis_type='{self.analysis_type}')>"
