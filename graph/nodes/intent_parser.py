"""
Intent Parser Node

This module extracts structured information from natural language queries about financial data.
It identifies time ranges, metrics, dimensions, and comparison periods.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Literal, TypedDict
from enum import Enum

class TimeGranularity(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"

class IntentType(str, Enum):
    SPENDING_BY_CATEGORY = "spending_by_category"
    SPENDING_OVER_TIME = "spending_over_time"
    TOP_ITEMS = "top_items"
    COMPARISON = "comparison"
    BREAKDOWN = "breakdown"

class ParsedIntent(TypedDict):
    """Structured representation of the parsed user intent."""
    intent_type: IntentType
    time_range: Tuple[Optional[datetime], Optional[datetime]]
    time_granularity: Optional[TimeGranularity]
    dimensions: List[str]
    metrics: List[str]
    filters: Dict[str, List[str]]
    limit: Optional[int]
    is_comparison: bool
    comparison_period: Optional[Tuple[Optional[datetime], Optional[datetime]]]

def parse_intent(query: str) -> ParsedIntent:
    """
    Parse a natural language query into structured intent.
    
    Args:
        query: The user's natural language query
        
    Returns:
        ParsedIntent: A dictionary containing the structured intent
    """
    # Default intent
    intent: ParsedIntent = {
        "intent_type": IntentType.SPENDING_OVER_TIME,
        "time_range": (None, None),
        "time_granularity": None,
        "dimensions": [],
        "metrics": ["amount"],
        "filters": {},
        "limit": None,
        "is_comparison": False,
        "comparison_period": None
    }
    
    query = query.lower()
    
    # 1. Detect intent type
    if any(word in query for word in ["by category", "per category", "categories"]):
        intent["intent_type"] = IntentType.SPENDING_BY_CATEGORY
        intent["dimensions"].append("category")
    elif any(word in query for word in ["top ", "highest ", "most expensive"]):
        intent["intent_type"] = IntentType.TOP_ITEMS
        # Extract the top N if specified
        if match := re.search(r'top\s+(\d+)', query):
            intent["limit"] = int(match.group(1))
        else:
            intent["limit"] = 10  # Default top 10
    elif any(word in query for word in ["compare", "vs", "versus"]):
        intent["intent_type"] = IntentType.COMPARISON
        intent["is_comparison"] = True
    
    # 2. Extract time range
    intent["time_range"] = _extract_time_range(query)
    
    # 3. Extract time granularity
    intent["time_granularity"] = _extract_time_granularity(query)
    
    # 4. Extract dimensions
    if "by" in query:
        # Simple keyword-based dimension detection
        if "category" in query or any(word in query for word in ["categories", "type"]):
            intent["dimensions"].append("category")
        if "merchant" in query or "store" in query:
            intent["dimensions"].append("merchant")
    
    # 5. Handle comparisons
    if intent["is_comparison"]:
        intent["comparison_period"] = _extract_comparison_period(query, intent["time_range"])
    
    return intent

def _extract_time_range(query: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Extract time range from query."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Common patterns
    if "last month" in query:
        first_day = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day = today.replace(day=1) - timedelta(days=1)
        return first_day, last_day
    elif "this month" in query:
        return today.replace(day=1), today
    elif "last 30 days" in query or "past month" in query:
        return today - timedelta(days=30), today
    elif "last 7 days" in query or "past week" in query:
        return today - timedelta(days=7), today
    elif "yesterday" in query:
        return today - timedelta(days=1), today - timedelta(days=1)
    
    # Default: last 30 days
    return today - timedelta(days=30), today

def _extract_time_granularity(query: str) -> Optional[TimeGranularity]:
    """Extract time granularity from query."""
    if any(word in query for word in ["daily", "day by day", "each day"]):
        return TimeGranularity.DAY
    elif any(word in query for word in ["weekly", "week by week", "each week"]):
        return TimeGranularity.WEEK
    elif any(word in query for word in ["monthly", "month by month", "each month"]):
        return TimeGranularity.MONTH
    elif any(word in query for word in ["quarterly", "quarter by quarter"]):
        return TimeGranularity.QUARTER
    elif any(word in query for word in ["yearly", "annually", "year by year"]):
        return TimeGranularity.YEAR
    return None

def _extract_comparison_period(query: str, 
                             current_range: Tuple[Optional[datetime], Optional[datetime]]) -> Optional[Tuple[Optional[datetime], Optional[datetime]]]:
    """
    Extract comparison period based on the current time range.
    
    Args:
        query: The user query
        current_range: The current time range (start, end)
        
    Returns:
        Optional time range for comparison or None
    """
    if not all(current_range):
        return None
        
    start, end = current_range
    if not (start and end):
        return None
        
    duration = end - start
    
    # Default to previous period of same length
    return start - duration, start
