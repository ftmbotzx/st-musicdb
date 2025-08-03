# Media Indexer Bot

## Overview

This is a fully functional Telegram bot designed to automatically index and backup media files shared in Telegram chats. The bot monitors incoming media messages (audio, video, documents, photos), extracts metadata and track information, stores the data in MongoDB, and forwards files to a backup channel for preservation. It's built using the Pyrogram library for Telegram API integration and MongoDB for data persistence.

**Current Status: ✅ UPDATED & ENHANCED - v2.7 (2025-08-03)**
- Bot architecture updated with improved caption generation and rate limiting
- **FIXED**: Caption generation now uses minimal format (Title, Artist, Track ID only)
- **ENHANCED**: Title and artist extraction from first and second lines of original captions
- **UPDATED**: MongoDB schema now includes dedicated title and artist fields for better indexing
- **IMPROVED**: Progress bar now includes processing speed calculation in files/min
- **REMOVED**: 1000 message processing limit - bot now processes unlimited messages
- **IMPLEMENTED**: Proper rate limiting at 20 messages per minute (3 seconds between messages)
- **UPDATED**: Database indexes now include title and artist fields for better search performance
- Previous features maintained:
  - Link extraction working perfectly with both \u2063 and \u00ad characters
  - Advanced \u2063 character detection in "info" sections for embedded URL extraction
  - Complete database export with ALL 30+ metadata fields in Excel format
  - Real-time progress tracking with fancy status displays
  - Track IDs prominently displayed in backup channel captions

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Pyrogram Client**: Uses Pyrogram as the main Telegram bot framework for handling API interactions
- **Handler-based Architecture**: Separates message handling logic into dedicated handler functions
- **Environment-based Configuration**: Loads sensitive credentials (API keys, tokens) from environment variables

### Message Processing Pipeline
- **Media Detection**: Automatically identifies and processes different media types (audio, video, documents, photos)
- **Metadata Extraction**: Extracts comprehensive file metadata including file IDs, sizes, dimensions, and durations
- **Track Information Parsing**: Analyzes message captions to extract music track information and URLs
- **Backup Strategy**: Forwards all processed media to a designated backup channel for redundancy

### Data Storage Design
- **MongoDB Integration**: Uses MongoDB as the primary database for storing file metadata and indexing information
- **Enhanced Document Schema**: Stores comprehensive metadata including file information, chat context, sender details, and extracted track data with dedicated title and artist fields
- **Improved Indexing Strategy**: Creates database indexes on frequently queried fields (file_id, file_name, track_id, title, artist, etc.) for performance optimization
- **Unique Constraints**: Prevents duplicate entries using unique indexes on file identifiers

### Error Handling and Logging
- **Structured Logging**: Implements comprehensive logging throughout the application for debugging and monitoring
- **Connection Management**: Handles database connection failures gracefully with proper error reporting
- **Environment Validation**: Validates required environment variables at startup to prevent runtime errors

## External Dependencies

### Telegram API Integration
- **Pyrogram**: Python library for Telegram Bot API and MTProto API interactions
- **Bot API Credentials**: Requires API_ID, API_HASH, and BOT_TOKEN from Telegram

### Database Services
- **MongoDB**: Primary database for storing file metadata and indexing information
- **PyMongo**: MongoDB driver for Python database operations

### Infrastructure Requirements
- **MONGODB_URI**: Connection string for MongoDB instance
- **BACKUP_CHANNEL_ID**: Telegram channel ID for file backup storage
- **Environment Variables**: Configuration management through .env files using python-dotenv

### Media Processing
- **File Metadata Extraction**: Built-in capability to extract metadata from various media formats
- **URL Pattern Recognition**: Regular expression-based parsing for extracting track information from captions