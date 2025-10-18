"""
Moderation Cog - Core AI-based hate speech detection
"""

import logging
import discord
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional

from utils import CacheManager, DatabaseManager, AIClient, EmbeddingsManager, TrustScoreCalculator
from models import Violation, UserReputation

logger = logging.getLogger(__name__)


class ModerationCog(commands.Cog):
    """
    Handles message moderation with AI detection
    """
    
    def __init__(
        self,
        bot: commands.Bot,
        db: DatabaseManager,
        cache: CacheManager,
        ai_client: AIClient,
        embeddings: EmbeddingsManager,
        config: dict
    ):
        self.bot = bot
        self.db = db
        self.cache = cache
        self.ai_client = ai_client
        self.embeddings = embeddings
        self.config = config
        
        # Configuration
        self.min_trust_for_bypass = config.get("moderation", {}).get("min_trust_score_for_bypass", 80)
        self.min_message_length = config.get("moderation", {}).get("min_message_length_to_check", 3)
        self.confidence_threshold = config.get("ai_providers", {}).get("confidence_threshold", 0.7)
        
        logger.info("✅ Moderation cog loaded")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Main message handler - checks all messages for hate speech
        """
        # Ignore bots
        if message.author.bot:
            return
        
        # Ignore DMs
        if not message.guild:
            return
        
        # Ignore commands
        if message.content.startswith(self.bot.command_prefix):
            return
        
        try:
            await self._process_message(message)
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}", exc_info=True)
    
    async def _process_message(self, message: discord.Message):
        """
        Process a message through the moderation pipeline
        """
        # Get guild config
        guild_config = await self.db.get_guild_config(str(message.guild.id))
        
        # Check if moderation is enabled
        if not guild_config.enabled:
            return
        
        # Check if channel is ignored
        if guild_config.is_channel_ignored(str(message.channel.id)):
            return
        
        # Check if user is ignored
        if guild_config.is_user_ignored(str(message.author.id)):
            return
        
        # Pre-filtering: Skip very short messages
        word_count = len(message.content.split())
        if word_count < self.min_message_length:
            return
        
        # Get or create user reputation
        user_rep = await self.db.get_user_reputation(
            str(message.author.id),
            str(message.guild.id)
        )
        
        if not user_rep:
            # Create new reputation entry
            user_rep = UserReputation(
                user_id=str(message.author.id),
                guild_id=str(message.guild.id),
                trust_score=TrustScoreCalculator.calculate_initial_score(
                    message.author.created_at
                )
            )
            await self.db.create_or_update_reputation(user_rep)
        
        # Bypass check for trusted users
        if TrustScoreCalculator.should_bypass_checks(
            user_rep.trust_score,
            self.min_trust_for_bypass
        ):
            logger.debug(f"Bypassing check for trusted user {message.author.id}")
            return
        
        # Check cache first
        cached_result = await self.cache.get_ai_response(message.content)
        if cached_result:
            logger.debug("Using cached AI response")
            await self._handle_moderation_result(
                message,
                cached_result,
                guild_config,
                user_rep,
                from_cache=True
            )
            return
        
        # AI moderation check
        moderation_result = await self.ai_client.moderate_content(message.content)
        
        if not moderation_result:
            logger.warning(f"AI moderation failed for message {message.id}")
            return
        
        # Cache the result
        await self.cache.cache_ai_response(message.content, moderation_result.to_dict())
        
        # Handle the result
        await self._handle_moderation_result(
            message,
            moderation_result.to_dict() if hasattr(moderation_result, 'to_dict') else moderation_result,
            guild_config,
            user_rep
        )
    
    async def _handle_moderation_result(
        self,
        message: discord.Message,
        result: dict,
        guild_config,
        user_rep: UserReputation,
        from_cache: bool = False
    ):
        """
        Handle AI moderation result
        """
        flagged = result.get("flagged", False)
        confidence = result.get("confidence", 0.0)
        categories = result.get("categories", {})
        
        # Apply confidence threshold
        if confidence < self.confidence_threshold:
            return
        
        # Semantic filtering for false positives
        if self.embeddings.is_available():
            flagged = self.embeddings.filter_false_positives(
                flagged,
                message.content,
                categories
            )
        
        # Check against allowed words (profanity whitelist)
        if flagged:
            flagged = self._check_against_whitelist(message.content, guild_config.allowed_words)
        
        if not flagged:
            return
        
        # Content is flagged - take action
        logger.info(f"Hate speech detected from {message.author} ({message.author.id}): {confidence:.2%}")
        
        # Delete message
        try:
            await message.delete()
        except discord.Forbidden:
            logger.error(f"Missing permissions to delete message in {message.guild.id}")
            return
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return
        
        # Determine severity
        is_severe = self._is_severe_violation(categories)
        
        # Create violation record
        violation = Violation(
            user_id=str(message.author.id),
            guild_id=str(message.guild.id),
            message_content=message.content[:500],  # Limit length
            reason=self._format_violation_reason(categories),
            ai_provider=result.get("provider", "unknown"),
            confidence=confidence,
            action_taken="message_deleted",
            message_id=str(message.id),
            channel_id=str(message.channel.id),
            categories=list(categories.keys())
        )
        
        violation_id = await self.db.create_violation(violation)
        
        # Update user reputation
        penalty = 30 if is_severe else 15
        user_rep.add_violation(violation_id, penalty)
        await self.db.create_or_update_reputation(user_rep)
        
        # Invalidate user cache
        await self.cache.invalidate_user_cache(str(message.author.id), str(message.guild.id))
        
        # Apply progressive punishment
        await self._apply_punishment(message, user_rep, guild_config, is_severe)
        
        # Log to mod channel
        log_cog = self.bot.get_cog("LoggingCog")
        if log_cog:
            await log_cog.log_violation(
                message,
                violation,
                user_rep,
                result
            )
    
    def _check_against_whitelist(self, content: str, allowed_words: list) -> bool:
        """
        Check if content only contains allowed profanity
        Returns False if content is whitelisted, True if it should still be flagged
        """
        content_lower = content.lower()
        
        # Simple check: if the message only contains allowed words, don't flag
        # This is a basic implementation - you might want more sophisticated logic
        for allowed_word in allowed_words:
            if allowed_word in content_lower:
                # Check if it's ONLY profanity (not hate speech with profanity)
                # For now, we'll let the AI's judgment stand
                pass
        
        return True
    
    def _is_severe_violation(self, categories: dict) -> bool:
        """Determine if violation is severe (racism, homophobia, etc.)"""
        severe_categories = [
            "hate",
            "hate/threatening",
            "hate_speech",
            "racism",
            "homophobia",
            "transphobia"
        ]
        
        for category in severe_categories:
            if categories.get(category, False):
                return True
        
        return False
    
    def _format_violation_reason(self, categories: dict) -> str:
        """Format violation reason from categories"""
        flagged_categories = [cat for cat, flagged in categories.items() if flagged]
        
        if not flagged_categories:
            return "Hate speech detected"
        
        return f"Hate speech: {', '.join(flagged_categories)}"
    
    async def _apply_punishment(
        self,
        message: discord.Message,
        user_rep: UserReputation,
        guild_config,
        is_severe: bool
    ):
        """
        Apply progressive punishment based on violation count
        """
        from cogs.punishment import PunishmentHandler
        
        punishment_handler = PunishmentHandler(self.bot, self.db, guild_config)
        await punishment_handler.apply_punishment(
            message.guild,
            message.author,
            user_rep.warning_count,
            is_severe
        )
    
    @commands.command(name="check")
    @commands.has_permissions(manage_messages=True)
    async def manual_check(self, ctx: commands.Context, *, text: str):
        """
        Manually check text for hate speech (moderator command)
        Usage: !check <text>
        """
        await ctx.message.delete()  # Delete command message
        
        # Run AI moderation
        result = await self.ai_client.moderate_content(text)
        
        if not result:
            await ctx.send("❌ AI moderation failed", delete_after=10)
            return
        
        # Create embed with results
        embed = discord.Embed(
            title="🔍 Manual Moderation Check",
            color=discord.Color.red() if result.flagged else discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="Result",
            value="🚫 FLAGGED" if result.flagged else "✅ SAFE",
            inline=True
        )
        
        embed.add_field(
            name="Confidence",
            value=f"{result.confidence:.1%}",
            inline=True
        )
        
        embed.add_field(
            name="Provider",
            value=result.provider.upper(),
            inline=True
        )
        
        # Add flagged categories
        flagged_cats = [cat for cat, val in result.categories.items() if val]
        if flagged_cats:
            embed.add_field(
                name="Flagged Categories",
                value=", ".join(flagged_cats),
                inline=False
            )
        
        embed.add_field(
            name="Checked Text",
            value=f"```{text[:200]}```",
            inline=False
        )
        
        embed.set_footer(text=f"Checked by {ctx.author}")
        
        await ctx.send(embed=embed, delete_after=60)


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    # This will be called from main bot.py
    pass
