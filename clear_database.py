#!/usr/bin/env python3
"""
Database Clearing Script for Media Indexer Bot
This script will completely clear the MongoDB database.
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_database():
    """Clear all collections in the database"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get MongoDB URI
        mongodb_uri = os.getenv('MONGODB_URI')
        if not mongodb_uri:
            logger.error("MONGODB_URI not found in environment variables")
            return False
            
        # Connect to MongoDB
        client = MongoClient(mongodb_uri)
        db = client['media_indexer']
        
        logger.info("Connected to MongoDB successfully")
        
        # Get all collection names
        collections = db.list_collection_names()
        logger.info(f"Found collections: {collections}")
        
        if not collections:
            logger.info("No collections found in database")
            return True
        
        # Clear each collection
        total_deleted = 0
        for collection_name in collections:
            collection = db[collection_name]
            count_before = collection.count_documents({})
            
            if count_before > 0:
                result = collection.delete_many({})
                logger.info(f"Deleted {result.deleted_count} documents from '{collection_name}' collection")
                total_deleted += result.deleted_count
            else:
                logger.info(f"Collection '{collection_name}' was already empty")
        
        logger.info(f"✅ Database clearing completed! Total documents deleted: {total_deleted}")
        
        # Close connection
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error clearing database: {e}")
        return False

def main():
    """Main function - auto clear without confirmation for script execution"""
    print("🗑️  Starting database clearing process...")
    
    success = clear_database()
    
    if success:
        print("✅ Database cleared successfully!")
        print("🔄 You can now restart the bot to begin fresh indexing")
    else:
        print("❌ Failed to clear database. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()