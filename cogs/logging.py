"""
Logging Cog - Creates rich embeds for moderation actions
"""

import logging
import discord
from discord.ext import commands
from datetime import datetime

from models import Violation, UserReputation
from utils import TrustScoreCalculator

logger = logging.getLogger(__name__)


class LoggingCog(commands.Cog):
    """
    Handles logging of moderation actions to designated channel
    """
    
    def __init__(self, bot: commands.Bot, db):
        self.bot = bot
        self.db = db
        
        logger.info("✅ Logging cog loaded")
    
    async def log_violation(
        self,
        message: discord.Message,
        violation: Violation,
        user_rep: UserReputation,
        moderation_result: dict
    ):
        """
        Log a violation to the mod log channel
        
        Args:
            message: Original message that was flagged
            violation: Violation record
            user_rep: User reputation data
            moderation_result: AI moderation result
        """
        # Get guild config to find log channel
        guild_config = await self.db.get_guild_config(str(message.guild.id))
        
        if not guild_config.log_channel_id:
            logger.debug("No log channel configured")
            return
        
        # Get log channel
        log_channel = message.guild.get_channel(int(guild_config.log_channel_id))
        
        if not log_channel:
            logger.warning(f"Log channel {guild_config.log_channel_id} not found")
            return
        
        # Create embed
        embed = await self._create_violation_embed(
            message,
            violation,
            user_rep,
            moderation_result
        )
        
        try:
            await log_channel.send(embed=embed)
            logger.debug(f"Violation logged to {log_channel.name}")
        except discord.Forbidden:
            logger.error(f"Missing permissions to send to log channel")
        except Exception as e:
            logger.error(f"Error sending log message: {e}")
    
    async def _create_violation_embed(
        self,
        message: discord.Message,
        violation: Violation,
        user_rep: UserReputation,
        moderation_result: dict
    ) -> discord.Embed:
        """Create rich embed for violation log"""
        
        # Determine embed color based on severity
        confidence = moderation_result.get("confidence", 0.0)
        if confidence >= 0.9:
            color = discord.Color.dark_red()
        elif confidence >= 0.75:
            color = discord.Color.red()
        else:
            color = discord.Color.orange()
        
        embed = discord.Embed(
            title="🚫 Hate Speech Detected",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        # User info
        embed.set_author(
            name=f"{message.author} ({message.author.id})",
            icon_url=message.author.display_avatar.url
        )
        
        # Violation details
        embed.add_field(
            name="Channel",
            value=message.channel.mention,
            inline=True
        )
        
        embed.add_field(
            name="AI Provider",
            value=moderation_result.get("provider", "unknown").upper(),
            inline=True
        )
        
        embed.add_field(
            name="Confidence",
            value=f"{confidence:.1%}",
            inline=True
        )
        
        # Flagged categories
        categories = moderation_result.get("categories", {})
        flagged_cats = [cat for cat, flagged in categories.items() if flagged]
        
        if flagged_cats:
            embed.add_field(
                name="Categories",
                value=", ".join(f"`{cat}`" for cat in flagged_cats[:5]),
                inline=False
            )
        
        # Message content (truncated)
        content = violation.message_content[:500]
        if len(violation.message_content) > 500:
            content += "..."
        
        embed.add_field(
            name="Message Content",
            value=f"```{content}```",
            inline=False
        )
        
        # User reputation
        trust_level = TrustScoreCalculator.get_trust_level(user_rep.trust_score)
        embed.add_field(
            name="Trust Score",
            value=f"{user_rep.trust_score}/100 ({trust_level})",
            inline=True
        )
        
        embed.add_field(
            name="Warning Count",
            value=f"#{user_rep.warning_count}",
            inline=True
        )
        
        # Action taken
        action_emoji = {
            "warning": "⚠️",
            "timeout": "🔇",
            "kick": "👢",
            "ban": "🔨"
        }
        
        action_type = violation.action_taken.split("_")[0] if "_" in violation.action_taken else violation.action_taken
        emoji = action_emoji.get(action_type, "🚫")
        
        embed.add_field(
            name="Action Taken",
            value=f"{emoji} {violation.action_taken.replace('_', ' ').title()}",
            inline=True
        )
        
        # Footer with message ID for reference
        embed.set_footer(text=f"Message ID: {message.id}")
        
        return embed
    
    async def log_manual_action(
        self,
        guild: discord.Guild,
        moderator: discord.Member,
        user: discord.Member,
        action: str,
        reason: str
    ):
        """
        Log manual moderator action
        
        Args:
            guild: Discord guild
            moderator: Moderator who took action
            user: User affected by action
            action: Action taken (reset_warnings, etc.)
            reason: Reason for action
        """
        guild_config = await self.db.get_guild_config(str(guild.id))
        
        if not guild_config.log_channel_id:
            return
        
        log_channel = guild.get_channel(int(guild_config.log_channel_id))
        
        if not log_channel:
            return
        
        embed = discord.Embed(
            title="🛠️ Manual Moderator Action",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=f"{moderator}",
            icon_url=moderator.display_avatar.url
        )
        
        embed.add_field(
            name="Target User",
            value=f"{user.mention} ({user.id})",
            inline=True
        )
        
        embed.add_field(
            name="Action",
            value=action.replace("_", " ").title(),
            inline=True
        )
        
        embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )
        
        embed.set_footer(text=f"Moderator: {moderator.id}")
        
        try:
            await log_channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error sending manual action log: {e}")
    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Log when a member is banned"""
        # Check if this was an automod ban by checking recent violations
        user_rep = await self.db.get_user_reputation(str(user.id), str(guild.id))
        
        if not user_rep or user_rep.warning_count == 0:
            return  # Not an automod ban
        
        logger.info(f"Member banned (automod): {user} in {guild}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log when a member leaves (could be kick)"""
        logger.debug(f"Member removed: {member} from {member.guild}")


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    pass
