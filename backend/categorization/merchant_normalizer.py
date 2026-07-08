"""Merchant name normalization for consistent categorization."""

import re
from typing import Optional


class MerchantNormalizer:
    """Normalizes merchant names to a canonical form for consistent categorization."""
    
    def __init__(self):
        """Initialize the merchant normalizer."""
        # Common patterns to normalize (order matters - compound first)
        self.patterns = [
            # Remove compound suffixes first
            (r"\s+(?:Pvt\s+Ltd\.?|Private\s+Limited|Pvt\.?\s+Ltd\.?)\s*$", ""),
            (r"\s+(?:Pvt\.?|Ltd\.?|Limited|LLP|Inc\.?|Corp\.?|Corporation)\s*$", ""),
            (r"\s+(?:LLC|GmbH|AG|SA|S\.A\.)\s*$", ""),
            
            # Normalize common variations
            (r"\b(?:The|A|An)\s+", ""),
            (r"\s+(?:Store|Shop|Mart|Market|Outlet|Retail)\s*$", ""),
            (r"\s+(?:Online|Web|Internet|E-commerce)\s*$", ""),
            
            # Remove extra whitespace and special characters
            (r"\s+", " "),
            (r"[^\w\s]", ""),
        ]
    
    def normalize(self, merchant: str) -> str:
        """Normalize a merchant name to its canonical form.
        
        Args:
            merchant: The raw merchant name from transaction data.
        
        Returns:
            Normalized merchant name.
        """
        if not merchant:
            return ""
        
        normalized = merchant.strip()
        
        # Apply normalization patterns in order
        for pattern, replacement in self.patterns:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        # Convert to lowercase and strip
        normalized = normalized.lower().strip()
        
        return normalized
    
    def normalize_batch(self, merchants: list[str]) -> list[str]:
        """Normalize a batch of merchant names.
        
        Args:
            merchants: List of raw merchant names.
        
        Returns:
            List of normalized merchant names.
        """
        return [self.normalize(m) for m in merchants]


# Global normalizer instance
_normalizer: Optional[MerchantNormalizer] = None


def get_merchant_normalizer() -> MerchantNormalizer:
    """Get the global merchant normalizer instance (singleton pattern)."""
    global _normalizer
    if _normalizer is None:
        _normalizer = MerchantNormalizer()
    return _normalizer


def reset_merchant_normalizer() -> None:
    """Reset the global merchant normalizer (useful for testing)."""
    global _normalizer
    _normalizer = None
