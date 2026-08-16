#!/usr/bin/env python3
"""
Analysis Page Component
Shows detailed endpoint analysis with risk filtering
"""

import streamlit as st
from simple_dashboard.components.data_loader import filter_endpoints_by_risk
from simple_dashboard.components.ui_components import create_endpoint_selector, display_endpoint_metrics, display_schema_tabs, display_pii_fields_fallback
from simple_dashboard.components.schema_utils import generate_simple_json_schema, highlight_pii_in_simple_json, get_schema_from_database


def show_analysis_page(endpoints):
    """Show the detailed analysis page with risk-based filtering."""
    st.title("🔍 Detailed PII Analysis")
    st.markdown("Analyze individual endpoints with simple JSON schemas")
    
    # Risk level filter
    st.subheader("⚠️ Risk Level Filter")
    
    risk_filter = st.selectbox(
        "Filter by risk level:",
        ["All Endpoints", "🔴 Critical Risk", "🟡 High Risk", "🟠 Medium Risk", "✅ Low Risk"],
        help="Select risk level to filter endpoints"
    )
    
    # Filter endpoints based on risk level
    filtered_endpoints = filter_endpoints_by_risk(endpoints, risk_filter)
    
    # Show filtered results count
    st.info(f"📊 Found {len(filtered_endpoints)} endpoints matching '{risk_filter}' criteria")
    
    if not filtered_endpoints:
        st.warning(f"No endpoints found for '{risk_filter}'")
        return
    
    # Endpoint selector from filtered list
    st.subheader("📋 Select Endpoint")
    
    selected_endpoint_data = create_endpoint_selector(filtered_endpoints)
    
    if selected_endpoint_data:
        display_endpoint_analysis(selected_endpoint_data)


def display_endpoint_analysis(endpoint_data):
    """Display detailed analysis for a single endpoint."""
    st.subheader(f"🔍 {endpoint_data['http_method']} {endpoint_data['endpoint_path']}")
    
    # Get PII summary
    critical_pii = endpoint_data.get('critical_pii', [])
    high_pii = endpoint_data.get('high_pii', [])
    medium_pii = endpoint_data.get('medium_pii', [])
    
    all_pii = critical_pii + high_pii + medium_pii
    
    # Show PII summary
    display_endpoint_metrics(endpoint_data)
    
    if not all_pii:
        st.success("✅ No PII detected in this endpoint")
        return
    
    # Get schema from database
    schemas = get_schema_from_database(
        endpoint_data['endpoint_path'],
        endpoint_data['http_method'],
        endpoint_data['api_id']
    )
    
    if schemas:
        # Generate simple schemas
        simple_schemas = {}
        
        if schemas.get('request_body'):
            simple_schemas['request_body'] = generate_simple_json_schema(schemas['request_body'])
        
        if schemas.get('response_body'):
            simple_schemas['response_body'] = generate_simple_json_schema(schemas['response_body'])
        
        # Show schemas with PII highlighting
        display_schema_tabs(simple_schemas, all_pii, highlight_pii_in_simple_json)
    else:
        # Fallback: show PII fields only
        display_pii_fields_fallback(all_pii)
