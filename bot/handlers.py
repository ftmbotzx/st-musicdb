import logging
import re
import asyncio
from datetime import datetime
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import ChannelPrivate, ChatAdminRequired, UsernameNotOccupied, FloodWait
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
        
        # Forward file to backup channel with rate limiting
        backup_file_id = await forward_to_backup(client, message)
        
        # Get additional audio metadata if available
        audio_metadata = {}
        if message.audio:
            audio_metadata.update({
                "performer": message.audio.performer,
                "title": message.audio.title,
                "thumbnail": message.audio.thumbs[0].file_id if message.audio.thumbs else None
            })
        elif message.video:
            audio_metadata.update({
                "thumbnail": message.video.thumbs[0].file_id if message.video.thumbs else None
            })
        elif message.document and message.document.thumbs:
            audio_metadata.update({
                "thumbnail": message.document.thumbs[0].file_id
            })
        
        # Add rate limiting for media processing
        await asyncio.sleep(0.3)  # Small delay to prevent rate limits
        
        # Prepare comprehensive document for MongoDB
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
            "chat_title": message.chat.title or (message.chat.first_name if message.chat.first_name else "Unknown"),
            "message_id": message.id,
            "sender_id": message.from_user.id if message.from_user else None,
            "sender_username": message.from_user.username if message.from_user else None,
            "sender_first_name": message.from_user.first_name if message.from_user else None,
            "sender_last_name": message.from_user.last_name if message.from_user else None,
            "date": message.date.isoformat(),
            "is_deleted": False,
            "track_url": track_info.get("track_url"),
            "track_id": track_info.get("track_id"),
            "platform": track_info.get("platform"),
            **audio_metadata  # Include performer, title, thumbnail if available
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
    """Forward message to backup channel with proper caption and return backup file_id"""
    try:
        backup_channel_id = db.get_backup_channel_id()
        if not backup_channel_id:
            logger.warning("No backup channel configured")
            return None
            
        # Extract track info from original message caption/text
        track_info = extract_track_info(message.text or message.caption or "")
        
        # Create detailed caption with track ID prominently displayed
        # Pass track_info to ensure track ID appears in backup caption
        backup_caption = format_file_caption(message, include_track_id=True, track_info_override=track_info)
        
        # Send file to backup channel with proper caption based on file type
        forwarded_msg = None
        
        try:
            if message.audio:
                forwarded_msg = await client.send_audio(
                    chat_id=backup_channel_id,
                    audio=message.audio.file_id,
                    caption=backup_caption,
                    duration=message.audio.duration,
                    performer=message.audio.performer,
                    title=message.audio.title
                )
            elif message.video:
                forwarded_msg = await client.send_video(
                    chat_id=backup_channel_id,
                    video=message.video.file_id,
                    caption=backup_caption,
                    duration=message.video.duration,
                    width=message.video.width,
                    height=message.video.height
                )
            elif message.document:
                forwarded_msg = await client.send_document(
                    chat_id=backup_channel_id,
                    document=message.document.file_id,
                    caption=backup_caption,
                    file_name=message.document.file_name
                )
            elif message.photo:
                forwarded_msg = await client.send_photo(
                    chat_id=backup_channel_id,
                    photo=message.photo.file_id,
                    caption=backup_caption
                )
            
            # Add rate limiting delay to avoid FloodWait errors
            await asyncio.sleep(0.5)  # Small delay between operations
                
        except FloodWait as e:
            logger.warning(f"Rate limit hit, waiting {e.value} seconds")
            await asyncio.sleep(float(e.value))
            # Retry the operation
            return await forward_to_backup(client, message)
        
        if forwarded_msg:
            backup_file_data = get_file_metadata(forwarded_msg)
            return backup_file_data["file_id"] if backup_file_data else None
            
    except Exception as e:
        logger.error(f"Error sending to backup channel: {e}")
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
                # Handle different chat types
                if hasattr(chat, 'id'):
                    chat_id = chat.id
                else:
                    # For ChatPreview objects, try to extract ID from username
                    try:
                        chat_full = await client.get_chat(f"@{channel_username}")
                        chat_id = chat_full.id
                    except:
                        await message.reply(f"❌ Cannot access channel @{channel_username}. Please make sure the bot has access.")
                        return
                
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
        
        # Initialize tracking variables
        total_messages = start_message_id  # Total messages in channel  
        fetched_messages = 0
        processed = 0
        errors = 0
        current_msg_id = start_message_id
        consecutive_failures = 0
        max_failures = 50  # Allow more failures before stopping
        max_processed = 1000  # Process up to 1000 messages
        
        while consecutive_failures < max_failures and processed < max_processed and not indexing_process["stop_requested"]:
            try:
                # Try to get the specific message
                try:
                    messages = await client.get_messages(chat_id, current_msg_id)
                    consecutive_failures = 0  # Reset failure count on success
                    fetched_messages += 1
                    
                    # Handle both single message and list of messages
                    msg_list = messages if isinstance(messages, list) else [messages]
                    
                    for msg in msg_list:
                        if msg and (msg.audio or msg.video or msg.document or msg.photo):
                            try:
                                await handle_media_message(client, msg)
                                processed += 1
                                indexing_process["processed"] = processed
                                
                                # Update progress every 5 files or every 20 messages
                                if processed % 5 == 0 or fetched_messages % 20 == 0:
                                    progress_percentage = min(100, (processed / 100) * 100) if processed < 100 else 100
                                    
                                    progress_text = f"""
🚀 **Indexing in Progress**

📂 **Channel:** {chat_title}
📊 **Progress:** {processed} files processed
📨 **Current Message:** {current_msg_id}
📥 **Scanned:** {fetched_messages} messages
❌ **Errors:** {errors}

⏳ **Status:** {"Processing..." if not indexing_process["stop_requested"] else "Stopping..."}

Use /cancel to stop indexing
                                    """
                                    
                                    await status_msg.edit_text(progress_text)
                                    
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
            total_fetched = start_message_id - current_msg_id
            skipped_final = total_fetched - processed
            final_status = create_final_status(
                processed=processed,
                errors=errors,
                chat_title=chat_title,
                total_messages=start_message_id,
                fetched_messages=total_fetched,
                skipped=skipped_final
            )
            await status_msg.edit_text(f"```\n{final_status}\n```")
            
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

def create_fancy_progress_status(processed: int, errors: int, current_msg_id: int, chat_title: str, total_messages: int, fetched_messages: int, skipped: int = 0) -> str:
    """Create a fancy progress status display"""
    
    # Calculate percentage based on fetched vs total messages
    percentage = int((fetched_messages / total_messages) * 100) if total_messages > 0 else 0
    
    status_text = f"""╔════❰ ɪɴᴅᴇxɪɴɢ sᴛᴀᴛᴜs  ❱═❍⊱❁
║╭━━━━━━━━━━━━━━━➣
║┣⪼𖨠 ᴄʜᴀɴɴᴇʟ ɴᴀᴍᴇ:  {chat_title}
║┃
║┣⪼𖨠 ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:  {total_messages}
║┃
║┣⪼𖨠 ғᴇᴛᴄʜᴇᴅ ᴍᴇssᴀɢᴇs:  {fetched_messages}
║┃
║┣⪼𖨠 ɪɴᴅᴇxᴇᴅ ᴍᴇᴅɪᴀ:  {processed}
║┃
║┣⪼𖨠 ᴇʀʀᴏʀ ᴄᴏᴜɴᴛ:  {errors}
║┃
║┣⪼𖨠 sᴋɪᴘᴘᴇᴅ ᴍᴇssᴀɢᴇs:  {skipped}
║┃
║┣⪼𖨠 ᴄᴜʀʀᴇɴᴛ ᴍᴇssᴀɢᴇ:  {current_msg_id}
║┃
║┣⪼𖨠 ᴄᴜʀʀᴇɴᴛ sᴛᴀᴛᴜs:  ɪɴᴅᴇxɪɴɢ
║┃
║┣⪼𖨠 ᴘᴇʀᴄᴇɴᴛᴀɢᴇ:  {percentage}%
║╰━━━━━━━━━━━━━━━➣ 
╚════❰ ᴘʀᴏᴄᴇssɪɴɢ ❱══❍⊱❁"""
    
    return status_text

def create_final_status(processed: int, errors: int, chat_title: str, total_messages: int, fetched_messages: int, skipped: int = 0) -> str:
    """Create final completion status"""
    
    status_text = f"""╔════❰ ɪɴᴅᴇxɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇ  ❱═❍⊱❁
║╭━━━━━━━━━━━━━━━➣
║┣⪼𖨠 ᴄʜᴀɴɴᴇʟ ɴᴀᴍᴇ:  {chat_title}
║┃
║┣⪼𖨠 ᴛᴏᴛᴀʟ ᴍᴇssᴀɢᴇs:  {total_messages}
║┃
║┣⪼𖨠 ғᴇᴛᴄʜᴇᴅ ᴍᴇssᴀɢᴇs:  {fetched_messages}
║┃
║┣⪼𖨠 ɪɴᴅᴇxᴇᴅ ᴍᴇᴅɪᴀ:  {processed}
║┃
║┣⪼𖨠 ᴇʀʀᴏʀ ᴄᴏᴜɴᴛ:  {errors}
║┃
║┣⪼𖨠 sᴋɪᴘᴘᴇᴅ ᴍᴇssᴀɢᴇs:  {skipped}
║┃
║┣⪼𖨠 ᴄᴜʀʀᴇɴᴛ sᴛᴀᴛᴜs:  ᴄᴏᴍᴘʟᴇᴛᴇᴅ
║┃
║┣⪼𖨠 ᴘᴇʀᴄᴇɴᴛᴀɢᴇ:  100%
║╰━━━━━━━━━━━━━━━➣ 
╚════❰ ғɪɴɪsʜᴇᴅ ❱══❍⊱❁

Use /send <filename> or /sendid <track_id> to retrieve files."""
    
    return status_text

async def handle_stop_index_command(client: Client, message: Message):
    """Handle /stop_index command"""
    global indexing_process
    
    if not indexing_process["active"]:
        await message.reply("ℹ️ No indexing process is currently running.")
        return
        
    indexing_process["stop_requested"] = True
    await message.reply("⚠️ Stopping indexing process...")

async def handle_db_command(client: Client, message: Message):
    """Handle /db command to export database as PDF"""
    try:
        await message.reply("📊 Generating database export PDF... This may take a few moments.")
        
        # Get all files from database
        files = db.get_all_files()
        
        if not files:
            await message.reply("📁 Database is empty. No files to export.")
            return
        
        # Generate PDF
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from datetime import datetime
        import tempfile
        import os
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
        
        # Create PDF document
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, 
                               rightMargin=72, leftMargin=72, 
                               topMargin=72, bottomMargin=18)
        
        # Container for PDF elements
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            alignment=1  # Center
        )
        
        # Title
        title = Paragraph("📊 Media Indexer Database Export", title_style)
        story.append(title)
        
        # Statistics
        stats = db.get_statistics()
        stats_text = f"""
        <b>Database Statistics:</b><br/>
        • Total Files: {stats['total_files']}<br/>
        • Audio Files: {stats['audio_files']}<br/>
        • Video Files: {stats['video_files']}<br/>
        • Document Files: {stats['document_files']}<br/>
        • Photo Files: {stats['photo_files']}<br/>
        • Files with Track URLs: {stats['files_with_tracks']}<br/>
        • Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        stats_para = Paragraph(stats_text, styles['Normal'])
        story.append(stats_para)
        story.append(Spacer(1, 20))
        
        # Prepare table data
        data = [['#', 'File Name', 'Type', 'Size (MB)', 'Duration', 'Track ID', 'Source', 'Date']]
        
        for i, file_doc in enumerate(files[:1000], 1):  # Limit to 1000 files for PDF
            file_name = file_doc.get('file_name', 'Unknown')[:30]  # Truncate long names
            file_type = file_doc.get('file_type', 'Unknown')
            file_size = file_doc.get('file_size', 0)
            size_mb = f"{round(file_size / (1024 * 1024), 2):.2f}" if file_size else "0"
            duration = file_doc.get('duration', 0)
            duration_str = f"{duration//60:02d}:{duration%60:02d}" if duration else "N/A"
            track_id = file_doc.get('track_id', 'N/A')[:20]  # Truncate long IDs
            source = file_doc.get('chat_title', 'Unknown')[:20]
            date = file_doc.get('date', '')[:10]  # Just date part
            
            data.append([
                str(i), file_name, file_type, size_mb, 
                duration_str, track_id, source, date
            ])
        
        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        
        # Build PDF
        doc.build(story)
        
        # Send PDF file
        await client.send_document(
            chat_id=message.chat.id,
            document=pdf_path,
            file_name=f"database_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            caption=f"📊 Database Export\n\n📁 Total Files: {len(files)}\n📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Clean up temporary file
        os.unlink(pdf_path)
        
        await message.reply("✅ Database export completed successfully!")
        
    except Exception as e:
        logger.error(f"Error generating database export: {e}")
        await message.reply(f"❌ Failed to generate database export: {str(e)}")

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
    app.on_message(filters.command("cancel"))(handle_stop_index_command)  # /cancel works same as /stop_index
    app.on_message(filters.command("db"))(handle_db_command)
    
    # Message link handler
    app.on_message(filters.text & filters.regex(r"https://t\.me/[^/]+/\d+") & ~filters.bot)(handle_message_link)
    
    # Forwarded message handler for automatic indexing
    app.on_message(filters.forwarded & ~filters.bot)(handle_forwarded_message)
    
    logger.info("All handlers registered successfully")
