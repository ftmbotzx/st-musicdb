import os
import logging
from pyrogram import Client
import pyrogram.utils as pyroutils
from bot.handlers import setup_handlers
from dotenv import load_dotenv

# Adjust Pyrogram chat ID ranges
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Get environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.error("Missing required environment variables: API_ID, API_HASH, BOT_TOKEN")
    exit(1)

# Convert API_ID to int and validate other variables
try:
    API_ID = int(API_ID) if API_ID else None
    if not API_ID or not API_HASH or not BOT_TOKEN:
        raise ValueError("Invalid environment variables")
except (ValueError, TypeError):
    logger.error("Invalid environment variable format")
    exit(1)

def main():
    """Initialize and start both the Telegram bot and web server"""
    try:
        # Import Flask app
        from app import run_flask_app
        
        # Create Pyrogram client
        app = Client(
            "media_indexer_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
        
        # Setup handlers
        setup_handlers(app)
        
        logger.info("Starting Media Indexer Bot and Web Server...")
        
        # Start Flask web server in a separate thread
        import threading
        web_thread = threading.Thread(target=run_flask_app, daemon=True)
        web_thread.start()
        logger.info("Web server started on http://0.0.0.0:5000")
        
        # Start the Telegram bot (blocking)
        app.run()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        exit(1)

if __name__ == "__main__":
    main()
