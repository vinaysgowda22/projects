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

# Skeuomorphic styling: soft depth, gradients, tactile controls, felt sidebar.
_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Paper-like app background with a subtle radial sheen. */
    .stApp {
        background:
            radial-gradient(1200px 600px at 20% -10%, #ffffff 0%, #eef1f6 55%, #e6eaf1 100%);
    }
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px; }

    /* ---- Skeuomorphic metric tiles ---- */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #ffffff 0%, #f2f5fa 100%);
        border: 1px solid #d7dde8;
        border-radius: 16px;
        padding: 18px 22px;
        box-shadow:
            0 1px 0 #ffffff inset,
            0 10px 20px -12px rgba(16, 24, 40, 0.35),
            0 2px 4px rgba(16, 24, 40, 0.06);
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 0.78rem; color: #5b6472; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.06em;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem; font-weight: 800; color: #0d1b2a;
        text-shadow: 0 1px 0 #ffffff;
    }

    /* ---- Felt / leather sidebar ---- */
    section[data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, #17304d 0%, #0d1b2e 100%);
        border-right: 1px solid #0a1522;
        box-shadow: inset -8px 0 16px -10px rgba(0,0,0,0.6);
    }
    section[data-testid="stSidebar"] * { color: #dbe4f0 !important; }
    section[data-testid="stSidebar"] .stRadio label {
        padding: 8px 12px; border-radius: 10px; margin-bottom: 2px;
        transition: background 0.15s ease;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.06);
    }

    /* ---- Embossed card helper ---- */
    .ei-card {
        background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%);
        border: 1px solid #d7dde8; border-radius: 14px;
        padding: 16px 20px; margin-bottom: 14px;
        box-shadow:
            0 1px 0 #ffffff inset,
            0 12px 22px -16px rgba(16, 24, 40, 0.45),
            0 2px 4px rgba(16, 24, 40, 0.05);
    }
    .ei-card .title { font-weight: 700; font-size: 1rem; color: #101828; }
    .ei-card .sub { color: #667085; font-size: 0.85rem; }

    /* ---- Pills / chips ---- */
    .ei-pill {
        display: inline-block; padding: 3px 11px; border-radius: 999px;
        font-size: 0.72rem; font-weight: 700; letter-spacing: 0.02em;
        box-shadow: 0 1px 0 #ffffff inset, 0 1px 2px rgba(0,0,0,0.08);
    }
    .ei-pill.ok { background: linear-gradient(180deg,#e9fbf0,#d1fadf); color: #05603a; }
    .ei-pill.warn { background: linear-gradient(180deg,#fef0ef,#fdd9d6); color: #912018; }

    /* ---- Tactile primary button ---- */
    .stButton > button, .stFormSubmitButton > button {
        background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
        color: #ffffff; border: 1px solid #1d4ed8; border-radius: 12px;
        font-weight: 700; padding: 0.5rem 1.1rem;
        box-shadow: 0 1px 0 rgba(255,255,255,0.4) inset,
                    0 6px 14px -6px rgba(37, 99, 235, 0.6);
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        filter: brightness(1.05);
    }
    .stButton > button:active, .stFormSubmitButton > button:active {
        box-shadow: 0 2px 6px rgba(0,0,0,0.25) inset; transform: translateY(1px);
    }

    /* ---- Skeuomorphic progress groove ---- */
    div[data-testid="stProgress"] > div > div {
        background: linear-gradient(180deg, #e2e8f0, #cbd5e1);
        border-radius: 999px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.18);
    }
    div[data-testid="stProgress"] > div > div > div {
        background: linear-gradient(180deg, #60a5fa, #2563eb);
        border-radius: 999px;
        box-shadow: 0 1px 0 rgba(255,255,255,0.5) inset;
    }

    /* Section headings. */
    h3 { color: #17304d; font-weight: 800; }
</style>
"""


def _fmt(amount) -> str:
    """Format a number as Indian rupees."""
    return f"₹{float(amount):,.2f}"


def _month_bounds(months_ago: int = 0):
    """Return (start, end) datetimes for the month `months_ago` before now."""
    now = datetime.now()
    year = now.year
    month = now.month - months_ago
    while month <= 0:
        month += 12
        year -= 1
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(seconds=1)
    # Cap the current month at "now".
    return start, min(end, now)


def main():
    """Main dashboard application."""
    st.markdown(_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("## 💰 Expense Intelligence")
        st.caption("Personal Finance Intelligence Platform")
        page = st.radio(
            "Navigate",
            [
                "📊 Dashboard",
                "🧾 Transactions",
                "🏦 Accounts",
                "📈 Analytics",
                "🎯 Budgets",
                "⚙️ Settings",
            ],
            label_visibility="collapsed",
        )

    pages = {
        "📊 Dashboard": show_dashboard,
        "🧾 Transactions": show_transactions,
        "🏦 Accounts": show_accounts,
        "📈 Analytics": show_analytics,
        "🎯 Budgets": show_budgets,
        "⚙️ Settings": show_settings,
    }
    pages[page]()


def show_dashboard():
    """Show main dashboard with summary metrics and month-over-month comparison."""
    st.title("Dashboard")
    st.caption("This month vs. last month")

    analytics = get_analytics_engine()
    this_start, this_end = _month_bounds(0)
    last_start, last_end = _month_bounds(1)

    this_ie = analytics.get_income_vs_expense(this_start, this_end)
    last_ie = analytics.get_income_vs_expense(last_start, last_end)

    def _delta(cur, prev):
        return _fmt(cur - prev) if prev is not None else None

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Income (this month)",
        _fmt(this_ie["total_income"]),
        _delta(this_ie["total_income"], last_ie["total_income"]),
    )
    col2.metric(
        "Expense (this month)",
        _fmt(this_ie["total_expense"]),
        _delta(this_ie["total_expense"], last_ie["total_expense"]),
        delta_color="inverse",
    )
    col3.metric(
        "Net (this month)",
        _fmt(this_ie["net"]),
        _delta(this_ie["net"], last_ie["net"]),
    )

    # ---- Comparison sheet: category spend this vs last month ----
    st.markdown("### 📋 Category comparison sheet")
    this_cat = {
        k: float(v)
        for k, v in analytics.get_spending_by_category(this_start, this_end).items()
    }
    last_cat = {
        k: float(v)
        for k, v in analytics.get_spending_by_category(last_start, last_end).items()
    }
    categories = sorted(set(this_cat) | set(last_cat))

    if categories:
        rows = []
        for cat in categories:
            cur = this_cat.get(cat, 0.0)
            prev = last_cat.get(cat, 0.0)
            change = cur - prev
            pct = (change / prev * 100) if prev else (100.0 if cur else 0.0)
            trend = "▲" if change > 0 else ("▼" if change < 0 else "—")
            rows.append(
                {
                    "Category": cat,
                    "This month": cur,
                    "Last month": prev,
                    "Change (₹)": change,
                    "Change (%)": round(pct, 1),
                    "Trend": trend,
                }
            )
        df = pd.DataFrame(rows)

        totals = {
            "Category": "TOTAL",
            "This month": df["This month"].sum(),
            "Last month": df["Last month"].sum(),
            "Change (₹)": df["Change (₹)"].sum(),
            "Change (%)": round(
                (
                    (df["Change (₹)"].sum() / df["Last month"].sum() * 100)
                    if df["Last month"].sum()
                    else 0.0
                ),
                1,
            ),
            "Trend": "▲" if df["Change (₹)"].sum() > 0 else "▼",
        }
        df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

        def _style_change(val):
            if isinstance(val, (int, float)):
                if val > 0:
                    return "color: #b42318; font-weight: 700;"
                if val < 0:
                    return "color: #05603a; font-weight: 700;"
            return ""

        styler = (
            df.style.map(_style_change, subset=["Change (₹)", "Change (%)"])
            .format(
                {
                    "This month": "₹{:,.0f}",
                    "Last month": "₹{:,.0f}",
                    "Change (₹)": "{:+,.0f}",
                    "Change (%)": "{:+.1f}%",
                }
            )
            .set_properties(
                subset=pd.IndexSlice[df.index[-1], :],
                **{"font-weight": "800", "background-color": "#eef2f7"},
            )
        )
        st.dataframe(styler, use_container_width=True, hide_index=True)
        st.caption("Higher spend than last month is red; lower is green.")
    else:
        st.info("No spending data yet — add transactions to see comparisons.")

    # ---- Spending donut + subscriptions ----
    left, right = st.columns([3, 2])
    with left:
        st.markdown("### 🍩 Spending by category (this month)")
        if this_cat:
            fig = px.pie(
                values=list(this_cat.values()),
                names=list(this_cat.keys()),
                hole=0.58,
                color_discrete_sequence=_PALETTE,
            )
            fig.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                legend=dict(orientation="h", y=-0.1),
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No spending data available.")

    with right:
        st.markdown("### 🔁 Subscriptions")
        subscriptions = analytics.get_subscriptions()
        if subscriptions:
            for sub in subscriptions:
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

    col1, col2 = st.columns([1, 3])
    with col1:
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
    debits = df[df["Type"] == "debit"]["Amount"].sum()
    credits = df[df["Type"] == "credit"]["Amount"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Shown", len(df))
    c2.metric("Total debits", _fmt(debits), delta_color="inverse")
    c3.metric("Total credits", _fmt(credits))

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

    st.markdown("### 📈 Monthly spending trend")
    monthly_spending = analytics.get_monthly_spending(months=12)
    if monthly_spending:
        df = pd.DataFrame(monthly_spending)
        fig = px.area(df, x="month", y="total", markers=True)
        fig.update_traces(line_color="#2563eb", fillcolor="rgba(37,99,235,0.15)")
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No monthly data yet.")

    left, right = st.columns(2)

    with left:
        st.markdown("### 🏪 Top merchants")
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
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No merchant data yet.")

    with right:
        st.markdown("### 📅 Daily spending (30d)")
        daily_spending = analytics.get_daily_spending(days=30)
        if daily_spending:
            df = pd.DataFrame(daily_spending)
            fig = px.bar(df, x="date", y="total", color_discrete_sequence=["#10b981"])
            fig.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No daily data yet.")


def show_budgets():
    """Show budgets page: set per-category budgets and track progress."""
    st.title("Budgets")

    analytics = get_analytics_engine()

    st.markdown("### 🎯 Set a budget")
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

    st.markdown("### 📊 This period")
    status = analytics.get_budget_status()
    if not status:
        st.info("No active budgets yet. Add one above.")
        return

    # Budget summary sheet.
    sheet = pd.DataFrame(
        [
            {
                "Category": s["category"],
                "Budget": float(s["budget"]),
                "Spent": float(s["spent"]),
                "Remaining": float(s["remaining"]),
                "Used (%)": s["percent_used"],
                "Status": "Over budget" if s["over_budget"] else "On track",
            }
            for s in status
        ]
    )
    st.dataframe(
        sheet,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Budget": st.column_config.NumberColumn(format="₹%.0f"),
            "Spent": st.column_config.NumberColumn(format="₹%.0f"),
            "Remaining": st.column_config.NumberColumn(format="₹%.0f"),
            "Used (%)": st.column_config.ProgressColumn(
                "Used (%)", min_value=0, max_value=100, format="%.0f%%"
            ),
        },
    )

    for item in status:
        pill = (
            "<span class='ei-pill warn'>Over budget</span>"
            if item["over_budget"]
            else "<span class='ei-pill ok'>On track</span>"
        )
        st.markdown(
            f"<div class='ei-card'><span class='title'>{item['category']}</span> {pill}"
            f"<br><span class='sub'>{_fmt(item['spent'])} of "
            f"{_fmt(item['budget'])} · {item['percent_used']}%</span></div>",
            unsafe_allow_html=True,
        )
        st.progress(min(item["percent_used"] / 100, 1.0))


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
