"""Tests for learned merchant->category mappings and user-correction learning."""

from backend.categorization.category_classifier import CategoryClassifier
from backend.categorization.merchant_mapping_store import MerchantMappingStore
from backend.categorization.merchant_normalizer import MerchantNormalizer


class TestMerchantMappingStore:
    """Test suite for the JSON-backed learned mapping store."""

    def test_set_and_get_roundtrip(self, tmp_path):
        store = MerchantMappingStore(path=tmp_path / "mapping.json")
        store.set("acme corp", "shopping")
        assert store.get("acme corp") == "shopping"

    def test_persists_across_instances(self, tmp_path):
        path = tmp_path / "mapping.json"
        MerchantMappingStore(path=path).set("acme corp", "shopping")
        # A fresh instance reads what the previous one persisted.
        assert MerchantMappingStore(path=path).get("acme corp") == "shopping"

    def test_missing_file_is_empty(self, tmp_path):
        store = MerchantMappingStore(path=tmp_path / "nope.json")
        assert store.get("anything") is None
        assert store.all() == {}

    def test_malformed_file_is_ignored(self, tmp_path):
        path = tmp_path / "mapping.json"
        path.write_text("not json {{{")
        store = MerchantMappingStore(path=path)
        assert store.all() == {}


class TestUserCorrectionLearning:
    """Test suite for classifier learning and Layer-0 precedence."""

    def _classifier(self, tmp_path):
        return CategoryClassifier(
            normalizer=MerchantNormalizer(),
            mapping_store=MerchantMappingStore(path=tmp_path / "mapping.json"),
        )

    def test_learned_mapping_overrides_other_layers(self, tmp_path):
        clf = self._classifier(tmp_path)
        # "amazon india" would normally classify as shopping via seed data.
        clf.learn("Amazon India", "business_expense")
        assert clf.classify("Amazon India") == "business_expense"

    def test_correction_persists_for_future_transactions(self, tmp_path):
        path = tmp_path / "mapping.json"
        first = CategoryClassifier(
            normalizer=MerchantNormalizer(),
            mapping_store=MerchantMappingStore(path=path),
        )
        first.learn("Mystery Merchant XYZ", "travel")

        # A new classifier (e.g. a different process) picks up the correction.
        second = CategoryClassifier(
            normalizer=MerchantNormalizer(),
            mapping_store=MerchantMappingStore(path=path),
        )
        assert second.classify("Mystery Merchant XYZ") == "travel"

    def test_ai_result_is_cached_and_reused(self, tmp_path, mocker):
        clf = self._classifier(tmp_path)
        # Force an unknown merchant down to the AI layer and stub the AI call.
        ai = mocker.patch.object(clf, "_ai_match", return_value="entertainment")

        merchant = "Totally Unknown Brand 9000"
        assert clf.classify(merchant) == "entertainment"
        # Second lookup should hit the cache (Layer 0), not the AI layer again.
        assert clf.classify(merchant) == "entertainment"
        ai.assert_called_once()
