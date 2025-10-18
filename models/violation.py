"""
Violation Model - Tracks hate speech violations
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any


class Violation:
    """
    MongoDB document model for storing violation records
    """
    
    collection_name = "violations"
    
    def __init__(
        self,
        user_id: str,
        guild_id: str,
        message_content: str,
        reason: str,
        ai_provider: str,
        confidence: float,
        action_taken: str,
        timestamp: Optional[datetime] = None,
        message_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        moderator_id: Optional[str] = None,
        categories: Optional[list] = None,
        _id: Optional[str] = None
    ):
        self.user_id = user_id
        self.guild_id = guild_id
        self.message_content = message_content
        self.reason = reason
        self.ai_provider = ai_provider
        self.confidence = confidence
        self.action_taken = action_taken
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.message_id = message_id
        self.channel_id = channel_id
        self.moderator_id = moderator_id
        self.categories = categories or []
        self._id = _id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB insertion"""
        doc = {
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "message_content": self.message_content,
            "reason": self.reason,
            "ai_provider": self.ai_provider,
            "confidence": self.confidence,
            "action_taken": self.action_taken,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "channel_id": self.channel_id,
            "moderator_id": self.moderator_id,
            "categories": self.categories
        }
        
        if self._id:
            doc["_id"] = self._id
        
        return doc
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Violation':
        """Create Violation instance from MongoDB document"""
        return cls(
            user_id=data.get("user_id"),
            guild_id=data.get("guild_id"),
            message_content=data.get("message_content"),
            reason=data.get("reason"),
            ai_provider=data.get("ai_provider"),
            confidence=data.get("confidence"),
            action_taken=data.get("action_taken"),
            timestamp=data.get("timestamp"),
            message_id=data.get("message_id"),
            channel_id=data.get("channel_id"),
            moderator_id=data.get("moderator_id"),
            categories=data.get("categories"),
            _id=data.get("_id")
        )
    
    @staticmethod
    def get_indexes():
        """Return list of indexes to create for this collection"""
        return [
            ("user_id", 1),
            ("guild_id", 1),
            ("timestamp", -1),
            [("guild_id", 1), ("user_id", 1)],
            [("guild_id", 1), ("timestamp", -1)]
        ]
