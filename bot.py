"""
Discord Automod Bot - Main Entry Point
AI-powered hate speech detection with progressive punishment system
"""

import os
import sys
import logging
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

import discord
from discord.ext import commands

# Import utilities
from utils import (
    CacheManager,
    DatabaseManager,
    AIClient,
    EmbeddingsManager,
    TrustScoreCalculator,
    MessageQueue
)

# Import cogs
from cogs.moderation import ModerationCog
from cogs.admin import AdminCog
from cogs.logging import LoggingCog

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("automod.log")
    ]
)

logger = logging.getLogger(__name__)


class AutomodBot(commands.Bot):
    """
    Main bot class with initialization and setup
    """
    
    def __init__(self):
        # Load configuration
        self.config = self._load_config()
        
        # Bot intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        # Initialize bot
        super().__init__(
            command_prefix=self.config.get("bot", {}).get("command_prefix", "!"),
            intents=intents,
            help_command=None
        )
        
        # Initialize managers (will be set up in setup_hook)
        self.db: DatabaseManager = None
        self.cache: CacheManager = None
        self.ai_client: AIClient = None
        self.embeddings: EmbeddingsManager = None
        self.message_queue: MessageQueue = None
        
        logger.info("🤖 Automod Bot initialized")
    
    def _load_config(self) -> dict:
        """Load configuration from JSON file"""
        config_path = Path("config/settings.json")
        
        if not config_path.exists():
            logger.error("Configuration file not found!")
            return {}
        
        with open(config_path, "r") as f:
            return json.load(f)
    
    async def setup_hook(self):
        """
        Setup hook - called before bot starts
        Initialize all managers and load cogs
        """
        logger.info("🔧 Running setup hook...")
        
        # Initialize Database
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            logger.error("MONGODB_URI not set in environment variables!")
            raise ValueError("MONGODB_URI required")
        
        self.db = DatabaseManager(mongodb_uri)
        await self.db.connect()
        
        # Initialize Cache
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.cache = CacheManager(redis_url)
        await self.cache.connect()
        
        # Initialize AI Client
        zai_key = os.getenv("Z_AI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not zai_key and not openai_key:
            logger.error("No AI API keys provided!")
            raise ValueError("At least one AI provider key required (Z_AI_API_KEY or OPENAI_API_KEY)")
        
        self.ai_client = AIClient(
            zai_api_key=zai_key,
            openai_api_key=openai_key,
            timeout=self.config.get("moderation", {}).get("ai_timeout_seconds", 1.0),
            confidence_threshold=self.config.get("ai_providers", {}).get("confidence_threshold", 0.7)
        )
        
        logger.info(f"Available AI providers: {self.ai_client.get_available_providers()}")
        
        # Initialize Embeddings Manager
        if self.config.get("moderation", {}).get("enable_semantic_filtering", True):
            self.embeddings = EmbeddingsManager()
        else:
            logger.info("Semantic filtering disabled")
            self.embeddings = EmbeddingsManager()  # Still initialize but won't be used
        
        # Initialize Message Queue
        rate_config = self.config.get("rate_limiting", {})
        self.message_queue = MessageQueue(
            max_requests_per_second=rate_config.get("max_requests_per_second", 40),
            delay_between_messages=rate_config.get("message_queue_delay_seconds", 0.5)
        )
        
        # Load cogs
        await self._load_cogs()
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
        
        logger.info("✅ Setup complete!")
    
    async def _load_cogs(self):
        """Load all cogs"""
        try:
            # Moderation Cog
            moderation_cog = ModerationCog(
                self,
                self.db,
                self.cache,
                self.ai_client,
                self.embeddings,
                self.config
            )
            await self.add_cog(moderation_cog)
            
            # Admin Cog
            admin_cog = AdminCog(self, self.db, self.cache)
            await self.add_cog(admin_cog)
            
            # Logging Cog
            logging_cog = LoggingCog(self, self.db)
            await self.add_cog(logging_cog)
            
            logger.info("✅ All cogs loaded")
            
        except Exception as e:
            logger.error(f"Failed to load cogs: {e}", exc_info=True)
            raise
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"✅ Bot is ready!")
        logger.info(f"   Logged in as: {self.user}")
        logger.info(f"   User ID: {self.user.id}")
        logger.info(f"   Servers: {len(self.guilds)}")
        
        # Set bot status
        activity_type = self.config.get("bot", {}).get("activity_type", "watching")
        status_text = self.config.get("bot", {}).get("status", "Moderating for hate speech")
        
        activity_map = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening
        }
        
        activity = discord.Activity(
            type=activity_map.get(activity_type, discord.ActivityType.watching),
            name=status_text
        )
        
        await self.change_presence(activity=activity, status=discord.Status.online)
    
    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a new server"""
        logger.info(f"Joined new server: {guild.name} ({guild.id})")
        
        # Create default guild config
        from models import GuildConfig
        config = GuildConfig(guild_id=str(guild.id))
        await self.db.create_or_update_guild_config(config)
        
        # Send welcome message to system channel
        if guild.system_channel:
            embed = discord.Embed(
                title="👋 Thanks for adding Automod Bot!",
                description=(
                    "I'm here to protect your server from hate speech using AI detection.\n\n"
                    "**Quick Start:**\n"
                    "• Use `/automod status` to view bot status\n"
                    "• Use `/automod config` to view configuration\n"
                    "• Set a log channel with `/automod` commands\n\n"
                    "**Features:**\n"
                    "✅ AI-powered hate speech detection\n"
                    "✅ Progressive punishment system\n"
                    "✅ User reputation tracking\n"
                    "✅ Profanity whitelist support\n\n"
                    "The bot is now active and monitoring messages!"
                ),
                color=discord.Color.blue()
            )
            
            embed.set_footer(text="Use /automod status to get started")
            
            try:
                await guild.system_channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Cannot send to system channel in {guild.name}")
    
    async def on_error(self, event_method: str, *args, **kwargs):
        """Global error handler"""
        logger.error(f"Error in {event_method}", exc_info=True)
    
    async def close(self):
        """Cleanup when bot shuts down"""
        logger.info("🛑 Shutting down bot...")
        
        # Close connections
        if self.db:
            await self.db.close()
        
        if self.cache:
            await self.cache.close()
        
        await super().close()
        logger.info("✅ Bot shutdown complete")


async def main():
    """Main entry point"""
    # Get Discord token
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        logger.error("DISCORD_TOKEN not found in environment variables!")
        logger.error("Please create a .env file with your Discord bot token")
        return
    
    # Create and run bot
    bot = AutomodBot()
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
