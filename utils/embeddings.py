"""
Semantic Embeddings Manager for False Positive Reduction
Uses sentence transformers for semantic similarity checking
"""

import logging
from typing import List, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available")

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """
    Manages semantic embeddings for context-aware moderation
    Reduces false positives by understanding semantic similarity
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embeddings manager
        
        Args:
            model_name: Sentence transformer model (default: all-MiniLM-L6-v2, fast and efficient)
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.reclaimed_language_examples = None
        self.false_positive_examples = None
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                logger.info(f"✅ Embeddings model loaded: {model_name}")
                self._load_reference_embeddings()
            except Exception as e:
                logger.error(f"Failed to load embeddings model: {e}")
                self.model = None
        else:
            logger.warning("Semantic filtering disabled - sentence-transformers not installed")
    
    def _load_reference_embeddings(self):
        """Load embeddings for known reclaimed language and false positives"""
        if not self.model:
            return
        
        # Examples of LGBTQ+ reclaimed language (to avoid false positives)
        reclaimed_examples = [
            "I'm so gay for this",
            "That's so gay (positive context)",
            "Queer community",
            "We're here, we're queer",
            "Yaas queen",
            "Slay queen"
        ]
        
        # Common false positive patterns
        false_positive_patterns = [
            "This is fire",
            "That's sick!",
            "This slaps",
            "Absolute banger",
            "No cap fr fr",
            "Bussin"
        ]
        
        try:
            self.reclaimed_language_examples = self.model.encode(
                reclaimed_examples,
                convert_to_numpy=True
            )
            
            self.false_positive_examples = self.model.encode(
                false_positive_patterns,
                convert_to_numpy=True
            )
            
            logger.info("✅ Reference embeddings loaded")
        except Exception as e:
            logger.error(f"Failed to load reference embeddings: {e}")
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
        
        Returns:
            Similarity score (0-1, higher = more similar)
        """
        if not self.model:
            return 0.0
        
        try:
            embeddings = self.model.encode([text1, text2], convert_to_numpy=True)
            
            # Cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            
            return float(similarity)
        except Exception as e:
            logger.error(f"Similarity calculation error: {e}")
            return 0.0
    
    def is_likely_reclaimed_language(
        self,
        text: str,
        similarity_threshold: float = 0.65
    ) -> bool:
        """
        Check if text is likely reclaimed language (LGBTQ+ community usage)
        
        Args:
            text: Text to check
            similarity_threshold: Minimum similarity to consider a match
        
        Returns:
            True if likely reclaimed language
        """
        if not self.model or self.reclaimed_language_examples is None:
            return False
        
        try:
            text_embedding = self.model.encode([text], convert_to_numpy=True)[0]
            
            # Calculate similarity with all reclaimed language examples
            similarities = []
            for example_embedding in self.reclaimed_language_examples:
                similarity = np.dot(text_embedding, example_embedding) / (
                    np.linalg.norm(text_embedding) * np.linalg.norm(example_embedding)
                )
                similarities.append(similarity)
            
            max_similarity = max(similarities) if similarities else 0.0
            
            if max_similarity >= similarity_threshold:
                logger.info(f"Detected reclaimed language (similarity: {max_similarity:.2f})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Reclaimed language check error: {e}")
            return False
    
    def is_likely_false_positive(
        self,
        text: str,
        similarity_threshold: float = 0.70
    ) -> bool:
        """
        Check if text matches common false positive patterns
        
        Args:
            text: Text to check
            similarity_threshold: Minimum similarity to consider a match
        
        Returns:
            True if likely a false positive
        """
        if not self.model or self.false_positive_examples is None:
            return False
        
        try:
            text_embedding = self.model.encode([text], convert_to_numpy=True)[0]
            
            # Calculate similarity with false positive examples
            similarities = []
            for example_embedding in self.false_positive_examples:
                similarity = np.dot(text_embedding, example_embedding) / (
                    np.linalg.norm(text_embedding) * np.linalg.norm(example_embedding)
                )
                similarities.append(similarity)
            
            max_similarity = max(similarities) if similarities else 0.0
            
            if max_similarity >= similarity_threshold:
                logger.info(f"Detected false positive pattern (similarity: {max_similarity:.2f})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"False positive check error: {e}")
            return False
    
    def filter_false_positives(
        self,
        flagged: bool,
        text: str,
        categories: dict
    ) -> bool:
        """
        Post-process AI results to reduce false positives
        
        Args:
            flagged: Whether AI flagged the content
            text: Original text
            categories: AI-detected categories
        
        Returns:
            Adjusted flagged status (may change from True to False)
        """
        if not flagged:
            return False  # Not flagged, no need to check
        
        # Check for reclaimed language
        if self.is_likely_reclaimed_language(text):
            logger.info(f"False positive filter: Reclaimed language detected")
            return False
        
        # Check for common false positive patterns
        if self.is_likely_false_positive(text):
            logger.info(f"False positive filter: Common slang detected")
            return False
        
        # Keep the original flagged status
        return flagged
    
    def is_available(self) -> bool:
        """Check if embeddings manager is available"""
        return self.model is not None
