"""
Tests for validation and edge case handling.
"""

from datetime import datetime, timedelta
import pytest

from graph.utils.validation import (
    sanitize_sql_identifier,
    parse_timeframe,
    handle_zero_results,
    normalize_currency,
    detect_potential_sql_injection
)

def test_sanitize_sql_identifier():
    """Test SQL identifier sanitization."""
    # Valid identifiers
    assert sanitize_sql_identifier("valid_identifier") == "valid_identifier"
    assert sanitize_sql_identifier("col1") == "col1"
    
    # Invalid identifiers
    with pytest.raises(ValueError):
        sanitize_sql_identifier("invalid-identifier")
    with pytest.raises(ValueError):
        sanitize_sql_identifier("invalid.identifier")
    with pytest.raises(ValueError):
        sanitize_sql_identifier("1invalid")
    with pytest.raises(ValueError):
        sanitize_sql_identifier("")
    with pytest.raises(ValueError):
        sanitize_sql_identifier("SELECT * FROM users")

def test_parse_timeframe():
    """Test timeframe parsing from natural language."""
    now = datetime.now()
    
    # Test various timeframes
    start, end = parse_timeframe("last 7 days")
    assert (end - start).days == 7
    
    start, end = parse_timeframe("last month")
    assert 28 <= (end - start).days <= 31
    
    start, end = parse_timeframe("last 3 months")
    assert 85 <= (end - start).days <= 95
    
    # Test default
    start, end = parse_timeframe(None, default_days=14)
    assert (end - start).days == 14
    
    # Test invalid format falls back to default
    start, end = parse_timeframe("some invalid string")
    assert (end - start).days == 30  # Default

def test_handle_zero_results():
    """Test handling of zero result scenarios."""
    intent = {
        'time_range': (
            datetime.now() - timedelta(days=30),
            datetime.now()
        ),
        'include_transfers': False
    }
    
    modified = handle_zero_results("test query", intent, [])
    
    # Should suggest a broader time range
    assert 'suggestions' in modified
    assert 'trying a broader range' in modified['suggestions'][0].lower()
    
    # Should try including transfers
    assert modified['include_transfers'] is True
    
    # Test with no time range
    intent_no_time = {'include_transfers': False}
    modified = handle_zero_results("test query", intent_no_time, [])
    assert 'suggestions' in modified

def test_normalize_currency():
    """Test currency normalization."""
    amounts = [
        {'amount': 100, 'currency': 'USD'},
        {'amount': 500, 'currency': 'CLP'},
        {'amount': 200, 'currency': 'EUR'}
    ]
    
    rates = {
        'USD': 950.0,  # 1 USD = 950 CLP
        'EUR': 1050.0,  # 1 EUR = 1050 CLP
        'CLP': 1.0
    }
    
    normalized = normalize_currency(amounts, rates, 'CLP')
    
    # Check USD conversion
    assert normalized[0]['amount'] == 95000.0  # 100 * 950
    assert normalized[0]['original_currency'] == 'USD'
    
    # Check CLP (no conversion)
    assert normalized[1]['amount'] == 500
    assert 'original_currency' not in normalized[1]
    
    # Check EUR conversion
    assert normalized[2]['amount'] == 210000.0  # 200 * 1050
    assert normalized[2]['original_currency'] == 'EUR'
    
    # Test with missing rate
    normalized = normalize_currency([{'amount': 100, 'currency': 'GBP'}], rates, 'CLP')
    assert 'conversion_warning' in normalized[0]
    assert normalized[0]['currency'] == 'GBP'  # Should remain unchanged

def test_detect_potential_sql_injection():
    """Test SQL injection detection."""
    # Safe queries
    assert detect_potential_sql_injection("SELECT * FROM users") is False
    assert detect_potential_sql_injection("show me transactions") is False
    
    # Potential injection attempts
    assert detect_potential_sql_injection("SELECT * FROM users; DROP TABLE users") is True
    assert detect_potential_sql_injection("1' OR '1'='1") is True
    assert detect_potential_sql_injection("admin'--") is True
    assert detect_potential_sql_injection("1; SELECT * FROM users") is True
    assert detect_potential_sql_injection("1; WAITFOR DELAY '0:0:10'--") is True
    
    # Edge cases
    assert detect_potential_sql_injection("") is False
    assert detect_potential_sql_injection(None) is False

def test_error_messages():
    """Test error message generation for various failure scenarios."""
    # Skip this test for now as it requires additional setup
    # We'll implement proper mocking in a separate test file
    pass
