"""
Category management handlers.
Supports viewing, creating, editing, and deleting categories.
"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from src.db import get_db
from src.db.models import TransactionType
from src.keyboards.keyboards import (
    get_categories_menu_keyboard,
    get_category_type_keyboard,
    get_categories_list_keyboard,
    get_cancel_keyboard,
    get_confirm_delete_keyboard,
    CallbackData
)
from src.lexicon.lexicon_ru import LEXICON_RU
from src.states.states import AddCategoryStates, EditCategoryStates

logger = logging.getLogger(__name__)
router = Router(name="categories")


# ==================== View Categories ====================

@router.callback_query(F.data == CallbackData.CATEGORIES)
async def callback_categories_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Show categories menu."""
    await state.clear()
    
    await callback.message.edit_text(
        text=LEXICON_RU["categories_title"],
        reply_markup=get_categories_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == CallbackData.VIEW_INCOME_CATS)
async def callback_view_income_categories(callback: CallbackQuery) -> None:
    """View income categories."""
    db = await get_db()
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer(LEXICON_RU["error_unknown"])
        return
    
    categories = await db.get_categories(user.id, TransactionType.INCOME)
    
    if not categories:
        await callback.message.edit_text(
            text=f"💰 <b>Категории доходов</b>\n\n{LEXICON_RU['categories_empty']}",
            reply_markup=get_categories_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            text="💰 <b>Категории доходов</b>",
            reply_markup=get_categories_list_keyboard(categories, TransactionType.INCOME)
        )
    
    await callback.answer()


@router.callback_query(F.data == CallbackData.VIEW_EXPENSE_CATS)
async def callback_view_expense_categories(callback: CallbackQuery) -> None:
    """View expense categories."""
    db = await get_db()
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer(LEXICON_RU["error_unknown"])
        return
    
    categories = await db.get_categories(user.id, TransactionType.EXPENSE)
    
    if not categories:
        await callback.message.edit_text(
            text=f"💸 <b>Категории расходов</b>\n\n{LEXICON_RU['categories_empty']}",
            reply_markup=get_categories_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            text="💸 <b>Категории расходов</b>",
            reply_markup=get_categories_list_keyboard(categories, TransactionType.EXPENSE)
        )
    
    await callback.answer()


# ==================== Create Category ====================

@router.callback_query(F.data == CallbackData.ADD_CATEGORY)
async def callback_add_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Start add category flow."""
    await state.set_state(AddCategoryStates.choosing_type)
    
    await callback.message.edit_text(
        text=LEXICON_RU["category_choose_type"],
        reply_markup=get_category_type_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CallbackData.ADD_CATEGORY}:"))
async def callback_choose_category_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle category type selection for creation."""
    _, category_type = callback.data.split(":")
    
    await state.update_data(category_type=category_type)
    await state.set_state(AddCategoryStates.entering_name)
    
    await callback.message.edit_text(
        text=LEXICON_RU["category_enter_name"],
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(AddCategoryStates.entering_name, F.text)
async def process_category_name(message: Message, state: FSMContext) -> None:
    """Process category name input."""
    data = await state.get_data()
    category_type_str = data.get("category_type")
    
    # Convert string to TransactionType
    category_type = (
        TransactionType.INCOME 
        if category_type_str == CallbackData.INCOME 
        else TransactionType.EXPENSE
    )
    
    # Validate and sanitize name
    name = message.text.strip()
    if len(name) > 50:
        name = name[:50]
    
    if len(name) < 1:
        await message.answer(
            text="⚠️ Название не может быть пустым.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    db = await get_db()
    user = await db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer(LEXICON_RU["error_unknown"])
        await state.clear()
        return
    
    # Check if category already exists
    existing_categories = await db.get_categories(user.id, category_type)
    if any(cat.name.lower() == name.lower() for cat in existing_categories):
        await message.answer(
            text=LEXICON_RU["category_exists"],
            reply_markup=get_categories_menu_keyboard()
        )
        await state.clear()
        return
    
    # Create category
    try:
        await db.create_category(user.id, name, category_type)
        logger.info(f"Category created: user={message.from_user.id}, name={name}, type={category_type.value}")
        await message.answer(
            text=LEXICON_RU["category_created"].format(name=name),
            reply_markup=get_categories_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to create category: {e}")
        await message.answer(
            text=LEXICON_RU["error_unknown"],
            reply_markup=get_categories_menu_keyboard()
        )
    
    await state.clear()


# ==================== Manage Categories (Edit/Delete) ====================

@router.callback_query(F.data.startswith(f"{CallbackData.MANAGE_CATEGORIES}:"))
async def callback_manage_categories(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle category management actions."""
    parts = callback.data.split(":")
    action = parts[1]  # edit or delete
    
    if len(parts) == 3:
        # Type selected: manage_cats:edit:income or manage_cats:delete:expense
        category_type_str = parts[2]
        category_type = (
            TransactionType.INCOME 
            if category_type_str == CallbackData.INCOME 
            else TransactionType.EXPENSE
        )
        
        db = await get_db()
        user = await db.get_user_by_telegram_id(callback.from_user.id)
        
        if not user:
            await callback.answer(LEXICON_RU["error_unknown"])
            return
        
        categories = await db.get_categories(user.id, category_type)
        
        if not categories:
            await callback.message.edit_text(
                text=LEXICON_RU["categories_empty"],
                reply_markup=get_categories_menu_keyboard()
            )
            await callback.answer()
            return
        
        # Show categories list for action
        if action == "edit":
            text = LEXICON_RU["category_select_to_edit"]
        else:
            text = LEXICON_RU["category_select_to_delete"]
        
        await callback.message.edit_text(
            text=text,
            reply_markup=get_categories_list_keyboard(categories, category_type, action=action)
        )
    else:
        # Just action selected, need to choose type
        await callback.message.edit_text(
            text=LEXICON_RU["category_choose_type"],
            reply_markup=get_category_type_keyboard(action=action)
        )
    
    await callback.answer()


# ==================== Edit Category ====================

@router.callback_query(F.data.startswith(f"{CallbackData.EDIT_CATEGORY}:"))
async def callback_edit_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing a category."""
    _, category_id_str = callback.data.split(":")
    category_id = int(category_id_str)
    
    db = await get_db()
    category = await db.get_category_by_id(category_id)
    
    if not category:
        await callback.answer(LEXICON_RU["error_unknown"])
        return
    
    await state.set_state(EditCategoryStates.entering_new_name)
    await state.update_data(category_id=category_id, old_name=category.name, category_type=category.type.value)
    
    await callback.message.edit_text(
        text=LEXICON_RU["category_enter_new_name"].format(name=category.name),
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(EditCategoryStates.entering_new_name, F.text)
async def process_edit_category_name(message: Message, state: FSMContext) -> None:
    """Process new category name."""
    data = await state.get_data()
    category_id = data.get("category_id")
    category_type_str = data.get("category_type")
    
    # Sanitize name
    new_name = message.text.strip()
    if len(new_name) > 50:
        new_name = new_name[:50]
    
    if len(new_name) < 1:
        await message.answer(
            text="⚠️ Название не может быть пустым.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    db = await get_db()
    user = await db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer(LEXICON_RU["error_unknown"])
        await state.clear()
        return
    
    # Check if name already exists
    category_type = TransactionType(category_type_str)
    existing_categories = await db.get_categories(user.id, category_type)
    if any(cat.name.lower() == new_name.lower() and cat.id != category_id for cat in existing_categories):
        await message.answer(
            text=LEXICON_RU["category_exists"],
            reply_markup=get_categories_menu_keyboard()
        )
        await state.clear()
        return
    
    # Update category
    try:
        await db.update_category(category_id, new_name)
        logger.info(f"Category updated: id={category_id}, new_name={new_name}")
        await message.answer(
            text=LEXICON_RU["category_updated"].format(name=new_name),
            reply_markup=get_categories_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to update category: {e}")
        await message.answer(
            text=LEXICON_RU["error_unknown"],
            reply_markup=get_categories_menu_keyboard()
        )
    
    await state.clear()


# ==================== Delete Category ====================

@router.callback_query(F.data.startswith(f"{CallbackData.DELETE_CATEGORY}:"))
async def callback_delete_category(callback: CallbackQuery) -> None:
    """Show confirmation for category deletion."""
    _, category_id_str = callback.data.split(":")
    category_id = int(category_id_str)
    
    db = await get_db()
    category = await db.get_category_by_id(category_id)
    
    if not category:
        await callback.answer(LEXICON_RU["error_unknown"])
        return
    
    # Check if has transactions
    transactions_count = await db.get_category_transactions_count(category_id)
    
    if transactions_count > 0:
        await callback.message.edit_text(
            text=LEXICON_RU["category_has_transactions"].format(count=transactions_count),
            reply_markup=get_categories_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Show confirmation
    await callback.message.edit_text(
        text=LEXICON_RU["category_confirm_delete"].format(name=category.name),
        reply_markup=get_confirm_delete_keyboard(category_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{CallbackData.CONFIRM_DELETE}:"))
async def callback_confirm_delete(callback: CallbackQuery) -> None:
    """Confirm and delete category."""
    _, category_id_str = callback.data.split(":")
    category_id = int(category_id_str)
    
    db = await get_db()
    category = await db.get_category_by_id(category_id)
    
    if not category:
        await callback.answer(LEXICON_RU["error_unknown"])
        return
    
    category_name = category.name
    
    # Try to delete
    success = await db.delete_category(category_id)
    
    if success:
        logger.info(f"Category deleted: id={category_id}, name={category_name}")
        await callback.message.edit_text(
            text=LEXICON_RU["category_deleted"].format(name=category_name),
            reply_markup=get_categories_menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            text=LEXICON_RU["category_has_transactions"].format(count="несколько"),
            reply_markup=get_categories_menu_keyboard()
        )
    
    await callback.answer()
