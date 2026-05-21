"""
Telegram RAG Chatbot — Entry Point
"""
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from core.config import Config
from handlers.command_handlers import start_handler, help_handler
from handlers.message_handlers import message_handler

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    cfg = Config()
    app = ApplicationBuilder().token(cfg.TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help",  help_handler))

    # Free-text messages → RAG pipeline
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Bot is running…")
    app.run_polling()


if __name__ == "__main__":
    main()
