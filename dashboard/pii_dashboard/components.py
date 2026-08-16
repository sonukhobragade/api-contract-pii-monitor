"""
PII Dashboard Components
Reusable components for the PII Analysis Dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, List, Any, Callable
from .utils import create_pii_heatmap


def render_filters_sidebar(
    dataframes: Dict[str, pd.DataFrame],
    on_filter_change: Callable[[Dict[str, Any]], None]
) -> Dict[str, Any]:
    """
    Render filter controls in the sidebar.
    
    Args:
        dataframes: Dictionary of DataFrames
        on_filter_change: Callback function when filters change
        
    Returns:
        Dictionary of selected filter values
    """
    st.sidebar.header("🔍 Filters")
    
    filters = {}
    
    # Only proceed if we have the necessary dataframes
    if not all(key in dataframes for key in ["detailed_results", "pii_matches"]):
        st.sidebar.warning("Data not available for filtering")
        return filters
    
    detailed_df = dataframes["detailed_results"]
    matches_df = dataframes["pii_matches"]
    
    # API filter
    api_options = ["All"] + sorted(detailed_df["api_title"].unique().tolist())
    filters["api"] = st.sidebar.selectbox("API", options=api_options)
    
    # Apply API filter to get relevant data for other filters
    filtered_matches = matches_df
    if filters["api"] != "All":
        filtered_matches = matches_df[matches_df["api_title"] == filters["api"]]
    
    # Severity filter
    severity_options = ["All", "Critical", "High", "Medium", "Low"]
    filters["severity"] = st.sidebar.selectbox("Severity Level", options=severity_options)
    
    # PII Type filter (based on available types in filtered data)
    pii_types = ["All"] + sorted(filtered_matches["pii_type"].unique().tolist())
    filters["pii_type"] = st.sidebar.selectbox("PII Type", options=pii_types)
    
    # Context filter (parameter, request_body, response)
    context_options = ["All"] + sorted(filtered_matches["context"].unique().tolist())
    filters["context"] = st.sidebar.selectbox("Context", options=context_options)
    
    # Compliance score range
    min_score = int(detailed_df["compliance_score"].min())
    max_score = int(detailed_df["compliance_score"].max())
    filters["compliance_range"] = st.sidebar.slider(
        "Compliance Score Range",
        min_value=min_score,
        max_value=max_score,
        value=(min_score, max_score)
    )
    
    # Endpoint path search
    filters["endpoint_search"] = st.sidebar.text_input("Search Endpoints", "")
    
    # Apply filters button
    if st.sidebar.button("Apply Filters"):
        on_filter_change(filters)
    
    # Reset filters button
    if st.sidebar.button("Reset Filters"):
        st.experimental_rerun()
    
    return filters


def render_summary_metrics(summary: Dict[str, Any]) -> None:
    """
    Render summary metrics in a row of columns.
    
    Args:
        summary: Summary data dictionary
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Endpoints", summary["total_endpoints_analyzed"])
    with col2:
        st.metric("Endpoints with PII", summary["endpoints_with_pii"])
    with col3:
        st.metric("PII Exposure Rate", f"{summary['pii_exposure_rate']}%")
    with col4:
        st.metric("Avg Compliance Score", f"{summary['average_compliance_score']}/100")


def render_pii_breakdown(pii_breakdown: Dict[str, int]) -> None:
    """
    Render PII breakdown chart.
    
    Args:
        pii_breakdown: Dictionary with counts for each severity level
    """
    st.subheader("PII Severity Breakdown")
    
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
    
    st.plotly_chart(fig, use_container_width=True)


def render_pii_types_chart(pii_types: List[List[str]]) -> None:
    """
    Render chart of most common PII types.
    
    Args:
        pii_types: List of [pii_type, count] pairs
    """
    st.subheader("Most Common PII Types")
    
    pii_types_df = pd.DataFrame(pii_types, columns=["PII Type", "Count"])
    
    fig = px.bar(
        pii_types_df,
        x="PII Type",
        y="Count",
        title="Most Common PII Types",
        labels={"Count": "Number of Occurrences", "PII Type": "PII Type"}
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_endpoint_analysis(
    detailed_df: pd.DataFrame,
    matches_df: pd.DataFrame,
    filters: Dict[str, Any]
) -> None:
    """
    Render endpoint analysis section with filtering.
    
    Args:
        detailed_df: DataFrame of detailed endpoint results
        matches_df: DataFrame of PII matches
        filters: Dictionary of filter values
    """
    st.header("🔌 Endpoint Analysis")
    
    # Apply filters
    filtered_detailed = detailed_df.copy()
    filtered_matches = matches_df.copy()
    
    # API filter
    if filters.get("api") != "All":
        filtered_detailed = filtered_detailed[filtered_detailed["api_title"] == filters["api"]]
        filtered_matches = filtered_matches[filtered_matches["api_title"] == filters["api"]]
    
    # Severity filter
    if filters.get("severity") != "All":
        severity = filters["severity"].lower()
        
        # Filter detailed results
        if severity == "critical":
            filtered_detailed = filtered_detailed[filtered_detailed["critical_pii"].apply(
                lambda x: len(x) > 0 if isinstance(x, list) else False
            )]
        elif severity == "high":
            filtered_detailed = filtered_detailed[filtered_detailed["high_pii"].apply(
                lambda x: len(x) > 0 if isinstance(x, list) else False
            )]
        elif severity == "medium":
            filtered_detailed = filtered_detailed[filtered_detailed["medium_pii"].apply(
                lambda x: len(x) > 0 if isinstance(x, list) else False
            )]
        elif severity == "low":
            filtered_detailed = filtered_detailed[filtered_detailed["low_pii"].apply(
                lambda x: len(x) > 0 if isinstance(x, list) else False
            )]
        
        # Filter matches
        filtered_matches = filtered_matches[filtered_matches["severity_level"] == severity]
    
    # PII Type filter
    if filters.get("pii_type") != "All":
        filtered_matches = filtered_matches[filtered_matches["pii_type"] == filters["pii_type"]]
        
        # Filter detailed results to only include endpoints with the selected PII type
        endpoint_paths = filtered_matches["endpoint_path"].unique()
        filtered_detailed = filtered_detailed[filtered_detailed["endpoint_path"].isin(endpoint_paths)]
    
    # Context filter
    if filters.get("context") != "All":
        filtered_matches = filtered_matches[filtered_matches["context"] == filters["context"]]
        
        # Filter detailed results to only include endpoints with the selected context
        endpoint_paths = filtered_matches["endpoint_path"].unique()
        filtered_detailed = filtered_detailed[filtered_detailed["endpoint_path"].isin(endpoint_paths)]
    
    # Compliance score range
    if "compliance_range" in filters:
        min_score, max_score = filters["compliance_range"]
        filtered_detailed = filtered_detailed[
            (filtered_detailed["compliance_score"] >= min_score) &
            (filtered_detailed["compliance_score"] <= max_score)
        ]
        
        # Filter matches to only include endpoints within the compliance score range
        endpoint_paths = filtered_detailed["endpoint_path"].unique()
        filtered_matches = filtered_matches[filtered_matches["endpoint_path"].isin(endpoint_paths)]
    
    # Endpoint path search
    if filters.get("endpoint_search"):
        search_term = filters["endpoint_search"].lower()
        filtered_detailed = filtered_detailed[filtered_detailed["endpoint_path"].str.lower().str.contains(search_term)]
        filtered_matches = filtered_matches[filtered_matches["endpoint_path"].str.lower().str.contains(search_term)]
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Filtered Endpoints", len(filtered_detailed))
    with col2:
        st.metric("Total PII Findings", len(filtered_matches))
    with col3:
        avg_score = filtered_detailed["compliance_score"].mean() if not filtered_detailed.empty else 0
        st.metric("Avg Compliance Score", f"{avg_score:.1f}/100")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["Endpoints", "PII Findings", "Visualizations"])
    
    with tab1:
        st.subheader("Endpoints with PII")
        if filtered_detailed.empty:
            st.info("No endpoints match the selected filters")
        else:
            # Add a column for severity counts
            endpoint_table = filtered_detailed[["api_title", "endpoint_path", "http_method", "total_pii_found", "compliance_score"]].copy()
            
            # Sort by total PII found (descending)
            endpoint_table = endpoint_table.sort_values("total_pii_found", ascending=False)
            
            st.dataframe(endpoint_table, use_container_width=True)
    
    with tab2:
        st.subheader("PII Findings")
        if filtered_matches.empty:
            st.info("No PII findings match the selected filters")
        else:
            # Sort by severity level
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            filtered_matches["severity_order"] = filtered_matches["severity_level"].map(severity_order)
            filtered_matches = filtered_matches.sort_values("severity_order")
            
            st.dataframe(
                filtered_matches[["endpoint_path", "http_method", "pii_type", "severity_level", "field_path", "context"]],
                use_container_width=True
            )
    
    with tab3:
        st.subheader("PII Visualizations")
        
        if filtered_matches.empty:
            st.info("No data available for visualization with the selected filters")
        else:
            # Create a heatmap of PII findings by endpoint and severity
            try:
                heatmap_fig = create_pii_heatmap(filtered_matches)
                st.plotly_chart(heatmap_fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error creating heatmap: {e}")
            
            # Create a pie chart of PII types
            pii_type_counts = filtered_matches["pii_type"].value_counts()
            
            fig = px.pie(
                values=pii_type_counts.values,
                names=pii_type_counts.index,
                title="PII Types Distribution",
                hole=0.4
            )
            
            st.plotly_chart(fig, use_container_width=True)


def render_api_analysis(
    api_df: pd.DataFrame,
    detailed_df: pd.DataFrame,
    selected_api: str
) -> None:
    """
    Render API-level analysis section.
    
    Args:
        api_df: DataFrame of API summaries
        detailed_df: DataFrame of detailed endpoint results
        selected_api: Selected API title
    """
    st.header("🔍 API-Level Analysis")
    
    # Filter data for selected API
    api_data = api_df[api_df["title"] == selected_api].iloc[0]
    api_endpoints = detailed_df[detailed_df["api_title"] == selected_api]
    
    # Display API metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Endpoints Analyzed", api_data["endpoints_analyzed"])
    with col2:
        st.metric("Total PII Found", api_data["total_pii_found"])
    with col3:
        st.metric("Critical PII", api_data["critical_pii"])
    with col4:
        st.metric("Compliance Score", f"{api_data['avg_compliance_score']}/100")
    
    # Create a DataFrame for the PII breakdown
    api_pii_df = pd.DataFrame({
        "Severity": ["Critical", "High", "Medium", "Low"],
        "Count": [
            api_data["critical_pii"],
            api_data["high_pii"],
            api_data["medium_pii"],
            api_data["low_pii"]
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
        api_pii_df,
        x="Severity",
        y="Count",
        color="Severity",
        color_discrete_map=color_map,
        title=f"PII Findings for {selected_api}",
        labels={"Count": "Number of Findings", "Severity": "Severity Level"}
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display endpoints with the most PII
    st.subheader("Top Endpoints by PII Count")
    
    top_endpoints = api_endpoints.sort_values("total_pii_found", ascending=False).head(10)
    
    if not top_endpoints.empty:
        fig = px.bar(
            top_endpoints,
            x="endpoint_path",
            y="total_pii_found",
            color="compliance_score",
            color_continuous_scale=["red", "yellow", "green"],
            labels={"endpoint_path": "Endpoint", "total_pii_found": "PII Count", "compliance_score": "Compliance Score"},
            title=f"Top 10 Endpoints by PII Count for {selected_api}"
        )
        
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No endpoint data available for this API")


def render_recommendations(recommendations: List[str]) -> None:
    """
    Render compliance recommendations.
    
    Args:
        recommendations: List of recommendation strings
    """
    st.header("📋 Compliance Recommendations")
    
    for rec in recommendations:
        st.markdown(f"- {rec}")


def render_risk_assessment(risk: str) -> None:
    """
    Render risk assessment.
    
    Args:
        risk: Risk assessment string
    """
    st.header("⚠️ Risk Assessment")
    
    # Determine color based on risk level
    if "CRITICAL" in risk:
        st.error(risk)
    elif "HIGH" in risk:
        st.warning(risk)
    elif "MEDIUM" in risk:
        st.info(risk)
    else:
        st.success(risk)