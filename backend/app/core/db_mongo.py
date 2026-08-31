import logging
from typing import Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import mongomock_motor
from .config import settings

logger = logging.getLogger(__name__)


class MongoDBManager:
    """Manages AsyncIO MongoDB client connections, databases, and transactions."""

    def __init__(self):
        self._client: Optional[Any] = None
        self._db: Optional[Any] = None
        self._is_mock: bool = False

    async def connect(self, force_mock: Optional[bool] = None) -> Any:
        use_mock = settings.USE_MOCK_SANDBOX if force_mock is None else force_mock

        if use_mock:
            logger.info("Initializing in-process Motor Mock Sandbox (mongomock-motor)...")
            self._client = mongomock_motor.AsyncMongoMockClient()
            self._db = self._client[settings.MONGODB_DB_NAME]
            self._is_mock = True
            return self._db

        try:
            logger.info("Connecting to live MongoDB cluster: %s", settings.MONGODB_URI)
            client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
            )
            # Test connection ping
            await client.admin.command("ping")
            self._client = client
            self._db = self._client[settings.MONGODB_DB_NAME]
            self._is_mock = False
            logger.info("Connected successfully to MongoDB database: %s", settings.MONGODB_DB_NAME)
            return self._db
        except Exception as exc:
            logger.warning(
                "Live MongoDB connection unavailable (%s). Activating in-process Motor Sandbox fallback.",
                exc,
            )
            self._client = mongomock_motor.AsyncMongoMockClient()
            self._db = self._client[settings.MONGODB_DB_NAME]
            self._is_mock = True
            return self._db

    async def disconnect(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB client connection closed.")

    @property
    def client(self) -> Any:
        if self._client is None:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return self._client

    @property
    def db(self) -> Any:
        if self._db is None:
            raise RuntimeError("Database not initialized. Call connect() first.")
        return self._db

    @property
    def is_mock(self) -> bool:
        return self._is_mock


mongo_manager = MongoDBManager()
