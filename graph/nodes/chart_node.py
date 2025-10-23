"""
Chart Generation Node

This module generates visualizations (charts) based on query results.
It supports various chart types and saves them to the specified output directory.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Literal, Union
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ChartSpec:
    """Specification for generating a chart."""
    chart_type: str
    x_axis: str
    y_axis: str
    title: str
    x_title: str
    y_title: str
    color_theme: str = "plotly"
    width: int = 800
    height: int = 500
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "chart_type": self.chart_type,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "title": self.title,
            "x_title": self.x_title,
            "y_title": self.y_title,
            "color_theme": self.color_theme,
            "width": self.width,
            "height": self.height
        }

def generate_chart_spec(
    results: List[Dict[str, Any]],
    intent: Dict[str, Any],
    chart_type: Optional[str] = None
) -> Optional[ChartSpec]:
    """
    Generate a chart specification based on query results and intent.
    
    Args:
        results: Query results as a list of dictionaries
        intent: Parsed intent from the query
        chart_type: Optional override for chart type
        
    Returns:
        ChartSpec if a chart should be generated, None otherwise
    """
    if not results:
        return None
        
    # Determine chart type from intent if not specified
    if not chart_type:
        if intent.get("is_comparison", False):
            chart_type = "bar"
        elif intent.get("intent_type") == "spending_by_category":
            chart_type = "pie" if len(results) <= 10 else "bar"
        elif intent.get("time_granularity"):
            chart_type = "line"
        else:
            chart_type = "bar"
    
    # Get column names from results
    columns = list(results[0].keys()) if results else []
    
    # Determine x and y axes
    x_axis = None
    y_axis = None
    
    # Common time-based columns
    time_columns = ["date", "time_period", "month", "year", "day"]
    
    # Find x-axis (prefer time-based columns)
    for col in time_columns:
        if col in columns:
            x_axis = col
            break
    
    # If no time column found, use the first non-numeric column for x-axis
    if not x_axis:
        for col in columns:
            if not any(isinstance(r.get(col), (int, float)) for r in results):
                x_axis = col
                break
    
    # Find y-axis (prefer numeric columns)
    for col in columns:
        if col != x_axis and all(isinstance(r.get(col), (int, float)) for r in results if r.get(col) is not None):
            y_axis = col
            break
    
    # If no y-axis found, use the first numeric column
    if not y_axis:
        for col in columns:
            if col != x_axis and any(isinstance(r.get(col), (int, float)) for r in results if r.get(col) is not None):
                y_axis = col
                break
    
    if not x_axis or not y_axis:
        return None
    
    # Generate title based on intent
    title = ""
    if intent.get("is_comparison", False):
        title = f"Comparison of {y_axis.replace('_', ' ').title()}"
    elif intent.get("intent_type") == "spending_by_category":
        title = f"Spending by {x_axis.replace('_', ' ').title()}"
    elif intent.get("time_granularity"):
        title = f"{y_axis.replace('_', ' ').title()} Over Time"
    else:
        title = f"{y_axis.replace('_', ' ').title()} by {x_axis.replace('_', ' ').title()}"
    
    return ChartSpec(
        chart_type=chart_type,
        x_axis=x_axis,
        y_axis=y_axis,
        title=title,
        x_title=x_axis.replace("_", " ").title(),
        y_title=y_axis.replace("_", " ").title(),
        color_theme="plotly",
        width=800,
        height=500
    )

ChartType = Literal["line", "bar", "pie", "scatter", "area"]

class ChartGenerator:
    """Generates various types of charts from query results."""
    
    def __init__(self, output_dir: Union[str, Path] = "artifacts/charts"):
        """
        Initialize the chart generator.
        
        Args:
            output_dir: Directory to save generated charts
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_chart(
        self,
        data: List[Dict[str, Any]],
        chart_type: ChartType = "bar",
        x_axis: Optional[str] = None,
        y_axis: Optional[Union[str, List[str]]] = None,
        title: str = "",
        x_title: str = "",
        y_title: str = "",
        color_theme: str = "plotly",
        width: int = 800,
        height: int = 500,
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a chart from the provided data.
        
        Args:
            data: List of dictionaries containing the data points
            chart_type: Type of chart to generate (line, bar, pie, scatter, area)
            x_axis: Name of the column to use for the x-axis
            y_axis: Name(s) of the column(s) to use for the y-axis
            title: Chart title
            x_title: X-axis title
            y_title: Y-axis title
            color_theme: Color theme to use
            width: Chart width in pixels
            height: Chart height in pixels
            filename: Optional filename (without extension) to save the chart
            
        Returns:
            Path to the saved chart image, or None if generation failed
        """
        if not data:
            logger.warning("No data provided for chart generation")
            return None
            
        # Create a timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"chart_{timestamp}"
        output_path = self.output_dir / f"{filename}.png"
        
        try:
            # Convert data to DataFrame for easier manipulation
            df = pd.DataFrame(data)
            
            # Generate the appropriate chart type
            if chart_type == "line":
                fig = self._create_line_chart(df, x_axis, y_axis, title, x_title, y_title, color_theme)
            elif chart_type == "bar":
                fig = self._create_bar_chart(df, x_axis, y_axis, title, x_title, y_title, color_theme)
            elif chart_type == "pie":
                fig = self._create_pie_chart(df, x_axis, y_axis, title, color_theme)
            elif chart_type == "scatter":
                fig = self._create_scatter_chart(df, x_axis, y_axis, title, x_title, y_title, color_theme)
            elif chart_type == "area":
                fig = self._create_area_chart(df, x_axis, y_axis, title, x_title, y_title, color_theme)
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
            
            # Update layout
            fig.update_layout(
                width=width,
                height=height,
                template=color_theme,
                margin=dict(l=50, r=50, t=80, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            # Save the figure
            fig.write_image(output_path)
            logger.info(f"Chart saved to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating chart: {e}", exc_info=True)
            return None
    
    def _create_line_chart(self, df, x_axis, y_axis, title, x_title, y_title, color_theme):
        """Create a line chart."""
        fig = go.Figure()
        
        y_columns = [y_axis] if isinstance(y_axis, str) else (y_axis or [])
        
        for col in y_columns:
            fig.add_trace(go.Scatter(
                x=df[x_axis],
                y=df[col],
                name=col,
                mode='lines+markers',
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_title or x_axis,
            yaxis_title=y_title or ", ".join(y_columns) if y_columns else "Value",
            hovermode="x unified"
        )
        
        return fig
    
    def _create_bar_chart(self, df, x_axis, y_axis, title, x_title, y_title, color_theme):
        """Create a bar chart."""
        fig = go.Figure()
        
        y_columns = [y_axis] if isinstance(y_axis, str) else (y_axis or [])
        
        for col in y_columns:
            fig.add_trace(go.Bar(
                x=df[x_axis],
                y=df[col],
                name=col,
                text=df[col],
                textposition='auto',
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_title or x_axis,
            yaxis_title=y_title or ", ".join(y_columns) if y_columns else "Value",
            barmode='group'
        )
        
        return fig
    
    def _create_pie_chart(self, df, x_axis, y_axis, title, color_theme):
        """Create a pie chart."""
        if not x_axis or not y_axis:
            raise ValueError("Both x_axis and y_axis must be specified for pie charts")
            
        fig = go.Figure(data=[go.Pie(
            labels=df[x_axis],
            values=df[y_axis],
            textinfo='label+percent',
            insidetextorientation='radial',
            hole=.3
        )])
        
        fig.update_layout(
            title=title,
            showlegend=False
        )
        
        return fig
    
    def _create_scatter_chart(self, df, x_axis, y_axis, title, x_title, y_title, color_theme):
        """Create a scatter plot."""
        fig = go.Figure()
        
        y_columns = [y_axis] if isinstance(y_axis, str) else (y_axis or [])
        
        for col in y_columns:
            fig.add_trace(go.Scatter(
                x=df[x_axis],
                y=df[col],
                name=col,
                mode='markers',
                marker=dict(size=10)
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_title or x_axis,
            yaxis_title=y_title or ", ".join(y_columns) if y_columns else "Value"
        )
        
        return fig
    
    def _create_area_chart(self, df, x_axis, y_axis, title, x_title, y_title, color_theme):
        """Create an area chart."""
        fig = go.Figure()
        
        y_columns = [y_axis] if isinstance(y_axis, str) else (y_axis or [])
        
        for col in y_columns:
            fig.add_trace(go.Scatter(
                x=df[x_axis],
                y=df[col],
                name=col,
                mode='lines',
                stackgroup='one',
                line=dict(width=0.5)
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_title or x_axis,
            yaxis_title=y_title or ", ".join(y_columns) if y_columns else "Value",
            hovermode='x'
        )
        
        return fig
