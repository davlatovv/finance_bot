"""
Database management module using aiosqlite.
Handles connection, schema creation, and data cleanup.
"""
import aiosqlite
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .models import User, Category, Transaction, TransactionType

logger = logging.getLogger(__name__)

# Database file path
DB_PATH = Path(__file__).parent.parent.parent / "data" / "finance_bot.db"

# SQL for creating tables
CREATE_TABLES_SQL = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, name, type)
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    description TEXT,
    raw_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_categories_user_id ON categories(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, created_at);
"""


class Database:
    """Async database manager for finance bot."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Initialize database connection and create tables."""
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        
        # Enable foreign keys
        await self._connection.execute("PRAGMA foreign_keys = ON")
        
        # Create tables
        await self._connection.executescript(CREATE_TABLES_SQL)
        await self._connection.commit()
        
        logger.info(f"Database connected: {self.db_path}")
    
    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")
    
    @property
    def connection(self) -> aiosqlite.Connection:
        """Get active connection."""
        if not self._connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection
    
    # ==================== User Operations ====================
    
    async def get_or_create_user(
        self, 
        telegram_id: int, 
        username: Optional[str] = None,
        first_name: Optional[str] = None
    ) -> User:
        """Get existing user or create new one."""
        cursor = await self.connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return User.from_row(tuple(row))
        
        # Create new user
        cursor = await self.connection.execute(
            """
            INSERT INTO users (telegram_id, username, first_name)
            VALUES (?, ?, ?)
            RETURNING *
            """,
            (telegram_id, username, first_name)
        )
        row = await cursor.fetchone()
        await self.connection.commit()
        
        logger.info(f"New user created: telegram_id={telegram_id}")
        return User.from_row(tuple(row))
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        cursor = await self.connection.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return User.from_row(tuple(row)) if row else None
    
    # ==================== Category Operations ====================
    
    async def create_category(
        self, 
        user_id: int, 
        name: str, 
        type: TransactionType
    ) -> Category:
        """Create new category for user."""
        cursor = await self.connection.execute(
            """
            INSERT INTO categories (user_id, name, type)
            VALUES (?, ?, ?)
            RETURNING *
            """,
            (user_id, name, type.value)
        )
        row = await cursor.fetchone()
        await self.connection.commit()
        
        logger.info(f"Category created: user_id={user_id}, name={name}, type={type.value}")
        return Category.from_row(tuple(row))
    
    async def get_categories(
        self, 
        user_id: int, 
        type: Optional[TransactionType] = None
    ) -> list[Category]:
        """Get all categories for user, optionally filtered by type."""
        if type:
            cursor = await self.connection.execute(
                "SELECT * FROM categories WHERE user_id = ? AND type = ? ORDER BY name",
                (user_id, type.value)
            )
        else:
            cursor = await self.connection.execute(
                "SELECT * FROM categories WHERE user_id = ? ORDER BY type, name",
                (user_id,)
            )
        
        rows = await cursor.fetchall()
        return [Category.from_row(tuple(row)) for row in rows]
    
    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID."""
        cursor = await self.connection.execute(
            "SELECT * FROM categories WHERE id = ?",
            (category_id,)
        )
        row = await cursor.fetchone()
        return Category.from_row(tuple(row)) if row else None
    
    async def update_category(self, category_id: int, name: str) -> Optional[Category]:
        """Update category name."""
        cursor = await self.connection.execute(
            """
            UPDATE categories SET name = ?
            WHERE id = ?
            RETURNING *
            """,
            (name, category_id)
        )
        row = await cursor.fetchone()
        await self.connection.commit()
        return Category.from_row(tuple(row)) if row else None
    
    async def get_category_transactions_count(self, category_id: int) -> int:
        """Get count of transactions for a category."""
        cursor = await self.connection.execute(
            "SELECT COUNT(*) FROM transactions WHERE category_id = ?",
            (category_id,)
        )
        return (await cursor.fetchone())[0]
    
    async def delete_category(self, category_id: int) -> bool:
        """Delete category if no transactions linked."""
        # Check for linked transactions
        count = await self.get_category_transactions_count(category_id)
        
        if count > 0:
            return False
        
        await self.connection.execute(
            "DELETE FROM categories WHERE id = ?",
            (category_id,)
        )
        await self.connection.commit()
        return True
    
    # ==================== Transaction Operations ====================
    
    async def create_transaction(
        self,
        user_id: int,
        category_id: int,
        amount: float,
        type: TransactionType,
        description: Optional[str] = None,
        raw_text: Optional[str] = None
    ) -> Transaction:
        """Create new transaction."""
        cursor = await self.connection.execute(
            """
            INSERT INTO transactions (user_id, category_id, amount, type, description, raw_text)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING *
            """,
            (user_id, category_id, amount, type.value, description, raw_text)
        )
        row = await cursor.fetchone()
        await self.connection.commit()
        
        logger.info(f"Transaction created: user_id={user_id}, amount={amount}, type={type.value}")
        return Transaction.from_row(tuple(row))
    
    async def get_transactions_by_month(
        self, 
        user_id: int, 
        year: int, 
        month: int
    ) -> list[Transaction]:
        """Get all transactions for user in specified month."""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        cursor = await self.connection.execute(
            """
            SELECT * FROM transactions 
            WHERE user_id = ? AND created_at >= ? AND created_at < ?
            ORDER BY created_at DESC
            """,
            (user_id, start_date.isoformat(), end_date.isoformat())
        )
        rows = await cursor.fetchall()
        return [Transaction.from_row(tuple(row)) for row in rows]
    
    # ==================== Data Cleanup ====================
    
    async def cleanup_old_data(self, months: int = 6) -> int:
        """Delete transactions older than specified months."""
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        
        cursor = await self.connection.execute(
            "DELETE FROM transactions WHERE created_at < ?",
            (cutoff_date.isoformat(),)
        )
        await self.connection.commit()
        
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old transactions")
        
        return deleted_count


# Global database instance
_db: Optional[Database] = None


async def get_db() -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = Database()
        await _db.connect()
    return _db


async def close_db() -> None:
    """Close database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None
