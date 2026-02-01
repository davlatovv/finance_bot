"""
Transaction handlers (add income/expense).
Integrates Whisper for voice and LLM for parsing.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from src.db import get_db, TransactionType
from src.services.whisper_service import get_whisper_service
from src.services.llm_service import get_llm_service, LLMResponse
from src.keyboards.keyboards import (
    get_transaction_type_keyboard,
    get_cancel_keyboard,
    get_main_menu_keyboard,
    CallbackData
)
from src.lexicon.lexicon_ru import LEXICON_RU
from src.states.states import AddTransactionStates

logger = logging.getLogger(__name__)
router = Router(name="transactions")


@router.callback_query(F.data == CallbackData.ADD_TRANSACTION)
async def callback_add_transaction(callback: CallbackQuery, state: FSMContext) -> None:
    """Start add transaction flow."""
    await state.set_state(AddTransactionStates.choosing_type)
    
    await callback.message.edit_text(
        text=LEXICON_RU["add_choose_type"],
        reply_markup=get_transaction_type_keyboard()
    )
    await callback.answer()


@router.callback_query(
    AddTransactionStates.choosing_type,
    F.data.in_({CallbackData.INCOME, CallbackData.EXPENSE})
)
async def callback_choose_transaction_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle transaction type selection."""
    transaction_type = callback.data
    
    # Save type to state
    await state.update_data(transaction_type=transaction_type)
    await state.set_state(AddTransactionStates.waiting_for_input)
    
    # Prepare prompt based on type
    if transaction_type == CallbackData.INCOME:
        type_text = "доход"
        example = LEXICON_RU["income_example"]
    else:
        type_text = "расход"
        example = LEXICON_RU["expense_example"]
    
    text = LEXICON_RU["add_enter_text"].format(type=type_text, example=example)
    
    await callback.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


async def process_transaction_with_llm(
    user_id: int,
    telegram_id: int,
    text: str,
    transaction_type: str,
    raw_text: str
) -> tuple[bool, str]:
    """
    Process transaction using LLM.
    
    Returns:
        Tuple of (success, message)
    """
    db = await get_db()
    user = await db.get_user_by_telegram_id(telegram_id)
    
    if not user:
        return False, LEXICON_RU["error_unknown"]
    
    # Get user's categories
    categories = await db.get_categories(user.id)
    categories_list = [
        {"name": cat.name, "type": cat.type.value}
        for cat in categories
    ]
    
    # Get LLM service (initialized in bot.py)
    from config import load_config
    config = load_config()
    llm_service = get_llm_service(
        api_key=config.openrouter.api_key,
        model=config.openrouter.model
    )
    
    # Process with LLM
    response: LLMResponse = await llm_service.process_transaction(
        user_text=text,
        transaction_type=transaction_type,
        categories=categories_list
    )
    
    if not response.success or not response.transaction:
        return False, response.error or LEXICON_RU["error_unknown"]
    
    tx_data = response.transaction
    
    # Validate amount
    if tx_data.amount <= 0:
        return False, LEXICON_RU["error_invalid_amount"]
    
    # Get or create category
    tx_type = TransactionType(tx_data.type)
    category = None
    
    # Try to find existing category
    existing_categories = await db.get_categories(user.id, tx_type)
    for cat in existing_categories:
        if cat.name.lower() == tx_data.category_name.lower():
            category = cat
            break
    
    # Create new category if needed
    if not category:
        try:
            category = await db.create_category(
                user_id=user.id,
                name=tx_data.category_name,
                type=tx_type
            )
        except Exception as e:
            logger.error(f"Failed to create category: {e}")
            return False, LEXICON_RU["error_unknown"]
    
    # Create transaction
    try:
        await db.create_transaction(
            user_id=user.id,
            category_id=category.id,
            amount=tx_data.amount,
            type=tx_type,
            description=tx_data.description,
            raw_text=raw_text
        )
    except Exception as e:
        logger.error(f"Failed to create transaction: {e}")
        return False, LEXICON_RU["error_unknown"]
    
    # Build success message
    type_text = "💰 Доход" if tx_type == TransactionType.INCOME else "💸 Расход"
    amount_formatted = f"{tx_data.amount:,.0f}".replace(",", " ")
    
    message = LEXICON_RU["transaction_saved"].format(
        type=type_text,
        amount=amount_formatted,
        category=category.name
    )
    
    return True, message


@router.message(AddTransactionStates.waiting_for_input, F.text)
async def process_transaction_text(message: Message, state: FSMContext) -> None:
    """Process text input for transaction."""
    data = await state.get_data()
    transaction_type = data.get("transaction_type")
    
    # Show processing message
    processing_msg = await message.answer(LEXICON_RU["processing"])
    
    try:
        success, result_text = await process_transaction_with_llm(
            user_id=message.from_user.id,
            telegram_id=message.from_user.id,
            text=message.text,
            transaction_type=transaction_type,
            raw_text=message.text
        )
        
        # Delete processing message
        await processing_msg.delete()
        
        await message.answer(
            text=result_text,
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Transaction processing error: {e}")
        await processing_msg.delete()
        await message.answer(
            text=LEXICON_RU["error_unknown"],
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()


@router.message(AddTransactionStates.waiting_for_input, F.voice)
async def process_transaction_voice(message: Message, state: FSMContext, bot: Bot) -> None:
    """Process voice input for transaction using Whisper."""
    data = await state.get_data()
    transaction_type = data.get("transaction_type")
    
    # Show processing message
    processing_msg = await message.answer(LEXICON_RU["processing"])
    
    try:
        # Get Whisper service
        from config import load_config
        config = load_config()
        whisper_service = get_whisper_service(
            model_name=config.whisper.model,
            temp_dir=config.whisper.temp_dir
        )
        
        # Download voice file
        voice = message.voice
        file = await bot.get_file(voice.file_id)
        
        # Get temp file path
        temp_path = whisper_service.get_temp_file_path(
            user_id=message.from_user.id,
            file_id=voice.file_id
        )
        
        # Download file
        await bot.download_file(file.file_path, temp_path)
        
        # Transcribe
        transcribed_text = await whisper_service.transcribe_file(temp_path)
        
        # Cleanup temp file
        whisper_service.cleanup_temp_file(temp_path)
        
        if not transcribed_text:
            await processing_msg.delete()
            await message.answer(
                text="😔 Не удалось распознать речь. Попробуй ещё раз или напиши текстом.",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        logger.info(f"Transcribed: {transcribed_text}")
        
        # Process transcribed text with LLM
        success, result_text = await process_transaction_with_llm(
            user_id=message.from_user.id,
            telegram_id=message.from_user.id,
            text=transcribed_text,
            transaction_type=transaction_type,
            raw_text=f"[voice] {transcribed_text}"
        )
        
        # Delete processing message
        await processing_msg.delete()
        
        # Show what was recognized
        if success:
            result_text = f"🎤 <i>«{transcribed_text}»</i>\n\n{result_text}"
        
        await message.answer(
            text=result_text,
            reply_markup=get_main_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        await processing_msg.delete()
        await message.answer(
            text=LEXICON_RU["error_unknown"],
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()
