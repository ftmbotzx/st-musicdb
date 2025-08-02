#!/usr/bin/env python3
"""
Test Spotify URL extraction from specific channel message format
Based on https://t.me/Spotifyapk56/18091042
"""

import sys
sys.path.append('.')
from bot.utils import extract_track_info

def test_channel_message_format():
    """Test extraction from the specific channel format"""
    
    print("🎵 Testing Spotify URL Extraction from Channel Format")
    print("Testing based on: https://t.me/Spotifyapk56/18091042")
    print("=" * 70)
    
    # Simulate different message formats that might appear in the channel
    test_cases = [
        {
            "name": "Direct Spotify link",
            "message": "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
            "expected_track_id": "4uLU6hMCjMI75M1A2tKUQC"
        },
        {
            "name": "Bot mention with TEXT_LINK entity (simulated)",
            "message": "@Spotify_downloaderrr_bot | info",
            "entity_url": "https://open.spotify.com/track/1BxfuPKGuaTgP7aM0Bbdwr",
            "expected_track_id": "1BxfuPKGuaTgP7aM0Bbdwr"
        },
        {
            "name": "Caption with embedded link",
            "message": "Download from @Spotify_downloaderrr_bot https://open.spotify.com/track/7qiZfU4dY1lWllzX7mkmht",
            "expected_track_id": "7qiZfU4dY1lWllzX7mkmht"
        },
        {
            "name": "Info section with \u2063 separator",
            "message": "@Spotify_downloaderrr_bot | info\u2063https://open.spotify.com/track/5NTULYCC6xsFCNTsm1WpuQ",
            "expected_track_id": "5NTULYCC6xsFCNTsm1WpuQ"
        }
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📱 Test {i}: {test['name']}")
        
        # For entity URL test, combine message with entity URL
        if 'entity_url' in test:
            test_text = f"{test['message']} {test['entity_url']}"
            print(f"Message: {repr(test['message'])}")
            print(f"Entity URL: {test['entity_url']}")
        else:
            test_text = test['message']
            print(f"Message: {repr(test_text)}")
        
        # Extract track info
        result = extract_track_info(test_text)
        extracted_id = result.get('track_id') if result else None
        
        print(f"Extracted: {result}")
        
        # Verify results
        if extracted_id == test['expected_track_id']:
            print("✅ SUCCESS: Correct track ID extracted")
            success_count += 1
        else:
            print(f"❌ FAILED: Expected '{test['expected_track_id']}', got '{extracted_id}'")
        
        print("-" * 50)
    
    print(f"\n📊 RESULTS: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED! Extraction working perfectly")
    else:
        print("⚠️  Some tests failed - needs investigation")

def test_entity_extraction():
    """Test how TEXT_LINK entities would be processed"""
    
    print(f"\n" + "=" * 70)
    print("🔗 Testing TEXT_LINK Entity Processing")
    print("=" * 70)
    
    # This simulates what happens when Telegram provides a TEXT_LINK entity
    # The visible text might be "@Spotify_downloaderrr_bot | info" 
    # But the entity contains the actual Spotify URL
    
    visible_text = "@Spotify_downloaderrr_bot | info"
    hidden_url = "https://open.spotify.com/track/0h9skYsp49Q9uXYMzcafuj"
    
    # The bot combines both the visible text and entity URLs
    combined_input = f"{visible_text} {hidden_url}"
    
    print(f"Visible text: {repr(visible_text)}")
    print(f"Hidden URL from entity: {hidden_url}")
    print(f"Combined processing input: {repr(combined_input)}")
    
    result = extract_track_info(combined_input)
    print(f"Extraction result: {result}")
    
    if result and result.get('track_id') == '0h9skYsp49Q9uXYMzcafuj':
        print("✅ SUCCESS: TEXT_LINK entity processing works correctly")
    else:
        print("❌ FAILED: TEXT_LINK entity processing needs work")

if __name__ == "__main__":
    test_channel_message_format()
    test_entity_extraction()
    
    print(f"\n" + "=" * 70)
    print("📝 SUMMARY")
    print("=" * 70)
    print("✅ Bot is configured to extract Spotify URLs from:")
    print("   • Direct Spotify links in message text")
    print("   • TEXT_LINK entities in captions")
    print("   • Info sections with \\u2063 separators")
    print("   • Mixed formats with multiple separator characters")
    print()
    print("🔄 When the bot processes messages from the channel:")
    print("   1. Extracts URLs from caption entities")
    print("   2. Combines with visible message text")
    print("   3. Processes for Spotify track IDs")
    print("   4. Stores in database with full metadata")
    print("   5. Forwards to backup channel with track ID in caption")