from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://app:app@postgres:5432/activity"
    jwt_secret: str = "change-me-in-prod"
    jwt_ttl_minutes: int = 15
    z_threshold: float = 3.0 
    z_window_days: int = 7
    forecast_horizon_max: int = 14
    mape_target: float = 8.0
    season_period: int = 7
    holidays: str = "2026-01-01,2026-05-01,2026-05-09,2026-06-12,2026-11-04"
    cors_origins: list[str] = ["http://localhost"]   
    
settings = Settings()