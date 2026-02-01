
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from src.db import get_db, close_db
from src.services.llm_service import close_llm_service
from src.security import RateLimitMiddleware, get_rate_limiter
from src.handlers import start, transactions, categories, reports

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Actions to perform on bot startup."""
    # Initialize database
    db = await get_db()
    
    # Run cleanup for old data (older than 6 months)
    deleted = await db.cleanup_old_data(months=6)
    if deleted:
        logger.info(f"Cleaned up {deleted} old transactions")
    
    logger.info("Bot started successfully")


async def on_shutdown(bot: Bot) -> None:
    """Actions to perform on bot shutdown."""
    await close_db()
    await close_llm_service()
    logger.info("Bot shutdown complete")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Configure security logger
    security_logger = logging.getLogger("security")
    security_logger.setLevel(logging.INFO)
    
    logger.info("Starting Finance Bot...")
    
    # Load configuration
    config = load_config()
    
    # Initialize bot with default properties
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Initialize dispatcher with memory storage for FSM
    # Note: For production, consider using Redis storage
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register middleware
    rate_limiter = get_rate_limiter()
    dp.message.middleware(RateLimitMiddleware(rate_limiter))
    dp.callback_query.middleware(RateLimitMiddleware(rate_limiter))
    
    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Include routers (order matters - more specific handlers first)
    dp.include_router(start.router)
    dp.include_router(transactions.router)
    dp.include_router(categories.router)
    dp.include_router(reports.router)
    
    # Start polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
