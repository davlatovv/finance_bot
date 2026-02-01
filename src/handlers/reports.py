"""
Reports handlers.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from collections import defaultdict

from src.db import get_db
from src.db.models import TransactionType
from src.keyboards.keyboards import (
    get_months_keyboard,
    get_back_keyboard,
    CallbackData
)
from src.lexicon.lexicon_ru import LEXICON_RU
from src.states.states import ReportsStates

router = Router(name="reports")


@router.callback_query(F.data == CallbackData.REPORTS)
async def callback_reports_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Show reports menu with month selection."""
    await state.set_state(ReportsStates.choosing_month)
    
    await callback.message.edit_text(
        text=LEXICON_RU["reports_choose_month"],
        reply_markup=get_months_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CallbackData.SELECT_MONTH}:"))
async def callback_select_month(callback: CallbackQuery, state: FSMContext) -> None:
    """Generate report for selected month."""
    _, year_str, month_str = callback.data.split(":")
    year = int(year_str)
    month = int(month_str)
    
    db = await get_db()
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer(LEXICON_RU["error_unknown"])
        return
    
    # Get transactions for the month
    transactions = await db.get_transactions_by_month(user.id, year, month)
    
    month_name = LEXICON_RU[f"month_{month}"]
    
    if not transactions:
        await callback.message.edit_text(
            text=f"{LEXICON_RU['report_title'].format(month=f'{month_name} {year}')}\n\n"
                 f"{LEXICON_RU['report_empty']}",
            reply_markup=get_months_keyboard()
        )
        await callback.answer()
        return
    
    # Calculate totals
    total_income = 0.0
    total_expense = 0.0
    by_category: dict[int, dict] = defaultdict(lambda: {"name": "", "amount": 0.0, "type": None})
    
    # Get all categories for the user
    categories = await db.get_categories(user.id)
    cat_map = {cat.id: cat for cat in categories}
    
    for t in transactions:
        if t.type == TransactionType.INCOME:
            total_income += t.amount
        else:
            total_expense += t.amount
        
        cat = cat_map.get(t.category_id)
        if cat:
            by_category[t.category_id]["name"] = cat.name
            by_category[t.category_id]["amount"] += t.amount
            by_category[t.category_id]["type"] = t.type
    
    # Build report text
    balance = total_income - total_expense
    balance_sign = "+" if balance >= 0 else ""
    
    text_parts = [
        LEXICON_RU["report_title"].format(month=f"{month_name} {year}"),
        "",
        LEXICON_RU["report_income"].format(amount=f"{total_income:,.0f}".replace(",", " ")),
        LEXICON_RU["report_expense"].format(amount=f"{total_expense:,.0f}".replace(",", " ")),
        LEXICON_RU["report_balance"].format(amount=f"{balance_sign}{balance:,.0f}".replace(",", " ")),
    ]
    
    # Add category breakdown if there are categories
    if by_category:
        details_lines = []
        
        # Income categories
        income_cats = [(k, v) for k, v in by_category.items() if v["type"] == TransactionType.INCOME]
        if income_cats:
            details_lines.append("\n💰 <b>Доходы:</b>")
            for _, data in sorted(income_cats, key=lambda x: -x[1]["amount"]):
                details_lines.append(f"  • {data['name']}: {data['amount']:,.0f} сўм".replace(",", " "))
        
        # Expense categories
        expense_cats = [(k, v) for k, v in by_category.items() if v["type"] == TransactionType.EXPENSE]
        if expense_cats:
            details_lines.append("\n💸 <b>Расходы:</b>")
            for _, data in sorted(expense_cats, key=lambda x: -x[1]["amount"]):
                details_lines.append(f"  • {data['name']}: {data['amount']:,.0f} сўм".replace(",", " "))
        
        text_parts.append("\n".join(details_lines))
    
    await callback.message.edit_text(
        text="\n".join(text_parts),
        reply_markup=get_months_keyboard()
    )
    await callback.answer()
    await state.clear()
