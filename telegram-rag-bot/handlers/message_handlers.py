"""
handlers/message_handlers.py — routes free-text messages through the RAG pipeline.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.config import Config
from core.rag import RAGPipeline
from core.api_client import APIClient

logger = logging.getLogger(__name__)

# Single pipeline instance shared across handlers (initialised lazily)
_pipeline: RAGPipeline | None = None
_api_client: APIClient | None = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        cfg = Config()
        _pipeline = RAGPipeline(cfg)
        try:
            _pipeline.load_index()   # load pre-built index
        except Exception:
            logger.warning("Could not load index — run build_index() first.")
    return _pipeline


def get_api_client() -> APIClient:
    global _api_client
    if _api_client is None:
        cfg = Config()
        _api_client = APIClient(base_url=cfg.API_BASE_URL)
    return _api_client


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    chat_id   = update.effective_chat.id
    logger.info("Message from %s: %s", chat_id, user_text)

    # Show typing indicator while we process
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        api_client = get_api_client()

        # Try to fetch API data
        if api_client.health_check():
            logger.info("API is healthy, fetching event information...")
            api_data = api_client.get_event_info()
            if api_data:
                answer = api_client.format_event_response(api_data)
            else:
                answer = "⚠️ Could not retrieve event information from the API."
        else:
            logger.warning("API server is not available")
            answer = "⚠️ Event API service is currently unavailable."

    except Exception as exc:
        logger.exception("Error processing message")
        answer = f"❌ Something went wrong: {exc}"

    await update.message.reply_text(answer, parse_mode="Markdown")
