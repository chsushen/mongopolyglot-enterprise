import logging
from typing import Optional, Any

from motor.motor_asyncio import AsyncIOMotorClient
import mongomock_motor

from .config import settings

logger = logging.getLogger(__name__)


class MongoDBManager:
    """Manage real MongoDB and explicitly requested mock connections."""

    def __init__(self):
        self._client: Optional[Any] = None
        self._db: Optional[Any] = None
        self._is_mock: bool = False

    async def connect(self, force_mock: Optional[bool] = None) -> Any:
        use_mock = (
            settings.USE_MOCK_SANDBOX
            if force_mock is None
            else force_mock
        )

        if self._client is not None:
            await self.disconnect()

        if use_mock:
            logger.info("Initializing explicit MongoDB mock sandbox.")
            self._client = mongomock_motor.AsyncMongoMockClient()
            self._db = self._client[settings.MONGODB_DB_NAME]
            self._is_mock = True
            return self._db

        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
            appname="MongoPolyglot Enterprise",
        )

        try:
            await client.admin.command("ping")

            self._client = client
            self._db = client[settings.MONGODB_DB_NAME]
            self._is_mock = False

            logger.info(
                "Connected to real MongoDB database: %s",
                settings.MONGODB_DB_NAME,
            )
            return self._db

        except Exception as exc:
            client.close()
            self._client = None
            self._db = None
            self._is_mock = False

            logger.error(
                "Real MongoDB connection failed. Error type: %s",
                type(exc).__name__,
            )
            raise RuntimeError(
                "Could not connect to MongoDB. Check the URI, "
                "database credentials, network access and Atlas configuration."
            ) from exc

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            self._is_mock = False
            logger.info("MongoDB connection closed.")

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
