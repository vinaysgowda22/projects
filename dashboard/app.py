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

# Chart colour palette (works on both themes).
_PALETTE = px.colors.qualitative.Set2

# ---------------------------------------------------------------------------
# Theming
# ---------------------------------------------------------------------------
_THEMES = {
    "Light": {
        "app_bg": (
            "radial-gradient(1200px 600px at 20% -10%, "
            "#ffffff 0%, #eef1f6 55%, #e6eaf1 100%)"
        ),
        "text": "#0d1b2a",
        "muted": "#5b6472",
        "heading": "#17304d",
        "card_bg": "linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%)",
        "card_inset": "0 1px 0 #ffffff inset",
        "card_border": "#d7dde8",
        "metric_bg": "linear-gradient(180deg, #ffffff 0%, #f2f5fa 100%)",
        "metric_shadow": (
            "0 1px 0 #ffffff inset, 0 10px 20px -12px rgba(16,24,40,0.35), "
            "0 2px 4px rgba(16,24,40,0.06)"
        ),
        "head_bg": "#eef2f7",
        "alt_bg": "#f7f9fc",
        "total_bg": "#e7edf5",
        "table_border": "#e6eaf1",
        "groove": "linear-gradient(180deg, #e2e8f0, #cbd5e1)",
        "up": "#b42318",
        "down": "#05603a",
        "grid": "rgba(16,24,40,0.08)",
        "sidebar": "linear-gradient(180deg, #17304d 0%, #0d1b2e 100%)",
        "sidebar_text": "#dbe4f0",
        "input_bg": "#ffffff",
    },
    "Dark": {
        "app_bg": (
            "radial-gradient(1200px 600px at 20% -10%, "
            "#1c2942 0%, #111b2e 55%, #0b1220 100%)"
        ),
        "text": "#e6eef8",
        "muted": "#93a4bd",
        "heading": "#c7d6ec",
        "card_bg": "linear-gradient(180deg, #1e293b 0%, #172032 100%)",
        "card_inset": "0 1px 0 rgba(255,255,255,0.05) inset",
        "card_border": "#2a3a53",
        "metric_bg": "linear-gradient(180deg, #1f2b3f 0%, #151f30 100%)",
        "metric_shadow": (
            "0 1px 0 rgba(255,255,255,0.05) inset, "
            "0 12px 24px -14px rgba(0,0,0,0.7), 0 2px 4px rgba(0,0,0,0.35)"
        ),
        "head_bg": "#1b273b",
        "alt_bg": "#182234",
        "total_bg": "#22314a",
        "table_border": "#2a3a53",
        "groove": "linear-gradient(180deg, #24334a, #1b2740)",
        "up": "#f97066",
        "down": "#32d583",
        "grid": "rgba(255,255,255,0.08)",
        "sidebar": "linear-gradient(180deg, #0f1a2e 0%, #070d18 100%)",
        "sidebar_text": "#c7d3e5",
        "input_bg": "#1b273b",
    },
}


def _theme_name() -> str:
    return st.session_state.get("theme", "Light")


def _theme() -> dict:
    return _THEMES[_theme_name()]


def _build_css(t: dict) -> str:
    """Build the stylesheet for the active theme."""
    return f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

    .stApp {{ background: {t['app_bg']}; }}
    .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px; }}

    /* Base text + headings. */
    .stApp, .stMarkdown, p, span, label, li {{ color: {t['text']}; }}
    h1, h2 {{ color: {t['heading']}; letter-spacing: -0.01em; }}
    h3 {{ color: {t['heading']}; font-weight: 800; }}
    [data-testid="stCaptionContainer"] {{ color: {t['muted']} !important; }}

    /* ---- Metric tiles ---- */
    div[data-testid="stMetric"] {{
        background: {t['metric_bg']};
        border: 1px solid {t['card_border']};
        border-radius: 16px; padding: 18px 22px;
        box-shadow: {t['metric_shadow']};
    }}
    div[data-testid="stMetricLabel"] p {{
        font-size: 0.78rem; color: {t['muted']}; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.06em;
    }}
    div[data-testid="stMetricValue"] {{
        font-size: 1.8rem; font-weight: 800; color: {t['text']};
    }}

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {{
        background: {t['sidebar']};
        border-right: 1px solid rgba(0,0,0,0.4);
        box-shadow: inset -8px 0 16px -10px rgba(0,0,0,0.6);
    }}
    section[data-testid="stSidebar"] * {{ color: {t['sidebar_text']} !important; }}
    section[data-testid="stSidebar"] .stRadio label {{
        padding: 8px 12px; border-radius: 10px; margin-bottom: 2px;
        transition: background 0.15s ease;
    }}
    section[data-testid="stSidebar"] .stRadio label:hover {{
        background: rgba(255,255,255,0.06);
    }}

    /* ---- Cards ---- */
    .ei-card {{
        background: {t['card_bg']}; border: 1px solid {t['card_border']};
        border-radius: 14px; padding: 16px 20px; margin-bottom: 14px;
        box-shadow: {t['card_inset']}, 0 12px 22px -16px rgba(0,0,0,0.45);
    }}
    .ei-card .title {{ font-weight: 700; font-size: 1rem; color: {t['text']}; }}
    .ei-card .sub {{ color: {t['muted']}; font-size: 0.85rem; }}

    /* ---- Pills ---- */
    .ei-pill {{
        display: inline-block; padding: 3px 11px; border-radius: 999px;
        font-size: 0.72rem; font-weight: 700; letter-spacing: 0.02em;
    }}
    .ei-pill.ok {{ background: rgba(16,185,129,0.16); color: {t['down']}; }}
    .ei-pill.warn {{ background: rgba(240,68,56,0.16); color: {t['up']}; }}

    /* ---- Themed tables (sheets) ---- */
    .ei-table {{
        width: 100%; border-collapse: collapse; font-size: 0.9rem;
        background: {t['card_bg']}; border: 1px solid {t['table_border']};
        border-radius: 12px; overflow: hidden;
        box-shadow: 0 12px 22px -16px rgba(0,0,0,0.45);
    }}
    .ei-table th {{
        text-align: left; padding: 11px 14px; background: {t['head_bg']};
        color: {t['muted']}; font-weight: 700; font-size: 0.7rem;
        text-transform: uppercase; letter-spacing: 0.05em;
    }}
    .ei-table td {{
        padding: 11px 14px; border-top: 1px solid {t['table_border']};
        color: {t['text']};
    }}
    .ei-table tr:nth-child(even) td {{ background: {t['alt_bg']}; }}
    .ei-table tr.ei-total td {{ background: {t['total_bg']}; font-weight: 800; }}
    .ei-num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .ei-up {{ color: {t['up']}; font-weight: 700; }}
    .ei-down {{ color: {t['down']}; font-weight: 700; }}
    .ei-bar {{
        background: {t['groove']}; border-radius: 999px; height: 9px;
        width: 120px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.25);
    }}
    .ei-bar > div {{ height: 100%; border-radius: 999px; }}

    /* ---- Buttons ---- */
    .stButton > button, .stFormSubmitButton > button {{
        background: linear-gradient(180deg, #3b82f6 0%, #2563eb 100%);
        color: #ffffff; border: 1px solid #1d4ed8; border-radius: 12px;
        font-weight: 700; padding: 0.5rem 1.1rem;
        box-shadow: 0 1px 0 rgba(255,255,255,0.4) inset,
                    0 6px 14px -6px rgba(37, 99, 235, 0.6);
    }}
    .stButton > button:hover, .stFormSubmitButton > button:hover {{
        filter: brightness(1.07);
    }}
    .stButton > button:active, .stFormSubmitButton > button:active {{
        box-shadow: 0 2px 6px rgba(0,0,0,0.25) inset; transform: translateY(1px);
    }}

    /* ---- Progress groove ---- */
    div[data-testid="stProgress"] > div > div {{
        background: {t['groove']}; border-radius: 999px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.18);
    }}
    div[data-testid="stProgress"] > div > div > div {{
        background: linear-gradient(180deg, #60a5fa, #2563eb);
        border-radius: 999px;
    }}

    /* Segmented theme toggle in the sidebar. */
    section[data-testid="stSidebar"] div[role="radiogroup"][aria-label="Theme"] {{
        gap: 6px;
    }}

    /* ---- Inputs (select / number / date / text) adapt to the theme ---- */
    .stDateInput div[data-baseweb="input"],
    .stDateInput div[data-baseweb="input"] *,
    .stNumberInput div[data-baseweb="input"],
    .stNumberInput div[data-baseweb="input"] *,
    .stTextInput div[data-baseweb="input"],
    .stTextInput div[data-baseweb="input"] *,
    div[data-baseweb="select"] > div {{
        background-color: {t['input_bg']} !important;
        border-color: {t['card_border']} !important;
    }}
    /* Number input (container + inner field + step buttons). */
    div[data-testid="stNumberInputContainer"],
    div[data-testid="stNumberInput-Input"],
    div[data-testid="stNumberInputContainer"] input,
    button[data-testid="stNumberInput-StepUp"],
    button[data-testid="stNumberInput-StepDown"] {{
        background-color: {t['input_bg']} !important;
        border-color: {t['card_border']} !important;
    }}
    .stDateInput input, .stNumberInput input, .stTextInput input,
    div[data-baseweb="select"] div {{
        color: {t['text']} !important;
    }}
    div[data-testid="stTabs"] button {{ color: {t['muted']}; }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{ color: {t['heading']}; }}
</style>
"""


def _fmt(amount) -> str:
    """Format a number as Indian rupees."""
    return f"₹{float(amount):,.2f}"


def _style_fig(fig):
    """Apply the active theme to a Plotly figure."""
    t = _theme()
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=t["text"]),
        legend=dict(font=dict(color=t["text"])),
    )
    fig.update_xaxes(gridcolor=t["grid"], zerolinecolor=t["grid"])
    fig.update_yaxes(gridcolor=t["grid"], zerolinecolor=t["grid"])
    return fig


def _table(headers, rows, total_row=None) -> str:
    """Render a themed HTML table. Cells may contain HTML."""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
    if total_row is not None:
        body += (
            "<tr class='ei-total'>"
            + "".join(f"<td>{c}</td>" for c in total_row)
            + "</tr>"
        )
    return f"<table class='ei-table'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


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
    return start, min(end, now)


def main():
    """Main dashboard application."""
    with st.sidebar:
        st.markdown("## 💰 Expense Intelligence")
        st.caption("Personal Finance Intelligence Platform")
        st.radio(
            "Theme",
            ["Light", "Dark"],
            horizontal=True,
            key="theme",
        )
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        page = st.radio(
            "Navigate",
            [
                "📊 Dashboard",
                "🧭 Explore",
                "🎯 Budgets",
                "⚙️ Settings",
            ],
            label_visibility="collapsed",
        )

    # Inject theme CSS after the toggle so the selection takes effect.
    st.markdown(_build_css(_theme()), unsafe_allow_html=True)

    pages = {
        "📊 Dashboard": show_dashboard,
        "🧭 Explore": show_explore,
        "🎯 Budgets": show_budgets,
        "⚙️ Settings": show_settings,
    }
    pages[page]()


def show_explore():
    """Combined page: transactions, analytics, and accounts under one roof."""
    st.title("Explore")
    st.caption("Transactions, analytics, and accounts in one place")

    tab_txns, tab_analytics, tab_accounts = st.tabs(
        ["🧾 Transactions", "📈 Analytics", "🏦 Accounts"]
    )
    with tab_txns:
        show_transactions()
    with tab_analytics:
        show_analytics()
    with tab_accounts:
        show_accounts()


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
        tot_cur = tot_prev = 0.0
        for cat in categories:
            cur = this_cat.get(cat, 0.0)
            prev = last_cat.get(cat, 0.0)
            tot_cur += cur
            tot_prev += prev
            change = cur - prev
            pct = (change / prev * 100) if prev else (100.0 if cur else 0.0)
            cls = "ei-up" if change > 0 else ("ei-down" if change < 0 else "")
            arrow = "▲" if change > 0 else ("▼" if change < 0 else "—")
            rows.append(
                [
                    cat,
                    f"<span class='ei-num'>{_fmt(cur)}</span>",
                    f"<span class='ei-num'>{_fmt(prev)}</span>",
                    f"<span class='{cls}'>{change:+,.0f}</span>",
                    f"<span class='{cls}'>{pct:+.1f}%</span>",
                    f"<span class='{cls}'>{arrow}</span>",
                ]
            )
        tot_change = tot_cur - tot_prev
        tot_pct = (tot_change / tot_prev * 100) if tot_prev else 0.0
        tcls = "ei-up" if tot_change > 0 else "ei-down"
        total_row = [
            "TOTAL",
            _fmt(tot_cur),
            _fmt(tot_prev),
            f"<span class='{tcls}'>{tot_change:+,.0f}</span>",
            f"<span class='{tcls}'>{tot_pct:+.1f}%</span>",
            f"<span class='{tcls}'>{'▲' if tot_change > 0 else '▼'}</span>",
        ]
        st.markdown(
            _table(
                [
                    "Category",
                    "This month",
                    "Last month",
                    "Change (₹)",
                    "Change (%)",
                    "",
                ],
                rows,
                total_row,
            ),
            unsafe_allow_html=True,
        )
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
            )
            st.plotly_chart(_style_fig(fig), use_container_width=True)
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
    col1, col2 = st.columns([1, 3])
    with col1:
        limit = st.slider("Show most recent", 10, 200, 50, step=10)

    with get_session().__enter__() as session:
        txns = [
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

    if not txns:
        st.info("No transactions found.")
        return

    debits = sum(x["Amount"] for x in txns if x["Type"] == "debit")
    credits = sum(x["Amount"] for x in txns if x["Type"] == "credit")
    c1, c2, c3 = st.columns(3)
    c1.metric("Shown", len(txns))
    c2.metric("Total debits", _fmt(debits), delta_color="inverse")
    c3.metric("Total credits", _fmt(credits))

    rows = []
    for x in txns:
        cls = "ei-up" if x["Type"] == "debit" else "ei-down"
        rows.append(
            [
                x["Date"],
                x["Merchant"],
                x["Category"],
                f"<span class='{cls}'>{x['Type']}</span>",
                f"<span class='ei-num'>{_fmt(x['Amount'])}</span>",
                x["Status"],
            ]
        )
    st.markdown(
        _table(
            ["Date", "Merchant", "Category", "Type", "Amount", "Status"],
            rows,
        ),
        unsafe_allow_html=True,
    )


def show_accounts():
    """Show accounts page."""
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
        fig.update_traces(line_color="#3b82f6", fillcolor="rgba(59,130,246,0.18)")
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
        st.plotly_chart(_style_fig(fig), use_container_width=True)
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
            )
            st.plotly_chart(_style_fig(fig), use_container_width=True)
        else:
            st.info("No merchant data yet.")

    with right:
        st.markdown("### 📅 Daily spending (30d)")
        daily_spending = analytics.get_daily_spending(days=30)
        if daily_spending:
            df = pd.DataFrame(daily_spending)
            fig = px.bar(df, x="date", y="total", color_discrete_sequence=["#10b981"])
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(_style_fig(fig), use_container_width=True)
        else:
            st.info("No daily data yet.")


def show_budgets():
    """Show budgets page: set per-category budgets and track progress."""
    analytics = get_analytics_engine()
    st.title("Budgets")

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

    rows = []
    for s in status:
        spent = float(s["spent"])
        budget = float(s["budget"])
        remaining = float(s["remaining"])
        pct = s["percent_used"]
        over = s["over_budget"]
        fill = "#f04438" if over else "linear-gradient(90deg,#60a5fa,#2563eb)"
        bar = (
            f"<div class='ei-bar'><div style='width:{min(pct, 100):.0f}%;"
            f"background:{fill};'></div></div>"
        )
        pill = (
            "<span class='ei-pill warn'>Over budget</span>"
            if over
            else "<span class='ei-pill ok'>On track</span>"
        )
        rows.append(
            [
                s["category"],
                f"<span class='ei-num'>{_fmt(budget)}</span>",
                f"<span class='ei-num'>{_fmt(spent)}</span>",
                f"<span class='ei-num'>{_fmt(remaining)}</span>",
                f"{bar}<span class='sub'>{pct:.0f}%</span>",
                pill,
            ]
        )
    st.markdown(
        _table(
            ["Category", "Budget", "Spent", "Remaining", "Used", "Status"],
            rows,
        ),
        unsafe_allow_html=True,
    )


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
