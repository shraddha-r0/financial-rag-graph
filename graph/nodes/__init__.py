"""
Core nodes for the financial analytics graph.

This package contains the main processing nodes for the financial analytics pipeline:
- Intent Parser: Extracts structured information from natural language queries
- Category Resolver: Maps user terms to canonical categories
- SQL Planner: Generates SQL queries from parsed intents
- DB Executor: Executes SQL queries and returns results
"""

from .intent_parser import parse_intent, IntentType, TimeGranularity, ParsedIntent
from .llm_intent_parser import parse_intent_with_llm, LLMIntentParser
from .category_resolver import resolve_categories, CategoryResolver
from .sql_planner import SQLPlanner, SQLTemplateType, SQLPlan, plan_sql, generate_sql_plan
from .db_executor import DBExecutor, execute_query, QueryResult
from .chart_node import ChartGenerator, ChartType, generate_chart_spec
from .logger import QueryLogger
from .answer_synth import generate_answer

__all__ = [
    # Intent Parser
    'parse_intent', 'parse_intent_with_llm', 'LLMIntentParser', 'IntentType', 'TimeGranularity', 'ParsedIntent',
    
    # Category Resolver
    'resolve_categories', 'CategoryResolver',
    
    # SQL Planner
    'SQLPlanner', 'SQLTemplateType', 'SQLPlan', 'plan_sql', 'generate_sql_plan',
    
    # DB Executor
    'DBExecutor', 'execute_query', 'QueryResult',
    
    # Chart Node
    'ChartGenerator', 'ChartType', 'generate_chart_spec',
    
    # Answer Synthesis
    'generate_answer',
    
    # Logger
    'QueryLogger'
]
