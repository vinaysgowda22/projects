"""3-layer merchant category classifier."""

import json
import re
from pathlib import Path
from typing import Optional

from loguru import logger
from rapidfuzz import fuzz, process

from backend.categorization.merchant_mapping_store import (
    MerchantMappingStore,
    get_merchant_mapping_store,
)
from backend.categorization.merchant_normalizer import (
    MerchantNormalizer,
    get_merchant_normalizer,
)


class CategoryClassifier:
    """Layered merchant category classifier with learned-mapping support."""

    def __init__(
        self,
        normalizer: Optional[MerchantNormalizer] = None,
        mapping_store: Optional[MerchantMappingStore] = None,
    ):
        """Initialize the category classifier.

        Args:
            normalizer: MerchantNormalizer instance. If None, uses global instance.
            mapping_store: Learned merchant->category store. If None, uses the
                global instance.
        """
        self.normalizer = normalizer or get_merchant_normalizer()
        self.mapping_store = mapping_store or get_merchant_mapping_store()
        self.categories = self._load_categories()

    def _load_categories(self) -> dict:
        """Load merchant category mappings from JSON file."""
        categories_path = Path(__file__).parent / "data" / "merchant_categories.json"
        with open(categories_path) as f:
            return json.load(f)

    def classify(self, merchant: str) -> str:
        """Classify a merchant into a category using a layered approach.

        Layer 0: Learned mappings (user corrections + cached AI results)
        Layer 1: Exact match after normalization
        Layer 2: Fuzzy match using string similarity
        Layer 3a: Pattern-based inference
        Layer 3b: AI classification (optional), cached back to the store

        Args:
            merchant: The merchant name to classify.

        Returns:
            Category name (defaults to "other" if no match found).
        """
        if not merchant:
            return "other"

        normalized = self.normalizer.normalize(merchant)

        # Layer 0: Learned mappings (user corrections + cached AI results)
        category = self.mapping_store.get(normalized)
        if category:
            return category

        # Layer 1: Exact match
        category = self._exact_match(normalized)
        if category:
            return category

        # Layer 2: Fuzzy match
        category = self._fuzzy_match(normalized)
        if category:
            return category

        # Layer 3a: Pattern match
        category = self._pattern_match(normalized)
        if category:
            return category

        # Layer 3b: AI classification (optional), cached back to the store
        category = self._ai_match(normalized)
        if category:
            self.mapping_store.set(normalized, category)
            return category

        # Default: other
        return "other"

    def learn(self, merchant: str, category: str) -> None:
        """Persist a user correction so future transactions use it.

        Args:
            merchant: The raw merchant name (will be normalized).
            category: The correct category chosen by the user.
        """
        if not merchant or not category:
            return
        normalized = self.normalizer.normalize(merchant)
        self.mapping_store.set(normalized, category)

    def _ai_match(self, normalized_merchant: str) -> Optional[str]:
        """Layer 3b: classify an unknown merchant via the AI provider.

        Only runs when AI features are enabled. The LLM is constrained to pick
        from the known category list; any out-of-list answer is rejected.

        Args:
            normalized_merchant: Normalized merchant name.

        Returns:
            A valid category name, or None if AI is disabled/unavailable or the
            response is not a recognized category.
        """
        from backend.config import get_config

        config = get_config()
        if not config.ai.enabled:
            return None

        categories = self.get_all_categories()
        try:
            from openai import OpenAI

            client = OpenAI(api_key=config.ai.api_key)
            response = client.chat.completions.create(
                model=config.ai.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You categorize merchant names. Reply with exactly "
                            "one category from this list and nothing else: "
                            + ", ".join(categories)
                        ),
                    },
                    {"role": "user", "content": normalized_merchant},
                ],
                temperature=0,
            )
            answer = (response.choices[0].message.content or "").strip().lower()
        except Exception as e:
            logger.warning(f"AI category classification failed: {e}")
            return None

        if answer in categories:
            return answer
        logger.warning(f"AI returned unknown category '{answer}'; ignoring")
        return None

    def _exact_match(self, normalized_merchant: str) -> Optional[str]:
        """Layer 1: Exact match against known merchants.

        Args:
            normalized_merchant: Normalized merchant name.

        Returns:
            Category name if exact match found, None otherwise.
        """
        for category, data in self.categories.items():
            exact_matches = data.get("exact_matches", [])
            if normalized_merchant in [
                self.normalizer.normalize(m) for m in exact_matches
            ]:
                return category
        return None

    def _fuzzy_match(
        self, normalized_merchant: str, threshold: int = 80
    ) -> Optional[str]:
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
            normalized_merchant, all_merchants, scorer=fuzz.ratio
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
