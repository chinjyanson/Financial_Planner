from typing import Final
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, CallbackContext
import components.initializer as init
from components.conversation_handler import handle_single_agent_1, handle_single_agent_2, handle_single_agent_all
# from components.conversation_handler import handle_multi_agent_1, handle_multi_agent_2
import components.gcs_bucket as gcs
import uuid
import requests

import logging
import io
import os

token: Final = init.TELEGRAM_API_KEY
bot_usernmae: Final = init.TELEGRAM_BOT_USERNAME
thread_id = 5001

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello, I am a Sunway AI bot. Ask me anything!")

# Change the functions within this function to handle_multi_agent_all or handle_single_agent_all to swap between single_agent and multi_agent
async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text: str = update.message.text

    if update.message.document or update.message.photo or update.message.video:
        if update.message.document:
            file = update.message.document
        elif update.message.photo:
            file = update.message.photo
        elif update.message.video:
            file = update.message.video
        # mime_type = update.message.document.mime_type
        # print(mime_type)
        file_extension = os.path.splitext(file.file_name)[1][1:]
        new_file = await context.bot.get_file(file.file_id)

        # getting file url from telegram api, then download and read file as bytes
        file_url = new_file.file_path
        response = requests.get(file_url)
        file_bytes = io.BytesIO(response.content)

        # upload and donwload file frim gcs
        link = gcs.upload_and_download_file(
            cred_path=init.GOOGLE_APPLICATION_CREDENTIALS_1,
            file_bytes=file_bytes,  # Pass the in-memory bytes directly
            file_extension=file_extension,
            blob_name=f"{uuid.uuid4().hex}.{file_extension}",
            bucket_name=init.GCS_BUCKET_NAME
        )
        text = link

    # else:
    response: str = await handle_single_agent_all(user_input=text, thread_id=thread_id)
    
    # print('Bot:', response)
    await update.message.reply_text(response)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} cause error {context.error}")


def telegram_bot():
    print( 'Starting bot ... ')
    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler('start', start_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_telegram_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_telegram_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_telegram_message))
    
    # Errors
    app.add_error_handler(error)

    # Polls the bot
    print('Polling ... ')
    app.run_polling(poll_interval=3)

if __name__ == "__main__":
    telegram_bot()