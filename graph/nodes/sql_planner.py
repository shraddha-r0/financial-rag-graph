"""
SQL Planner Node

This module generates SQL queries based on the parsed intent.
It uses a template-based approach to ensure safe and efficient queries.
"""

from typing import Dict, List, Optional, Tuple, Any, Literal, TypedDict
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

@dataclass
class SQLPlan:
    """Container for SQL query plan."""
    query: str
    params: Dict[str, Any]

class SQLTemplateType(str, Enum):
    """Types of SQL templates available."""
    SPENDING_OVER_TIME = "spending_over_time"
    SPENDING_BY_CATEGORY = "spending_by_category"
    TOP_ITEMS = "top_items"
    COMPARISON = "comparison"
    BREAKDOWN = "breakdown"

class SQLPlanner:
    """Generates SQL queries from parsed intents using predefined templates."""
    
    def __init__(self, table_name: str = "transactions"):
        """
        Initialize the SQL planner.
        
        Args:
            table_name: Name of the main transactions table
        """
        self.table_name = table_name
        self._templates = self._init_templates()
    
    def _init_templates(self) -> Dict[str, str]:
        """Initialize the SQL templates."""
        return {
            SQLTemplateType.SPENDING_OVER_TIME: """
                SELECT 
                    {time_expr} AS time_period,
                    {select_expression}
                FROM {table_name}
                {where_clause}
                GROUP BY time_period
                ORDER BY time_period
            """,
            
            SQLTemplateType.SPENDING_BY_CATEGORY: """
                SELECT 
                    category,
                    {select_expression}
                FROM {table_name}
                {where_clause}
                GROUP BY category
                ORDER BY {order_expression} DESC
                {limit_clause}
            """,
            
            SQLTemplateType.TOP_ITEMS: """
                SELECT 
                    {dimension},
                    {select_expression}
                FROM {table_name}
                {where_clause}
                GROUP BY {dimension}
                ORDER BY {order_expression} DESC
                LIMIT {limit}
            """,
            
            SQLTemplateType.COMPARISON: """
                WITH current_period AS (
                    SELECT 
                        {select_expression} as current_value
                    FROM {table_name}
                    {current_where_clause}
                    {group_by_clause}
                ),
                previous_period AS (
                    SELECT 
                        {select_expression} as previous_value
                    FROM {table_name}
                    {previous_where_clause}
                    {group_by_clause}
                )
                SELECT 
                    current_period.*,
                    previous_period.previous_value,
                    (current_period.current_value - previous_period.previous_value) as difference,
                    (current_period.current_value / NULLIF(previous_period.previous_value, 0) - 1) * 100 as pct_change
                FROM current_period
                LEFT JOIN previous_period ON 1=1
            """
        }
    
    def plan_sql(self, intent: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Generate a SQL query based on the parsed intent.
        
        Args:
            intent: The parsed intent from the intent parser
            
        Returns:
            A tuple of (sql_query, params_dict)
        """
        params = {}
        intent_type = intent.get("intent_type")
        
        if intent_type == SQLTemplateType.SPENDING_OVER_TIME:
            return self._plan_spending_over_time(intent)
        elif intent_type == SQLTemplateType.SPENDING_BY_CATEGORY:
            return self._plan_spending_by_category(intent)
        elif intent_type == SQLTemplateType.TOP_ITEMS:
            return self._plan_top_items(intent)
        elif intent.get("is_comparison", False):
            return self._plan_comparison(intent)
        else:
            # Default to spending over time
            return self._plan_spending_over_time(intent)
    
    def _plan_spending_over_time(self, intent: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate SQL for spending over time queries."""
        time_granularity = intent.get("time_granularity", "month")
        time_expr = self._get_time_expression(time_granularity)
        
        template = self._templates[SQLTemplateType.SPENDING_OVER_TIME]
        
        # Build where clause and params
        where_clause, where_params = self._build_where_clause(intent)
        
        sql = template.format(
            time_expr=time_expr,
            select_expression="SUM(amount) as total_amount",
            table_name=self.table_name,
            where_clause=where_clause
        )
        
        return sql, where_params
    
    def _plan_spending_by_category(self, intent: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate SQL for spending by category queries."""
        template = self._templates[SQLTemplateType.SPENDING_BY_CATEGORY]
        
        # Build where clause and params
        where_clause, where_params = self._build_where_clause(intent)
        
        sql = template.format(
            select_expression="SUM(amount) as total_amount",
            table_name=self.table_name,
            where_clause=where_clause,
            order_expression="total_amount",
            limit_clause=f"LIMIT {intent.get('limit', 20)}" if 'limit' in intent else ""
        )
        
        return sql, where_params
    
    def _plan_top_items(self, intent: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate SQL for top items queries."""
        dimension = intent.get("dimensions", ["merchant"])[0]  # Default to merchant
        
        template = self._templates[SQLTemplateType.TOP_ITEMS]
        
        # Build where clause and params
        where_clause, where_params = self._build_where_clause(intent)
        
        sql = template.format(
            dimension=dimension,
            select_expression="SUM(amount) as total_amount",
            table_name=self.table_name,
            where_clause=where_clause,
            order_expression="total_amount",
            limit=intent.get("limit", 10)
        )
        
        return sql, where_params
    
    def _plan_comparison(self, intent: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Generate SQL for comparison queries."""
        current_start, current_end = intent["time_range"]
        prev_start, prev_end = intent.get("comparison_period", (None, None))
        
        if not all([current_start, current_end, prev_start, prev_end]):
            raise ValueError("Invalid time range for comparison")
        
        # Build where clauses
        current_where, current_params = self._build_where_clause(intent)
        
        # For the previous period, we use the same filters but different dates
        prev_intent = intent.copy()
        prev_intent["time_range"] = (prev_start, prev_end)
        prev_where, prev_params = self._build_where_clause(prev_intent)
        
        # Update param names to avoid conflicts
        prev_params = {f"prev_{k}": v for k, v in prev_params.items()}
        
        # Get the appropriate select expression based on intent
        if intent.get("intent_type") == SQLTemplateType.SPENDING_BY_CATEGORY:
            select_expr = "category, SUM(amount) as total_amount"
            group_by = "GROUP BY category"
        else:
            time_granularity = intent.get("time_granularity", "month")
            time_expr = self._get_time_expression(time_granularity)
            select_expr = f"{time_expr} AS time_period, SUM(amount) as total_amount"
            group_by = "GROUP BY time_period"
        
        template = self._templates[SQLTemplateType.COMPARISON]
        
        sql = template.format(
            select_expression=select_expr,
            table_name=self.table_name,
            current_where_clause=current_where.replace("WHERE ", ""),
            previous_where_clause=prev_where.replace("WHERE ", ""),
            group_by_clause=group_by
        )
        
        # Combine params
        params = {**current_params, **prev_params}
        
        return sql, params
    
    def _build_where_clause(self, intent: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Build a WHERE clause from the intent filters."""
        conditions = []
        params = {}
        
        # Time range filter
        time_start, time_end = intent.get("time_range", (None, None))
        if time_start:
            conditions.append("date >= :time_start")
            params["time_start"] = time_start.strftime("%Y-%m-%d")
        if time_end:
            conditions.append("date <= :time_end")
            params["time_end"] = time_end.strftime("%Y-%m-%d")
        
        # Category filter
        if "category" in intent.get("filters", {}):
            categories = intent["filters"]["category"]
            if categories:
                placeholders = ", ".join(f":category_{i}" for i in range(len(categories)))
                conditions.append(f"category IN ({placeholders})")
                params.update({f"category_{i}": cat for i, cat in enumerate(categories)})
        
        # Amount filters (min/max)
        if "min_amount" in intent.get("filters", {}):
            conditions.append("amount >= :min_amount")
            params["min_amount"] = float(intent["filters"]["min_amount"])
        
        if "max_amount" in intent.get("filters", {}):
            conditions.append("amount <= :max_amount")
            params["max_amount"] = float(intent["filters"]["max_amount"])
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return where_clause, params
    
    def _get_time_expression(self, granularity: str) -> str:
        """Get the appropriate SQL expression for time grouping."""
        if granularity == "day":
            return "date"
        elif granularity == "week":
            return "date(date, 'weekday 0', '-6 days')"  # Start of week (Sunday)
        elif granularity == "month":
            return "strftime('%Y-%m', date)"
        elif granularity == "quarter":
            return "strftime('%Y', date) || '-Q' || ((strftime('%m', date) + 2) / 3)"
        elif granularity == "year":
            return "strftime('%Y', date)"
        else:
            # Default to month
            return "strftime('%Y-%m', date)"


def plan_sql(intent: Dict[str, Any], table_name: str = "expenses") -> Tuple[str, Dict[str, Any]]:
    """
    Generate SQL query and parameters from a parsed intent.
    
    Args:
        intent: Parsed intent dictionary
        table_name: Name of the transactions table (default: 'expenses')
        
    Returns:
        Tuple of (sql_query, parameters)
    """
    planner = SQLPlanner(table_name=table_name)
    return planner.plan_sql(intent)


def generate_sql_plan(intent: Dict[str, Any]) -> SQLPlan:
    """
    Generate a SQL plan from a parsed intent.
    
    Args:
        intent: The parsed intent dictionary
        
    Returns:
        SQLPlan object containing the query and parameters
    """
    query, params = plan_sql(intent, table_name="expenses")
    return SQLPlan(query=query, params=params)
