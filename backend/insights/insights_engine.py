"""AI insights engine with natural language query using function calling."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from openai import OpenAI
from loguru import logger

from backend.analytics import get_analytics_engine
from backend.config import get_config


class InsightsEngine:
    """Engine for AI-powered insights and natural language queries."""
    
    def __init__(self, analytics_engine=None):
        """Initialize the insights engine.
        
        Args:
            analytics_engine: AnalyticsEngine instance. If None, uses global instance.
        """
        config = get_config()
        self.client = OpenAI(api_key=config.ai.api_key)
        self.model = config.ai.model
        self.analytics = analytics_engine or get_analytics_engine()
    
    def query_natural_language(self, question: str) -> dict:
        """Answer natural language questions about finances using function calling.
        
        Args:
            question: Natural language question about finances.
        
        Returns:
            Dict with answer and supporting data.
        """
        try:
            # Define available functions
            functions = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_spending_by_category",
                        "description": "Get total spending by category for a given time period",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date in YYYY-MM-DD format",
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date in YYYY-MM-DD format",
                                },
                            },
                            "required": [],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_spending_by_merchant",
                        "description": "Get top spending by merchant for a given time period",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date in YYYY-MM-DD format",
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date in YYYY-MM-DD format",
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Number of top merchants to return",
                                },
                            },
                            "required": [],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_income_vs_expense",
                        "description": "Get income vs expense summary for a given time period",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date in YYYY-MM-DD format",
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date in YYYY-MM-DD format",
                                },
                            },
                            "required": [],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_subscriptions",
                        "description": "Get detected recurring subscription payments",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "lookback_days": {
                                    "type": "integer",
                                    "description": "Number of days to look back for detection",
                                },
                            },
                            "required": [],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_monthly_spending",
                        "description": "Get monthly spending trend",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "months": {
                                    "type": "integer",
                                    "description": "Number of months to include",
                                },
                            },
                            "required": [],
                        },
                    },
                },
            ]
            
            # Call OpenAI with function calling
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial assistant. Answer questions about personal finances by calling the appropriate functions. Use the current date when needed.",
                    },
                    {
                        "role": "user",
                        "content": question,
                    },
                ],
                tools=functions,
                tool_choice="auto",
            )
            
            # Check if function was called
            tool_calls = response.choices[0].message.tool_calls
            
            if tool_calls:
                # Execute function calls
                function_results = []
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = tool_call.function.arguments
                    
                    # Parse arguments
                    import json
                    args = json.loads(function_args)
                    
                    # Execute function
                    result = self._execute_function(function_name, args)
                    function_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": json.dumps(result),
                    })
                
                # Get final answer with function results
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a financial assistant. Answer questions about personal finances based on the function results provided.",
                        },
                        {
                            "role": "user",
                            "content": question,
                        },
                        response.choices[0].message,
                        *function_results,
                    ],
                )
                
                answer = final_response.choices[0].message.content
                
                return {
                    "answer": answer,
                    "function_calls": [
                        {
                            "name": tc.function.name,
                            "args": json.loads(tc.function.arguments),
                        }
                        for tc in tool_calls
                    ],
                }
            else:
                # Direct answer without function calls
                answer = response.choices[0].message.content
                return {
                    "answer": answer,
                    "function_calls": [],
                }
                
        except Exception as e:
            logger.error(f"Natural language query failed: {e}")
            return {
                "answer": f"Sorry, I couldn't process your question: {str(e)}",
                "function_calls": [],
            }
    
    def _execute_function(self, function_name: str, args: dict) -> dict:
        """Execute a function by name with given arguments.
        
        Args:
            function_name: Name of the function to execute.
            args: Arguments to pass to the function.
        
        Returns:
            Function result as dict.
        """
        if function_name == "get_spending_by_category":
            start_date = self._parse_date(args.get("start_date"))
            end_date = self._parse_date(args.get("end_date"))
            result = self.analytics.get_spending_by_category(start_date, end_date)
            return {k: float(v) for k, v in result.items()}
        
        elif function_name == "get_spending_by_merchant":
            start_date = self._parse_date(args.get("start_date"))
            end_date = self._parse_date(args.get("end_date"))
            limit = args.get("limit", 20)
            result = self.analytics.get_spending_by_merchant(start_date, end_date, limit)
            return [{"merchant": m, "amount": float(a)} for m, a in result]
        
        elif function_name == "get_income_vs_expense":
            start_date = self._parse_date(args.get("start_date"))
            end_date = self._parse_date(args.get("end_date"))
            result = self.analytics.get_income_vs_expense(start_date, end_date)
            return result
        
        elif function_name == "get_subscriptions":
            lookback_days = args.get("lookback_days", 90)
            result = self.analytics.get_subscriptions(lookback_days)
            return result
        
        elif function_name == "get_monthly_spending":
            months = args.get("months", 12)
            result = self.analytics.get_monthly_spending(months)
            return result
        
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object.
        
        Args:
            date_str: Date string in YYYY-MM-DD format.
        
        Returns:
            Datetime object or None if invalid.
        """
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
            return None
    
    def get_insights(self) -> list[str]:
        """Generate AI-powered insights about spending patterns.
        
        Returns:
            List of insight strings.
        """
        try:
            # Get summary metrics
            summary = self.analytics.get_summary_metrics()
            
            # Build prompt for insights
            prompt = f"""Analyze the following financial data and provide 3-5 actionable insights:

Income vs Expense:
- Total Income: ₹{summary['income_vs_expense']['total_income']}
- Total Expense: ₹{summary['income_vs_expense']['total_expense']}
- Net: ₹{summary['income_vs_expense']['net']}

Spending by Category:
{', '.join(f'{k}: ₹{v}' for k, v in summary['spending_by_category'].items())}

Subscriptions:
{', '.join(f"{s['merchant']}: ₹{s['average_amount']}/month" for s in summary['subscriptions'])}

Provide specific, actionable insights to help improve financial health."""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial advisor. Provide actionable insights based on financial data.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.7,
            )
            
            insights_text = response.choices[0].message.content
            
            # Split into individual insights
            insights = [
                insight.strip()
                for insight in insights_text.split("\n")
                if insight.strip()
            ]
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return ["Unable to generate insights at this time."]


# Global insights engine instance
_insights_engine: Optional[InsightsEngine] = None


def get_insights_engine() -> InsightsEngine:
    """Get the global insights engine instance (singleton pattern)."""
    global _insights_engine
    if _insights_engine is None:
        _insights_engine = InsightsEngine()
    return _insights_engine


def reset_insights_engine() -> None:
    """Reset the global insights engine (useful for testing)."""
    global _insights_engine
    _insights_engine = None
