"""
handlers/command_handlers.py
"""
from telegram import Update
from telegram.ext import ContextTypes


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Hello! I'm your RAG-powered assistant.\n"
        "Ask me anything and I'll answer from my knowledge base.\n\n"
        "Use /help to see available commands."
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *Commands*\n"
        "/start — welcome message\n"
        "/help  — this message\n\n"
        "Just send any text and I'll search my knowledge base for you.",
        parse_mode="Markdown",
    )
