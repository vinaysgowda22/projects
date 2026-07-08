"""Analytics engine for computing financial metrics."""

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from loguru import logger

from backend.database import get_session
from backend.repositories.transaction_repository import TransactionRepository


class AnalyticsEngine:
    """Engine for computing financial analytics metrics."""
    
    # Subscription detection patterns
    SUBSCRIPTION_PATTERNS = [
        "netflix", "spotify", "amazon prime", "youtube premium",
        "apple music", "google one", "microsoft 365", "adobe",
        "disney+", "hulu", "hbo max", "peacock",
    ]
    
    def __init__(self, transaction_repository=None):
        """Initialize the analytics engine.
        
        Args:
            transaction_repository: TransactionRepository instance. If None, uses global instance.
        """
        self.transaction_repo = transaction_repository
    
    def get_spending_by_category(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get total spending by category.
        
        Args:
            start_date: Start date for filtering.
            end_date: End date for filtering.
        
        Returns:
            Dict mapping category to total amount.
        """
        with get_session().__enter__() as session:
            repo = self.transaction_repo or TransactionRepository(session)
            
            transactions = repo.search(
                start_date=start_date,
                end_date=end_date,
                limit=1000,
            )
            
            spending_by_category = defaultdict(Decimal)
            
            for tx in transactions:
                if tx.transaction_type == "debit" and tx.category:
                    spending_by_category[tx.category] += tx.amount
            
            return dict(spending_by_category)
    
    def get_spending_by_merchant(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20,
    ) -> list[tuple]:
        """Get top spending by merchant.
        
        Args:
            start_date: Start date for filtering.
            end_date: End date for filtering.
            limit: Number of top merchants to return.
        
        Returns:
            List of (merchant, amount) tuples sorted by amount descending.
        """
        with get_session().__enter__() as session:
            repo = self.transaction_repo or TransactionRepository(session)
            
            transactions = repo.search(
                start_date=start_date,
                end_date=end_date,
                limit=1000,
            )
            
            spending_by_merchant = defaultdict(Decimal)
            
            for tx in transactions:
                if tx.transaction_type == "debit":
                    spending_by_merchant[tx.merchant] += tx.amount
            
            # Sort by amount descending
            sorted_spending = sorted(
                spending_by_merchant.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            
            return sorted_spending[:limit]
    
    def get_monthly_spending(
        self,
        months: int = 12,
    ) -> list[dict]:
        """Get monthly spending trend.
        
        Args:
            months: Number of months to include.
        
        Returns:
            List of dicts with month and total spending.
        """
        with get_session().__enter__() as session:
            repo = self.transaction_repo or TransactionRepository(session)
            
            monthly_spending = []
            
            for i in range(months):
                # Calculate month start and end
                month_date = datetime.now() - timedelta(days=30 * i)
                month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                # Get next month start
                if month_date.month == 12:
                    month_end = month_date.replace(year=month_date.year + 1, month=1, day=1)
                else:
                    month_end = month_date.replace(month=month_date.month + 1, day=1)
                
                transactions = repo.get_by_date_range(month_start, month_end)
                
                total = sum(
                    tx.amount for tx in transactions
                    if tx.transaction_type == "debit"
                )
                
                monthly_spending.append({
                    "month": month_start.strftime("%Y-%m"),
                    "total": float(total),
                })
            
            return monthly_spending[::-1]  # Reverse to show oldest first
    
    def get_subscriptions(
        self,
        lookback_days: int = 90,
    ) -> list[dict]:
        """Detect recurring subscription payments.
        
        Args:
            lookback_days: Number of days to look back for detection.
        
        Returns:
            List of detected subscriptions with merchant and average amount.
        """
        with get_session().__enter__() as session:
            repo = self.transaction_repo or TransactionRepository(session)
            
            start_date = datetime.now() - timedelta(days=lookback_days)
            transactions = repo.get_by_date_range(start_date, datetime.now())
            
            # Group by merchant
            merchant_transactions = defaultdict(list)
            
            for tx in transactions:
                if tx.transaction_type == "debit":
                    merchant_transactions[tx.merchant.lower()].append(tx)
            
            subscriptions = []
            
            for merchant, txs in merchant_transactions.items():
                # Check if merchant matches subscription patterns
                is_subscription = any(
                    pattern in merchant
                    for pattern in self.SUBSCRIPTION_PATTERNS
                )
                
                # Or check for recurring pattern (same merchant, similar amount, monthly)
                if len(txs) >= 2:
                    amounts = [tx.amount for tx in txs]
                    avg_amount = sum(amounts) / len(amounts)
                    
                    # Check if amounts are similar (within 10% variance)
                    variance = max(amounts) - min(amounts)
                    if variance < avg_amount * Decimal("0.1"):
                        is_subscription = True
                
                if is_subscription:
                    avg_amount = sum(tx.amount for tx in txs) / len(txs)
                    subscriptions.append({
                        "merchant": merchant,
                        "average_amount": float(avg_amount),
                        "frequency": "monthly",
                        "last_transaction": max(tx.transaction_date for tx in txs).isoformat(),
                    })
            
            return subscriptions
    
    def get_income_vs_expense(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get income vs expense summary.
        
        Args:
            start_date: Start date for filtering.
            end_date: End date for filtering.
        
        Returns:
            Dict with total income, total expense, and net.
        """
        with get_session().__enter__() as session:
            repo = self.transaction_repo or TransactionRepository(session)
            
            transactions = repo.search(
                start_date=start_date,
                end_date=end_date,
                limit=1000,
            )
            
            total_income = Decimal("0")
            total_expense = Decimal("0")
            
            for tx in transactions:
                if tx.transaction_type == "credit":
                    total_income += tx.amount
                elif tx.transaction_type == "debit":
                    total_expense += tx.amount
            
            return {
                "total_income": float(total_income),
                "total_expense": float(total_expense),
                "net": float(total_income - total_expense),
            }
    
    def get_daily_spending(
        self,
        days: int = 30,
    ) -> list[dict]:
        """Get daily spending trend.
        
        Args:
            days: Number of days to include.
        
        Returns:
            List of dicts with date and total spending.
        """
        with get_session().__enter__() as session:
            repo = self.transaction_repo or TransactionRepository(session)
            
            daily_spending = []
            
            for i in range(days):
                day_date = datetime.now() - timedelta(days=i)
                day_start = day_date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                transactions = repo.get_by_date_range(day_start, day_end)
                
                total = sum(
                    tx.amount for tx in transactions
                    if tx.transaction_type == "debit"
                )
                
                daily_spending.append({
                    "date": day_start.strftime("%Y-%m-%d"),
                    "total": float(total),
                })
            
            return daily_spending[::-1]  # Reverse to show oldest first
    
    def get_summary_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get comprehensive summary metrics.
        
        Args:
            start_date: Start date for filtering.
            end_date: End date for filtering.
        
        Returns:
            Dict with all summary metrics.
        """
        income_expense = self.get_income_vs_expense(start_date, end_date)
        spending_by_category = self.get_spending_by_category(start_date, end_date)
        subscriptions = self.get_subscriptions()
        
        return {
            "income_vs_expense": income_expense,
            "spending_by_category": spending_by_category,
            "subscriptions": subscriptions,
            "top_merchants": self.get_spending_by_merchant(start_date, end_date, limit=10),
        }


# Global analytics engine instance
_analytics_engine: Optional[AnalyticsEngine] = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get the global analytics engine instance (singleton pattern)."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AnalyticsEngine()
    return _analytics_engine


def reset_analytics_engine() -> None:
    """Reset the global analytics engine (useful for testing)."""
    global _analytics_engine
    _analytics_engine = None
