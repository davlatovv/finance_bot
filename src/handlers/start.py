"""
Start command and main menu handlers.
"""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.db import get_db
from src.keyboards.keyboards import (
    get_main_menu_keyboard,
    get_back_keyboard,
    CallbackData
)
from src.lexicon.lexicon_ru import LEXICON_RU

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command."""
    # Clear any existing state
    await state.clear()
    
    # Get or create user in database
    db = await get_db()
    user = await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    # Get user's name for greeting
    name = message.from_user.first_name or message.from_user.username or "друг"
    
    # Check if this is a new user or returning user
    # For simplicity, always show welcome message
    text = LEXICON_RU["start_welcome"].format(name=name)
    
    await message.answer(
        text=text,
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == CallbackData.BACK_MAIN)
async def callback_back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    """Return to main menu."""
    await state.clear()
    
    name = callback.from_user.first_name or callback.from_user.username or "друг"
    text = LEXICON_RU["start_welcome_back"].format(name=name)
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == CallbackData.CANCEL)
async def callback_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel current action and return to main menu."""
    await state.clear()
    
    name = callback.from_user.first_name or callback.from_user.username or "друг"
    text = LEXICON_RU["start_welcome_back"].format(name=name)
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == CallbackData.HELP)
async def callback_help(callback: CallbackQuery) -> None:
    """Show help message."""
    await callback.message.edit_text(
        text=LEXICON_RU["help_text"],
        reply_markup=get_back_keyboard()
    )
    await callback.answer()
