"""
Admin Commands Cog - Slash commands for server administrators
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

from utils import DatabaseManager, CacheManager, TrustScoreCalculator

logger = logging.getLogger(__name__)


class AdminCog(commands.Cog):
    """
    Admin and moderator commands via slash commands
    """
    
    def __init__(self, bot: commands.Bot, db: DatabaseManager, cache: CacheManager):
        self.bot = bot
        self.db = db
        self.cache = cache
        
        logger.info("✅ Admin cog loaded")
    
    # Create slash command group
    automod_group = app_commands.Group(
        name="automod",
        description="Automod management commands"
    )
    
    @automod_group.command(name="status", description="View bot status and statistics")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def status(self, interaction: discord.Interaction):
        """Display bot status and guild statistics"""
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild_id)
        
        # Get statistics
        stats = await self.db.get_guild_stats(guild_id)
        
        # Get guild config
        config = await self.db.get_guild_config(guild_id)
        
        # Create embed
        embed = discord.Embed(
            title="🤖 Automod Bot Status",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Statistics
        embed.add_field(
            name="📊 Statistics",
            value=(
                f"Total Violations: {stats['total_violations']}\n"
                f"Last 24h: {stats['recent_violations_24h']}\n"
                f"Tracked Users: {stats['total_tracked_users']}\n"
                f"Warned Users: {stats['warned_users']}"
            ),
            inline=True
        )
        
        # Configuration
        embed.add_field(
            name="⚙️ Configuration",
            value=(
                f"Status: {'✅ Enabled' if config.enabled else '❌ Disabled'}\n"
                f"Avg Trust Score: {stats['average_trust_score']}/100\n"
                f"Log Channel: {'<#' + config.log_channel_id + '>' if config.log_channel_id else 'Not set'}"
            ),
            inline=True
        )
        
        # AI Providers
        from utils import AIClient
        embed.add_field(
            name="🤖 AI Providers",
            value="OpenAI, Z.ai",
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {interaction.user}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @automod_group.command(name="warnings", description="Check user warnings")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        """View warning history for a user"""
        await interaction.response.defer(ephemeral=True)
        
        # Get user reputation
        user_rep = await self.db.get_user_reputation(
            str(user.id),
            str(interaction.guild_id)
        )
        
        if not user_rep:
            await interaction.followup.send(
                f"ℹ️ No warnings found for {user.mention}",
                ephemeral=True
            )
            return
        
        # Get violation history
        violations = await self.db.get_user_violations(
            str(user.id),
            str(interaction.guild_id),
            limit=10
        )
        
        # Create embed
        embed = discord.Embed(
            title=f"⚠️ Warnings for {user}",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Trust score
        trust_level = TrustScoreCalculator.get_trust_level(user_rep.trust_score)
        embed.add_field(
            name="Trust Score",
            value=f"{user_rep.trust_score}/100 ({trust_level})",
            inline=True
        )
        
        embed.add_field(
            name="Warning Count",
            value=str(user_rep.warning_count),
            inline=True
        )
        
        # Recent violations
        if violations:
            violation_text = []
            for i, v in enumerate(violations[:5], 1):
                time_ago = (datetime.now(timezone.utc) - v.timestamp).days
                violation_text.append(
                    f"{i}. {v.reason} ({time_ago}d ago)"
                )
            
            embed.add_field(
                name="Recent Violations",
                value="\n".join(violation_text) if violation_text else "None",
                inline=False
            )
        
        embed.set_footer(text=f"User ID: {user.id}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @automod_group.command(name="reset", description="Reset user warnings")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_warnings(self, interaction: discord.Interaction, user: discord.Member):
        """Reset warnings for a user"""
        await interaction.response.defer(ephemeral=True)
        
        success = await self.db.reset_user_warnings(
            str(user.id),
            str(interaction.guild_id)
        )
        
        if success:
            # Invalidate cache
            await self.cache.invalidate_user_cache(str(user.id), str(interaction.guild_id))
            
            embed = discord.Embed(
                title="✅ Warnings Reset",
                description=f"Warnings have been reset for {user.mention}",
                color=discord.Color.green()
            )
            
            logger.info(f"Warnings reset for {user} by {interaction.user}")
        else:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to reset warnings for {user.mention}",
                color=discord.Color.red()
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @automod_group.command(name="whitelist", description="Manage allowed words")
    @app_commands.checks.has_permissions(administrator=True)
    async def whitelist(
        self,
        interaction: discord.Interaction,
        action: str,
        word: str
    ):
        """Add or remove words from whitelist"""
        await interaction.response.defer(ephemeral=True)
        
        guild_config = await self.db.get_guild_config(str(interaction.guild_id))
        
        if action.lower() == "add":
            guild_config.add_allowed_word(word)
            message = f"✅ Added `{word}` to whitelist"
            color = discord.Color.green()
        
        elif action.lower() == "remove":
            success = guild_config.remove_allowed_word(word)
            if success:
                message = f"✅ Removed `{word}` from whitelist"
                color = discord.Color.green()
            else:
                message = f"❌ `{word}` not found in whitelist"
                color = discord.Color.red()
        else:
            message = "❌ Invalid action. Use `add` or `remove`"
            color = discord.Color.red()
            embed = discord.Embed(description=message, color=color)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Save config
        await self.db.create_or_update_guild_config(guild_config)
        await self.cache.invalidate_guild_cache(str(interaction.guild_id))
        
        embed = discord.Embed(description=message, color=color)
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @automod_group.command(name="config", description="View current configuration")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_config(self, interaction: discord.Interaction):
        """Display current guild configuration"""
        await interaction.response.defer(ephemeral=True)
        
        config = await self.db.get_guild_config(str(interaction.guild_id))
        
        embed = discord.Embed(
            title="⚙️ Automod Configuration",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Status
        embed.add_field(
            name="Status",
            value="✅ Enabled" if config.enabled else "❌ Disabled",
            inline=True
        )
        
        # Trust threshold
        embed.add_field(
            name="Trust Bypass Threshold",
            value=f"{config.min_trust_score_for_bypass}/100",
            inline=True
        )
        
        # Whitelist
        embed.add_field(
            name="Whitelisted Words",
            value=", ".join(f"`{w}`" for w in config.allowed_words[:10]),
            inline=False
        )
        
        # Log channel
        log_channel = "Not set"
        if config.log_channel_id:
            log_channel = f"<#{config.log_channel_id}>"
        
        embed.add_field(
            name="Log Channel",
            value=log_channel,
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @automod_group.command(name="trust", description="Check user trust score")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def check_trust(self, interaction: discord.Interaction, user: discord.Member):
        """View detailed trust score breakdown"""
        await interaction.response.defer(ephemeral=True)
        
        user_rep = await self.db.get_user_reputation(
            str(user.id),
            str(interaction.guild_id)
        )
        
        if not user_rep:
            # Calculate initial score
            initial_score = TrustScoreCalculator.calculate_initial_score(user.created_at)
            trust_level = TrustScoreCalculator.get_trust_level(initial_score)
            
            embed = discord.Embed(
                title=f"🔍 Trust Score: {user}",
                description=f"**{initial_score}/100** ({trust_level})",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Status",
                value="No violations recorded",
                inline=False
            )
        else:
            trust_level = TrustScoreCalculator.get_trust_level(user_rep.trust_score)
            
            embed = discord.Embed(
                title=f"🔍 Trust Score: {user}",
                description=f"**{user_rep.trust_score}/100** ({trust_level})",
                color=discord.Color.blue()
            )
            
            # Account age bonus
            now = datetime.now(timezone.utc)
            account_creation = user.created_at
            if account_creation.tzinfo is None:
                account_creation = account_creation.replace(tzinfo=timezone.utc)
            account_age_days = (now - account_creation).days
            age_bonus = TrustScoreCalculator.calculate_account_age_bonus(user.created_at)
            
            embed.add_field(
                name="Account Age",
                value=f"{account_age_days} days (+{age_bonus} bonus)",
                inline=True
            )
            
            # Violations
            embed.add_field(
                name="Warnings",
                value=f"{user_rep.warning_count} (-{user_rep.warning_count * 15} penalty)",
                inline=True
            )
            
            # Positive actions
            positive_bonus = TrustScoreCalculator.calculate_positive_action_bonus(user_rep.positive_actions)
            embed.add_field(
                name="Positive Actions",
                value=f"{user_rep.positive_actions} (+{positive_bonus} bonus)",
                inline=True
            )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    pass
