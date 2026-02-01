"""
Database models for finance bot.
Uses dataclasses for type safety and clarity.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TransactionType(str, Enum):
    """Type of financial transaction."""
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class User:
    """User model."""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    created_at: datetime
    
    @classmethod
    def from_row(cls, row: tuple) -> "User":
        """Create User from database row."""
        return cls(
            id=row[0],
            telegram_id=row[1],
            username=row[2],
            first_name=row[3],
            created_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4]
        )


@dataclass
class Category:
    """Category model for income/expense categorization."""
    id: int
    user_id: int
    name: str
    type: TransactionType
    created_at: datetime
    
    @classmethod
    def from_row(cls, row: tuple) -> "Category":
        """Create Category from database row."""
        return cls(
            id=row[0],
            user_id=row[1],
            name=row[2],
            type=TransactionType(row[3]),
            created_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4]
        )


@dataclass
class Transaction:
    """Transaction model for income/expense records."""
    id: int
    user_id: int
    category_id: int
    amount: float
    type: TransactionType
    description: Optional[str]
    raw_text: Optional[str]
    created_at: datetime
    
    @classmethod
    def from_row(cls, row: tuple) -> "Transaction":
        """Create Transaction from database row."""
        return cls(
            id=row[0],
            user_id=row[1],
            category_id=row[2],
            amount=row[3],
            type=TransactionType(row[4]),
            description=row[5],
            raw_text=row[6],
            created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7]
        )
