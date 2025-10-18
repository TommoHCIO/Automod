"""
Trust Score Calculator for User Reputation System
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TrustScoreCalculator:
    """
    Calculate and manage user trust scores (0-100)
    """
    
    # Default score thresholds
    MIN_SCORE = 0
    MAX_SCORE = 100
    DEFAULT_SCORE = 60
    NEW_ACCOUNT_SCORE = 30
    
    # Penalties and rewards
    VIOLATION_PENALTY = 15
    SEVERE_VIOLATION_PENALTY = 30
    POSITIVE_ACTION_REWARD = 5
    
    # Account age thresholds
    NEW_ACCOUNT_DAYS = 7
    MATURE_ACCOUNT_DAYS = 90
    
    @staticmethod
    def calculate_initial_score(account_creation_date: datetime) -> int:
        """
        Calculate initial trust score based on account age
        
        Args:
            account_creation_date: When the Discord account was created
        
        Returns:
            Initial trust score (0-100)
        """
        account_age_days = (datetime.utcnow() - account_creation_date).days
        
        # New accounts start lower
        if account_age_days < TrustScoreCalculator.NEW_ACCOUNT_DAYS:
            return TrustScoreCalculator.NEW_ACCOUNT_SCORE
        
        # Mature accounts start at default
        return TrustScoreCalculator.DEFAULT_SCORE
    
    @staticmethod
    def calculate_account_age_bonus(account_creation_date: datetime) -> int:
        """
        Calculate bonus points for account age
        
        Args:
            account_creation_date: When the Discord account was created
        
        Returns:
            Bonus points (0-20)
        """
        account_age_days = (datetime.utcnow() - account_creation_date).days
        
        # +1 point per week, max 20 points
        bonus = min(20, account_age_days // 7)
        return bonus
    
    @staticmethod
    def calculate_violation_penalty(
        violation_count: int,
        is_severe: bool = False
    ) -> int:
        """
        Calculate penalty for violations
        
        Args:
            violation_count: Number of violations
            is_severe: Whether violations are severe (racism, homophobia, etc.)
        
        Returns:
            Penalty points to subtract
        """
        base_penalty = TrustScoreCalculator.VIOLATION_PENALTY
        
        if is_severe:
            base_penalty = TrustScoreCalculator.SEVERE_VIOLATION_PENALTY
        
        return violation_count * base_penalty
    
    @staticmethod
    def calculate_positive_action_bonus(positive_actions: int) -> int:
        """
        Calculate bonus for positive actions
        
        Args:
            positive_actions: Number of positive actions (helpful reactions, etc.)
        
        Returns:
            Bonus points to add (max 20)
        """
        return min(20, positive_actions * TrustScoreCalculator.POSITIVE_ACTION_REWARD)
    
    @staticmethod
    def apply_time_decay(
        violations: list,
        decay_days: int = 90,
        decay_percentage: int = 50
    ) -> int:
        """
        Apply time decay to old violations
        
        Args:
            violations: List of violation timestamps
            decay_days: Days before decay starts
            decay_percentage: Percentage to reduce weight of old violations
        
        Returns:
            Effective violation count after decay
        """
        cutoff_date = datetime.utcnow() - timedelta(days=decay_days)
        
        recent_violations = 0
        old_violations = 0
        
        for violation_timestamp in violations:
            if isinstance(violation_timestamp, str):
                # Handle if timestamp is string
                continue
            
            if violation_timestamp >= cutoff_date:
                recent_violations += 1
            else:
                old_violations += 1
        
        # Old violations count for less
        decay_multiplier = (100 - decay_percentage) / 100
        effective_old_violations = old_violations * decay_multiplier
        
        return recent_violations + int(effective_old_violations)
    
    @staticmethod
    def calculate_comprehensive_score(
        account_creation_date: datetime,
        violation_count: int = 0,
        positive_actions: int = 0,
        is_severe: bool = False,
        violations_history: Optional[list] = None
    ) -> int:
        """
        Calculate comprehensive trust score
        
        Args:
            account_creation_date: Discord account creation date
            violation_count: Number of violations
            positive_actions: Number of positive actions
            is_severe: Whether violations are severe
            violations_history: List of violation timestamps for time decay
        
        Returns:
            Trust score (0-100)
        """
        # Start with base score
        base_score = TrustScoreCalculator.calculate_initial_score(account_creation_date)
        
        # Account age bonus
        age_bonus = TrustScoreCalculator.calculate_account_age_bonus(account_creation_date)
        
        # Violation penalty (with time decay if history provided)
        if violations_history:
            effective_violations = TrustScoreCalculator.apply_time_decay(violations_history)
        else:
            effective_violations = violation_count
        
        violation_penalty = TrustScoreCalculator.calculate_violation_penalty(
            effective_violations,
            is_severe
        )
        
        # Positive action bonus
        positive_bonus = TrustScoreCalculator.calculate_positive_action_bonus(positive_actions)
        
        # Calculate final score
        final_score = base_score + age_bonus + positive_bonus - violation_penalty
        
        # Clamp between MIN and MAX
        final_score = max(TrustScoreCalculator.MIN_SCORE, min(TrustScoreCalculator.MAX_SCORE, final_score))
        
        return final_score
    
    @staticmethod
    def get_trust_level(score: int) -> str:
        """
        Get human-readable trust level
        
        Args:
            score: Trust score (0-100)
        
        Returns:
            Trust level description
        """
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "High"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Fair"
        elif score >= 20:
            return "Low"
        else:
            return "Very Low"
    
    @staticmethod
    def should_apply_enhanced_scrutiny(score: int) -> bool:
        """
        Determine if user should receive enhanced moderation
        
        Args:
            score: Trust score (0-100)
        
        Returns:
            True if enhanced scrutiny should be applied
        """
        return score < 40
    
    @staticmethod
    def should_bypass_checks(score: int, threshold: int = 80) -> bool:
        """
        Determine if user can bypass pre-filtering
        
        Args:
            score: Trust score (0-100)
            threshold: Minimum score to bypass (default: 80)
        
        Returns:
            True if user can bypass checks
        """
        return score >= threshold
