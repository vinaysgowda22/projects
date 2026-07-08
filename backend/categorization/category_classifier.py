"""3-layer merchant category classifier."""

import json
import re
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz, process

from backend.categorization.merchant_normalizer import MerchantNormalizer, get_merchant_normalizer


class CategoryClassifier:
    """3-layer merchant category classifier."""
    
    def __init__(self, normalizer: Optional[MerchantNormalizer] = None):
        """Initialize the category classifier.
        
        Args:
            normalizer: MerchantNormalizer instance. If None, uses global instance.
        """
        self.normalizer = normalizer or get_merchant_normalizer()
        self.categories = self._load_categories()
    
    def _load_categories(self) -> dict:
        """Load merchant category mappings from JSON file."""
        categories_path = Path(__file__).parent / "data" / "merchant_categories.json"
        with open(categories_path) as f:
            return json.load(f)
    
    def classify(self, merchant: str) -> str:
        """Classify a merchant into a category using 3-layer approach.
        
        Layer 1: Exact match after normalization
        Layer 2: Fuzzy match using string similarity
        Layer 3: Pattern-based inference
        
        Args:
            merchant: The merchant name to classify.
        
        Returns:
            Category name (defaults to "other" if no match found).
        """
        if not merchant:
            return "other"
        
        normalized = self.normalizer.normalize(merchant)
        
        # Layer 1: Exact match
        category = self._exact_match(normalized)
        if category:
            return category
        
        # Layer 2: Fuzzy match
        category = self._fuzzy_match(normalized)
        if category:
            return category
        
        # Layer 3: Pattern match
        category = self._pattern_match(normalized)
        if category:
            return category
        
        # Default: other
        return "other"
    
    def _exact_match(self, normalized_merchant: str) -> Optional[str]:
        """Layer 1: Exact match against known merchants.
        
        Args:
            normalized_merchant: Normalized merchant name.
        
        Returns:
            Category name if exact match found, None otherwise.
        """
        for category, data in self.categories.items():
            exact_matches = data.get("exact_matches", [])
            if normalized_merchant in [self.normalizer.normalize(m) for m in exact_matches]:
                return category
        return None
    
    def _fuzzy_match(self, normalized_merchant: str, threshold: int = 80) -> Optional[str]:
        """Layer 2: Fuzzy match using string similarity.
        
        Args:
            normalized_merchant: Normalized merchant name.
            threshold: Similarity threshold (0-100).
        
        Returns:
            Category name if fuzzy match found, None otherwise.
        """
        all_merchants = []
        merchant_to_category = {}
        
        for category, data in self.categories.items():
            exact_matches = data.get("exact_matches", [])
            for merchant in exact_matches:
                normalized = self.normalizer.normalize(merchant)
                all_merchants.append(normalized)
                merchant_to_category[normalized] = category
        
        if not all_merchants:
            return None
        
        # Use rapidfuzz for fuzzy matching
        result = process.extractOne(
            normalized_merchant,
            all_merchants,
            scorer=fuzz.ratio
        )
        
        if result and result[1] >= threshold:
            matched_merchant = result[0]
            return merchant_to_category.get(matched_merchant)
        
        return None
    
    def _pattern_match(self, normalized_merchant: str) -> Optional[str]:
        """Layer 3: Pattern-based category inference.
        
        Args:
            normalized_merchant: Normalized merchant name.
        
        Returns:
            Category name if pattern match found, None otherwise.
        """
        for category, data in self.categories.items():
            patterns = data.get("patterns", [])
            for pattern in patterns:
                if re.match(pattern, normalized_merchant, re.IGNORECASE):
                    return category
        return None
    
    def classify_batch(self, merchants: list[str]) -> list[str]:
        """Classify a batch of merchants.
        
        Args:
            merchants: List of merchant names.
        
        Returns:
            List of category names.
        """
        return [self.classify(m) for m in merchants]
    
    def get_all_categories(self) -> list[str]:
        """Get all available category names.
        
        Returns:
            List of category names.
        """
        return list(self.categories.keys())


# Global classifier instance
_classifier: Optional[CategoryClassifier] = None


def get_category_classifier() -> CategoryClassifier:
    """Get the global category classifier instance (singleton pattern)."""
    global _classifier
    if _classifier is None:
        _classifier = CategoryClassifier()
    return _classifier


def reset_category_classifier() -> None:
    """Reset the global category classifier (useful for testing)."""
    global _classifier
    _classifier = None
