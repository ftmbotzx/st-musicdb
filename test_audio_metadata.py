#!/usr/bin/env python3
"""Test script to verify audio metadata extraction and caption generation"""

import sys
import os
sys.path.append('.')

from bot.utils import generate_minimal_caption

def test_audio_metadata_caption():
    """Test minimal caption generation with audio metadata"""
    
    # Test case 1: Audio metadata available (should prioritize this)
    file_metadata = {
        'title': 'Me Mata',
        'performer': 'Dany Ome, Kevincito El 13',
        'file_type': 'audio'
    }
    
    track_info = {
        'track_id': '5mOeJ8dmjxr0gOEez4PTUf',
        'track_url': 'https://open.spotify.com/track/5mOeJ8dmjxr0gOEez4PTUf',
        'title': 'Wrong Title From URL',  # Should be ignored
        'artist': 'Wrong Artist From URL'  # Should be ignored
    }
    
    caption1 = generate_minimal_caption(track_info, file_metadata)
    print("Test 1 - Audio metadata available:")
    print(caption1)
    print()
    
    # Test case 2: No audio metadata, fallback to track info
    track_info_only = {
        'track_id': '3VmHqPccXgI7qGIfAcgbXs',
        'track_url': 'https://open.spotify.com/track/3VmHqPccXgI7qGIfAcgbXs',
        'title': 'Track Title From URL',
        'artist': 'Track Artist From URL'
    }
    
    caption2 = generate_minimal_caption(track_info_only, None)
    print("Test 2 - No audio metadata, using track info:")
    print(caption2)
    print()
    
    # Test case 3: No metadata at all
    empty_track_info = {
        'track_id': 'ABC123XYZ'
    }
    
    caption3 = generate_minimal_caption(empty_track_info, None)
    print("Test 3 - No metadata available:")
    print(caption3)
    print()

if __name__ == "__main__":
    test_audio_metadata_caption()