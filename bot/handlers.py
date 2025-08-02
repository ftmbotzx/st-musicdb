import logging
import re
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.database import DatabaseManager
from bot.utils import extract_track_info, format_file_caption, get_file_metadata

logger = logging.getLogger(__name__)

# Initialize database manager
db = DatabaseManager()

async def handle_media_message(client: Client, message: Message):
    """Handle incoming media messages and index them"""
    try:
        # Extract file metadata based on message type
        file_data = get_file_metadata(message)
        if not file_data:
            return
        
        # Extract track information from caption
        track_info = extract_track_info(message.caption) if message.caption else {}
        
        # Forward file to backup channel
        backup_file_id = await forward_to_backup(client, message)
        
        # Prepare document for MongoDB
        document = {
            "file_id": file_data["file_id"],
            "backup_file_id": backup_file_id,
            "file_unique_id": file_data["file_unique_id"],
            "file_name": file_data.get("file_name"),
            "caption": message.caption or "",
            "file_type": file_data["file_type"],
            "mime_type": file_data.get("mime_type"),
            "file_size": file_data.get("file_size"),
            "duration": file_data.get("duration"),
            "width": file_data.get("width"),
            "height": file_data.get("height"),
            "chat_id": message.chat.id,
            "chat_title": message.chat.title or message.chat.first_name,
            "message_id": message.id,
            "sender_id": message.from_user.id if message.from_user else None,
            "sender_username": message.from_user.username if message.from_user else None,
            "date": message.date.isoformat(),
            "is_deleted": False,
            "track_url": track_info.get("track_url"),
            "track_id": track_info.get("track_id")
        }
        
        # Store in MongoDB
        result = db.insert_file(document)
        
        if result:
            logger.info(f"Successfully indexed file: {file_data['file_id']}")
        else:
            logger.error(f"Failed to index file: {file_data['file_id']}")
            
    except Exception as e:
        logger.error(f"Error handling media message: {e}")

async def forward_to_backup(client: Client, message: Message):
    """Forward message to backup channel and return backup file_id"""
    try:
        backup_channel_id = db.get_backup_channel_id()
        if not backup_channel_id:
            logger.warning("No backup channel configured")
            return None
            
        # Forward the message to backup channel
        forwarded = await client.forward_messages(
            chat_id=backup_channel_id,
            from_chat_id=message.chat.id,
            message_ids=message.id
        )
        
        if forwarded:
            # Get the file_id from the forwarded message
            # forwarded is a list, get the first message
            forwarded_msg = forwarded[0] if isinstance(forwarded, list) else forwarded
            backup_file_data = get_file_metadata(forwarded_msg)
            return backup_file_data["file_id"] if backup_file_data else None
            
    except Exception as e:
        logger.error(f"Error forwarding to backup channel: {e}")
        return None

async def handle_send_command(client: Client, message: Message):
    """Handle /send command to retrieve file by filename"""
    try:
        # Extract filename from command
        command_parts = message.text.split(" ", 1)
        if len(command_parts) < 2:
            await message.reply("Usage: /send <filename>")
            return
            
        filename = command_parts[1].strip()
        
        # Search for file in database
        file_doc = db.find_file_by_name(filename)
        
        if not file_doc:
            await message.reply(f"File '{filename}' not found in database.")
            return
            
        # Send the file from backup
        await send_file_from_backup(client, message, file_doc)
        
    except Exception as e:
        logger.error(f"Error handling send command: {e}")
        await message.reply("An error occurred while processing your request.")

async def handle_sendid_command(client: Client, message: Message):
    """Handle /sendid command to retrieve file by track ID"""
    try:
        # Extract track ID from command
        command_parts = message.text.split(" ", 1)
        if len(command_parts) < 2:
            await message.reply("Usage: /sendid <track_id>")
            return
            
        track_id = command_parts[1].strip()
        
        # Search for file in database
        file_doc = db.find_file_by_track_id(track_id)
        
        if not file_doc:
            await message.reply(f"Track ID '{track_id}' not found in database.")
            return
            
        # Send the file from backup
        await send_file_from_backup(client, message, file_doc)
        
    except Exception as e:
        logger.error(f"Error handling sendid command: {e}")
        await message.reply("An error occurred while processing your request.")

async def send_file_from_backup(client: Client, message: Message, file_doc: dict):
    """Send file from backup with formatted caption"""
    try:
        backup_file_id = file_doc.get("backup_file_id")
        if not backup_file_id:
            await message.reply("Backup file not available for this item.")
            return
            
        # Generate formatted caption
        caption = format_file_caption(file_doc)
        
        # Determine file type and send accordingly
        file_type = file_doc.get("file_type")
        
        if file_type == "audio":
            await client.send_audio(
                chat_id=message.chat.id,
                audio=backup_file_id,
                caption=caption
            )
        elif file_type == "video":
            await client.send_video(
                chat_id=message.chat.id,
                video=backup_file_id,
                caption=caption
            )
        elif file_type == "document":
            await client.send_document(
                chat_id=message.chat.id,
                document=backup_file_id,
                caption=caption
            )
        elif file_type == "photo":
            await client.send_photo(
                chat_id=message.chat.id,
                photo=backup_file_id,
                caption=caption
            )
        else:
            await message.reply("Unsupported file type for retrieval.")
            
    except Exception as e:
        logger.error(f"Error sending file from backup: {e}")
        await message.reply("Failed to retrieve and send the file.")

async def handle_start_command(client: Client, message: Message):
    """Handle /start command"""
    welcome_text = """
🤖 **Media Indexer Bot**

This bot automatically indexes media files and provides retrieval functionality.

**Commands:**
• `/send <filename>` - Retrieve file by filename
• `/sendid <track_id>` - Retrieve file by track ID
• `/stats` - Show database statistics

The bot automatically indexes all media files (audio, video, documents, photos) with their metadata and track information.
    """
    await message.reply(welcome_text)

async def handle_stats_command(client: Client, message: Message):
    """Handle /stats command to show database statistics"""
    try:
        stats = db.get_statistics()
        
        stats_text = f"""
📊 **Database Statistics**

• Total Files: {stats['total_files']}
• Audio Files: {stats['audio_files']}
• Video Files: {stats['video_files']}
• Documents: {stats['document_files']}
• Photos: {stats['photo_files']}
• Files with Track URLs: {stats['files_with_tracks']}
        """
        
        await message.reply(stats_text)
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        await message.reply("Failed to retrieve statistics.")

def setup_handlers(app: Client):
    """Setup all message handlers"""
    
    # Media message handlers
    app.on_message(filters.audio & ~filters.bot)(handle_media_message)
    app.on_message(filters.video & ~filters.bot)(handle_media_message)
    app.on_message(filters.document & ~filters.bot)(handle_media_message)
    app.on_message(filters.photo & ~filters.bot)(handle_media_message)
    
    # Command handlers
    app.on_message(filters.command("start"))(handle_start_command)
    app.on_message(filters.command("send"))(handle_send_command)
    app.on_message(filters.command("sendid"))(handle_sendid_command)
    app.on_message(filters.command("stats"))(handle_stats_command)
    
    logger.info("All handlers registered successfully")
