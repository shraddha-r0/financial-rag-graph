"""
Logging Utilities

This module provides logging functionality for tracking query execution,
performance metrics, and results for analysis and debugging.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import uuid

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class QueryLogger:
    """Logs query execution details to a JSONL file."""
    
    def __init__(self, log_dir: Union[str, Path] = "logs"):
        """
        Initialize the query logger.
        
        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"run_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self.logger = logging.getLogger("query_logger")
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Set up file handler for JSON logging."""
        # Remove any existing handlers to avoid duplicates
        self.logger.handlers = []
        
        # Add a file handler for JSON logs
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
    
    def log_query(
        self,
        query: str,
        intent: Dict[str, Any],
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        results: Optional[List[Dict[str, Any]]] = None,
        error: Optional[Exception] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        chart_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a query execution with its results.
        
        Args:
            query: The original user query
            intent: Parsed intent from the intent parser
            sql: The generated SQL query
            params: Parameters used in the SQL query
            results: Query results (limited to first 10 rows if large)
            error: Any error that occurred during execution
            start_time: Timestamp when query started
            end_time: Timestamp when query completed
            chart_path: Path to any generated chart
            metadata: Additional metadata to include in the log
            
        Returns:
            A unique query ID for reference
        """
        query_id = str(uuid.uuid4())
        end_time = end_time or time.time()
        start_time = start_time or (end_time - 0.1)  # Default to 100ms if not provided
        
        # Limit result size for logging
        result_sample = None
        if results is not None:
            result_sample = results[:10]  # Only log first 10 rows
            if len(results) > 10:
                result_sample.append({"_info": f"... {len(results) - 10} more rows not shown"})
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query_id": query_id,
            "query": query,
            "intent": intent,
            "sql": sql,
            "params": params or {},
            "execution_time_ms": int((end_time - start_time) * 1000),
            "result_count": len(results) if results is not None else 0,
            "error": str(error) if error else None,
            "chart_generated": chart_path is not None,
            "chart_path": chart_path,
            "metadata": metadata or {}
        }
        
        # Add result sample if available
        if result_sample is not None:
            log_entry["result_sample"] = result_sample
        
        # Log to JSONL file
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, default=str) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write to log file: {e}")
        
        return query_id
    
    def get_query_log(self, query_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific query log by its ID.
        
        Args:
            query_id: The ID of the query to retrieve
            
        Returns:
            The log entry as a dictionary, or None if not found
        """
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get('query_id') == query_id:
                        return entry
        except FileNotFoundError:
            pass
        return None
    
    def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent query logs.
        
        Args:
            limit: Maximum number of recent queries to return
            
        Returns:
            List of recent query logs, most recent first
        """
        entries = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # Read last 'limit' lines efficiently for large files
                lines = []
                for line in f:
                    lines.append(line)
                    if len(lines) > limit:
                        lines.pop(0)
                
                # Parse the lines
                for line in lines:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        
        # Return in reverse chronological order
        return sorted(entries, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
