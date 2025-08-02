import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class DatabaseManager:
    """MongoDB database manager for the media indexer bot"""
    
    def __init__(self):
        self.mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        self.backup_channel_id = os.getenv("BACKUP_CHANNEL_ID")
        self.client = None
        self.db = None
        self.collection = None
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB database"""
        try:
            # Set connection timeout to avoid hanging
            self.client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            
            # Get database and collection
            self.db = self.client.media_indexer
            self.collection = self.db.files
            
            # Create indexes for better performance
            self._create_indexes()
            
            logger.info("Successfully connected to MongoDB")
            
        except Exception as e:
            logger.warning(f"MongoDB connection failed: {e}")
            logger.warning("Bot will run without database functionality")
            # Don't raise, allow bot to run without database
            self.client = None
            self.db = None
            self.collection = None
    
    def _create_indexes(self):
        """Create database indexes for efficient querying"""
        try:
            if self.collection is None:
                return
                
            # Create indexes
            self.collection.create_index("file_id", unique=True)
            self.collection.create_index("file_unique_id")
            self.collection.create_index("file_name")
            self.collection.create_index("track_id")
            self.collection.create_index("track_url")
            self.collection.create_index("chat_id")
            self.collection.create_index("sender_id")
            self.collection.create_index("date")
            self.collection.create_index("is_deleted")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def insert_file(self, document: Dict) -> bool:
        """Insert a new file document into the database"""
        try:
            if self.collection is None:
                logger.warning("Database not connected, skipping file insertion")
                return False
                
            result = self.collection.insert_one(document)
            return result.inserted_id is not None
            
        except DuplicateKeyError:
            logger.warning(f"File already exists: {document.get('file_id')}")
            return False
        except Exception as e:
            logger.error(f"Error inserting file: {e}")
            return False
    
    def get_file_by_id(self, file_id: str):
        """Get file by file_id"""
        try:
            if self.collection is None:
                logger.warning("Database not connected")
                return None
            return self.collection.find_one({"file_id": file_id})
        except Exception as e:
            logger.error(f"Error finding file by ID: {e}")
            return None
    
    def find_file_by_name(self, filename: str) -> Optional[Dict]:
        """Find a file by its filename"""
        try:
            if self.collection is None:
                logger.warning("Database not connected")
                return None
                
            import re
            # Search for exact match first, then partial match
            document = self.collection.find_one({
                "file_name": {"$regex": f"^{re.escape(filename)}$", "$options": "i"},
                "is_deleted": False
            })
            
            if not document:
                # Try partial match
                document = self.collection.find_one({
                    "file_name": {"$regex": re.escape(filename), "$options": "i"},
                    "is_deleted": False
                })
            
            return document
            
        except Exception as e:
            logger.error(f"Error finding file by name: {e}")
            return None
    
    def find_file_by_track_id(self, track_id: str) -> Optional[Dict]:
        """Find a file by its track ID"""
        try:
            if self.collection is None:
                logger.warning("Database not connected")
                return None
                
            document = self.collection.find_one({
                "track_id": track_id,
                "is_deleted": False
            })
            
            return document
            
        except Exception as e:
            logger.error(f"Error finding file by track ID: {e}")
            return None
    
    def find_files_by_chat(self, chat_id: int) -> List[Dict]:
        """Find all files from a specific chat"""
        try:
            if self.collection is None:
                logger.warning("Database not connected")
                return []
                
            cursor = self.collection.find({
                "chat_id": chat_id,
                "is_deleted": False
            }).sort("date", -1)
            
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error finding files by chat: {e}")
            return []
    
    def mark_file_deleted(self, file_id: str) -> bool:
        """Mark a file as deleted"""
        try:
            if self.collection is None:
                logger.warning("Database not connected")
                return False
                
            result = self.collection.update_one(
                {"file_id": file_id},
                {"$set": {"is_deleted": True}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error marking file as deleted: {e}")
            return False
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        try:
            if self.collection is None:
                logger.warning("Database not connected")
                return {
                    "total_files": 0,
                    "audio_files": 0,
                    "video_files": 0,
                    "document_files": 0,
                    "photo_files": 0,
                    "files_with_tracks": 0
                }
                
            total_files = self.collection.count_documents({"is_deleted": False})
            audio_files = self.collection.count_documents({
                "file_type": "audio",
                "is_deleted": False
            })
            video_files = self.collection.count_documents({
                "file_type": "video",
                "is_deleted": False
            })
            document_files = self.collection.count_documents({
                "file_type": "document",
                "is_deleted": False
            })
            photo_files = self.collection.count_documents({
                "file_type": "photo",
                "is_deleted": False
            })
            files_with_tracks = self.collection.count_documents({
                "track_url": {"$ne": None, "$ne": ""},
                "is_deleted": False
            })
            
            return {
                "total_files": total_files,
                "audio_files": audio_files,
                "video_files": video_files,
                "document_files": document_files,
                "photo_files": photo_files,
                "files_with_tracks": files_with_tracks
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total_files": 0,
                "audio_files": 0,
                "video_files": 0,
                "document_files": 0,
                "photo_files": 0,
                "files_with_tracks": 0
            }
    
    def get_backup_channel_id(self) -> Optional[int]:
        """Get backup channel ID"""
        try:
            if not self.backup_channel_id:
                return None
            # Return the channel ID as-is since Pyrogram range is now adjusted
            channel_id = int(self.backup_channel_id)
            return channel_id
        except (ValueError, TypeError):
            logger.error(f"Invalid backup channel ID format: {self.backup_channel_id}")
            return None
    
    def get_all_files(self, limit: int = None, skip: int = None) -> List[Dict]:
        """Get all files from database for export"""
        try:
            if self.collection is None:
                logger.warning("Database not connected")
                return []
                
            query = {"is_deleted": False}
            cursor = self.collection.find(query).sort("date", -1)
            
            if skip:
                cursor = cursor.skip(skip)
            
            if limit:
                cursor = cursor.limit(limit)
                
            return list(cursor)
            
        except Exception as e:
            logger.error(f"Error getting all files: {e}")
            return []
    
    def get_file_by_unique_id(self, unique_id: str):
        """Get file by unique_id"""
        try:
            if self.collection is None:
                logger.warning("Database not connected")
                return None
            return self.collection.find_one({"file_unique_id": unique_id})
        except Exception as e:
            logger.error(f"Error finding file by unique ID: {e}")
            return None
    
    def get_file_by_backup_id(self, backup_file_id: str):
        """Check if file already exists in backup by backup_file_id"""
        try:
            if self.collection is None:
                logger.warning("Database not connected")
                return None
            return self.collection.find_one({"backup_file_id": backup_file_id})
        except Exception as e:
            logger.error(f"Error finding file by backup ID: {e}")
            return None
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
