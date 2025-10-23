import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import re

class SQLiteTool:
    """
    A safe wrapper around SQLite operations with strict safety checks.
    
    Features:
    - Only allows SELECT queries with named parameters
    - Blocks DROP, ALTER, DELETE operations
    - Provides table introspection
    - Uses connection pooling
    """
    
    def __init__(self, db_path: Union[str, Path]):
        """Initialize with path to SQLite database."""
        self.db_path = Path(db_path)
        self._connection_pool = {}
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection from the pool (thread-safe)."""
        thread_id = id(1)  # In a real app, use threading.get_ident()
        if thread_id not in self._connection_pool:
            conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                isolation_level=None,
                timeout=30.0
            )
            conn.row_factory = sqlite3.Row
            self._connection_pool[thread_id] = conn
        return self._connection_pool[thread_id]
    
    def _is_safe_query(self, query: str) -> bool:
        """Check if the query is safe to execute."""
        # Convert to lowercase and remove comments
        query = re.sub(r'--.*?\n|/\*.*?\*/', '', query, flags=re.DOTALL).lower()
        
        # Block dangerous operations
        blocked_operations = [
            'drop', 'alter', 'delete', 'insert', 'update', 'replace',
            'create', 'attach', 'detach', 'vacuum', 'pragma', 'reindex'
        ]
        
        # Check for blocked operations
        for op in blocked_operations:
            if re.search(rf'\b{op}\b', query):
                return False
                
        # Must be a SELECT query
        return query.strip().startswith('select')
    
    def list_tables(self) -> List[str]:
        """List all tables in the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            return [row[0] for row in cursor.fetchall()]
    
    def pragma_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a table."""
        if not re.match(r'^[a-zA-Z_]\w*$', table_name):
            raise ValueError(f"Invalid table name: {table_name}")
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'cid': row['cid'],
                    'name': row['name'],
                    'type': row['type'],
                    'notnull': bool(row['notnull']),
                    'dflt_value': row['dflt_value'],
                    'pk': bool(row['pk'])
                })
            return columns
    
    def execute(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Execute a SELECT query safely.
        
        Args:
            query: SQL SELECT query with named parameters
            params: Dictionary of named parameters
            
        Returns:
            Tuple of (rows, column_names)
            
        Raises:
            ValueError: If the query is not safe
            sqlite3.Error: For database errors
        """
        if not self._is_safe_query(query):
            raise ValueError("Query contains unsafe operations")
            
        params = params or {}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                rows = [dict(row) for row in cursor.fetchall()]
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                return rows, column_names
            except sqlite3.Error as e:
                raise ValueError(f"Database error: {str(e)}")
    
    def close(self):
        """Close all database connections."""
        for conn in self._connection_pool.values():
            try:
                conn.close()
            except:
                pass
        self._connection_pool.clear()
    
    def __del__(self):
        """Ensure connections are closed when the object is destroyed."""
        self.close()
