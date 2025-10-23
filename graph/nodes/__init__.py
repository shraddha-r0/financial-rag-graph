""
Core nodes for the financial analytics graph.

This package contains the main processing nodes for the financial analytics pipeline:
- Intent Parser: Extracts structured information from natural language queries
- Category Resolver: Maps user terms to canonical categories
- SQL Planner: Generates SQL queries from parsed intents
- DB Executor: Executes SQL queries and returns results
"""

from .intent_parser import parse_intent
from .category_resolver import resolve_categories
from .sql_planner import plan_sql
from .db_executor import execute_query

__all__ = [
    'parse_intent',
    'resolve_categories',
    'plan_sql',
    'execute_query'
]
