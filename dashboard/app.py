"""Streamlit dashboard for Expense Intelligence."""

import streamlit as st
from datetime import datetime, timedelta

from backend.analytics import get_analytics_engine
from backend.api.routes.accounts import list_accounts
from backend.api.routes.transactions import list_transactions


st.set_page_config(
    page_title="Expense Intelligence",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    """Main dashboard application."""
    st.title("💰 Expense Intelligence")
    st.markdown("Personal Finance Intelligence Platform")
    
    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "Transactions", "Accounts", "Analytics", "Settings"],
    )
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Transactions":
        show_transactions()
    elif page == "Accounts":
        show_accounts()
    elif page == "Analytics":
        show_analytics()
    elif page == "Settings":
        show_settings()


def show_dashboard():
    """Show main dashboard with summary metrics."""
    st.header("Dashboard")
    
    analytics = get_analytics_engine()
    
    # Get summary metrics
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    summary = analytics.get_summary_metrics(start_date, end_date)
    
    # Income vs Expense
    income_expense = summary["income_vs_expense"]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Income", f"₹{income_expense['total_income']:,.2f}")
    col2.metric("Total Expense", f"₹{income_expense['total_expense']:,.2f}")
    col3.metric("Net", f"₹{income_expense['net']:,.2f}")
    
    # Spending by category
    st.subheader("Spending by Category")
    spending_by_category = summary["spending_by_category"]
    
    if spending_by_category:
        import plotly.express as px
        
        categories = list(spending_by_category.keys())
        amounts = [float(v) for v in spending_by_category.values()]
        
        fig = px.pie(
            values=amounts,
            names=categories,
            title="Spending Distribution",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No spending data available for the selected period.")
    
    # Subscriptions
    st.subheader("Detected Subscriptions")
    subscriptions = summary["subscriptions"]
    
    if subscriptions:
        for sub in subscriptions:
            st.write(f"**{sub['merchant'].title()}**: ₹{sub['average_amount']:.2f}/month")
    else:
        st.info("No subscriptions detected.")


def show_transactions():
    """Show transactions page."""
    st.header("Transactions")
    
    # Get transactions
    transactions = list_transactions(limit=100)
    
    if transactions:
        import pandas as pd
        
        df = pd.DataFrame([tx.model_dump() for tx in transactions])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No transactions found.")


def show_accounts():
    """Show accounts page."""
    st.header("Accounts")
    
    # Get accounts
    accounts = list_accounts()
    
    if accounts:
        for account in accounts:
            with st.expander(f"{account.bank_name} - {account.account_identifier}"):
                st.write(f"**Type:** {account.account_type}")
                st.write(f"**Nickname:** {account.nickname}")
                st.write(f"**Status:** {'Active' if account.is_active else 'Inactive'}")
    else:
        st.info("No accounts found.")


def show_analytics():
    """Show analytics page."""
    st.header("Analytics")
    
    analytics = get_analytics_engine()
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Monthly spending trend
    st.subheader("Monthly Spending Trend")
    monthly_spending = analytics.get_monthly_spending(months=12)
    
    if monthly_spending:
        import plotly.express as px
        import pandas as pd
        
        df = pd.DataFrame(monthly_spending)
        fig = px.line(df, x="month", y="total", title="Monthly Spending")
        st.plotly_chart(fig, use_container_width=True)
    
    # Top merchants
    st.subheader("Top Merchants")
    top_merchants = analytics.get_spending_by_merchant(start_datetime, end_datetime, limit=10)
    
    if top_merchants:
        for merchant, amount in top_merchants:
            st.write(f"**{merchant}**: ₹{amount:.2f}")
    
    # Daily spending
    st.subheader("Daily Spending")
    daily_spending = analytics.get_daily_spending(days=30)
    
    if daily_spending:
        import plotly.express as px
        import pandas as pd
        
        df = pd.DataFrame(daily_spending)
        fig = px.bar(df, x="date", y="total", title="Daily Spending")
        st.plotly_chart(fig, use_container_width=True)


def show_settings():
    """Show settings page."""
    st.header("Settings")
    
    st.subheader("Gmail Sync")
    st.write("Configure Gmail sync settings")
    
    st.subheader("Categories")
    st.write("Manage merchant categories")
    
    st.subheader("API Keys")
    st.write("Configure API keys for external services")


if __name__ == "__main__":
    main()
