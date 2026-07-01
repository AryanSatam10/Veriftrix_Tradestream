from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "TradeStream AI"
    VERSION: str = "2.0.0"
    
    # Database
    DATABASE_URL: str
    
    # External APIs
    MARKET_DATA_API_URL: str
    MARKET_DATA_API_KEY: str
    
    # Security (For future JWT implementation)
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Initialize global settings
settings = Settings()