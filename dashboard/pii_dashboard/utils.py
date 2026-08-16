"""
PII Dashboard Utilities
Helper functions for data processing and visualization.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any


def create_severity_color_map() -> Dict[str, str]:
    """
    Create a color map for PII severity levels.
    
    Returns:
        Dictionary mapping severity levels to colors
    """
    return {
        "critical": "#FF0000",  # Red
        "high": "#FFA500",      # Orange
        "medium": "#FFFF00",    # Yellow
        "low": "#00FF00"        # Green
    }


def create_pii_breakdown_chart(pii_breakdown: Dict[str, int]) -> go.Figure:
    """
    Create a bar chart for PII severity breakdown.
    
    Args:
        pii_breakdown: Dictionary with counts for each severity level
        
    Returns:
        Plotly figure object
    """
    # Create a DataFrame for the PII breakdown
    pii_df = pd.DataFrame({
        "Severity": ["Critical", "High", "Medium", "Low"],
        "Count": [
            pii_breakdown.get("critical", 0),
            pii_breakdown.get("high", 0),
            pii_breakdown.get("medium", 0),
            pii_breakdown.get("low", 0)
        ]
    })
    
    # Create a color map for severity levels
    color_map = {
        "Critical": "#FF0000",  # Red
        "High": "#FFA500",      # Orange
        "Medium": "#FFFF00",    # Yellow
        "Low": "#00FF00"        # Green
    }
    
    # Create a bar chart
    fig = px.bar(
        pii_df,
        x="Severity",
        y="Count",
        color="Severity",
        color_discrete_map=color_map,
        title="PII Findings by Severity Level",
        labels={"Count": "Number of Findings", "Severity": "Severity Level"}
    )
    
    return fig


def create_pii_types_chart(pii_types: List[List[str]]) -> go.Figure:
    """
    Create a bar chart for most common PII types.
    
    Args:
        pii_types: List of [pii_type, count] pairs
        
    Returns:
        Plotly figure object
    """
    pii_types_df = pd.DataFrame(pii_types, columns=["PII Type", "Count"])
    
    fig = px.bar(
        pii_types_df,
        x="PII Type",
        y="Count",
        title="Most Common PII Types",
        labels={"Count": "Number of Occurrences", "PII Type": "PII Type"}
    )
    
    return fig


def create_compliance_score_gauge(score: float) -> go.Figure:
    """
    Create a gauge chart for compliance score.
    
    Args:
        score: Compliance score (0-100)
        
    Returns:
        Plotly figure object
    """
    # Determine color based on score
    if score >= 90:
        color = "green"
    elif score >= 70:
        color = "yellow"
    elif score >= 50:
        color = "orange"
    else:
        color = "red"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Compliance Score"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 50], "color": "lightgray"},
                {"range": [50, 70], "color": "gray"},
                {"range": [70, 90], "color": "lightgreen"},
                {"range": [90, 100], "color": "green"}
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 90
            }
        }
    ))
    
    return fig


def create_pii_heatmap(matches_df: pd.DataFrame) -> go.Figure:
    """
    Create a heatmap of PII findings by endpoint and severity.
    
    Args:
        matches_df: DataFrame of PII matches
        
    Returns:
        Plotly figure object
    """
    # Group by endpoint and severity level
    heatmap_data = matches_df.groupby(["endpoint_path", "severity_level"]).size().reset_index(name="count")
    
    # Pivot the data for the heatmap
    pivot_data = heatmap_data.pivot(
        index="endpoint_path",
        columns="severity_level",
        values="count"
    ).fillna(0)
    
    # Create the heatmap
    fig = px.imshow(
        pivot_data,
        labels=dict(x="Severity Level", y="Endpoint", color="Count"),
        x=pivot_data.columns,
        y=pivot_data.index,
        color_continuous_scale=["green", "yellow", "orange", "red"],
        title="PII Findings Heatmap by Endpoint and Severity"
    )
    
    return fig


def filter_endpoints_by_severity(detailed_df: pd.DataFrame, severity: str) -> pd.DataFrame:
    """
    Filter endpoints that have PII of the specified severity.
    
    Args:
        detailed_df: DataFrame of detailed endpoint results
        severity: Severity level to filter by
        
    Returns:
        Filtered DataFrame
    """
    if severity == "all":
        return detailed_df
    
    if severity == "critical":
        return detailed_df[detailed_df["critical_pii"].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)]
    elif severity == "high":
        return detailed_df[detailed_df["high_pii"].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)]
    elif severity == "medium":
        return detailed_df[detailed_df["medium_pii"].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)]
    elif severity == "low":
        return detailed_df[detailed_df["low_pii"].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)]
    
    return detailed_df


def calculate_api_statistics(detailed_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate statistics for APIs in the dataset.
    
    Args:
        detailed_df: DataFrame of detailed endpoint results
        
    Returns:
        Dictionary of API statistics
    """
    stats = {}
    
    # Group by API
    api_groups = detailed_df.groupby("api_title")
    
    for api, group in api_groups:
        stats[api] = {
            "endpoints_analyzed": len(group),
            "endpoints_with_pii": len(group[group["total_pii_found"] > 0]),
            "total_pii_found": group["total_pii_found"].sum(),
            "critical_pii": sum(len(x) for x in group["critical_pii"] if isinstance(x, list)),
            "high_pii": sum(len(x) for x in group["high_pii"] if isinstance(x, list)),
            "medium_pii": sum(len(x) for x in group["medium_pii"] if isinstance(x, list)),
            "low_pii": sum(len(x) for x in group["low_pii"] if isinstance(x, list)),
            "avg_compliance_score": group["compliance_score"].mean()
        }
    
    return stats