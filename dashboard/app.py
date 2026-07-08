"""Streamlit dashboard for Expense Intelligence."""

import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

# Streamlit puts the script's directory on sys.path, not the repo root, so make
# the repo root importable regardless of how the dashboard is launched.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from backend.analytics import get_analytics_engine  # noqa: E402
from backend.categorization import get_category_classifier  # noqa: E402
from backend.database import get_session  # noqa: E402
from backend.repositories import (  # noqa: E402
    AccountRepository,
    BudgetRepository,
    TransactionRepository,
)

st.set_page_config(
    page_title="Expense Intelligence",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Colour palette used across the charts for a consistent look.
_PALETTE = px.colors.qualitative.Set2

_CSS = """
<style>
    /* Tighten the default top padding. */
    .block-container { padding-top: 2.5rem; padding-bottom: 3rem; max-width: 1200px; }

    /* Metric cards. */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e6e8eb;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.8rem; color: #667085; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.04em;
    }
    div[data-testid="stMetricValue"] { font-size: 1.7rem; font-weight: 700; }

    /* Sidebar. */
    section[data-testid="stSidebar"] { background: #0f172a; }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    /* Card helper used for custom blocks. */
    .ei-card {
        background: #ffffff; border: 1px solid #e6e8eb; border-radius: 12px;
        padding: 16px 20px; margin-bottom: 12px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    }
    .ei-card .title { font-weight: 700; font-size: 1rem; color: #101828; }
    .ei-card .sub { color: #667085; font-size: 0.85rem; }
    .ei-pill {
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: 0.75rem; font-weight: 600;
    }
    .ei-pill.ok { background: #ecfdf3; color: #027a48; }
    .ei-pill.warn { background: #fef3f2; color: #b42318; }
</style>
"""


def _fmt(amount) -> str:
    """Format a number as Indian rupees."""
    return f"₹{float(amount):,.2f}"


def main():
    """Main dashboard application."""
    st.markdown(_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 💰 Expense Intelligence")
        st.caption("Personal Finance Intelligence Platform")
        page = st.radio(
            "Navigate",
            [
                "Dashboard",
                "Transactions",
                "Accounts",
                "Analytics",
                "Budgets",
                "Settings",
            ],
            label_visibility="collapsed",
        )

    pages = {
        "Dashboard": show_dashboard,
        "Transactions": show_transactions,
        "Accounts": show_accounts,
        "Analytics": show_analytics,
        "Budgets": show_budgets,
        "Settings": show_settings,
    }
    pages[page]()


def show_dashboard():
    """Show main dashboard with summary metrics."""
    st.title("Dashboard")
    st.caption("Last 30 days")

    analytics = get_analytics_engine()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    summary = analytics.get_summary_metrics(start_date, end_date)
    income_expense = summary["income_vs_expense"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", _fmt(income_expense["total_income"]))
    col2.metric("Total Expense", _fmt(income_expense["total_expense"]))
    col3.metric("Net", _fmt(income_expense["net"]))

    st.markdown("### Spending by category")
    spending_by_category = summary["spending_by_category"]
    left, right = st.columns([3, 2])
    if spending_by_category:
        categories = list(spending_by_category.keys())
        amounts = [float(v) for v in spending_by_category.values()]
        fig = px.pie(
            values=amounts,
            names=categories,
            hole=0.55,
            color_discrete_sequence=_PALETTE,
        )
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", y=-0.1),
            height=320,
        )
        left.plotly_chart(fig, use_container_width=True)

        ranked = sorted(
            spending_by_category.items(), key=lambda kv: float(kv[1]), reverse=True
        )
        with right:
            st.markdown("#### Top categories")
            for category, amount in ranked[:6]:
                st.markdown(
                    f"<div class='ei-card'><span class='title'>{category}</span>"
                    f"<br><span class='sub'>{_fmt(amount)}</span></div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("No spending data available for the selected period.")

    st.markdown("### Detected subscriptions")
    subscriptions = summary["subscriptions"]
    if subscriptions:
        cols = st.columns(3)
        for i, sub in enumerate(subscriptions):
            with cols[i % 3]:
                st.markdown(
                    f"<div class='ei-card'>"
                    f"<span class='title'>{sub['merchant'].title()}</span><br>"
                    f"<span class='sub'>{_fmt(sub['average_amount'])} · "
                    f"{sub['frequency']} · {sub['occurrences']}x</span></div>",
                    unsafe_allow_html=True,
                )
    else:
        st.info("No subscriptions detected.")


def show_transactions():
    """Show transactions page."""
    st.title("Transactions")

    limit = st.slider("Show most recent", 10, 200, 50, step=10)
    with get_session().__enter__() as session:
        rows = [
            {
                "Date": tx.transaction_date.strftime("%Y-%m-%d"),
                "Merchant": tx.merchant,
                "Category": tx.category or "—",
                "Type": tx.transaction_type,
                "Amount": float(tx.amount),
                "Status": tx.status,
            }
            for tx in TransactionRepository(session).get_recent(limit=limit)
        ]

    if not rows:
        st.info("No transactions found.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Amount": st.column_config.NumberColumn("Amount", format="₹%.2f"),
        },
    )


def show_accounts():
    """Show accounts page."""
    st.title("Accounts")

    with get_session().__enter__() as session:
        accounts = AccountRepository(session).get_all()
        rows = [
            {
                "bank": a.bank_name,
                "identifier": a.account_identifier,
                "type": a.account_type,
                "nickname": a.nickname or "—",
                "active": a.is_active,
            }
            for a in accounts
        ]

    if not rows:
        st.info("No accounts found.")
        return

    cols = st.columns(3)
    for i, a in enumerate(rows):
        pill = (
            "<span class='ei-pill ok'>Active</span>"
            if a["active"]
            else "<span class='ei-pill warn'>Inactive</span>"
        )
        with cols[i % 3]:
            st.markdown(
                f"<div class='ei-card'>"
                f"<span class='title'>{a['bank']} ····{a['identifier']}</span> {pill}"
                f"<br><span class='sub'>{a['type']} · {a['nickname']}</span></div>",
                unsafe_allow_html=True,
            )


def show_analytics():
    """Show analytics page."""
    st.title("Analytics")

    analytics = get_analytics_engine()

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.now())

    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    st.markdown("### Monthly spending trend")
    monthly_spending = analytics.get_monthly_spending(months=12)
    if monthly_spending:
        df = pd.DataFrame(monthly_spending)
        fig = px.line(df, x="month", y="total", markers=True)
        fig.update_traces(line_color="#3b82f6")
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No monthly data yet.")

    left, right = st.columns(2)

    with left:
        st.markdown("### Top merchants")
        top_merchants = analytics.get_spending_by_merchant(
            start_datetime, end_datetime, limit=10
        )
        if top_merchants:
            df = pd.DataFrame(
                [{"merchant": m, "amount": float(a)} for m, a in top_merchants]
            )
            fig = px.bar(
                df,
                x="amount",
                y="merchant",
                orientation="h",
                color_discrete_sequence=["#6366f1"],
            )
            fig.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=320,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No merchant data yet.")

    with right:
        st.markdown("### Daily spending (30d)")
        daily_spending = analytics.get_daily_spending(days=30)
        if daily_spending:
            df = pd.DataFrame(daily_spending)
            fig = px.bar(df, x="date", y="total", color_discrete_sequence=["#10b981"])
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No daily data yet.")


def show_budgets():
    """Show budgets page: set per-category budgets and track progress."""
    st.title("Budgets")

    analytics = get_analytics_engine()

    st.markdown("### Set a budget")
    categories = get_category_classifier().get_all_categories()
    with st.form("add_budget"):
        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("Category", categories)
        with col2:
            amount = st.number_input("Amount (₹)", min_value=0.0, step=100.0)
        with col3:
            period = st.selectbox("Period", ["monthly", "weekly", "yearly"])
        if st.form_submit_button("Save budget", type="primary") and amount > 0:
            with get_session().__enter__() as session:
                BudgetRepository(session).upsert(
                    category=category, amount=Decimal(str(amount)), period=period
                )
            st.success(f"Budget saved for {category}.")

    st.markdown("### This period")
    status = analytics.get_budget_status()
    if not status:
        st.info("No active budgets yet. Add one above.")
        return

    for item in status:
        spent = float(item["spent"])
        budget = float(item["budget"])
        pct = item["percent_used"]
        pill = (
            "<span class='ei-pill warn'>Over budget</span>"
            if item["over_budget"]
            else "<span class='ei-pill ok'>On track</span>"
        )
        st.markdown(
            f"<div class='ei-card'><span class='title'>{item['category']}</span> {pill}"
            f"<br><span class='sub'>{_fmt(spent)} of {_fmt(budget)} · {pct}%</span></div>",
            unsafe_allow_html=True,
        )
        st.progress(min(pct / 100, 1.0))


def show_settings():
    """Show settings page."""
    st.title("Settings")

    with st.expander("Gmail Sync", expanded=True):
        st.write("Configure Gmail sync settings (credentials via Keychain).")
    with st.expander("Categories"):
        st.write("Manage merchant categories and learned corrections.")
    with st.expander("API Keys"):
        st.write("Configure API keys for external services.")


if __name__ == "__main__":
    main()
