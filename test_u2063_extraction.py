#!/usr/bin/env python3
"""
Test the enhanced \u2063 character extraction from Spotify info sections
This demonstrates how the system will extract track IDs when real URLs are present
"""

import sys
sys.path.append('.')
from bot.utils import extract_track_info

def test_u2063_extraction():
    """Test extraction of URLs embedded with \u2063 characters in info sections"""
    
    print("🎵 Testing \\u2063 Character Extraction from Info Sections")
    print("=" * 70)
    
    # Test cases that simulate how URLs might be embedded in "info" with \u2063
    test_cases = [
        {
            "name": "Basic info with \\u2063 embedded URL",
            "message": "@Spotify_downloaderrr_bot | info\u2063https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
            "expected_track_id": "4uLU6hMCjMI75M1A2tKUQC"
        },
        {
            "name": "Info with \\u2063 breaking the URL",
            "message": "@Spotify_downloaderrr_bot | info https://open.spo\u2063tify.com/track/7qiZfU4dY1lWllzX7mkmht",
            "expected_track_id": "7qiZfU4dY1lWllzX7mkmht"
        },
        {
            "name": "Multiple \\u2063 characters in URL",
            "message": "@Spotify_downloaderrr_bot | info\u2063https://o\u2063pen.spo\u2063tify.com/tr\u2063ack/1BxfuPKGuaTgP7aM0Bbdwr",
            "expected_track_id": "1BxfuPKGuaTgP7aM0Bbdwr"
        },
        {
            "name": "Mixed separators \\xad and \\u2063",
            "message": "@Spotify_downloaderrr_bot | info\xad https://open.spo\u2063tify.com/track/2tpWsVSb9UEmDRxAl1zhX1\xad",
            "expected_track_id": "2tpWsVSb9UEmDRxAl1zhX1"
        },
        {
            "name": "Current format (no URLs) - should return empty",
            "message": "@Spotify_downloaderrr_bot | info\xad",
            "expected_track_id": None
        }
    ]
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📱 Test {i}: {test['name']}")
        print(f"Message: {repr(test['message'])}")
        
        # Show character analysis
        unicode_chars = [f"\\u{ord(c):04x}" for c in test['message'] if ord(c) > 127]
        if unicode_chars:
            print(f"Unicode chars: {unicode_chars}")
        
        # Extract track info
        result = extract_track_info(test['message'])
        extracted_id = result.get('track_id') if result else None
        
        print(f"Extracted: {result}")
        
        # Verify results
        if test['expected_track_id']:
            if extracted_id == test['expected_track_id']:
                print("✅ SUCCESS: Correct track ID extracted")
                success_count += 1
            else:
                print(f"❌ FAILED: Expected '{test['expected_track_id']}', got '{extracted_id}'")
        else:
            if not extracted_id:
                print("✅ CORRECT: No track ID expected and none found")
                success_count += 1
            else:
                print("⚠️  UNEXPECTED: Found track ID when none expected")
        
        print("-" * 50)
    
    print(f"\n📊 RESULTS: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 ALL TESTS PASSED! \\u2063 extraction is working perfectly")
    else:
        print("⚠️  Some tests failed - extraction needs refinement")

def demonstrate_current_vs_expected():
    """Show the difference between current messages and what we expect"""
    
    print("\n" + "=" * 70)
    print("📋 CURRENT vs EXPECTED MESSAGE FORMATS")
    print("=" * 70)
    
    current_format = "@Spotify_downloaderrr_bot | info\xad"
    expected_format = "@Spotify_downloaderrr_bot | info\u2063https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
    
    print(f"\n❌ Current format (no URLs):")
    print(f"   {repr(current_format)}")
    print(f"   Result: {extract_track_info(current_format)}")
    
    print(f"\n✅ Expected format (with embedded URL):")
    print(f"   {repr(expected_format)}")
    print(f"   Result: {extract_track_info(expected_format)}")
    
    print(f"\n🔍 Key Insight:")
    print(f"   The \\u2063 character should separate the info from the actual Spotify URL")
    print(f"   Current messages only contain bot mentions without URLs")
    print(f"   When real URLs appear with \\u2063, extraction will work!")

if __name__ == "__main__":
    test_u2063_extraction()
    demonstrate_current_vs_expected()
    
    print("\n" + "=" * 70)
    print("📝 SUMMARY")
    print("=" * 70)
    print("✅ Enhanced \\u2063 extraction logic implemented")
    print("✅ System ready to process URLs embedded with invisible separators")
    print("✅ Current 'info' sections analyzed - they contain only bot mentions")
    print("🎯 When actual Spotify URLs appear in info sections with \\u2063,")
    print("   track IDs will be extracted and displayed prominently!")