#!/usr/bin/env python3
"""
Overview Page Component
Shows high-level PII analysis overview
"""

import streamlit as st
from simple_dashboard.components.data_loader import calculate_overall_metrics, group_endpoints_by_api
from simple_dashboard.components.ui_components import display_metrics_row, display_api_breakdown, display_pii_endpoints_list
from simple_dashboard.components.charts import (
    create_pii_severity_chart, 
    create_api_risk_chart, 
    create_endpoint_risk_scatter,
    create_pii_type_chart,
    create_risk_trend_chart
)


def show_overview_page(endpoints):
    """Show the overview page with all APIs and endpoints."""
    st.title("🔒 PII Security Overview")
    st.markdown("Complete overview of all APIs and their PII findings")
    
    # Overall summary
    st.subheader("📊 Overall Summary")
    
    metrics = calculate_overall_metrics(endpoints)
    display_metrics_row(metrics)
    
    # Charts section
    st.subheader("📈 Visual Analytics")
    
    # Create two columns for charts
    col1, col2 = st.columns(2)
    
    with col1:
        # PII Severity Distribution
        severity_chart = create_pii_severity_chart(endpoints)
        st.plotly_chart(severity_chart, use_container_width=True)
        
        # PII Types Distribution
        pii_type_chart = create_pii_type_chart(endpoints)
        if pii_type_chart:
            st.plotly_chart(pii_type_chart, use_container_width=True)
    
    with col2:
        # API Risk Chart
        api_risk_chart = create_api_risk_chart(endpoints)
        st.plotly_chart(api_risk_chart, use_container_width=True)
        
        # Risk Trends
        trend_chart = create_risk_trend_chart(endpoints)
        st.plotly_chart(trend_chart, use_container_width=True)
    
    # Endpoint Risk Scatter Plot (full width)
    st.subheader("🎯 Endpoint Risk Analysis")
    scatter_chart = create_endpoint_risk_scatter(endpoints)
    st.plotly_chart(scatter_chart, use_container_width=True)
    
    # API breakdown
    st.subheader("📈 API Breakdown")
    
    api_groups = group_endpoints_by_api(endpoints)
    display_api_breakdown(api_groups)
    
    # Endpoints with PII
    st.subheader("🔴 Endpoints with PII")
    display_pii_endpoints_list(endpoints)
