"""Seed demo data so the dashboard/analytics have something to show."""

from datetime import datetime, timedelta
from decimal import Decimal

from backend.database import get_session, init_db
from backend.repositories import (
    AccountRepository,
    BudgetRepository,
    TransactionRepository,
)


def main() -> None:
    init_db()
    now = datetime.now()
    with get_session().__enter__() as session:
        accounts = AccountRepository(session)
        txs = TransactionRepository(session)
        budgets = BudgetRepository(session)

        acct = accounts.create(
            bank_name="HDFC",
            account_identifier="1234",
            account_type="savings",
            nickname="Primary",
        )

        def month_start(months_ago: int) -> datetime:
            year, month = now.year, now.month - months_ago
            while month <= 0:
                month += 12
                year -= 1
            return datetime(year, month, 2)

        this_month = month_start(0)
        last_month = month_start(1)

        # Salary (income) in both months.
        for anchor in (this_month, last_month):
            txs.create(
                transaction_date=anchor,
                amount=Decimal("120000"),
                merchant="Acme Payroll",
                category="income",
                account_id=acct.id,
                transaction_type="credit",
            )

        # A regular monthly subscription (3 months) -> should be detected.
        for i in range(3):
            txs.create(
                transaction_date=now - timedelta(days=30 * i),
                amount=Decimal("499"),
                merchant="netflix",
                category="entertainment",
                account_id=acct.id,
                transaction_type="debit",
            )

        # Assorted spending across categories, for this month and last month, so
        # the month-over-month comparison sheet has meaningful deltas.
        # (merchant, category, this-month amount, last-month amount)
        samples = [
            ("zomato", "food_dining", "820", "600"),
            ("swiggy food delivery", "food_dining", "640", "980"),
            ("amazon india", "shopping", "2500", "1200"),
            ("uber", "travel", "310", "540"),
            ("croma electronics", "shopping", "1800", "0"),
            ("starbucks", "food_dining", "450", "300"),
            ("indian oil", "travel", "0", "2100"),
        ]
        for merchant, category, this_amt, last_amt in samples:
            if Decimal(this_amt) > 0:
                txs.create(
                    transaction_date=this_month + timedelta(days=3),
                    amount=Decimal(this_amt),
                    merchant=merchant,
                    category=category,
                    account_id=acct.id,
                    transaction_type="debit",
                )
            if Decimal(last_amt) > 0:
                txs.create(
                    transaction_date=last_month + timedelta(days=3),
                    amount=Decimal(last_amt),
                    merchant=merchant,
                    category=category,
                    account_id=acct.id,
                    transaction_type="debit",
                )

        # A couple of budgets (one deliberately exceeded).
        budgets.upsert("food_dining", Decimal("1500"))  # over budget
        budgets.upsert("shopping", Decimal("6000"))  # under budget

        session.commit()
    print("Seeded demo data.")


if __name__ == "__main__":
    main()
