"""
Progressive Punishment System
Implements tiered punishment based on violation count
"""

import logging
import discord
from discord import Member, Guild
from datetime import timedelta
import json

logger = logging.getLogger(__name__)


class PunishmentHandler:
    """
    Handles progressive punishment system
    """
    
    def __init__(self, bot, db, guild_config):
        self.bot = bot
        self.db = db
        self.guild_config = guild_config
        
        # Load punishment tiers from config
        self.punishment_tiers = guild_config.punishment_tiers
    
    async def apply_punishment(
        self,
        guild: Guild,
        member: Member,
        violation_count: int,
        is_severe: bool = False
    ):
        """
        Apply punishment based on violation count
        
        Args:
            guild: Discord guild
            member: Member who violated rules
            violation_count: Number of violations
            is_severe: Whether this is a severe violation (multiplier applies)
        """
        # Apply severity multiplier
        effective_count = violation_count
        if is_severe:
            effective_count = min(5, violation_count * 2)  # Cap at ban tier
        
        # Get appropriate tier
        tier = self._get_punishment_tier(effective_count)
        
        if not tier:
            logger.error(f"No punishment tier found for count {effective_count}")
            return
        
        action = tier.get("action")
        duration = tier.get("duration", 0)
        
        logger.info(f"Applying {action} to {member} (violation #{violation_count})")
        
        try:
            if action == "warning":
                await self._send_warning(member, tier, violation_count)
            
            elif action == "timeout":
                await self._apply_timeout(guild, member, duration, tier, violation_count)
            
            elif action == "kick":
                await self._apply_kick(guild, member, tier, violation_count)
            
            elif action == "ban":
                await self._apply_ban(guild, member, tier, violation_count)
            
        except discord.Forbidden:
            logger.error(f"Missing permissions to apply {action} in {guild.id}")
        except Exception as e:
            logger.error(f"Error applying punishment: {e}", exc_info=True)
    
    def _get_punishment_tier(self, violation_count: int) -> dict:
        """Get punishment tier for violation count"""
        # Get tier from config (tiers are 1-indexed)
        tier_key = str(min(violation_count, 5))  # Cap at tier 5
        return self.punishment_tiers.get(tier_key, self.punishment_tiers.get("1"))
    
    async def _send_warning(self, member: Member, tier: dict, count: int):
        """Send warning DM to user"""
        try:
            embed = discord.Embed(
                title="⚠️ Moderation Warning",
                description=tier.get("message", "Your message violated community guidelines."),
                color=discord.Color.yellow()
            )
            
            embed.add_field(
                name="Violation Count",
                value=f"This is violation #{count}",
                inline=True
            )
            
            embed.add_field(
                name="Action Taken",
                value="Message deleted",
                inline=True
            )
            
            embed.set_footer(text="Please review the server rules to avoid further action.")
            
            await member.send(embed=embed)
            logger.info(f"Warning sent to {member}")
        except discord.Forbidden:
            logger.warning(f"Cannot DM {member} - DMs disabled")
        except Exception as e:
            logger.error(f"Error sending warning DM: {e}")
    
    async def _apply_timeout(
        self,
        guild: Guild,
        member: Member,
        duration: int,
        tier: dict,
        count: int
    ):
        """Apply timeout to member"""
        timeout_until = discord.utils.utcnow() + timedelta(seconds=duration)
        
        await member.timeout(
            timeout_until,
            reason=f"Hate speech violation #{count}"
        )
        
        # Send DM
        try:
            duration_str = self._format_duration(duration)
            
            embed = discord.Embed(
                title="🚫 You've Been Timed Out",
                description=tier.get("message", "You have been timed out for violating community guidelines."),
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="Duration",
                value=duration_str,
                inline=True
            )
            
            embed.add_field(
                name="Violation Count",
                value=f"#{count}",
                inline=True
            )
            
            embed.set_footer(text="This is an automated action. Contact moderators if you believe this is an error.")
            
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        
        logger.info(f"Timeout applied to {member} for {duration}s")
    
    async def _apply_kick(
        self,
        guild: Guild,
        member: Member,
        tier: dict,
        count: int
    ):
        """Kick member from server"""
        # Send DM before kicking
        try:
            embed = discord.Embed(
                title="👢 You've Been Kicked",
                description=tier.get("message", "You have been kicked for repeated violations."),
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Server",
                value=guild.name,
                inline=True
            )
            
            embed.add_field(
                name="Violation Count",
                value=f"#{count}",
                inline=True
            )
            
            embed.set_footer(text="You may rejoin if you agree to follow the rules.")
            
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        
        # Kick
        await member.kick(reason=f"Hate speech violations (#{count})")
        logger.info(f"Kicked {member} from {guild}")
    
    async def _apply_ban(
        self,
        guild: Guild,
        member: Member,
        tier: dict,
        count: int
    ):
        """Ban member from server"""
        # Send DM before banning
        try:
            embed = discord.Embed(
                title="🔨 You've Been Banned",
                description=tier.get("message", "You have been permanently banned for severe violations."),
                color=discord.Color.dark_red()
            )
            
            embed.add_field(
                name="Server",
                value=guild.name,
                inline=True
            )
            
            embed.add_field(
                name="Reason",
                value="Multiple hate speech violations",
                inline=True
            )
            
            embed.set_footer(text="You may appeal this decision by contacting server administrators.")
            
            await member.send(embed=embed)
        except discord.Forbidden:
            pass
        
        # Ban
        await member.ban(
            reason=f"Hate speech violations (#{count})",
            delete_message_days=1
        )
        logger.info(f"Banned {member} from {guild}")
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days > 1 else ''}"
