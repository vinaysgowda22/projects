"""Unit tests for the analytics engine's recurring-subscription detection.

These target the interval-regularity logic (§5.8) directly via the pure helper
methods, so they need no database.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from backend.analytics.analytics_engine import AnalyticsEngine


def _tx(amount: str, date: datetime, merchant: str = "netflix"):
    """Build a lightweight transaction stand-in for the analytics helpers."""
    return SimpleNamespace(
        amount=Decimal(amount),
        transaction_date=date,
        merchant=merchant,
        transaction_type="debit",
    )


class TestCadenceDetection:
    """Tests for AnalyticsEngine._detect_cadence."""

    def setup_method(self):
        self.engine = AnalyticsEngine()

    def test_regular_monthly_is_detected(self):
        base = datetime(2024, 1, 1)
        cluster = [_tx("499.00", base + timedelta(days=30 * i)) for i in range(3)]
        assert self.engine._detect_cadence(cluster) == "monthly"

    def test_two_irregular_purchases_not_flagged(self):
        # Two similar-amount purchases 2 days apart must NOT be a subscription.
        base = datetime(2024, 1, 1)
        cluster = [_tx("499.00", base), _tx("499.00", base + timedelta(days=2))]
        assert self.engine._detect_cadence(cluster) is None

    def test_three_purchases_with_irregular_gaps_not_flagged(self):
        base = datetime(2024, 1, 1)
        cluster = [
            _tx("499.00", base),
            _tx("499.00", base + timedelta(days=5)),
            _tx("499.00", base + timedelta(days=45)),
        ]
        assert self.engine._detect_cadence(cluster) is None

    def test_known_merchant_single_monthly_interval_is_lenient(self):
        base = datetime(2024, 1, 1)
        cluster = [_tx("499.00", base), _tx("499.00", base + timedelta(days=30))]
        # Lenient path (known subscription merchant): one regular interval is enough.
        assert self.engine._detect_cadence(cluster, lenient=True) == "monthly"
        # Strict path still requires 3+ occurrences.
        assert self.engine._detect_cadence(cluster, lenient=False) is None

    def test_monthly_tolerates_plus_minus_three_days(self):
        base = datetime(2024, 1, 1)
        # Gaps of 28 and 34 days both fall inside the monthly band.
        cluster = [
            _tx("499.00", base),
            _tx("499.00", base + timedelta(days=28)),
            _tx("499.00", base + timedelta(days=28 + 34)),
        ]
        assert self.engine._detect_cadence(cluster) == "monthly"


class TestAmountClustering:
    """Tests for AnalyticsEngine._cluster_by_amount."""

    def setup_method(self):
        self.engine = AnalyticsEngine()

    def test_similar_amounts_group_together(self):
        base = datetime(2024, 1, 1)
        txs = [_tx("500.00", base), _tx("505.00", base), _tx("495.00", base)]
        clusters = self.engine._cluster_by_amount(txs)
        assert len(clusters) == 1
        assert len(clusters[0]) == 3

    def test_dissimilar_amounts_split(self):
        base = datetime(2024, 1, 1)
        txs = [_tx("100.00", base), _tx("900.00", base)]
        clusters = self.engine._cluster_by_amount(txs)
        assert len(clusters) == 2
