"""Application configuration."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str
    api_key: str
    webhook_base_url: str
    
    # Database
    database_url: str
    redis_url: str
    
    # McLeod LoadMaster
    mcleod_api_url: str
    mcleod_api_token: str
    mcleod_company_id: str
    
    # Terminal49
    terminal49_api_key: str
    terminal49_webhook_secret: str
    
    # QuickBooks
    quickbooks_client_id: str
    quickbooks_client_secret: str
    quickbooks_realm_id: str
    quickbooks_redirect_uri: str
    quickbooks_environment: str = "sandbox"
    
    # Anthropic Claude
    anthropic_api_key: str
    
    # Notifications
    sendgrid_api_key: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    # Sentry
    sentry_dsn: Optional[str] = None
    
    # Billing Configuration
    default_per_diem_rate: float = 100.0
    default_demurrage_rate: float = 150.0
    default_detention_rate: float = 125.0
    default_free_days: int = 3
    
    # Sync Intervals (minutes)
    mcleod_sync_interval: int = 15
    alert_check_interval: int = 60
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

