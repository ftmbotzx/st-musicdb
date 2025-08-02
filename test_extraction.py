#!/usr/bin/env python3
"""Test script to verify link extraction functionality"""

import sys
import os
sys.path.append('.')

from bot.utils import extract_track_info

def test_link_extraction():
    """Test various link extraction scenarios"""
    
    # Test cases with different separator characters
    test_cases = [
        {
            "name": "URL with \\xad (soft hyphen)",
            "caption": "Check this: https://open.spo\xadtify.com/track/4uLU6hMCjMI75M1A2tKUQC | info\xad",
            "expected_track_id": "4uLU6hMCjMI75M1A2tKUQC"
        },
        {
            "name": "URL with \\u2063 (invisible separator)",
            "caption": "Check this: https://open.spo\u2063tify.com/track/4uLU6hMCjMI75M1A2tKUQC | info",
            "expected_track_id": "4uLU6hMCjMI75M1A2tKUQC"
        },
        {
            "name": "Clean URL without separators",
            "caption": "Check this: https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC | info",
            "expected_track_id": "4uLU6hMCjMI75M1A2tKUQC"
        },
        {
            "name": "No URL in caption",
            "caption": "@Spotify_downloaderrr_bot | info\xad",
            "expected_track_id": None
        }
    ]
    
    print("🔍 Testing Link Extraction Functionality")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print(f"Caption: {repr(test_case['caption'])}")
        
        # Extract track info
        result = extract_track_info(test_case['caption'])
        
        print(f"Result: {result}")
        
        # Check if extraction worked as expected
        if test_case['expected_track_id']:
            if result.get('track_id') == test_case['expected_track_id']:
                print("✅ PASS - Track ID extracted correctly")
            else:
                print("❌ FAIL - Track ID not extracted or incorrect")
        else:
            if not result.get('track_id'):
                print("✅ PASS - No track ID expected and none found")
            else:
                print("❌ FAIL - Unexpected track ID found")
        
        print("-" * 30)

if __name__ == "__main__":
    test_link_extraction()