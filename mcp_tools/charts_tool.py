import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union, Tuple
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from enum import Enum
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class ChartType(str, Enum):
    """Supported chart types."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"

class ChartTool:
    """
    Handles chart generation from data.
    
    Uses Plotly for interactive charts and Matplotlib for static ones.
    """
    
    def __init__(self, output_dir: Union[str, Path] = "artifacts/charts"):
        """
        Initialize with output directory for charts.
        
        Args:
            output_dir: Directory to save chart images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_chart(
        self,
        data: List[Dict[str, Any]],
        chart_type: Union[str, ChartType],
        x_axis: str,
        y_axis: str,
        title: Optional[str] = None,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
        color: Optional[str] = None,
        output_file: Optional[Union[str, Path]] = None,
        width: int = 800,
        height: int = 500,
        template: str = "plotly_white",
        return_figure: bool = False
    ) -> Union[Path, go.Figure]:
        """
        Create a chart from data.
        
        Args:
            data: List of dictionaries containing the data
            chart_type: Type of chart to create (line, bar, pie, etc.)
            x_axis: Column name for x-axis
            y_axis: Column name for y-axis
            title: Chart title
            x_label: Label for x-axis
            y_label: Label for y-axis
            color: Column name to use for coloring
            output_file: Path to save the chart (if None, generates a filename)
            width: Chart width in pixels
            height: Chart height in pixels
            template: Plotly template name
            return_figure: If True, return the Plotly figure instead of saving
            
        Returns:
            Path to the saved chart or the Plotly figure
        """
        if not data:
            raise ValueError("No data provided for chart")
            
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(data)
        
        # Generate a filename if none provided
        if output_file is None:
            chart_type_str = chart_type.value if isinstance(chart_type, ChartType) else str(chart_type)
            safe_title = "".join(c if c.isalnum() else "_" for c in (title or f"{y_label}_by_{x_axis}"))
            output_file = self.output_dir / f"{safe_title}_{chart_type_str}.png"
        else:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create the appropriate chart type
        fig = self._create_plotly_chart(
            df=df,
            chart_type=chart_type,
            x_axis=x_axis,
            y_axis=y_axis,
            title=title,
            x_label=x_label,
            y_label=y_label,
            color=color,
            width=width,
            height=height,
            template=template
        )
        
        if return_figure:
            return fig
            
        # Save the chart
        output_file.parent.mkdir(parents=True, exist_ok=True)
        fig.write_image(output_file)
        return output_file
    
    def _create_plotly_chart(
        self,
        df: pd.DataFrame,
        chart_type: Union[str, ChartType],
        x_axis: str,
        y_axis: str,
        title: Optional[str] = None,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
        color: Optional[str] = None,
        width: int = 800,
        height: int = 500,
        template: str = "plotly_white"
    ) -> go.Figure:
        """Create a Plotly figure based on the specified chart type."""
        chart_type = ChartType(chart_type.lower()) if isinstance(chart_type, str) else chart_type
        
        # Set default labels if not provided
        x_label = x_label or x_axis
        y_label = y_label or y_axis
        title = title or f"{y_label} by {x_label}"
        
        # Create the figure
        fig = go.Figure()
        
        # Add the appropriate trace based on chart type
        if chart_type == ChartType.LINE:
            if color and color in df.columns:
                for name, group in df.groupby(color):
                    fig.add_trace(go.Scatter(
                        x=group[x_axis],
                        y=group[y_axis],
                        name=str(name),
                        mode='lines+markers'
                    ))
            else:
                fig.add_trace(go.Scatter(
                    x=df[x_axis],
                    y=df[y_axis],
                    mode='lines+markers'
                ))
                
        elif chart_type == ChartType.BAR:
            fig.add_trace(go.Bar(
                x=df[x_axis],
                y=df[y_axis],
                name=y_label,
                marker_color=color
            ))
            
        elif chart_type == ChartType.PIE:
            fig.add_trace(go.Pie(
                labels=df[x_axis],
                values=df[y_axis],
                name=title
            ))
            
        elif chart_type == ChartType.SCATTER:
            fig.add_trace(go.Scatter(
                x=df[x_axis],
                y=df[y_axis],
                mode='markers',
                marker=dict(size=12, color=df[color] if color and color in df.columns else None),
                text=df[color] if color and color in df.columns else None
            ))
            
        elif chart_type == ChartType.AREA:
            fig.add_trace(go.Scatter(
                x=df[x_axis],
                y=df[y_axis],
                fill='tozeroy',
                mode='none'  # No lines or markers
            ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            template=template,
            width=width,
            height=height,
            margin=dict(l=50, r=50, t=80, b=50),
            showlegend=color is not None
        )
        
        return fig
    
    def create_comparison_chart(
        self,
        data_dict: Dict[str, List[Dict[str, Any]]],
        chart_type: Union[str, ChartType],
        x_axis: str,
        y_axis: str,
        group_by: str = "group",
        title: Optional[str] = None,
        x_label: Optional[str] = None,
        y_label: Optional[str] = None,
        output_file: Optional[Union[str, Path]] = None,
        width: int = 1000,
        height: int = 600,
        template: str = "plotly_white"
    ) -> Path:
        """
        Create a chart comparing multiple datasets.
        
        Args:
            data_dict: Dictionary of {group_name: data_list} pairs
            chart_type: Type of chart to create
            x_axis: Column name for x-axis
            y_axis: Column name for y-axis
            group_by: Column name that identifies groups in the data
            title: Chart title
            x_label: Label for x-axis
            y_label: Label for y-axis
            output_file: Path to save the chart
            width: Chart width in pixels
            height: Chart height in pixels
            template: Plotly template name
            
        Returns:
            Path to the saved chart
        """
        # Convert all data to DataFrames and add group column
        dfs = []
        for group_name, data in data_dict.items():
            df = pd.DataFrame(data)
            df[group_by] = group_name
            dfs.append(df)
        
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Generate output filename if not provided
        if output_file is None:
            safe_title = "".join(c if c.isalnum() else "_" for c in (title or f"comparison_{y_axis}_by_{x_axis}"))
            output_file = self.output_dir / f"{safe_title}.png"
        else:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create the chart
        fig = self._create_plotly_chart(
            df=combined_df,
            chart_type=chart_type,
            x_axis=x_axis,
            y_axis=y_axis,
            title=title or f"Comparison of {y_axis} by {x_axis}",
            x_label=x_label or x_axis,
            y_label=y_label or y_axis,
            color=group_by,
            width=width,
            height=height,
            template=template
        )
        
        # Save the chart
        fig.write_image(output_file)
        return output_file
