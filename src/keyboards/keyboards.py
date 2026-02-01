"""
Inline keyboards for finance bot.
All user interactions happen through buttons.
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from typing import Optional

from src.lexicon.lexicon_ru import LEXICON_RU
from src.db.models import Category, TransactionType


# Callback data prefixes
class CallbackData:
    """Callback data constants."""
    # Main menu
    ADD_TRANSACTION = "add"
    CATEGORIES = "categories"
    REPORTS = "reports"
    HELP = "help"
    
    # Transaction type
    INCOME = "income"
    EXPENSE = "expense"
    
    # Navigation
    BACK = "back"
    BACK_MAIN = "back_main"
    CANCEL = "cancel"
    
    # Categories
    ADD_CATEGORY = "add_cat"
    EDIT_CATEGORY = "edit_cat"
    DELETE_CATEGORY = "del_cat"
    CONFIRM_DELETE = "confirm_del"
    VIEW_INCOME_CATS = "view_income_cats"
    VIEW_EXPENSE_CATS = "view_expense_cats"
    SELECT_CATEGORY = "sel_cat"
    MANAGE_CATEGORIES = "manage_cats"
    
    # Reports
    SELECT_MONTH = "month"


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_add_transaction"],
            callback_data=CallbackData.ADD_TRANSACTION
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_categories"],
            callback_data=CallbackData.CATEGORIES
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["btn_reports"],
            callback_data=CallbackData.REPORTS
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_help"],
            callback_data=CallbackData.HELP
        )
    )
    
    return builder.as_markup()


def get_transaction_type_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for choosing transaction type (income/expense)."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_income"],
            callback_data=CallbackData.INCOME
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["btn_expense"],
            callback_data=CallbackData.EXPENSE
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_back"],
            callback_data=CallbackData.BACK_MAIN
        )
    )
    
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel button keyboard."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_cancel"],
            callback_data=CallbackData.CANCEL
        )
    )
    
    return builder.as_markup()


def get_back_keyboard(callback_data: str = CallbackData.BACK_MAIN) -> InlineKeyboardMarkup:
    """Back button keyboard."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_back"],
            callback_data=callback_data
        )
    )
    
    return builder.as_markup()


def get_categories_menu_keyboard() -> InlineKeyboardMarkup:
    """Categories menu keyboard."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_income_categories"],
            callback_data=CallbackData.VIEW_INCOME_CATS
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["btn_expense_categories"],
            callback_data=CallbackData.VIEW_EXPENSE_CATS
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_add_category"],
            callback_data=CallbackData.ADD_CATEGORY
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["btn_edit_categories"],
            callback_data=f"{CallbackData.MANAGE_CATEGORIES}:edit"
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["btn_delete_categories"],
            callback_data=f"{CallbackData.MANAGE_CATEGORIES}:delete"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_back"],
            callback_data=CallbackData.BACK_MAIN
        )
    )
    
    return builder.as_markup()


def get_category_type_keyboard(action: str = "add") -> InlineKeyboardMarkup:
    """Keyboard for choosing category type."""
    builder = InlineKeyboardBuilder()
    
    prefix = CallbackData.ADD_CATEGORY if action == "add" else f"{CallbackData.MANAGE_CATEGORIES}:{action}"
    
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_income"],
            callback_data=f"{prefix}:{CallbackData.INCOME}"
        ),
        InlineKeyboardButton(
            text=LEXICON_RU["btn_expense"],
            callback_data=f"{prefix}:{CallbackData.EXPENSE}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_back"],
            callback_data=CallbackData.CATEGORIES
        )
    )
    
    return builder.as_markup()


def get_categories_list_keyboard(
    categories: list[Category],
    category_type: TransactionType,
    action: str = "view"  # view, edit, delete
) -> InlineKeyboardMarkup:
    """Keyboard with list of categories."""
    builder = InlineKeyboardBuilder()
    
    for cat in categories:
        if action == "delete":
            prefix = CallbackData.DELETE_CATEGORY
            icon = "🗑 "
        elif action == "edit":
            prefix = CallbackData.EDIT_CATEGORY
            icon = "✏️ "
        else:
            prefix = CallbackData.SELECT_CATEGORY
            icon = ""
        
        builder.row(
            InlineKeyboardButton(
                text=f"{icon}{cat.name}",
                callback_data=f"{prefix}:{cat.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_back"],
            callback_data=CallbackData.CATEGORIES
        )
    )
    
    return builder.as_markup()


def get_confirm_delete_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard for category deletion."""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_confirm_delete"],
            callback_data=f"{CallbackData.CONFIRM_DELETE}:{category_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_cancel"],
            callback_data=CallbackData.CATEGORIES
        )
    )
    
    return builder.as_markup()


def get_months_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting month for reports."""
    builder = InlineKeyboardBuilder()
    
    current_date = datetime.now()
    
    # Show last 6 months
    for i in range(6):
        month = current_date.month - i
        year = current_date.year
        
        if month <= 0:
            month += 12
            year -= 1
        
        month_name = LEXICON_RU[f"month_{month}"]
        builder.row(
            InlineKeyboardButton(
                text=f"{month_name} {year}",
                callback_data=f"{CallbackData.SELECT_MONTH}:{year}:{month}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=LEXICON_RU["btn_back"],
            callback_data=CallbackData.BACK_MAIN
        )
    )
    
    return builder.as_markup()
