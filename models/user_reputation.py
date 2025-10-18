"""
User Reputation Model - Tracks user trust scores and warning counts
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List


class UserReputation:
    """
    MongoDB document model for user reputation and trust scores
    """
    
    collection_name = "user_reputation"
    
    def __init__(
        self,
        user_id: str,
        guild_id: str,
        trust_score: int = 60,
        warning_count: int = 0,
        last_violation: Optional[datetime] = None,
        history: Optional[List[str]] = None,
        positive_actions: int = 0,
        account_age_days: int = 0,
        first_seen: Optional[datetime] = None,
        last_updated: Optional[datetime] = None,
        _id: Optional[str] = None
    ):
        self.user_id = user_id
        self.guild_id = guild_id
        self.trust_score = max(0, min(100, trust_score))  # Clamp between 0-100
        self.warning_count = warning_count
        self.last_violation = last_violation
        self.history = history or []
        self.positive_actions = positive_actions
        self.account_age_days = account_age_days
        self.first_seen = first_seen or datetime.now(timezone.utc)
        self.last_updated = last_updated or datetime.now(timezone.utc)
        self._id = _id
    
    def add_violation(self, violation_id: str, penalty: int = 15):
        """Add a violation to history and reduce trust score"""
        self.history.append(violation_id)
        self.warning_count += 1
        self.trust_score = max(0, self.trust_score - penalty)
        self.last_violation = datetime.now(timezone.utc)
        self.last_updated = datetime.now(timezone.utc)
    
    def add_positive_action(self, reward: int = 5):
        """Reward positive behavior"""
        self.positive_actions += 1
        self.trust_score = min(100, self.trust_score + reward)
        self.last_updated = datetime.now(timezone.utc)
    
    def reset_warnings(self):
        """Reset warnings (admin action)"""
        self.warning_count = 0
        self.history = []
        self.trust_score = 60  # Reset to default
        self.last_updated = datetime.now(timezone.utc)
    
    def calculate_trust_score(self, account_creation_date: datetime) -> int:
        """
        Calculate trust score based on multiple factors
        Returns: int between 0-100
        """
        # Base score
        base_score = 60
        
        # Account age bonus (max +20)
        now = datetime.now(timezone.utc)
        if account_creation_date.tzinfo is None:
            account_creation_date = account_creation_date.replace(tzinfo=timezone.utc)
        account_age_days = (now - account_creation_date).days
        age_bonus = min(20, account_age_days // 7)  # +1 per week, max 20
        
        # New account penalty
        if account_age_days < 7:
            base_score = 30
        
        # Violation penalty
        violation_penalty = self.warning_count * 15
        
        # Positive action bonus
        positive_bonus = min(20, self.positive_actions * 5)
        
        # Calculate final score
        final_score = base_score + age_bonus + positive_bonus - violation_penalty
        
        # Clamp between 0-100
        return max(0, min(100, final_score))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB insertion"""
        doc = {
            "user_id": self.user_id,
            "guild_id": self.guild_id,
            "trust_score": self.trust_score,
            "warning_count": self.warning_count,
            "last_violation": self.last_violation,
            "history": self.history,
            "positive_actions": self.positive_actions,
            "account_age_days": self.account_age_days,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated
        }
        
        if self._id:
            doc["_id"] = self._id
        
        return doc
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserReputation':
        """Create UserReputation instance from MongoDB document"""
        return cls(
            user_id=data.get("user_id"),
            guild_id=data.get("guild_id"),
            trust_score=data.get("trust_score", 60),
            warning_count=data.get("warning_count", 0),
            last_violation=data.get("last_violation"),
            history=data.get("history", []),
            positive_actions=data.get("positive_actions", 0),
            account_age_days=data.get("account_age_days", 0),
            first_seen=data.get("first_seen"),
            last_updated=data.get("last_updated"),
            _id=data.get("_id")
        )
    
    @staticmethod
    def get_indexes():
        """Return list of indexes to create for this collection"""
        return [
            ("user_id", 1),
            ("guild_id", 1),
            ("trust_score", -1),
            [("guild_id", 1), ("user_id", 1)],
            [("guild_id", 1), ("trust_score", -1)]
        ]
