"""
Guild Configuration Model - Per-server settings
"""

from datetime import datetime
from typing import Optional, Dict, Any, List


class GuildConfig:
    """
    MongoDB document model for guild-specific configuration
    """
    
    collection_name = "guild_config"
    
    def __init__(
        self,
        guild_id: str,
        log_channel_id: Optional[str] = None,
        allowed_words: Optional[List[str]] = None,
        enable_cross_server_reputation: bool = False,
        punishment_tiers: Optional[Dict[str, Any]] = None,
        min_trust_score_for_bypass: int = 80,
        ai_confidence_threshold: float = 0.7,
        enabled: bool = True,
        moderator_role_ids: Optional[List[str]] = None,
        admin_role_ids: Optional[List[str]] = None,
        ignored_channel_ids: Optional[List[str]] = None,
        ignored_user_ids: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        last_updated: Optional[datetime] = None,
        _id: Optional[str] = None
    ):
        self.guild_id = guild_id
        self.log_channel_id = log_channel_id
        self.allowed_words = allowed_words or ["fuck", "shit", "bitch", "damn", "hell", "ass", "crap"]
        self.enable_cross_server_reputation = enable_cross_server_reputation
        self.punishment_tiers = punishment_tiers or self._get_default_punishment_tiers()
        self.min_trust_score_for_bypass = min_trust_score_for_bypass
        self.ai_confidence_threshold = ai_confidence_threshold
        self.enabled = enabled
        self.moderator_role_ids = moderator_role_ids or []
        self.admin_role_ids = admin_role_ids or []
        self.ignored_channel_ids = ignored_channel_ids or []
        self.ignored_user_ids = ignored_user_ids or []
        self.created_at = created_at or datetime.utcnow()
        self.last_updated = last_updated or datetime.utcnow()
        self._id = _id
    
    @staticmethod
    def _get_default_punishment_tiers() -> Dict[str, Any]:
        """Get default punishment tier configuration"""
        return {
            "1": {"action": "warning", "duration": 0, "trust_penalty": 0},
            "2": {"action": "timeout", "duration": 600, "trust_penalty": 15},
            "3": {"action": "timeout", "duration": 3600, "trust_penalty": 20},
            "4": {"action": "timeout", "duration": 86400, "trust_penalty": 25},
            "5": {"action": "ban", "duration": 0, "trust_penalty": 100}
        }
    
    def is_channel_ignored(self, channel_id: str) -> bool:
        """Check if a channel is ignored"""
        return channel_id in self.ignored_channel_ids
    
    def is_user_ignored(self, user_id: str) -> bool:
        """Check if a user is ignored (e.g., other bots)"""
        return user_id in self.ignored_user_ids
    
    def add_allowed_word(self, word: str):
        """Add a word to the allowed list"""
        word_lower = word.lower()
        if word_lower not in self.allowed_words:
            self.allowed_words.append(word_lower)
            self.last_updated = datetime.utcnow()
    
    def remove_allowed_word(self, word: str) -> bool:
        """Remove a word from the allowed list"""
        word_lower = word.lower()
        if word_lower in self.allowed_words:
            self.allowed_words.remove(word_lower)
            self.last_updated = datetime.utcnow()
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB insertion"""
        doc = {
            "guild_id": self.guild_id,
            "log_channel_id": self.log_channel_id,
            "allowed_words": self.allowed_words,
            "enable_cross_server_reputation": self.enable_cross_server_reputation,
            "punishment_tiers": self.punishment_tiers,
            "min_trust_score_for_bypass": self.min_trust_score_for_bypass,
            "ai_confidence_threshold": self.ai_confidence_threshold,
            "enabled": self.enabled,
            "moderator_role_ids": self.moderator_role_ids,
            "admin_role_ids": self.admin_role_ids,
            "ignored_channel_ids": self.ignored_channel_ids,
            "ignored_user_ids": self.ignored_user_ids,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
        
        if self._id:
            doc["_id"] = self._id
        
        return doc
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GuildConfig':
        """Create GuildConfig instance from MongoDB document"""
        return cls(
            guild_id=data.get("guild_id"),
            log_channel_id=data.get("log_channel_id"),
            allowed_words=data.get("allowed_words"),
            enable_cross_server_reputation=data.get("enable_cross_server_reputation", False),
            punishment_tiers=data.get("punishment_tiers"),
            min_trust_score_for_bypass=data.get("min_trust_score_for_bypass", 80),
            ai_confidence_threshold=data.get("ai_confidence_threshold", 0.7),
            enabled=data.get("enabled", True),
            moderator_role_ids=data.get("moderator_role_ids", []),
            admin_role_ids=data.get("admin_role_ids", []),
            ignored_channel_ids=data.get("ignored_channel_ids", []),
            ignored_user_ids=data.get("ignored_user_ids", []),
            created_at=data.get("created_at"),
            last_updated=data.get("last_updated"),
            _id=data.get("_id")
        )
    
    @staticmethod
    def get_indexes():
        """Return list of indexes to create for this collection"""
        return [
            ("guild_id", 1)
        ]
