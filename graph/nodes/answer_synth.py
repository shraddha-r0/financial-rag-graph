"""
Answer Synthesis Node

This module formats query results into a clear, informative markdown response.
It includes key metrics, comparisons, and chart references when available.
Handles various edge cases and provides helpful error messages.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class Answer:
    """Container for the formatted answer and related artifacts."""
    markdown: str
    chart_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AnswerSynthesizer:
    """Formats query results into a human-readable answer."""
    
    def __init__(self, currency: str = "CLP"):
        """
        Initialize the answer synthesizer.
        
        Args:
            currency: Default currency to use for monetary values
        """
        self.currency = currency
    
    def format_currency(self, amount: float) -> str:
        """Format a monetary value with the appropriate currency symbol."""
        if self.currency == "USD":
            return f"${amount:,.2f}"
        elif self.currency == "EUR":
            return f"€{amount:,.2f}"
        else:  # Default to CLP
            return f"${int(amount):,} {self.currency}"
    
    def format_number(self, number: float) -> str:
        """Format a number with appropriate precision."""
        if number == 0:
            return "0"
        if abs(number) < 0.01:
            return f"{number:.4f}"
        if abs(number) < 1:
            return f"{number:.3f}"
        if abs(number) < 10:
            return f"{number:.2f}"
        if abs(number) < 1000:
            return f"{int(round(number, 0)):,}"
        return f"{number:,.0f}"
    
    def format_percentage(self, value: float) -> str:
        """Format a percentage value."""
        return f"{value:+.1f}%"
    
    def format_date_range(self, start_date: str, end_date: str) -> str:
        """Format a date range in a human-readable way."""
        try:
            start = datetime.fromisoformat(start_date) if start_date else None
            end = datetime.fromisoformat(end_date) if end_date else None
            
            if start and end:
                if start.year == end.year:
                    if start.month == end.month:
                        return f"{start.strftime('%b %d')}-{end.strftime('%d, %Y')}"
                    return f"{start.strftime('%b %d')}-{end.strftime('%b %d, %Y')}"
                return f"{start.strftime('%b %d, %Y')} to {end.strftime('%b %d, %Y')}"
            elif start:
                return f"since {start.strftime('%b %d, %Y')}"
            elif end:
                return f"until {end.strftime('%b %d, %Y')}"
        except (ValueError, AttributeError):
            pass
        return "the specified period"
    
    def synthesize_answer(
        self,
        query: str,
        results: Optional[List[Dict[str, Any]]],
        metadata: Dict[str, Any],
        chart_path: Optional[str] = None
    ) -> Answer:
        """
        Synthesize a human-readable answer from query results.
        
        Args:
            query: The original user query
            results: The query results (None if there was an error)
            metadata: Additional metadata about the query
            chart_path: Optional path to a generated chart
            
        Returns:
            An Answer object with the formatted markdown and metadata
        """
        # Handle error cases first
        if 'error' in metadata:
            return self._format_error_response(query, metadata)
            
        # Handle empty results
        if not results:
            return self._format_empty_results(query, metadata)
            
        # Handle specific intent types
        intent = metadata.get("intent", {})
        intent_type = intent.get("intent_type")
        
        if intent_type == "spending_by_category":
            return self._format_spending_by_category(query, results, metadata, chart_path)
        elif intent_type == "spending_over_time":
            return self._format_spending_over_time(query, results, metadata, chart_path)
        elif intent_type == "top_items":
            return self._format_top_items(query, results, metadata, chart_path)
        elif intent_type == "comparison":
            return self._format_comparison(query, results, metadata, chart_path)
        else:
            # Default formatting
            return self._format_generic_response(query, results, metadata, chart_path)
        """
        Synthesize a human-readable answer from query results.
        
        Args:
            query: The original user query
            results: The query results
            metadata: Additional metadata about the query
            chart_path: Optional path to a generated chart image
            
        Returns:
            An Answer object with the formatted markdown and metadata
        """
        intent = metadata.get("intent", {})
        time_range = intent.get("time_range", (None, None))
        is_comparison = intent.get("is_comparison", False)
        
    def _format_error_response(self, query: str, metadata: Dict[str, Any]) -> Answer:
        """Format an error response."""
        error_msg = metadata.get('error', 'An unknown error occurred')
        error_type = metadata.get('error_type', 'execution_error')
        
        # Special handling for common error types
        if 'syntax error' in str(error_msg).lower():
            message = f"## ❌ Invalid Query Syntax\n\nI couldn't process your query due to a syntax error: `{error_msg}`"
        elif 'no such table' in str(error_msg).lower():
            message = "## ❌ Data Unavailable\n\nThe requested data is not available in the current dataset."
        elif 'ambiguous' in str(error_msg).lower():
            message = f"## ❓ Ambiguous Request\n\n{error_msg}\n\nPlease provide more specific details."
        else:
            message = f"## ❌ Error Processing Request\n\n{error_msg}"
        
        return Answer(
            markdown=message,
            metadata={
                "query": query,
                "error": str(error_msg),
                "error_type": error_type,
                **{k: v for k, v in metadata.items() if k != 'error'}
            }
        )
    
    def _format_empty_results(self, query: str, metadata: Dict[str, Any]) -> Answer:
        """Format a response when no results are found."""
        intent = metadata.get('intent', {})
        time_range = intent.get('time_range', (None, None))
        
        message = ["## 🔍 No Results Found"]
        
        # Add time range context
        if time_range[0] and time_range[1]:
            message.append(f"No data found for the period: {self.format_date_range(*time_range)}.")
        else:
            message.append("No matching data found.")
        
        # Add suggestions if available
        suggestions = metadata.get('suggestions', [])
        if suggestions:
            message.append("\n**Suggestions:**")
            message.extend(f"- {s}" for s in suggestions)
        else:
            message.extend([
                "",
                "### Try these suggestions:",
                "- Broaden your time range",
                "- Check your spelling or try different keywords",
                "- Include refunds or transfers if applicable"
            ])
        
        return Answer(
            markdown="\n".join(message),
            metadata={
                "query": query,
                "result_count": 0,
                **metadata
            })


def generate_answer(
    results: List[Dict[str, Any]],
    intent: Dict[str, Any],
    chart_spec: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a natural language answer from query results.
    
    Args:
        results: List of result rows as dictionaries
        intent: The parsed intent from the query
        chart_spec: Optional chart specification if a chart was generated
        
    Returns:
        A markdown-formatted string with the answer
    """
    if not results:
        return "No results found matching your query."
    
    synthesizer = AnswerSynthesizer()
    
    # Prepare metadata
    metadata = {
        'intent': intent,
        'result_count': len(results),
        'columns': list(results[0].keys()) if results else []
    }
    
    # Generate the answer
    answer = synthesizer.synthesize_answer(
        query=intent.get('original_query', ''),
        results=results,
        metadata=metadata,
        chart_path=chart_spec.get('path') if chart_spec else None
    )
    
    return answer.markdown

    def _format_spending_by_category(self, query: str, results: List[Dict[str, Any]], 
                                  metadata: Dict[str, Any], chart_path: Optional[str]) -> Answer:
        """Format spending by category results."""
        parts = ["## 💰 Spending by Category"]
        
        # Add total spending
        total = sum(row.get('total', 0) for row in results)
        parts.append(f"**Total Spending:** {self.format_currency(total)}")
        
        # Add top categories
        if results:
            parts.append("\n### Top Categories:")
            for i, row in enumerate(results[:5], 1):
                category = row.get('category', 'Uncategorized')
                amount = row.get('total', 0)
                percentage = (amount / total * 100) if total > 0 else 0
                parts.append(
                    f"{i}. **{category}**: {self.format_currency(amount)} "
                    f"({percentage:.1f}%)"
                )
        
        return self._finalize_answer(query, results, metadata, chart_path, parts)
    
    def _format_spending_over_time(self, query: str, results: List[Dict[str, Any]], 
                                 metadata: Dict[str, Any], chart_path: Optional[str]) -> Answer:
        """Format spending over time results."""
        parts = ["## 📈 Spending Over Time"]
        
        if results:
            # Add summary stats
            amounts = [row.get('total', 0) for row in results]
            total = sum(amounts)
            avg = total / len(amounts) if amounts else 0
            
            parts.extend([
                f"**Total Spending:** {self.format_currency(total)}",
                f"**Average per Period:** {self.format_currency(avg)}",
                f"**Number of Periods:** {len(results)}"
            ])
            
            # Add trend information if we have multiple periods
            if len(results) > 1:
                first = results[0].get('total', 0)
                last = results[-1].get('total', 0)
                if first > 0:
                    pct_change = ((last - first) / first) * 100
                    trend = "▲" if pct_change > 0 else "▼"
                    parts.append(
                        f"**Trend:** {trend} {abs(pct_change):.1f}% "
                        f"({self.format_currency(first)} → {self.format_currency(last)})"
                    )
        
        return self._finalize_answer(query, results, metadata, chart_path, parts)
    
    def _format_top_items(self, query: str, results: List[Dict[str, Any]], 
                         metadata: Dict[str, Any], chart_path: Optional[str]) -> Answer:
        """Format top items results."""
        intent = metadata.get('intent', {})
        limit = intent.get('limit', 10)
        
        parts = [f"## 🏆 Top {min(limit, len(results))} Items"]
        
        if results:
            total = sum(row.get('total', 0) for row in results)
            parts.append(f"**Total:** {self.format_currency(total)}")
            
            parts.append("\n### Items:")
            for i, row in enumerate(results[:limit], 1):
                # Find the first non-standard column as the item name
                item_col = next(
                    (k for k in row.keys() 
                     if k not in {'total', 'sum', 'count', 'amount'}),
                    'item'
                )
                item_name = row.get(item_col, 'Unknown')
                amount = row.get('total', 0)
                percentage = (amount / total * 100) if total > 0 else 0
                
                parts.append(
                    f"{i}. **{item_name}**: {self.format_currency(amount)} "
                    f"({percentage:.1f}%)"
                )
        
        return self._finalize_answer(query, results, metadata, chart_path, parts)
    
    def _format_comparison(self, query: str, results: List[Dict[str, Any]], 
                          metadata: Dict[str, Any], chart_path: Optional[str]) -> Answer:
        """Format comparison results."""
        parts = ["## 🔄 Comparison"]
        
        if results and len(results) > 0:
            row = results[0]
            current = row.get('current_value', 0)
            previous = row.get('previous_value', 0)
            difference = row.get('difference', 0)
            pct_change = row.get('pct_change', 0)
            
            if previous == 0:
                parts.append("No previous data available for comparison.")
            else:
                direction = "up" if difference >= 0 else "down"
                emoji = "📈" if difference >= 0 else "📉"
                
                parts.extend([
                    f"**Current Period:** {self.format_currency(current)}",
                    f"**Previous Period:** {self.format_currency(previous)}",
                    f"**Change ({direction}):** {emoji} {self.format_currency(abs(difference))} "
                    f"({abs(pct_change):.1f}%)"
                ])
        
        return self._finalize_answer(query, results, metadata, chart_path, parts)
    
    def _format_generic_response(self, query: str, results: List[Dict[str, Any]], 
                               metadata: Dict[str, Any], chart_path: Optional[str]) -> Answer:
        """Format a generic response for unhandled intent types."""
        parts = ["## 📊 Query Results"]
        
        if results:
            # Show a preview of the results
            parts.append(f"Found {len(results)} results:")
            
            # Get column names, excluding internal ones
            if results:
                columns = [
                    k for k in results[0].keys()
                    if not k.startswith('_')
                ][:5]  # Limit to first 5 columns
                
                # Create a simple table
                parts.append("\n| " + " | ".join(columns) + " |")
                parts.append("|" + "|".join(["---"] * len(columns)) + "|")
                
                for row in results[:5]:  # Limit to first 5 rows
                    parts.append("| " + " | ".join(
                        str(row.get(col, ''))[:30]  # Limit cell width
                        for col in columns
                    ) + " |")
                
                if len(results) > 5:
                    parts.append(f"\n... and {len(results) - 5} more rows")
        
        return self._finalize_answer(query, results, metadata, chart_path, parts)
    
    def _finalize_answer(self, query: str, results: List[Dict[str, Any]], 
                        metadata: Dict[str, Any], chart_path: Optional[str],
                        parts: List[str]) -> Answer:
        """Finalize the answer with common elements."""
        intent = metadata.get('intent', {})
        time_range = intent.get('time_range', (None, None))
        
        # Add chart if available
        if chart_path:
            parts.append(f"\n![Chart]({chart_path})")
        
        # Add caveats and metadata
        caveats = [
            f"Assumes currency = {self.currency} unless otherwise specified.",
            f"Data from {self.format_date_range(*time_range)}."
        ]
        
        # Add any warnings from metadata
        if 'warnings' in metadata and metadata['warnings']:
            caveats.append("**Note:** " + "; ".join(metadata['warnings']))
        
        parts.append("\n" + "\n".join(["> " + c for c in caveats if c]))
        
        return Answer(
            markdown="\n\n".join(parts),
            chart_path=chart_path,
            metadata={
                "query": query,
                "result_count": len(results) if results is not None else 0,
                **{k: v for k, v in metadata.items() if k != 'warnings'}
            }
        )
    
    def _extract_main_metric(
        self, 
        results: List[Dict[str, Any]], 
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """Extract and format the main metric from the results."""
        if not results:
            return None
            
        intent = metadata.get("intent", {})
        metrics = intent.get("metrics", ["amount"])
        
        # For now, just handle the first metric
        metric = metrics[0] if metrics else "amount"
        
        # Calculate total if it makes sense
        if metric in ["amount", "sum"] and results:
            total = sum(row.get("total", row.get("sum", 0)) for row in results)
            return f"Total: {self.format_currency(total)}"
        
        # For top items, show the top item
        if intent.get("intent_type") == "top_items" and results:
            top_item = results[0]
            value = top_item.get("total", top_item.get("sum", 0))
            return f"Top {list(top_item.keys())[0]}: {self.format_currency(value)}"
            
        return None
    
    def _format_comparison(
        self,
        results: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """Format comparison information if available."""
        if not results or "current_value" not in results[0] or "previous_value" not in results[0]:
            return ""
            
        current = results[0].get("current_value", 0)
        previous = results[0].get("previous_value", 0)
        difference = results[0].get("difference", 0)
        pct_change = results[0].get("pct_change", 0)
        
        if previous == 0:
            return "No previous data for comparison."
            
        direction = "up" if difference >= 0 else "down"
        abs_pct = abs(pct_change)
        
        return (
            f"**Change from previous period:** {self.format_currency(abs(difference))} "
            f"({self.format_percentage(abs_pct)}) {direction}"
        )
    
    def _create_data_summary(
        self,
        results: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """Create a summary of the data points."""
        if not results:
            return ""
            
        intent = metadata.get("intent", {})
        intent_type = intent.get("intent_type")
        
        if intent_type == "spending_by_category" and len(results) > 0:
            top_categories = results[:3]
            lines = ["**Top categories:**"]
            for i, row in enumerate(top_categories, 1):
                category = row.get("category", "Unknown")
                amount = row.get("total", row.get("sum", 0))
                lines.append(f"{i}. {category}: {self.format_currency(amount)}")
            return "\n".join(lines)
            
        elif intent_type == "top_items" and len(results) > 0:
            lines = ["**Top items:**"]
            for i, row in enumerate(results, 1):
                # Get the first non-id, non-metric column as the item name
                item_col = next((k for k in row.keys() if k not in {"id", "sum", "total", "count", "average"}), None)
                if item_col:
                    item_name = row[item_col]
                    amount = row.get("total", row.get("sum", 0))
                    lines.append(f"{i}. {item_name}: {self.format_currency(amount)}")
            return "\n".join(lines)
            
        return ""
