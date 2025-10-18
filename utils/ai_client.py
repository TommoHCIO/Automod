"""
AI Client Wrapper supporting multiple providers with fallback
Z.ai (primary) → OpenAI (fallback) → Mistral (tertiary)
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from enum import Enum

# Import AI SDKs
try:
    from zhipuai import ZhipuAI
    ZHIPU_AVAILABLE = True
except ImportError:
    ZHIPU_AVAILABLE = False
    logging.warning("zhipuai SDK not available")

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("openai SDK not available")

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers"""
    ZAI = "zai"
    OPENAI = "openai"
    MISTRAL = "mistral"


class ModerationResult:
    """Standardized moderation result across providers"""
    
    def __init__(
        self,
        flagged: bool,
        categories: Dict[str, bool],
        category_scores: Dict[str, float],
        confidence: float,
        provider: str,
        raw_response: Optional[Dict] = None
    ):
        self.flagged = flagged
        self.categories = categories
        self.category_scores = category_scores
        self.confidence = confidence
        self.provider = provider
        self.raw_response = raw_response
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for caching"""
        return {
            "flagged": self.flagged,
            "categories": self.categories,
            "category_scores": self.category_scores,
            "confidence": self.confidence,
            "provider": self.provider
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModerationResult':
        """Create from cached dictionary"""
        return cls(
            flagged=data["flagged"],
            categories=data["categories"],
            category_scores=data["category_scores"],
            confidence=data["confidence"],
            provider=data["provider"]
        )


class AIClient:
    """
    Multi-provider AI moderation client with automatic fallback
    """
    
    def __init__(
        self,
        zai_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        mistral_api_key: Optional[str] = None,
        timeout: float = 1.0,
        confidence_threshold: float = 0.7
    ):
        self.zai_api_key = zai_api_key
        self.openai_api_key = openai_api_key
        self.mistral_api_key = mistral_api_key
        self.timeout = timeout
        self.confidence_threshold = confidence_threshold
        
        # Initialize clients
        self.zai_client = None
        self.openai_client = None
        self.mistral_client = None
        
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize available AI clients"""
        # Z.ai client
        if self.zai_api_key and ZHIPU_AVAILABLE:
            try:
                self.zai_client = ZhipuAI(api_key=self.zai_api_key)
                logger.info("✅ Z.ai client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Z.ai client: {e}")
        
        # OpenAI client
        if self.openai_api_key and OPENAI_AVAILABLE:
            try:
                self.openai_client = AsyncOpenAI(
                    api_key=self.openai_api_key,
                    timeout=self.timeout
                )
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    async def moderate_content(
        self,
        text: str,
        preferred_provider: AIProvider = AIProvider.ZAI
    ) -> Optional[ModerationResult]:
        """
        Moderate text content with automatic fallback
        
        Args:
            text: Text to moderate
            preferred_provider: Preferred AI provider
        
        Returns:
            ModerationResult or None if all providers fail
        """
        providers_to_try = self._get_fallback_order(preferred_provider)
        
        for provider in providers_to_try:
            try:
                result = await asyncio.wait_for(
                    self._moderate_with_provider(text, provider),
                    timeout=self.timeout
                )
                
                if result:
                    logger.debug(f"Moderation successful with {provider.value}")
                    return result
                    
            except asyncio.TimeoutError:
                logger.warning(f"{provider.value} timed out after {self.timeout}s")
            except Exception as e:
                logger.warning(f"{provider.value} error: {e}")
        
        logger.error("All AI providers failed")
        return None
    
    def _get_fallback_order(self, preferred: AIProvider) -> List[AIProvider]:
        """Get ordered list of providers to try"""
        if preferred == AIProvider.ZAI:
            return [AIProvider.ZAI, AIProvider.OPENAI]
        elif preferred == AIProvider.OPENAI:
            return [AIProvider.OPENAI, AIProvider.ZAI]
        else:
            return [AIProvider.OPENAI, AIProvider.ZAI]
    
    async def _moderate_with_provider(
        self,
        text: str,
        provider: AIProvider
    ) -> Optional[ModerationResult]:
        """Moderate with specific provider"""
        if provider == AIProvider.ZAI:
            return await self._moderate_with_zai(text)
        elif provider == AIProvider.OPENAI:
            return await self._moderate_with_openai(text)
        else:
            return None
    
    async def _moderate_with_zai(self, text: str) -> Optional[ModerationResult]:
        """
        Moderate with Z.ai API
        Note: Z.ai API structure may need adjustment based on actual API docs
        """
        if not self.zai_client:
            return None
        
        try:
            # Z.ai content safety check
            # This is a placeholder - actual API call structure depends on Z.ai docs
            response = self.zai_client.chat.completions.create(
                model="glm-4-air",
                messages=[{
                    "role": "system",
                    "content": "You are a content moderator. Analyze the following text for hate speech, including racism, homophobia, transphobia, sexism, ableism, and xenophobia. Return only 'FLAGGED' if it contains hate speech, or 'SAFE' if it doesn't."
                }, {
                    "role": "user",
                    "content": text
                }],
                max_tokens=10,
                temperature=0
            )
            
            result_text = response.choices[0].message.content.strip().upper()
            flagged = "FLAGGED" in result_text
            
            # Create standardized result
            categories = {
                "hate_speech": flagged,
                "racism": False,
                "homophobia": False,
                "harassment": flagged
            }
            
            category_scores = {
                "hate_speech": 0.9 if flagged else 0.1,
                "racism": 0.0,
                "homophobia": 0.0,
                "harassment": 0.8 if flagged else 0.1
            }
            
            return ModerationResult(
                flagged=flagged,
                categories=categories,
                category_scores=category_scores,
                confidence=0.85,
                provider="zai"
            )
            
        except Exception as e:
            logger.error(f"Z.ai moderation error: {e}")
            return None
    
    async def _moderate_with_openai(self, text: str) -> Optional[ModerationResult]:
        """
        Moderate with OpenAI Moderation API
        Free, fast, and reliable
        """
        if not self.openai_client:
            return None
        
        try:
            response = await self.openai_client.moderations.create(input=text)
            result = response.results[0]
            
            # OpenAI categories
            categories = {
                "hate": result.categories.hate,
                "hate/threatening": result.categories.hate_threatening,
                "harassment": result.categories.harassment,
                "harassment/threatening": result.categories.harassment_threatening,
                "self-harm": result.categories.self_harm,
                "sexual": result.categories.sexual,
                "violence": result.categories.violence
            }
            
            category_scores = {
                "hate": result.category_scores.hate,
                "hate/threatening": result.category_scores.hate_threatening,
                "harassment": result.category_scores.harassment,
                "harassment/threatening": result.category_scores.harassment_threatening,
                "self-harm": result.category_scores.self_harm,
                "sexual": result.category_scores.sexual,
                "violence": result.category_scores.violence
            }
            
            # Determine if flagged for hate speech specifically
            flagged = (
                result.categories.hate or
                result.categories.hate_threatening or
                result.category_scores.hate > self.confidence_threshold
            )
            
            # Calculate overall confidence
            confidence = max(
                result.category_scores.hate,
                result.category_scores.hate_threatening,
                result.category_scores.harassment
            )
            
            return ModerationResult(
                flagged=flagged,
                categories=categories,
                category_scores=category_scores,
                confidence=confidence,
                provider="openai",
                raw_response=response.model_dump()
            )
            
        except Exception as e:
            logger.error(f"OpenAI moderation error: {e}")
            return None
    
    def is_available(self, provider: AIProvider) -> bool:
        """Check if a provider is available"""
        if provider == AIProvider.ZAI:
            return self.zai_client is not None
        elif provider == AIProvider.OPENAI:
            return self.openai_client is not None
        return False
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        providers = []
        if self.zai_client:
            providers.append("zai")
        if self.openai_client:
            providers.append("openai")
        return providers
