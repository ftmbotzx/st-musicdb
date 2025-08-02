import re
import logging
from typing import Dict, Optional
from pyrogram.types import Message
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_file_metadata(message: Message) -> Optional[Dict]:
    """Extract file metadata from message based on its type"""
    try:
        file_data = {}
        
        if message.audio:
            file_data = {
                "file_id": message.audio.file_id,
                "file_unique_id": message.audio.file_unique_id,
                "file_name": message.audio.file_name or "Unknown Audio",
                "file_type": "audio",
                "mime_type": message.audio.mime_type,
                "file_size": message.audio.file_size,
                "duration": message.audio.duration
            }
            
        elif message.video:
            file_data = {
                "file_id": message.video.file_id,
                "file_unique_id": message.video.file_unique_id,
                "file_name": message.video.file_name or "Unknown Video",
                "file_type": "video",
                "mime_type": message.video.mime_type,
                "file_size": message.video.file_size,
                "duration": message.video.duration,
                "width": message.video.width,
                "height": message.video.height
            }
            
        elif message.document:
            file_data = {
                "file_id": message.document.file_id,
                "file_unique_id": message.document.file_unique_id,
                "file_name": message.document.file_name or "Unknown Document",
                "file_type": "document",
                "mime_type": message.document.mime_type,
                "file_size": message.document.file_size
            }
            
        elif message.photo:
            # Get the largest photo size (message.photo is a list of PhotoSize objects)
            photo = max(message.photo, key=lambda x: getattr(x, 'file_size', 0) or 0)
            file_data = {
                "file_id": photo.file_id,
                "file_unique_id": photo.file_unique_id,
                "file_name": f"photo_{message.id}.jpg",
                "file_type": "photo",
                "file_size": photo.file_size,
                "width": photo.width,
                "height": photo.height
            }
        
        return file_data if file_data else None
        
    except Exception as e:
        logger.error(f"Error extracting file metadata: {e}")
        return None

def extract_track_info(caption: str) -> Dict:
    """Extract track URL and ID from caption text links"""
    track_info = {}
    
    if not caption:
        return track_info
    
    try:
        # Patterns for different music platforms
        patterns = {
            "spotify": r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)",
            "jiosaavn": r"https?://(?:www\.)?jiosaavn\.com/song/[^/]+/([a-zA-Z0-9]+)",
            "youtube": r"https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
            "youtu.be": r"https?://youtu\.be/([a-zA-Z0-9_-]+)",
            "soundcloud": r"https?://soundcloud\.com/[\w-]+/[\w-]+",
            "apple_music": r"https?://music\.apple\.com/[^/]+/album/[^/]+/([0-9]+)"
        }
        
        # Search for URLs in caption
        url_pattern = r"https?://[^\s\)]+"
        urls = re.findall(url_pattern, caption)
        
        for url in urls:
            for platform, pattern in patterns.items():
                match = re.search(pattern, url)
                if match:
                    track_info["track_url"] = url
                    
                    # Extract track ID based on platform
                    if platform in ["spotify", "jiosaavn", "youtube", "youtu.be", "apple_music"]:
                        track_info["track_id"] = match.group(1)
                    else:
                        # For platforms like SoundCloud, use the full URL as ID
                        track_info["track_id"] = url.split("/")[-1]
                    
                    track_info["platform"] = platform
                    break
            
            if track_info:
                break
        
        return track_info
        
    except Exception as e:
        logger.error(f"Error extracting track info: {e}")
        return {}

def format_file_caption(file_doc: Dict) -> str:
    """Format a custom caption for file retrieval"""
    try:
        caption_parts = []
        
        # File information
        file_name = file_doc.get("file_name", "Unknown")
        file_type = file_doc.get("file_type", "file").title()
        
        caption_parts.append(f"🎵 **{file_name}**")
        caption_parts.append(f"📁 Type: {file_type}")
        
        # File size
        file_size = file_doc.get("file_size")
        if file_size:
            size_mb = round(file_size / (1024 * 1024), 2)
            caption_parts.append(f"💾 Size: {size_mb} MB")
        
        # Duration for audio/video
        duration = file_doc.get("duration")
        if duration:
            minutes = duration // 60
            seconds = duration % 60
            caption_parts.append(f"🕒 Duration: {minutes:02d}:{seconds:02d}")
        
        # Dimensions for video/photo
        width = file_doc.get("width")
        height = file_doc.get("height")
        if width and height:
            caption_parts.append(f"📐 Resolution: {width}x{height}")
        
        # Track information
        track_url = file_doc.get("track_url")
        track_id = file_doc.get("track_id")
        
        if track_url:
            # Determine platform from URL
            if "spotify.com" in track_url:
                caption_parts.append(f"🎵 [Spotify Track]({track_url})")
            elif "jiosaavn.com" in track_url:
                caption_parts.append(f"🎵 [JioSaavn Track]({track_url})")
            elif "youtube.com" in track_url or "youtu.be" in track_url:
                caption_parts.append(f"🎵 [YouTube Track]({track_url})")
            elif "soundcloud.com" in track_url:
                caption_parts.append(f"🎵 [SoundCloud Track]({track_url})")
            else:
                caption_parts.append(f"🔗 [Track Link]({track_url})")
        
        if track_id:
            caption_parts.append(f"🆔 Track ID: `{track_id}`")
        
        # Source information
        chat_title = file_doc.get("chat_title")
        sender_username = file_doc.get("sender_username")
        
        if chat_title:
            caption_parts.append(f"📍 Source: {chat_title}")
        
        if sender_username:
            caption_parts.append(f"👤 Uploaded by: @{sender_username}")
        
        # Date
        date = file_doc.get("date")
        if date:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                caption_parts.append(f"📅 Date: {formatted_date}")
            except:
                pass
        
        return "\n".join(caption_parts)
        
    except Exception as e:
        logger.error(f"Error formatting caption: {e}")
        return f"📁 {file_doc.get('file_name', 'Unknown File')}"

def format_duration(seconds: int) -> str:
    """Format duration in seconds to MM:SS format"""
    if not seconds:
        return "00:00"
    
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def format_file_size(bytes_size: int) -> str:
    """Format file size in bytes to human readable format"""
    if not bytes_size:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size = int(bytes_size / 1024)
    
    return f"{bytes_size:.1f} TB"

def is_valid_track_url(url: str) -> bool:
    """Validate if URL is a supported track URL"""
    if not url:
        return False
    
    supported_domains = [
        "spotify.com",
        "jiosaavn.com", 
        "youtube.com",
        "youtu.be",
        "soundcloud.com",
        "music.apple.com"
    ]
    
    try:
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in supported_domains)
    except:
        return False
