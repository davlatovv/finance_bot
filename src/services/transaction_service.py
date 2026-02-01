"""
Transaction service - business logic for financial operations.
Handles logging, duplicate protection, and data validation.
"""
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from src.db import get_db, TransactionType
from src.db.models import Transaction, Category

logger = logging.getLogger(__name__)


class TransactionService:
    """Service for managing financial transactions."""
    
    # Time window for duplicate detection (in seconds)
    DUPLICATE_WINDOW_SECONDS = 60
    
    # Minimum allowed amount
    MIN_AMOUNT = 0.01
    
    # Maximum allowed amount (10 million)
    MAX_AMOUNT = 10_000_000
    
    @staticmethod
    def _generate_hash(user_id: int, amount: float, category_id: int, raw_text: str) -> str:
        """Generate hash for duplicate detection."""
        data = f"{user_id}:{amount}:{category_id}:{raw_text}"
        return hashlib.md5(data.encode()).hexdigest()
    
    @classmethod
    async def create_transaction(
        cls,
        telegram_id: int,
        amount: float,
        transaction_type: TransactionType,
        category_name: str,
        description: Optional[str] = None,
        raw_text: Optional[str] = None
    ) -> tuple[bool, str, Optional[Transaction]]:
        """
        Create a new transaction with validation and duplicate protection.
        
        Args:
            telegram_id: User's Telegram ID
            amount: Transaction amount
            transaction_type: Income or expense
            category_name: Category name
            description: Optional description
            raw_text: Original user input
            
        Returns:
            Tuple of (success, message, transaction)
        """
        db = await get_db()
        
        # Get user
        user = await db.get_user_by_telegram_id(telegram_id)
        if not user:
            logger.warning(f"User not found: telegram_id={telegram_id}")
            return False, "Пользователь не найден", None
        
        # Validate amount
        if amount < cls.MIN_AMOUNT:
            logger.info(f"Invalid amount (too small): {amount} for user {telegram_id}")
            return False, "Сумма слишком маленькая", None
        
        if amount > cls.MAX_AMOUNT:
            logger.warning(f"Suspicious amount (too large): {amount} for user {telegram_id}")
            return False, "Сумма слишком большая", None
        
        # Get or create category
        category = await cls._get_or_create_category(
            user.id, category_name, transaction_type
        )
        if not category:
            return False, "Не удалось создать категорию", None
        
        # Check for duplicates
        is_duplicate = await cls._check_duplicate(
            user.id, amount, category.id, raw_text or ""
        )
        if is_duplicate:
            logger.info(f"Duplicate transaction detected for user {telegram_id}")
            return False, "Похожая запись уже добавлена. Подожди минуту.", None
        
        # Create transaction
        try:
            transaction = await db.create_transaction(
                user_id=user.id,
                category_id=category.id,
                amount=amount,
                type=transaction_type,
                description=description,
                raw_text=raw_text
            )
            
            # Log successful operation
            type_text = "доход" if transaction_type == TransactionType.INCOME else "расход"
            logger.info(
                f"Transaction created: user={telegram_id}, "
                f"type={type_text}, amount={amount}, category={category_name}"
            )
            
            return True, "Записано!", transaction
            
        except Exception as e:
            logger.error(f"Failed to create transaction: {e}")
            return False, "Ошибка при сохранении", None
    
    @classmethod
    async def _get_or_create_category(
        cls,
        user_id: int,
        name: str,
        category_type: TransactionType
    ) -> Optional[Category]:
        """Get existing category or create new one."""
        db = await get_db()
        
        # Try to find existing category (case-insensitive)
        categories = await db.get_categories(user_id, category_type)
        for cat in categories:
            if cat.name.lower() == name.lower():
                return cat
        
        # Create new category
        try:
            category = await db.create_category(user_id, name, category_type)
            logger.info(f"Category created: user_id={user_id}, name={name}, type={category_type.value}")
            return category
        except Exception as e:
            logger.error(f"Failed to create category: {e}")
            return None
    
    @classmethod
    async def _check_duplicate(
        cls,
        user_id: int,
        amount: float,
        category_id: int,
        raw_text: str
    ) -> bool:
        """Check if similar transaction was created recently."""
        db = await get_db()
        
        # Get recent transactions
        now = datetime.now()
        
        # Get transactions from current month
        transactions = await db.get_transactions_by_month(
            user_id, now.year, now.month
        )
        
        # Check for duplicates within time window
        cutoff = now - timedelta(seconds=cls.DUPLICATE_WINDOW_SECONDS)
        
        for t in transactions:
            # Check if within time window
            if t.created_at < cutoff:
                continue
            
            # Check if same amount and category
            if t.amount == amount and t.category_id == category_id:
                # Same raw text is definitely a duplicate
                if t.raw_text and raw_text and t.raw_text.lower() == raw_text.lower():
                    return True
                
                # Same amount and category within 60 seconds is likely duplicate
                return True
        
        return False
    
    @classmethod
    async def get_user_stats(cls, telegram_id: int, year: int, month: int) -> dict:
        """
        Get user statistics for a month.
        
        Returns:
            Dict with income, expense, balance, and category breakdown
        """
        db = await get_db()
        user = await db.get_user_by_telegram_id(telegram_id)
        
        if not user:
            return {"error": "User not found"}
        
        transactions = await db.get_transactions_by_month(user.id, year, month)
        categories = await db.get_categories(user.id)
        cat_map = {cat.id: cat for cat in categories}
        
        total_income = 0.0
        total_expense = 0.0
        by_category = {}
        
        for t in transactions:
            if t.type == TransactionType.INCOME:
                total_income += t.amount
            else:
                total_expense += t.amount
            
            cat = cat_map.get(t.category_id)
            if cat:
                key = cat.name
                if key not in by_category:
                    by_category[key] = {"amount": 0.0, "type": t.type.value}
                by_category[key]["amount"] += t.amount
        
        return {
            "income": total_income,
            "expense": total_expense,
            "balance": total_income - total_expense,
            "by_category": by_category,
            "transaction_count": len(transactions)
        }
