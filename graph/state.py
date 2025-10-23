from typing import List, Dict, Optional, Any, Union, Literal, TypedDict
from pydantic import BaseModel, Field, validator, root_validator
from datetime import date, datetime, timedelta
from enum import Enum
import re
from pathlib import Path

# Database configuration
DB_PATH = Path("data/clean/finances.db")

class TimeRange(BaseModel):
    """Represents a time range for filtering data."""
    start_date: Optional[date] = Field(
        None,
        description="Start date of the time range (inclusive)"
    )
    end_date: Optional[date] = Field(
        None,
        description="End date of the time range (inclusive)"
    )
    label: Optional[str] = Field(
        None,
        description="Human-readable label for the time range (e.g., 'last_quarter', 'jan_2025')"
    )

    @classmethod
    def from_string(cls, time_str: str) -> 'TimeRange':
        """Create a TimeRange from a natural language string."""
        time_str = time_str.lower().strip()
        today = date.today()
        
        # Handle relative dates
        if time_str == 'today':
            return cls(start_date=today, end_date=today, label="today")
        elif time_str == 'yesterday':
            yesterday = today - timedelta(days=1)
            return cls(start_date=yesterday, end_date=yesterday, label="yesterday")
        elif time_str == 'this month':
            start = today.replace(day=1)
            return cls(start_date=start, end_date=today, label="this_month")
        elif time_str == 'last month':
            if today.month == 1:
                start = date(today.year - 1, 12, 1)
                end = date(today.year - 1, 12, 31)
            else:
                start = today.replace(month=today.month - 1, day=1)
                end = (start.replace(day=28) + timedelta(days=4))  # Last day of month
                end = end.replace(day=1) - timedelta(days=1)
            return cls(start_date=start, end_date=end, label="last_month")
        
        # Handle month-year format (e.g., 'january 2025')
        month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        for month_name, month_num in month_map.items():
            if month_name in time_str:
                # Extract year (default to current year if not specified)
                year_match = re.search(r'\b(20\d{2})\b', time_str)
                year = int(year_match.group(1)) if year_match else today.year
                
                # Calculate start and end dates for the month
                if today.year == year and today.month == month_num:
                    # Current month (up to today)
                    start_date = today.replace(day=1)
                    end_date = today
                else:
                    # Past or future month
                    if month_num == 12:
                        end_date = date(year, 12, 31)
                    else:
                        end_date = date(year, month_num + 1, 1) - timedelta(days=1)
                    start_date = date(year, month_num, 1)
                
                return cls(
                    start_date=start_date,
                    end_date=end_date,
                    label=f"{month_name}_{year}"
                )
        
        # If no pattern matched, return a default range
        return cls(
            start_date=today - timedelta(days=30),
            end_date=today,
            label="last_30_days"
        )

class IntentType(str, Enum):
    """Types of intents that can be extracted from user queries."""
    SPENDING_BY_CATEGORY = "spending_by_category"
    SPENDING_OVER_TIME = "spending_over_time"
    COMPARISON = "comparison"
    TOP_ITEMS = "top_items"
    TREND = "trend"
    BREAKDOWN = "breakdown"
    UNKNOWN = "unknown"

class TableType(str, Enum):
    """Supported database tables."""
    EXPENSES = "expenses"
    INCOMES = "incomes"
    EXPENSES_MONTHLY = "v_expenses_monthly"
    INCOMES_MONTHLY = "v_incomes_monthly"
    META = "meta"

class UserQuery(BaseModel):
    """Represents a user's natural language query with extracted intents."""
    text: str = Field(..., description="The original query text")
    intent: IntentType = Field(
        default=IntentType.UNKNOWN,
        description="Detected intent of the query"
    )
    table: TableType = Field(
        default=TableType.EXPENSES,
        description="Which table to query (expenses or incomes)"
    )
    time_range: Optional[TimeRange] = Field(
        None,
        description="Extracted time range"
    )
    categories: List[str] = Field(
        default_factory=list,
        description="Relevant expense categories"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags to filter by"
    )
    metrics: List[str] = Field(
        default_factory=lambda: ["total_spend"],
        description="Metrics to compute (total_spend, avg_spend, transaction_count)"
    )
    dimensions: List[str] = Field(
        default_factory=list,
        description="Dimensions to group by (category, day, month, year)"
    )
    limit: Optional[int] = Field(
        None,
        description="Maximum number of results to return"
    )
    comparison_windows: List[TimeRange] = Field(
        default_factory=list,
        description="For comparison queries"
    )

    @validator('metrics', each_item=True)
    def validate_metric(cls, v):
        valid_metrics = METRICS.keys()
        if v not in valid_metrics:
            raise ValueError(f"Invalid metric: {v}. Must be one of {list(valid_metrics)}")
        return v

    @validator('dimensions', each_item=True)
    def validate_dimension(cls, v):
        valid_dims = DIMENSIONS.keys()
        if v not in valid_dims:
            raise ValueError(f"Invalid dimension: {v}. Must be one of {list(valid_dims)}")
        return v

class SQLPlan(BaseModel):
    """Represents a SQL query plan with parameters."""
    query: str = Field(..., description="The SQL query to execute")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the query"
    )
    required_tables: List[TableType] = Field(
        default_factory=list,
        description="Tables needed for the query"
    )
    is_safe: bool = Field(
        default=False,
        description="Whether the query is safe to execute"
    )
    
    @classmethod
    def from_user_query(cls, user_query: UserQuery) -> 'SQLPlan':
        """Generate a SQLPlan from a UserQuery."""
        # Start with basic query parts
        select_columns = []
        group_by = []
        where_conditions = []
        params = {}
        
        # Add dimensions to SELECT and GROUP BY
        for dim in user_query.dimensions:
            select_columns.append(DIMENSIONS[dim])
            # Extract the base column name (before 'as' if present)
            base_col = DIMENSIONS[dim].split(' as ')[0].strip()
            group_by.append(base_col)
        
        # Add metrics to SELECT
        for metric in user_query.metrics:
            select_columns.append(METRICS[metric])
        
        # Build WHERE conditions
        if user_query.time_range:
            if user_query.time_range.start_date:
                where_conditions.append("date >= :start_date")
                params["start_date"] = user_query.time_range.start_date
            if user_query.time_range.end_date:
                where_conditions.append("date <= :end_date")
                params["end_date"] = user_query.time_range.end_date
        
        if user_query.categories:
            placeholders = ", ".join(f":category_{i}" for i in range(len(user_query.categories)))
            where_conditions.append(f"category IN ({placeholders})")
            params.update({f"category_{i}": cat for i, cat in enumerate(user_query.categories)})
        
        if user_query.tags:
            # For tags, we need to check if any of the tags is in the tags column
            tag_conditions = []
            for i, tag in enumerate(user_query.tags):
                tag_conditions.append("tags LIKE :tag_" + str(i))
                params[f"tag_{i}"] = f"%{tag}%"
            where_conditions.append("(" + " OR ".join(tag_conditions) + ")")
        
        # Build the final query
        table_name = user_query.table.value
        query_parts = ["SELECT", ",\n    ".join(select_columns)]
        query_parts.append(f"FROM {table_name}")
        
        if where_conditions:
            query_parts.append("WHERE " + " AND ".join(where_conditions))
        
        if group_by:
            query_parts.append(f"GROUP BY {', '.join(group_by)}")
            
            # Add ORDER BY for the first dimension (if any)
            if user_query.dimensions:
                first_dim = user_query.dimensions[0]
                query_parts.append(f"ORDER BY {DIMENSIONS[first_dim]}")
        
        if user_query.limit:
            query_parts.append(f"LIMIT {user_query.limit}")
        
        query = "\n".join(query_parts) + ";"
        
        return cls(
            query=query,
            params=params,
            required_tables=[user_query.table],
            is_safe=True  # We've validated all inputs
        )

class ResultFrame(BaseModel):
    """Wrapper for query results that can be converted to different formats."""
    data: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="The result rows as dictionaries"
    )
    columns: List[str] = Field(
        default_factory=list,
        description="Column names"
    )
    rowcount: int = Field(
        default=0,
        description="Number of rows returned"
    )
    sql: Optional[str] = Field(
        None,
        description="The SQL query that generated these results"
    )
    
    def to_pandas(self) -> 'pd.DataFrame':
        """Convert results to a pandas DataFrame."""
        import pandas as pd
        return pd.DataFrame(self.data, columns=self.columns)
    
    def to_markdown(self, floatfmt: str = ".2f") -> str:
        """Convert results to a markdown table."""
        import pandas as pd
        df = self.to_pandas()
        
        # Format numeric columns
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            if df[col].dtype == 'float64':
                df[col] = df[col].apply(lambda x: f"{x:{floatfmt}}" if pd.notnull(x) else "")
        
        return df.to_markdown(index=False, tablefmt="github")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to a dictionary."""
        return {
            "columns": self.columns,
            "data": self.data,
            "rowcount": self.rowcount,
            "sql": self.sql
        }
    
    @classmethod
    def from_sql(
        cls,
        conn: 'sqlite3.Connection',
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> 'ResultFrame':
        """Create a ResultFrame by executing a SQL query."""
        import sqlite3
        from typing import Any, Dict, List, Optional
        
        if params is None:
            params = {}
        
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return cls(
                data=data,
                columns=columns,
                rowcount=len(data),
                sql=query
            )
        except sqlite3.Error as e:
            raise ValueError(f"SQL Error: {e}")
        finally:
            cursor.close()

class ChartType(str, Enum):
    """Supported chart types."""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"


class ChartSpec(BaseModel):
    """Specification for generating a chart."""
    chart_type: ChartType = Field(
        default=ChartType.BAR,
        description="Type of chart to generate"
    )
    x_axis: str = Field(
        ...,
        description="Column to use for x-axis"
    )
    y_axis: str = Field(
        ...,
        description="Column to use for y-axis"
    )
    title: Optional[str] = Field(
        None,
        description="Chart title (auto-generated if None)"
    )
    x_label: Optional[str] = Field(
        None,
        description="X-axis label (defaults to x_axis column name)"
    )
    y_label: Optional[str] = Field(
        None,
        description="Y-axis label (defaults to y_axis column name)"
    )
    width: int = Field(
        800,
        description="Chart width in pixels"
    )
    height: int = Field(
        400,
        description="Chart height in pixels"
    )
    color_scheme: str = Field(
        "category10",
        description="Color scheme to use for the chart"
    )
    
    def generate(
        self,
        data: 'pd.DataFrame',
        output_path: Optional[Union[str, Path]] = None
    ) -> Optional[bytes]:
        """Generate a chart and optionally save it to a file.
        
        Args:
            data: The data to plot
            output_path: If provided, save the chart to this path
            
        Returns:
            The chart as bytes if output_path is None, otherwise None
        """
        import plotly.express as px
        import plotly.io as pio
        
        # Set default labels if not provided
        title = self.title or f"{self.y_axis} by {self.x_axis}"
        x_label = self.x_label or self.x_axis
        y_label = self.y_label or self.y_axis
        
        # Create the appropriate chart type
        if self.chart_type == ChartType.BAR:
            fig = px.bar(
                data,
                x=self.x_axis,
                y=self.y_axis,
                title=title,
                labels={self.x_axis: x_label, self.y_axis: y_label},
                color=self.x_axis if len(data) > 1 else None,
                color_discrete_sequence=px.colors.qualitative[self.color_scheme]
            )
        elif self.chart_type == ChartType.LINE:
            fig = px.line(
                data,
                x=self.x_axis,
                y=self.y_axis,
                title=title,
                labels={self.x_axis: x_label, self.y_axis: y_label},
                color=self.x_axis if len(data) > 1 else None,
                line_shape="spline"
            )
        elif self.chart_type == ChartType.PIE:
            fig = px.pie(
                data,
                names=self.x_axis,
                values=self.y_axis,
                title=title,
                color_discrete_sequence=px.colors.qualitative[self.color_scheme]
            )
        elif self.chart_type == ChartType.AREA:
            fig = px.area(
                data,
                x=self.x_axis,
                y=self.y_axis,
                title=title,
                labels={self.x_axis: x_label, self.y_axis: y_label}
            )
        elif self.chart_type == ChartType.SCATTER:
            fig = px.scatter(
                data,
                x=self.x_axis,
                y=self.y_axis,
                title=title,
                labels={self.x_axis: x_label, self.y_axis: y_label}
            )
        else:
            raise ValueError(f"Unsupported chart type: {self.chart_type}")
        
        # Update layout
        fig.update_layout(
            width=self.width,
            height=self.height,
            margin=dict(l=50, r=50, t=50, b=50),
            showlegend=len(data) > 1
        )
        
        # Save or return the chart
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if output_path.suffix == '.html':
                fig.write_html(output_path)
            else:
                fig.write_image(output_path)
            return None
        else:
            return pio.to_image(fig, format='png')

class Answer(BaseModel):
    """Final answer to be presented to the user."""
    markdown: str = Field(
        ...,
        description="Markdown formatted answer"
    )
    artifacts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of artifacts (charts, tables, etc.) with their metadata"
    )
    source_data: Optional[ResultFrame] = Field(
        None,
        description="The data used to generate this answer"
    )
    
    def add_chart(
        self,
        chart_spec: ChartSpec,
        data: 'pd.DataFrame',
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """Add a chart to the answer.
        
        Args:
            chart_spec: The chart specification
            data: The data to plot
            title: Optional title for the chart
            description: Optional description of the chart
            
        Returns:
            The path to the generated chart
        """
        import uuid
        from pathlib import Path
        
        # Create a unique filename for the chart
        chart_id = str(uuid.uuid4())[:8]
        chart_path = Path(f"artifacts/charts/chart_{chart_id}.png")
        
        # Generate the chart
        chart_spec.generate(data, output_path=chart_path)
        
        # Add to artifacts
        self.artifacts.append({
            "type": "chart",
            "path": str(chart_path),
            "title": title or f"Chart {len(self.artifacts) + 1}",
            "description": description or "",
            "spec": chart_spec.dict()
        })
        
        # Update markdown with a reference to the chart
        self.markdown += f"\n\n![{title or 'Chart'}]({chart_path})"
        
        return str(chart_path)
    
    def add_table(
        self,
        data: 'pd.DataFrame',
        title: Optional[str] = None,
        description: Optional[str] = None,
        max_rows: int = 10
    ) -> str:
        """Add a table to the answer.
        
        Args:
            data: The data to display as a table
            title: Optional title for the table
            description: Optional description of the table
            max_rows: Maximum number of rows to show (truncate if necessary)
            
        Returns:
            The markdown for the table
        """
        import uuid
        from pathlib import Path
        
        # Truncate data if necessary
        if len(data) > max_rows:
            data = data.head(max_rows)
        
        # Convert to markdown
        table_md = data.to_markdown(index=False)
        
        # Add to artifacts
        table_id = str(uuid.uuid4())[:8]
        table_path = Path(f"artifacts/tables/table_{table_id}.md")
        table_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(table_path, 'w') as f:
            if title:
                f.write(f"# {title}\n\n")
            if description:
                f.write(f"{description}\n\n")
            f.write(table_md)
        
        self.artifacts.append({
            "type": "table",
            "path": str(table_path),
            "title": title or f"Table {len([a for a in self.artifacts if a['type'] == 'table']) + 1}",
            "description": description or "",
            "row_count": len(data),
            "column_count": len(data.columns)
        })
        
        # Update markdown with the table
        if title:
            self.markdown += f"\n\n### {title}\n"
        if description:
            self.markdown += f"{description}\n\n"
        self.markdown += table_md
        
        return table_md

class GraphState(BaseModel):
    """The state that flows through the LangGraph."""
    user_query: Optional[UserQuery] = Field(
        None,
        description="The parsed user query"
    )
    sql_plan: Optional[SQLPlan] = Field(
        None,
        description="The generated SQL query plan"
    )
    results: Optional[ResultFrame] = Field(
        None,
        description="Query results"
    )
    chart_spec: Optional[ChartSpec] = Field(
        None,
        description="Chart specification"
    )
    answer: Optional[Answer] = Field(
        None,
        description="Final answer to the user"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if something went wrong"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the state"
    )
    
    def has_error(self) -> bool:
        """Check if there's an error in the state."""
        return self.error is not None
    
    def update_metadata(self, **kwargs) -> 'GraphState':
        """Update the metadata dictionary with new key-value pairs."""
        self.metadata.update(kwargs)
        return self

# Common metrics and dimensions for reference
METRICS = {
    "total_spend": "SUM(expense) as total_spend",
    "avg_spend": "AVG(expense) as avg_spend",
    "transaction_count": "COUNT(*) as transaction_count",
    "max_spend": "MAX(expense) as max_spend",
    "min_spend": "MIN(expense) as min_spend"
}

DIMENSIONS = {
    "category": "category",
    "tags": "tags",
    "day": "day",
    "day_of_week": "strftime('%w', date) as day_of_week",
    "day_name": "day as day_name",
    "month": "strftime('%Y-%m', date) as month",
    "month_name": "strftime('%B', date) as month_name",
    "year": "strftime('%Y', date) as year",
    "date": "date"
}

# Common categories for categorization
CATEGORIES = [
    "Food & Drinks",
    "Shopping",
    "Transportation",
    "Home",
    "Bills & Utilities",
    "Entertainment",
    "Health",
    "Education",
    "Travel",
    "Groceries",
    "Others"
]

# Common tags for better filtering
COMMON_TAGS = [
    "coffee", "restaurant", "groceries", "utilities", 
    "rent", "transport", "entertainment", "shopping",
    "health", "travel", "education", "subscription"
]

# Time-based groupings
TIME_GROUPINGS = {
    "daily": "%Y-%m-%d",
    "weekly": "%Y-W%W",
    "monthly": "%Y-%m",
    "quarterly": "%Y-Q%q",
    "yearly": "%Y"
}

# Default chart configurations
DEFAULT_CHART_CONFIG = {
    "width": 800,
    "height": 400,
    "margin": {"l": 50, "r": 50, "t": 50, "b": 50},
    "color_scale": "Viridis"
}