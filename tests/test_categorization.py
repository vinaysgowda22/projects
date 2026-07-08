"""Tests for merchant categorization and normalization."""

from backend.categorization.category_classifier import (
    CategoryClassifier,
    get_category_classifier,
    reset_category_classifier,
)
from backend.categorization.merchant_normalizer import (
    MerchantNormalizer,
    reset_merchant_normalizer,
)


class TestMerchantNormalizer:
    """Test suite for MerchantNormalizer."""

    def setup_method(self):
        """Reset normalizer before each test."""
        reset_merchant_normalizer()

    def test_normalize_removes_suffixes(self):
        """Test that common company suffixes are removed."""
        normalizer = MerchantNormalizer()

        assert normalizer.normalize("Amazon Pvt Ltd") == "amazon"
        assert normalizer.normalize("Flipkart Limited") == "flipkart"
        assert normalizer.normalize("Myntra Pvt. Ltd.") == "myntra"

    def test_normalize_removes_articles(self):
        """Test that articles are removed."""
        normalizer = MerchantNormalizer()

        assert normalizer.normalize("The Starbucks") == "starbucks"
        assert normalizer.normalize("A Cafe") == "cafe"

    def test_normalize_removes_common_words(self):
        """Test that common store-related words are removed."""
        normalizer = MerchantNormalizer()

        assert normalizer.normalize("Nike Store") == "nike"
        assert normalizer.normalize("Apple Online Store") == "apple"
        assert normalizer.normalize("Bigbasket Online") == "bigbasket"

    def test_normalize_handles_special_characters(self):
        """Test that special characters are removed."""
        normalizer = MerchantNormalizer()

        assert normalizer.normalize("Swiggy-Food-Delivery") == "swiggyfooddelivery"
        assert normalizer.normalize("Zomato!") == "zomato"

    def test_normalize_batch(self):
        """Test batch normalization."""
        normalizer = MerchantNormalizer()

        merchants = ["Amazon Pvt Ltd", "Flipkart Limited", "Myntra Pvt. Ltd."]
        normalized = normalizer.normalize_batch(merchants)

        assert normalized == ["amazon", "flipkart", "myntra"]

    def test_normalize_empty_string(self):
        """Test normalization of empty string."""
        normalizer = MerchantNormalizer()
        assert normalizer.normalize("") == ""
        assert normalizer.normalize(None) == ""


class TestCategoryClassifier:
    """Test suite for CategoryClassifier."""

    def setup_method(self):
        """Reset classifier before each test."""
        reset_category_classifier()

    def test_exact_match_layer1(self):
        """Test Layer 1: Exact match classification."""
        classifier = CategoryClassifier()

        assert classifier.classify("Swiggy Food Delivery") == "food_dining"
        assert classifier.classify("Amazon India") == "shopping"
        assert classifier.classify("Uber India") == "transport"

    def test_fuzzy_match_layer2(self):
        """Test Layer 2: Fuzzy match classification."""
        classifier = CategoryClassifier()

        # Similar but not exact matches
        assert classifier.classify("Swiggy") == "food_dining"
        assert classifier.classify("Amazon") == "shopping"
        assert classifier.classify("Uber") == "transport"

    def test_pattern_match_layer3(self):
        """Test Layer 3: Pattern-based classification."""
        classifier = CategoryClassifier()

        # Merchants matching patterns but not in exact list
        assert classifier.classify("Pizza Palace") == "food_dining"
        assert classifier.classify("Fashion Hub") == "shopping"
        assert classifier.classify("Cab Service") == "transport"

    def test_unknown_merchant_defaults_to_other(self):
        """Test that unknown merchants default to 'other'."""
        classifier = CategoryClassifier()

        assert classifier.classify("Unknown Merchant XYZ") == "other"
        assert classifier.classify("Random Store 123") == "other"

    def test_classify_batch(self):
        """Test batch classification."""
        classifier = CategoryClassifier()

        merchants = ["Swiggy", "Amazon", "Uber", "Unknown"]
        categories = classifier.classify_batch(merchants)

        assert categories == ["food_dining", "shopping", "transport", "other"]

    def test_get_all_categories(self):
        """Test getting all available categories."""
        classifier = CategoryClassifier()

        categories = classifier.get_all_categories()

        assert "food_dining" in categories
        assert "shopping" in categories
        assert "transport" in categories
        assert "other" in categories

    def test_global_singleton(self):
        """Test that global classifier is a singleton."""
        classifier1 = get_category_classifier()
        classifier2 = get_category_classifier()

        assert classifier1 is classifier2


class TestIntegration:
    """Integration tests for categorization system."""

    def setup_method(self):
        """Reset both normalizer and classifier before each test."""
        reset_merchant_normalizer()
        reset_category_classifier()

    def test_full_pipeline_normalization_and_classification(self):
        """Test full pipeline: normalize then classify."""
        classifier = get_category_classifier()

        # Raw merchant name with suffixes
        merchant = "Swiggy Food Delivery Pvt Ltd"
        category = classifier.classify(merchant)

        assert category == "food_dining"

    def test_real_world_merchant_names(self):
        """Test classification of real-world merchant names."""
        classifier = get_category_classifier()

        test_cases = [
            ("NETFLIX SUBSCRIPTION", "entertainment"),
            ("Amazon India Pvt Ltd", "shopping"),
            ("UBER INDIA", "transport"),
            ("Electricity Board", "utilities"),
            ("Apollo Pharmacy Ltd", "healthcare"),
        ]

        for merchant, expected_category in test_cases:
            assert classifier.classify(merchant) == expected_category
