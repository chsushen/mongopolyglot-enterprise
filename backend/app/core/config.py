from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import os


class Settings(BaseSettings):
    PROJECT_NAME: str = "MongoPolyglot Enterprise"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # MongoDB Config
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "mongopolyglot_db")
    USE_MOCK_SANDBOX: bool = os.getenv("USE_MOCK_SANDBOX", "true").lower() in ("true", "1", "yes")

    # SQL Relational Database Config (SQLite / MySQL abstraction)
    SQL_DB_PATH: str = os.getenv("SQL_DB_PATH", "/Users/chundurisushen/.gemini/antigravity/scratch/mongopolyglot-enterprise/polyglot_relational.db")

    model_config = ConfigDict(case_sensitive=True)


settings = Settings()
