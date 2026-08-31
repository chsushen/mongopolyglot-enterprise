import logging
import aiosqlite
from typing import Optional, List, Dict, Any
from .config import settings

logger = logging.getLogger(__name__)


class RelationalSQLManager:
    """Manages Relational SQL Database (SQLite / MySQL syntax compatible) for polyglot benchmarking."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.SQL_DB_PATH

    async def init_schema(self) -> None:
        """Initializes normalized relational schema for e-commerce and restaurants."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            
            # Users
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

            # Accounts (for ACID banking / funds transfer)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    balance REAL NOT NULL,
                    currency TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

            # Products
            await db.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL,
                    stock_quantity INTEGER NOT NULL
                );
            """)

            # Orders
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    order_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_amount REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

            # Order Items (Relational Join table)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    item_id TEXT PRIMARY KEY,
                    order_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(order_id),
                    FOREIGN KEY (product_id) REFERENCES products(product_id)
                );
            """)

            # Restaurants
            await db.execute("""
                CREATE TABLE IF NOT EXISTS restaurants (
                    restaurant_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    borough TEXT NOT NULL,
                    cuisine TEXT NOT NULL,
                    street TEXT NOT NULL,
                    zipcode TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    avg_rating REAL NOT NULL
                );
            """)

            # Indexes for SQL execution comparison
            await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_borough ON restaurants(borough);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_restaurants_cuisine ON restaurants(cuisine);")
            
            await db.commit()
            logger.info("Relational SQL schema initialized at %s", self.db_path)

    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Executes a SELECT query and returns rows as dictionaries."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def execute_write(self, statement: str, params: tuple = ()) -> int:
        """Executes INSERT/UPDATE/DELETE and returns rows affected."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(statement, params)
            await db.commit()
            return cursor.rowcount


sql_manager = RelationalSQLManager()
