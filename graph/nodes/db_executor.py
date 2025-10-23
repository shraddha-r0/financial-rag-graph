"""
DB Executor Node

This module executes SQL queries against the database using the SQLite tool.
It handles query execution, result formatting, and error handling.
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
import logging
from pathlib import Path

from mcp_tools.sqlite_tool import SQLiteTool

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Container for query execution results."""
    rows: List[Dict[str, Any]]
    columns: List[str]
    rowcount: int
    sql: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

class DBExecutor:
    """Executes SQL queries and returns formatted results."""
    
    def __init__(self, db_path: str):
        """
        Initialize the DB executor.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.sqlite_tool = SQLiteTool(str(self.db_path.absolute()))
    
    def execute_query(
        self, 
        sql: str, 
        params: Optional[Dict[str, Any]] = None,
        fetch_all: bool = True
    ) -> QueryResult:
        """
        Execute a SQL query and return the results.
        
        Args:
            sql: The SQL query to execute
            params: Dictionary of parameters for the query
            fetch_all: If True, fetch all rows; if False, fetch one row
            
        Returns:
            QueryResult containing the results or error information
        """
        params = params or {}
        
        try:
            # Execute the query
            rows, columns = self.sqlite_tool.execute(sql, params)
            
            # Convert rows to dictionaries for easier handling
            result_rows = []
            for row in rows:
                result_rows.append(dict(zip(columns, row)))
            
            return QueryResult(
                rows=result_rows,
                columns=columns,
                rowcount=len(result_rows),
                sql=sql,
                params=params
            )
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return QueryResult(
                rows=[],
                columns=[],
                rowcount=0,
                sql=sql,
                params=params,
                error=e
            )
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """
        Get the schema for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary mapping column names to their types
        """
        try:
            table_info = self.sqlite_tool.pragma_table_info(table_name)
            return {col['name']: col['type'] for col in table_info}
        except Exception as e:
            logger.error(f"Error getting schema for table {table_name}: {e}")
            return {}
    
    def list_tables(self) -> List[str]:
        """
        List all tables in the database.
        
        Returns:
            List of table names
        """
        try:
            return self.sqlite_tool.list_tables()
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return []

def execute_query(
    sql: str, 
    db_path: str,
    params: Optional[Dict[str, Any]] = None,
    fetch_all: bool = True
) -> QueryResult:
    """
    Execute a SQL query and return the results.
    
    This is a convenience function that creates a DBExecutor instance
    and executes the query.
    
    Args:
        sql: The SQL query to execute
        db_path: Path to the SQLite database file
        params: Optional parameters for the query
        fetch_all: Whether to fetch all results or just the first row
        
    Returns:
        QueryResult containing the results
    """
    executor = DBExecutor(db_path)
    return executor.execute_query(sql, params=params, fetch_all=fetch_all)


# Example usage:
if __name__ == "__main__":
    # Initialize with your database path
    db_path = "path/to/your/database.db"
    executor = DBExecutor(db_path)
    
    # Example query
    result = executor.execute_query(
        "SELECT * FROM transactions WHERE date >= :start_date LIMIT 10",
        {"start_date": "2023-01-01"}
    )
    
    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Columns: {result.columns}")
        print(f"Found {result.rowcount} rows")
        for row in result.rows[:5]:  # Print first 5 rows
            print(row)
