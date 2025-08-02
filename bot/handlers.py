import logging
import re
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import ChannelPrivate, ChatAdminRequired, UsernameNotOccupied
from bot.database import DatabaseManager
from bot.utils import extract_track_info, format_file_caption, get_file_metadata

logger = logging.getLogger(__name__)

# Initialize database manager
db = DatabaseManager()

# Global variable to track indexing process
indexing_process = {
    "active": False,
    "chat_id": None,
    "message_id": None,
    "total": 0,
    "processed": 0,
    "stop_requested": False
}

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

**To start indexing:**
1. For private channels: Add this bot as admin to the channel
2. For public channels: No admin access needed
3. Send any message link (t.me/channel/123) or forward any message from the channel
4. Bot will automatically start indexing from that message and show progress

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

async def handle_message_link(client: Client, message: Message):
    """Handle message links to start indexing"""
    global indexing_process
    
    if indexing_process["active"]:
        await message.reply("⚠️ Indexing is already in progress.")
        return
    
    try:
        text = message.text or message.caption or ""
        
        # Extract message link
        link_pattern = r"https://t\.me/([^/]+)/(\d+)"
        match = re.search(link_pattern, text)
        
        if match:
            channel_username = match.group(1)
            message_id = int(match.group(2))
            
            # Try to get chat info
            try:
                chat = await client.get_chat(channel_username)
                chat_id = chat.id
                chat_title = getattr(chat, 'title', None) or getattr(chat, 'username', None) or channel_username
                
                await start_indexing_process(client, message, chat_id, message_id, chat_title)
                
            except ChannelPrivate:
                await message.reply(f"""
❌ **Channel is Private**

To index this channel:
1. Add this bot as **admin** to @{channel_username}
2. Give it permission to read messages
3. Send the message link again
                """)
                
            except ChatAdminRequired:
                await message.reply(f"""
❌ **Admin Rights Required**

To index this channel:
1. Add this bot as **admin** to @{channel_username}
2. Give it permission to read messages
3. Send the message link again
                """)
                
            except UsernameNotOccupied:
                await message.reply(f"❌ Channel @{channel_username} not found.")
                
    except Exception as e:
        logger.error(f"Error handling message link: {e}")
        await message.reply("❌ Error processing message link.")



async def start_indexing_process(client: Client, message: Message, chat_id: int, start_message_id: int, chat_title: str = "Unknown"):
    """Start the indexing process for a channel"""
    global indexing_process
    
    try:
        # Check if bot has access to the channel
        try:
            chat = await client.get_chat(chat_id)
            if start_message_id is None:
                # Use a default message ID if none provided
                start_message_id = 1
                    
        except Exception as e:
            if "CHAT_ADMIN_REQUIRED" in str(e):
                await message.reply(f"""
❌ **Bot needs admin access**

To index **{chat_title}**:
1. Add this bot as admin to the channel
2. Give it permission to read messages
3. Try again
                """)
                return
            else:
                raise e
        
        # Initialize indexing process
        indexing_process.update({
            "active": True,
            "chat_id": chat_id,
            "message_id": start_message_id,
            "total": 0,
            "processed": 0,
            "stop_requested": False
        })
        
        # Send initial status
        status_msg = await message.reply(f"""
🚀 **Starting Indexing Process**

📂 **Channel:** {chat_title}
🔍 **Starting from:** Message {start_message_id}

⏳ Scanning messages...
        """)
        
        # Start indexing in background
        asyncio.create_task(index_channel_messages(client, status_msg, chat_id, start_message_id, chat_title))
        
    except Exception as e:
        logger.error(f"Error starting indexing: {e}")
        await message.reply("❌ Failed to start indexing process.")

async def index_channel_messages(client: Client, status_msg: Message, chat_id: int, start_message_id: int, chat_title: str):
    """Index messages from a channel with progress updates"""
    global indexing_process
    
    try:
        # Set initial estimate since we can't access chat history directly
        indexing_process["total"] = 100  # Conservative estimate
        
        await status_msg.edit_text(f"""
🚀 **Indexing Process Started**

📂 **Channel:** {chat_title}
🔍 **Starting from:** Message {start_message_id}

⏳ Searching for media files...
        """)
        
        # Process messages by iterating backwards from the starting message
        processed = 0
        errors = 0
        current_msg_id = start_message_id
        consecutive_failures = 0
        max_failures = 10  # Stop after 10 consecutive failed message retrievals
        
        while consecutive_failures < max_failures and not indexing_process["stop_requested"]:
            try:
                # Try to get the specific message
                try:
                    messages = await client.get_messages(chat_id, current_msg_id)
                    consecutive_failures = 0  # Reset failure count on success
                    
                    # Handle both single message and list of messages
                    msg_list = messages if isinstance(messages, list) else [messages]
                    
                    for msg in msg_list:
                        if msg and (msg.audio or msg.video or msg.document or msg.photo):
                            try:
                                await handle_media_message(client, msg)
                                processed += 1
                                indexing_process["processed"] = processed
                                
                                # Update progress every 5 files
                                if processed % 5 == 0:
                                    await status_msg.edit_text(f"""
🚀 **Indexing In Progress**

📂 **Channel:** {chat_title}
📊 **Media Files Found:** {processed}
🔍 **Current Message:** {current_msg_id}

⏳ Processing... 
                                    """)
                                    
                            except Exception as e:
                                logger.error(f"Error processing message {msg.id}: {e}")
                                errors += 1
                            
                except Exception as e:
                    # Message doesn't exist or can't be accessed
                    consecutive_failures += 1
                    if "MESSAGE_ID_INVALID" not in str(e):
                        logger.debug(f"Could not get message {current_msg_id}: {e}")
                
                # Move to previous message
                current_msg_id -= 1
                
                # Don't go below message ID 1
                if current_msg_id < 1:
                    break
                    
            except Exception as e:
                logger.error(f"Error in message iteration loop: {e}")
                consecutive_failures += 1
                current_msg_id -= 1
                
        # Final status
        if indexing_process["stop_requested"]:
            await status_msg.edit_text(f"""
⚠️ **Indexing Stopped**

📂 **Channel:** {chat_title}
📊 **Processed:** {processed} media files
❌ **Stopped by user**
            """)
        else:
            await status_msg.edit_text(f"""
✅ **Indexing Complete!**

📂 **Channel:** {chat_title}
📊 **Total Processed:** {processed} media files
❌ **Errors:** {errors}
✨ **Status:** All accessible media files indexed successfully!

Use `/send <filename>` or `/sendid <track_id>` to retrieve files.
            """)
            
    except Exception as e:
        logger.error(f"Error during indexing: {e}")
        processed = indexing_process.get("processed", 0)
        await status_msg.edit_text(f"""
❌ **Indexing Failed**

📂 **Channel:** {chat_title}
📊 **Processed:** {processed} media files
❌ **Error:** {str(e)}
        """)
    finally:
        indexing_process["active"] = False

def create_progress_bar(current: int, total: int, length: int = 20) -> str:
    """Create a visual progress bar"""
    if total == 0:
        return "█" * length
        
    filled = int((current / total) * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

async def handle_stop_index_command(client: Client, message: Message):
    """Handle /stop_index command"""
    global indexing_process
    
    if not indexing_process["active"]:
        await message.reply("ℹ️ No indexing process is currently running.")
        return
        
    indexing_process["stop_requested"] = True
    await message.reply("⚠️ Stopping indexing process...")

async def handle_forwarded_message(client: Client, message: Message):
    """Handle forwarded messages to automatically start indexing"""
    global indexing_process
    
    if message.forward_from_chat and not indexing_process["active"]:
        chat_id = message.forward_from_chat.id
        start_message_id = message.forward_from_message_id
        chat_title = message.forward_from_chat.title or message.forward_from_chat.username
        
        await start_indexing_process(client, message, chat_id, start_message_id, chat_title)

def setup_handlers(app: Client):
    """Setup all message handlers"""
    
    # Media message handlers (only for direct media, not for indexing)
    app.on_message(filters.audio & ~filters.bot & ~filters.forwarded & filters.private)(handle_media_message)
    app.on_message(filters.video & ~filters.bot & ~filters.forwarded & filters.private)(handle_media_message)
    app.on_message(filters.document & ~filters.bot & ~filters.forwarded & filters.private)(handle_media_message)
    app.on_message(filters.photo & ~filters.bot & ~filters.forwarded & filters.private)(handle_media_message)
    
    # Command handlers
    app.on_message(filters.command("start"))(handle_start_command)
    app.on_message(filters.command("send"))(handle_send_command)
    app.on_message(filters.command("sendid"))(handle_sendid_command)
    app.on_message(filters.command("stats"))(handle_stats_command)
    app.on_message(filters.command("stop_index"))(handle_stop_index_command)
    
    # Message link handler
    app.on_message(filters.text & filters.regex(r"https://t\.me/[^/]+/\d+") & ~filters.bot)(handle_message_link)
    
    # Forwarded message handler for automatic indexing
    app.on_message(filters.forwarded & ~filters.bot)(handle_forwarded_message)
    
    logger.info("All handlers registered successfully")
