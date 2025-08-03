#!/usr/bin/env python3
"""
Test script to validate the new minimal caption generation logic.
"""

# Test the track info extraction and minimal caption generation
test_caption = """O Bedardeya Lofi Flip
Arijit Singh
| info: https://open.spotify.com/track/4Ujv2PgOK79mtAHd5qezhE"""

def extract_track_info_test(caption: str):
    """Test version of extract_track_info function"""
    import re
    
    track_info = {}
    
    if not caption:
        return track_info
    
    try:
        # Extract URLs (simplified for test)
        spotify_pattern = r'https?://open\.spotify\.com/track/([a-zA-Z0-9]+)'
        match = re.search(spotify_pattern, caption)
        if match:
            track_info["track_url"] = match.group(0)
            track_info["track_id"] = match.group(1)
            track_info["platform"] = "spotify"
        
        # Extract title and artist from caption lines
        caption_lines = caption.split('\n')
        
        # Title from first line (clean it from extra characters)
        if len(caption_lines) > 0:
            title_line = caption_lines[0].strip()
            # Remove common prefixes and clean the title
            title_line = re.sub(r'^[🎵🎶🎧]*\s*', '', title_line)  # Remove music emojis
            title_line = re.sub(r'\s*[\|\-\–\—]\s*.*$', '', title_line)  # Remove everything after | - – —
            if title_line:
                track_info["title"] = title_line.strip()
        
        # Artist from second line (if exists)
        if len(caption_lines) > 1:
            artist_line = caption_lines[1].strip()
            # Remove common prefixes and clean the artist
            artist_line = re.sub(r'^[👤🎤🎙️]*\s*', '', artist_line)  # Remove person/mic emojis
            artist_line = re.sub(r'\s*[\|\-\–\—]\s*.*$', '', artist_line)  # Remove everything after separators
            if artist_line and not any(x in artist_line.lower() for x in ['http', 'www', '.com', 'info']):
                track_info["artist"] = artist_line.strip()
        
        return track_info
        
    except Exception as e:
        print(f"Error extracting track info: {e}")
        return {}

def generate_minimal_caption_test(entry):
    """Test version of generate_minimal_caption function"""
    title = entry.get('title', 'Unknown Title')
    artist = entry.get('artist', 'Unknown Artist') 
    track_id = entry.get('track_id', 'N/A')
    
    return (
        f"🎵 {title}\n"
        f"👤 {artist}\n"
        f"🆔 {track_id}"
    )

if __name__ == "__main__":
    print("Testing caption extraction and generation...")
    print(f"Input caption:\n{test_caption}")
    print("\n" + "="*50)
    
    # Test extraction
    extracted = extract_track_info_test(test_caption)
    print(f"Extracted data: {extracted}")
    
    # Test minimal caption generation
    minimal_caption = generate_minimal_caption_test(extracted)
    print(f"\nGenerated minimal caption:\n{minimal_caption}")
    
    print("\n" + "="*50)
    print("Expected output:")
    print("🎵 O Bedardeya Lofi Flip")
    print("👤 Arijit Singh") 
    print("🆔 4Ujv2PgOK79mtAHd5qezhE")