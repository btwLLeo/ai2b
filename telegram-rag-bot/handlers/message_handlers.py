"""
handlers/message_handlers.py — routes free-text messages through the RAG pipeline.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.config import Config
from core.rag import RAGPipeline

logger = logging.getLogger(__name__)

# Single pipeline instance shared across handlers (initialised lazily)
_pipeline: RAGPipeline | None = None


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


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    chat_id   = update.effective_chat.id
    logger.info("Message from %s: %s", chat_id, user_text)

    # Show typing indicator while we process
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        pipeline = get_pipeline()
        answer   = pipeline.query(user_text)
    except NotImplementedError:
        answer = (
            "⚙️ The RAG pipeline stubs haven't been implemented yet.\n"
            "Please plug in your embedding model and vector store in `core/rag.py`."
        )
    except Exception as exc:
        logger.exception("Error processing message")
        answer = f"❌ Something went wrong: {exc}"

    await update.message.reply_text(answer)
