"""
Validation and Sanitization Utilities

This module provides functions to validate and sanitize user inputs,
handle edge cases, and ensure data quality.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

def sanitize_sql_identifier(identifier: str) -> str:
    """
    Sanitize SQL identifiers to prevent SQL injection.
    Only allows alphanumeric characters and underscores.
    
    Args:
        identifier: The SQL identifier to sanitize
        
    Returns:
        The sanitized identifier
        
    Raises:
        ValueError: If the identifier is invalid or contains invalid characters
    """
    if not identifier or not isinstance(identifier, str):
        raise ValueError("Identifier must be a non-empty string")
    
    # Check if the first character is a letter or underscore
    if not re.match(r'^[a-zA-Z_]', identifier):
        raise ValueError("Identifier must start with a letter or underscore")
    
    # Only allow alphanumeric and underscores
    if not re.match(r'^[a-zA-Z0-9_]+$', identifier):
        raise ValueError("Identifier can only contain alphanumeric characters and underscores")
    
    # Check if it's a reserved SQL keyword
    sql_keywords = {
        'select', 'insert', 'update', 'delete', 'from', 'where', 'group', 'by', 
        'order', 'having', 'join', 'inner', 'outer', 'left', 'right', 'as', 'and',
        'or', 'not', 'in', 'like', 'between', 'is', 'null', 'true', 'false'
    }
    if identifier.lower() in sql_keywords:
        raise ValueError(f"Identifier cannot be a reserved SQL keyword: {identifier}")
    
    return identifier

def parse_timeframe(
    time_str: Optional[str] = None,
    default_days: int = 30
) -> Tuple[datetime, datetime]:
    """
    Parse a natural language timeframe into start and end datetimes.
    
    Args:
        time_str: Natural language time description (e.g., "last 3 months")
        default_days: Default number of days if time_str is None or ambiguous
        
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    end_date = datetime.now()
    
    if not time_str:
        # Default to last N days if no time specified
        start_date = end_date - timedelta(days=default_days)
        logger.info(f"No timeframe specified, defaulting to last {default_days} days")
        return start_date, end_date
    
    time_str = time_str.lower().strip()
    
    # Common time patterns
    patterns = [
        (r'last\s+(\d+)\s+days?', lambda m: timedelta(days=int(m.group(1)))),
        (r'last\s+week', lambda _: timedelta(weeks=1)),
        (r'last\s+(\d+)\s+weeks?', lambda m: timedelta(weeks=int(m.group(1)))),
        (r'last\s+month', lambda _: timedelta(days=30)),
        (r'last\s+(\d+)\s+months?', lambda m: timedelta(days=30*int(m.group(1)))),
        (r'last\s+year', lambda _: timedelta(days=365)),
        (r'last\s+(\d+)\s+years?', lambda m: timedelta(days=365*int(m.group(1)))),
        (r'today', lambda _: timedelta(days=1)),
        (r'yesterday', lambda _: timedelta(days=2)),
    ]
    
    for pattern, delta_func in patterns:
        match = re.match(pattern, time_str)
        if match:
            delta = delta_func(match)
            start_date = end_date - delta
            return start_date, end_date
    
    # If no pattern matched, use default
    logger.warning(f"Could not parse timeframe: '{time_str}'. Using default of {default_days} days.")
    start_date = end_date - timedelta(days=default_days)
    return start_date, end_date

def handle_zero_results(
    query: str,
    intent: Dict[str, Any],
    original_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Handle cases where a query returns no results.
    
    Args:
        query: The original user query
        intent: The parsed intent
        original_results: The (empty) results
        
    Returns:
        Modified intent with suggestions or fallbacks
    """
    modified_intent = intent.copy()
    
    # Check if we can suggest a broader time range
    time_range = intent.get('time_range', (None, None))
    if time_range[0] and time_range[1]:
        # Try doubling the time range
        time_span = (time_range[1] - time_range[0]) * 2
        new_start = time_range[1] - time_span
        modified_intent['time_range'] = (new_start, time_range[1])
        modified_intent['suggestions'] = [
            f"No results found for the specified time period. "
            f"Trying a broader range: {new_start.strftime('%Y-%m-%d')} to {time_range[1].strftime('%Y-%m-%d')}",
            "Try including refunds with `include_refunds:true`"
        ]
    
    # Check if we're excluding transfers
    if not intent.get('include_transfers', False):
        modified_intent['include_transfers'] = True
        modified_intent['suggestions'] = modified_intent.get('suggestions', []) + [
            "No results found. Trying again with transfers included."
        ]
    
    return modified_intent

def normalize_currency(
    amounts: List[Dict[str, Any]],
    currency_rates: Dict[str, float],
    target_currency: str = "CLP"
) -> List[Dict[str, Any]]:
    """
    Normalize amounts to a target currency using provided exchange rates.
    
    Args:
        amounts: List of amount dictionaries with 'amount' and 'currency' keys
        currency_rates: Dictionary of exchange rates (e.g., {'USD': 950.0})
        target_currency: The currency to convert to
        
    Returns:
        List of dictionaries with normalized amounts
    """
    if not currency_rates:
        return amounts
    
    normalized = []
    
    for item in amounts:
        amount = item.get('amount', 0)
        currency = item.get('currency', target_currency).upper()
        
        if currency == target_currency:
            normalized.append(item)
            continue
            
        if currency not in currency_rates:
            logger.warning(f"No exchange rate available for {currency}")
            item['conversion_warning'] = f"No exchange rate for {currency}"
            normalized.append(item)
            continue
            
        # Convert to target currency
        rate = currency_rates[currency]
        item['original_amount'] = amount
        item['original_currency'] = currency
        item['amount'] = amount * rate
        item['currency'] = target_currency
        item['exchange_rate'] = rate
        
        normalized.append(item)
    
    return normalized

def detect_potential_sql_injection(query: str) -> bool:
    """
    Check if a query string contains potential SQL injection patterns.
    
    Args:
        query: The query string to check
        
    Returns:
        True if potential SQL injection is detected, False otherwise
    """
    if not query:
        return False
    
    # Common SQL injection patterns
    patterns = [
        # Match common SQL injection patterns
        r'(?i)\b(?:union|select|insert|update|delete|drop|alter|create|truncate)\b.*\b(?:union|select|insert|update|delete|drop|alter|create|truncate)\b',
        # Match OR 1=1 type injections
        r'(?i)\b(?:or\s+\d+\s*=\s*\d+|\d+\s*=\s*\d+\s+or)\b',
        # Match string-based injections like ' OR '1'='1
        r'(?i)(?:\'\s*or\s*[\'"][^\'"]*[\'"])|(?:[\'"][^\'"]*[\'"]\s*or\s*)',
        # Match exec/execute statements
        r'(?i)\b(?:exec\s*\(|execute\s+\w+\s+with\s+recompile\b)',
        # Match time-based injection patterns
        r'(?i)\b(?:waitfor\s+delay\b|sleep\s*\(|benchmark\s*\()',
        # Match dangerous procedures
        r'(?i)\b(?:xp_cmdshell|sp_configure|sp_oacreate|sp_oamethod|sp_oagetproperty)\b',
        # Match SQL comments and statement terminators
        r'(?:--|#|\/\*|\*\/|;)'
    ]
    
    for pattern in patterns:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Potential SQL injection detected in query: {query}")
            return True
    
    return False
