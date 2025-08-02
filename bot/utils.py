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
            # Get the largest photo size
            try:
                # message.photo is typically a list of PhotoSize objects
                if isinstance(message.photo, list):
                    photo = max(message.photo, key=lambda x: getattr(x, 'file_size', 0) or 0)
                else:
                    # If it's a single PhotoSize object
                    photo = message.photo
            except (TypeError, AttributeError):
                # Fallback: use the photo object directly
                photo = message.photo
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
        
        logger.info(f"Original caption: {repr(caption)}")
        
        # Try multiple extraction approaches without losing URLs
        urls = []
        
        # Strategy 1: Handle multiple separator characters for proper link extraction
        comprehensive_clean = caption
        
        # Handle both common separator characters that break URLs in source channels
        separator_chars = [
            '\u2063',  # Invisible separator - preferred character for link extraction
            '\u00ad',  # Soft hyphen - commonly present in messages
        ]
        
        # Replace all separator characters to reconstruct proper URLs
        for separator_char in separator_chars:
            comprehensive_clean = comprehensive_clean.replace(separator_char, '')
        
        # Also remove extra spaces that might break URLs
        comprehensive_clean = re.sub(r'\s+', ' ', comprehensive_clean)
        
        logger.info(f"Cleaned caption: {repr(comprehensive_clean)}")
        
        # Strategy 2: Extract from comprehensively cleaned text
        spotify_pattern = r'https?://open\.spotify\.com/track/[a-zA-Z0-9]+'
        clean_matches = re.findall(spotify_pattern, comprehensive_clean)
        urls.extend(clean_matches)
        
        # Strategy 3: Direct regex on original text (in case cleaning broke something)
        original_matches = re.findall(spotify_pattern, caption)
        urls.extend(original_matches)
        
        # Strategy 4: Enhanced extraction from "info" sections with hidden/embedded URLs
        # The "info" text may contain encoded or hidden Spotify URLs
        info_patterns = [
            r'info[^\n]*?(https?://[^\s\)\n]+)',
            r'Info[^\n]*?(https?://[^\s\)\n]+)',
            r'INFO[^\n]*?(https?://[^\s\)\n]+)',
            r'\|\s*info[^\n]*?(https?://[^\s\)\n]+)',
        ]
        
        for pattern in info_patterns:
            matches = re.findall(pattern, comprehensive_clean, re.IGNORECASE)
            urls.extend(matches)
            # Also try on original in case the pattern exists there
            original_pattern_matches = re.findall(pattern, caption, re.IGNORECASE)
            urls.extend(original_pattern_matches)
        
        # Strategy 5: Extract URLs that might be encoded/hidden in the "info" section
        # Look for patterns where info might contain encoded URLs
        if 'info' in comprehensive_clean.lower():
            # Check if there are any characters after "info" that might be encoded URLs
            info_section_patterns = [
                r'info[\s]*([^\s\n]*)',  # Capture anything after info
                r'\|\s*info[\s]*([^\s\n]*)',  # Capture anything after | info
            ]
            
            for pattern in info_section_patterns:
                info_matches = re.findall(pattern, comprehensive_clean, re.IGNORECASE)
                for info_content in info_matches:
                    if info_content and len(info_content) > 10:  # Potential encoded URL
                        logger.info(f"Found potential encoded content in info: {repr(info_content)}")
                        
                        # Try to decode or reconstruct URLs from the info content
                        # Look for patterns that might be Spotify track IDs or encoded URLs
                        spotify_id_pattern = r'[a-zA-Z0-9]{22}'  # Spotify track IDs are 22 characters
                        potential_ids = re.findall(spotify_id_pattern, info_content)
                        
                        for track_id in potential_ids:
                            if len(track_id) == 22:  # Valid Spotify track ID length
                                reconstructed_url = f"https://open.spotify.com/track/{track_id}"
                                urls.append(reconstructed_url)
                                logger.info(f"Reconstructed URL from info content: {reconstructed_url}")
        
        # Strategy 5: General URL extraction from both original and cleaned text
        general_patterns = [
            r'https?://[^\s\)\n]+',
            r'https?://open\.spotify\.com/track/[a-zA-Z0-9]+',
        ]
        
        for pattern in general_patterns:
            # From original caption
            original_urls = re.findall(pattern, caption)
            urls.extend(original_urls)
            # From cleaned caption  
            clean_urls = re.findall(pattern, comprehensive_clean)
            urls.extend(clean_urls)
        
        # Strategy 6: Split by whitespace and check each part from cleaned text
        words = comprehensive_clean.split()
        for word in words:
            # Remove common trailing chars and check
            clean_word = word.rstrip('.,!?;)')
            if 'spotify.com/track/' in clean_word:
                urls.append(clean_word)
        
        # Strategy 7: Reconstruct broken URLs from fragments
        # Look for "https ://open.spotify.com" patterns (broken by spaces)
        broken_patterns = [
            r'https\s*:\s*//\s*open\.\s*spotify\.\s*com\s*/\s*track\s*/\s*([a-zA-Z0-9]+)',
            r'https://open\.\s*spotify\.\s*com\s*/\s*track\s*/\s*([a-zA-Z0-9]+)',
            r'https://open\.spotify\.\s*com\s*/\s*track\s*/\s*([a-zA-Z0-9]+)',
        ]
        
        for pattern in broken_patterns:
            broken_matches = re.findall(pattern, caption)
            for track_id in broken_matches:
                reconstructed = f"https://open.spotify.com/track/{track_id}"
                urls.append(reconstructed)
                logger.info(f"Reconstructed broken URL: {reconstructed}")
            
            # Also try on cleaned text
            clean_broken_matches = re.findall(pattern, comprehensive_clean)
            for track_id in clean_broken_matches:
                reconstructed = f"https://open.spotify.com/track/{track_id}"
                urls.append(reconstructed)
                logger.info(f"Reconstructed broken URL from cleaned text: {reconstructed}")
        
        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys([url for url in urls if url]))
        logger.info(f"Found URLs: {unique_urls}")
        
        # Also check for partial URLs that might be split
        if not unique_urls and 'spotify.com' in caption:
            logger.warning(f"Found 'spotify.com' in caption but no complete URLs: {repr(caption)}")
            # Try to reconstruct URL if it's fragmented
            if 'open.spotify.com/track/' in caption:
                # Extract potential track ID after the pattern
                track_match = re.search(r'open\.spotify\.com/track/([a-zA-Z0-9]+)', caption)
                if track_match:
                    reconstructed_url = f"https://open.spotify.com/track/{track_match.group(1)}"
                    unique_urls.append(reconstructed_url)
                    logger.info(f"Reconstructed URL: {reconstructed_url}")
        
        for url in unique_urls:
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

def format_file_caption(message_or_doc, include_track_id=False, track_info_override=None) -> str:
    """Format a detailed caption for file"""
    try:
        caption_parts = []
        
        # Check if it's a Message object or a dict
        if hasattr(message_or_doc, 'audio') or hasattr(message_or_doc, 'video') or hasattr(message_or_doc, 'document') or hasattr(message_or_doc, 'photo'):
            # It's a Message object - extract info directly
            file_metadata = get_file_metadata(message_or_doc)
            if not file_metadata:
                return "📁 Media File"
            
            file_name = file_metadata.get("file_name", "Unknown")
            file_type = file_metadata.get("file_type", "file").title()
            file_size = file_metadata.get("file_size")
            duration = file_metadata.get("duration")
            width = file_metadata.get("width")
            height = file_metadata.get("height")
            
            # Extract track info from message text/caption or use override
            if track_info_override:
                track_info = track_info_override
            else:
                text_content = getattr(message_or_doc, 'text', '') or getattr(message_or_doc, 'caption', '')
                track_info = extract_track_info(text_content)
            
            track_url = track_info.get("track_url")
            track_id = track_info.get("track_id")
            
            # Source info from message
            chat_title = message_or_doc.chat.title if message_or_doc.chat else "Unknown Channel"
            date = message_or_doc.date
            
        else:
            # It's a dict - use directly
            file_name = message_or_doc.get("file_name", "Unknown")
            file_type = message_or_doc.get("file_type", "file").title()
            file_size = message_or_doc.get("file_size")
            duration = message_or_doc.get("duration")
            width = message_or_doc.get("width")
            height = message_or_doc.get("height")
            
            # Use override track info if provided, otherwise use from document
            if track_info_override:
                track_url = track_info_override.get("track_url")
                track_id = track_info_override.get("track_id")
            else:
                track_url = message_or_doc.get("track_url")
                track_id = message_or_doc.get("track_id")
            
            chat_title = message_or_doc.get("chat_title", "Unknown Channel")
            date = message_or_doc.get("date")
        
        # Track ID prominently at the top if requested (for backup channel)
        if include_track_id and track_id:
            caption_parts.append(f"🆔 **TRACK ID: {track_id}**")
            caption_parts.append("━━━━━━━━━━━━━━━━━━━━")
        
        caption_parts.append(f"🎵 **{file_name}**")
        caption_parts.append(f"📁 Type: {file_type}")
        
        # File size
        if file_size:
            size_mb = round(file_size / (1024 * 1024), 2)
            caption_parts.append(f"💾 Size: {size_mb} MB")
        
        # Duration for audio/video
        if duration:
            minutes = duration // 60
            seconds = duration % 60
            caption_parts.append(f"🕒 Duration: {minutes:02d}:{seconds:02d}")
        
        # Dimensions for video/photo
        if width and height:
            caption_parts.append(f"📐 Resolution: {width}x{height}")
        
        # Track information
        if track_url:
            caption_parts.append(f"🔗 Track: {track_url}")
        if track_id and not include_track_id:  # Don't repeat if already shown at top
            caption_parts.append(f"🆔 ID: {track_id}")
        
        # Source information  
        caption_parts.append(f"📍 Source: {chat_title}")
        
        # Date
        if date:
            if hasattr(date, 'strftime'):
                formatted_date = date.strftime("%Y-%m-%d")
                caption_parts.append(f"📅 Date: {formatted_date}")
            elif isinstance(date, str):
                try:
                    from datetime import datetime
                    parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    formatted_date = parsed_date.strftime("%Y-%m-%d")
                    caption_parts.append(f"📅 Date: {formatted_date}")
                except:
                    pass
        
        # Join all parts
        return "\n".join(caption_parts)
        
    except Exception as e:
        logger.error(f"Error formatting caption: {e}")
        return "📁 Media File"

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
