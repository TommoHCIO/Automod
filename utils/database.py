"""
MongoDB Database Manager with async operations using Motor
"""

import logging
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime

from models import Violation, UserReputation, GuildConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Async MongoDB database manager
    """
    
    def __init__(self, mongodb_uri: str):
        self.mongodb_uri = mongodb_uri
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self):
        """Connect to MongoDB and create indexes"""
        try:
            self.client = AsyncIOMotorClient(self.mongodb_uri)
            self.db = self.client.get_database()
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("✅ Connected to MongoDB")
            
            # Create indexes
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            raise
    
    async def _create_indexes(self):
        """Create indexes for all collections"""
        try:
            # Violation indexes
            violation_col = self.db[Violation.collection_name]
            await violation_col.create_index("user_id")
            await violation_col.create_index("guild_id")
            await violation_col.create_index("timestamp")
            await violation_col.create_index([("guild_id", 1), ("user_id", 1)])
            
            # User reputation indexes
            reputation_col = self.db[UserReputation.collection_name]
            await reputation_col.create_index("user_id")
            await reputation_col.create_index("guild_id")
            await reputation_col.create_index("trust_score")
            await reputation_col.create_index([("guild_id", 1), ("user_id", 1)], unique=True)
            
            # Guild config indexes
            config_col = self.db[GuildConfig.collection_name]
            await config_col.create_index("guild_id", unique=True)
            
            logger.info("✅ Database indexes created")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    # Violation operations
    
    async def create_violation(self, violation: Violation) -> str:
        """
        Insert a new violation record
        Returns: violation document _id
        """
        collection = self.db[Violation.collection_name]
        result = await collection.insert_one(violation.to_dict())
        return str(result.inserted_id)
    
    async def get_user_violations(
        self,
        user_id: str,
        guild_id: str,
        limit: int = 50
    ) -> List[Violation]:
        """Get violation history for a user in a guild"""
        collection = self.db[Violation.collection_name]
        cursor = collection.find(
            {"user_id": user_id, "guild_id": guild_id}
        ).sort("timestamp", -1).limit(limit)
        
        violations = []
        async for doc in cursor:
            violations.append(Violation.from_dict(doc))
        return violations
    
    async def get_recent_violations(
        self,
        guild_id: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[Violation]:
        """Get recent violations in a guild"""
        from datetime import timedelta
        
        collection = self.db[Violation.collection_name]
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        cursor = collection.find({
            "guild_id": guild_id,
            "timestamp": {"$gte": cutoff_time}
        }).sort("timestamp", -1).limit(limit)
        
        violations = []
        async for doc in cursor:
            violations.append(Violation.from_dict(doc))
        return violations
    
    # User reputation operations
    
    async def get_user_reputation(
        self,
        user_id: str,
        guild_id: str
    ) -> Optional[UserReputation]:
        """Get user reputation, returns None if not found"""
        collection = self.db[UserReputation.collection_name]
        doc = await collection.find_one({"user_id": user_id, "guild_id": guild_id})
        
        if doc:
            return UserReputation.from_dict(doc)
        return None
    
    async def create_or_update_reputation(
        self,
        reputation: UserReputation
    ) -> bool:
        """Create or update user reputation"""
        collection = self.db[UserReputation.collection_name]
        
        result = await collection.update_one(
            {"user_id": reputation.user_id, "guild_id": reputation.guild_id},
            {"$set": reputation.to_dict()},
            upsert=True
        )
        
        return result.acknowledged
    
    async def reset_user_warnings(
        self,
        user_id: str,
        guild_id: str
    ) -> bool:
        """Reset user warnings and restore default trust score"""
        reputation = await self.get_user_reputation(user_id, guild_id)
        if reputation:
            reputation.reset_warnings()
            return await self.create_or_update_reputation(reputation)
        return False
    
    async def get_top_users_by_trust(
        self,
        guild_id: str,
        limit: int = 10
    ) -> List[UserReputation]:
        """Get users with highest trust scores"""
        collection = self.db[UserReputation.collection_name]
        cursor = collection.find(
            {"guild_id": guild_id}
        ).sort("trust_score", -1).limit(limit)
        
        users = []
        async for doc in cursor:
            users.append(UserReputation.from_dict(doc))
        return users
    
    async def get_users_below_trust_threshold(
        self,
        guild_id: str,
        threshold: int = 40
    ) -> List[UserReputation]:
        """Get users below trust threshold (for enhanced scrutiny)"""
        collection = self.db[UserReputation.collection_name]
        cursor = collection.find({
            "guild_id": guild_id,
            "trust_score": {"$lt": threshold}
        })
        
        users = []
        async for doc in cursor:
            users.append(UserReputation.from_dict(doc))
        return users
    
    # Guild config operations
    
    async def get_guild_config(self, guild_id: str) -> Optional[GuildConfig]:
        """Get guild configuration"""
        collection = self.db[GuildConfig.collection_name]
        doc = await collection.find_one({"guild_id": guild_id})
        
        if doc:
            return GuildConfig.from_dict(doc)
        
        # Create default config if doesn't exist
        default_config = GuildConfig(guild_id=guild_id)
        await self.create_or_update_guild_config(default_config)
        return default_config
    
    async def create_or_update_guild_config(
        self,
        config: GuildConfig
    ) -> bool:
        """Create or update guild configuration"""
        collection = self.db[GuildConfig.collection_name]
        
        result = await collection.update_one(
            {"guild_id": config.guild_id},
            {"$set": config.to_dict()},
            upsert=True
        )
        
        return result.acknowledged
    
    # Statistics and analytics
    
    async def get_guild_stats(self, guild_id: str) -> Dict[str, Any]:
        """Get moderation statistics for a guild"""
        violation_col = self.db[Violation.collection_name]
        reputation_col = self.db[UserReputation.collection_name]
        
        # Total violations
        total_violations = await violation_col.count_documents({"guild_id": guild_id})
        
        # Violations in last 24 hours
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_violations = await violation_col.count_documents({
            "guild_id": guild_id,
            "timestamp": {"$gte": cutoff}
        })
        
        # Total tracked users
        total_users = await reputation_col.count_documents({"guild_id": guild_id})
        
        # Users with warnings
        warned_users = await reputation_col.count_documents({
            "guild_id": guild_id,
            "warning_count": {"$gt": 0}
        })
        
        # Average trust score
        pipeline = [
            {"$match": {"guild_id": guild_id}},
            {"$group": {"_id": None, "avg_trust": {"$avg": "$trust_score"}}}
        ]
        avg_result = await reputation_col.aggregate(pipeline).to_list(1)
        avg_trust = avg_result[0]["avg_trust"] if avg_result else 0
        
        return {
            "total_violations": total_violations,
            "recent_violations_24h": recent_violations,
            "total_tracked_users": total_users,
            "warned_users": warned_users,
            "average_trust_score": round(avg_trust, 2)
        }
