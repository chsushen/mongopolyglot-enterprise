from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MongoPolyglot Enterprise"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # MongoDB configuration
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "mongopolyglot_db"
    USE_MOCK_SANDBOX: bool = True

    # SQLite relational database configuration
    SQL_DB_PATH: str = "./polyglot_relational.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
