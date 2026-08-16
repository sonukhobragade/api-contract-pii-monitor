#!/usr/bin/env python3
"""
Large Scale UI Component
Handles UI for large-scale data (1300+ APIs)
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from .data_loader import (
    paginate_endpoints, 
    get_unique_values, 
    calculate_overall_metrics
)
from .schema_utils import generate_simple_json_schema, highlight_pii_in_simple_json, get_schema_from_database, get_schema_from_database_by_endpoint_id


def create_advanced_filters(endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create advanced filter controls for large datasets."""
    st.subheader("🔍 Advanced Filters")
    
    col1, col2, col3 = st.columns(3)
    
    filters = {}
    
    with col1:
        # API Title filter
        api_titles = get_unique_values(endpoints, 'api_title')
        selected_api = st.selectbox(
            "API Title",
            ["All APIs"] + api_titles,
            help="Filter by specific API"
        )
        if selected_api != "All APIs":
            filters['api_title'] = selected_api
        
        # HTTP Method filter
        http_methods = get_unique_values(endpoints, 'http_method')
        selected_method = st.selectbox(
            "HTTP Method",
            ["All Methods"] + http_methods,
            help="Filter by HTTP method"
        )
        if selected_method != "All Methods":
            filters['http_method'] = selected_method
    
    with col2:
        # Risk Level filter
        risk_level = st.selectbox(
            "Risk Level",
            ["All Risk Levels", "🔴 Critical Risk", "🟡 High Risk", "🟠 Medium Risk", "✅ Low Risk"],
            help="Filter by PII risk level"
        )
        if risk_level != "All Risk Levels":
            filters['risk_level'] = risk_level
        
        # Minimum PII count
        min_pii = st.number_input(
            "Min PII Count",
            min_value=0,
            max_value=20,
            value=0,
            help="Show endpoints with at least this many PII fields"
        )
        if min_pii > 0:
            filters['min_pii_count'] = min_pii
    
    with col3:
        # PII Type filter
        pii_types = get_unique_values(endpoints, 'pii_type')
        selected_pii_type = st.selectbox(
            "PII Type",
            ["All PII Types"] + pii_types,
            help="Filter by specific PII type"
        )
        if selected_pii_type != "All PII Types":
            filters['pii_type'] = selected_pii_type
        
        # Path contains
        path_contains = st.text_input(
            "Path Contains",
            placeholder="e.g., /users, /payment",
            help="Filter by endpoint path"
        )
        if path_contains:
            filters['path_contains'] = path_contains
    
    return filters


def create_search_bar() -> str:
    """Create a search bar for endpoints."""
    search_term = st.text_input(
        "🔍 Search Endpoints",
        placeholder="Search by path, API title, or PII type...",
        help="Search across endpoint paths, API titles, and PII types"
    )
    return search_term


def display_paginated_endpoints(endpoints: List[Dict[str, Any]], page_size: int = 50, show_schemas: bool = False):
    """Display endpoints with pagination."""
    if not endpoints:
        st.warning("No endpoints found matching your filters.")
        return
    
    # Pagination controls
    total = len(endpoints)
    total_pages = (total + page_size - 1) // page_size
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.write(f"📊 **{total}** endpoints found")
    
    with col2:
        page = st.selectbox(
            "Page",
            range(1, total_pages + 1),
            index=0,
            help=f"Page {1} of {total_pages}"
        )
    
    with col3:
        page_size_options = [25, 50, 100, 200]
        selected_page_size = st.selectbox(
            "Per Page",
            page_size_options,
            index=1,
            help="Number of endpoints per page"
        )
    
    # Get paginated data
    pagination = paginate_endpoints(endpoints, page, selected_page_size)
    
    # Show pagination info
    st.info(f"Showing endpoints {pagination['start_idx']}-{pagination['end_idx']} of {pagination['total']}")
    
    # Display endpoints
    for i, ep in enumerate(pagination['endpoints']):
        critical_count = len(ep.get('critical_pii', []))
        high_count = len(ep.get('high_pii', []))
        medium_count = len(ep.get('medium_pii', []))
        
        # Determine risk indicator
        if critical_count > 0:
            risk_indicator = "🔴"
        elif high_count > 0:
            risk_indicator = "🟡"
        elif medium_count > 0:
            risk_indicator = "🟠"
        else:
            risk_indicator = "✅"
        
        with st.expander(
            f"{risk_indicator} **{ep['http_method']}** `{ep['endpoint_path']}` "
            f"(🔴{critical_count} 🟡{high_count} 🟠{medium_count}) - {ep['api_title']}",
            expanded=False
        ):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**API:** {ep['api_title']}")
                st.write(f"**Path:** `{ep['endpoint_path']}`")
                st.write(f"**Method:** {ep['http_method']}")
            
            with col2:
                if critical_count > 0:
                    st.write("**🔴 Critical PII:**")
                    for pii in ep['critical_pii']:
                        st.write(f"  - `{pii['field_path']}` ({pii['pii_type']})")
                
                if high_count > 0:
                    st.write("**🟡 High PII:**")
                    for pii in ep['high_pii']:
                        st.write(f"  - `{pii['field_path']}` ({pii['pii_type']})")
                
                if medium_count > 0:
                    st.write("**🟠 Medium PII:**")
                    for pii in ep['medium_pii']:
                        st.write(f"  - `{pii['field_path']}` ({pii['pii_type']})")
            
            # Add JSON Schema display
            if show_schemas:
                display_endpoint_schema(ep)
            else:
                # Create unique key using index to avoid duplicates
                endpoint_id = ep.get('endpoint_id', ep.get('api_id', str(i)))
                path_clean = ep['endpoint_path'].replace('/', '_').replace(' ', '_').replace('-', '_')[:50]  # Limit length
                unique_key = f"schema_{i}_{endpoint_id}_{path_clean}"
                if st.button("📋 Show JSON Schema", key=unique_key):
                    display_endpoint_schema(ep)


def display_quick_stats(endpoints: List[Dict[str, Any]]):
    """Display quick statistics for large datasets."""
    if not endpoints:
        return
    
    metrics = calculate_overall_metrics(endpoints)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📋 Total", metrics['total_endpoints'])
    
    with col2:
        st.metric("🔴 Critical", metrics['total_critical'])
    
    with col3:
        st.metric("🟡 High", metrics['total_high'])
    
    with col4:
        st.metric("🟠 Medium", metrics['total_medium'])
    
    with col5:
        st.metric("⚠️ Risk Score", f"{metrics['risk_score']:.1f}")
    
    # Schema availability info
    endpoints_with_pii = [ep for ep in endpoints if ep.get('critical_pii') or ep.get('high_pii') or ep.get('medium_pii')]
    if endpoints_with_pii:
        st.info(f"📋 **{len(endpoints_with_pii)}** endpoints have PII data and can display JSON schemas")


def display_api_summary_table(endpoints: List[Dict[str, Any]]):
    """Display a summary table of APIs with their PII counts."""
    if not endpoints:
        return
    
    # Group by API and calculate metrics
    api_summary = {}
    
    for ep in endpoints:
        api_title = ep.get('api_title', 'Unknown API')
        if api_title not in api_summary:
            api_summary[api_title] = {
                'endpoint_count': 0,
                'critical_pii': 0,
                'high_pii': 0,
                'medium_pii': 0
            }
        
        api_summary[api_title]['endpoint_count'] += 1
        api_summary[api_title]['critical_pii'] += len(ep.get('critical_pii', []))
        api_summary[api_title]['high_pii'] += len(ep.get('high_pii', []))
        api_summary[api_title]['medium_pii'] += len(ep.get('medium_pii', []))
    
    # Convert to DataFrame for display
    df_data = []
    for api_title, data in api_summary.items():
        total_pii = data['critical_pii'] + data['high_pii'] + data['medium_pii']
        risk_score = (data['critical_pii'] * 3 + data['high_pii'] * 2 + data['medium_pii'] * 1) / max(data['endpoint_count'], 1)
        
        df_data.append({
            'API': api_title,
            'Endpoints': data['endpoint_count'],
            'Critical': data['critical_pii'],
            'High': data['high_pii'],
            'Medium': data['medium_pii'],
            'Total PII': total_pii,
            'Risk Score': f"{risk_score:.1f}"
        })
    
    df = pd.DataFrame(df_data)
    
    # Sort by risk score (descending)
    df['Risk Score Num'] = df['Risk Score'].astype(float)
    df = df.sort_values('Risk Score Num', ascending=False)
    df = df.drop('Risk Score Num', axis=1)
    
    st.subheader("📊 API Summary Table")
    st.dataframe(df, use_container_width=True)


def create_export_options(endpoints: List[Dict[str, Any]]):
    """Create export options for filtered data."""
    if not endpoints:
        return
    
    st.subheader("📤 Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export to CSV"):
            # Convert to DataFrame for CSV export
            df_data = []
            for ep in endpoints:
                critical_count = len(ep.get('critical_pii', []))
                high_count = len(ep.get('high_pii', []))
                medium_count = len(ep.get('medium_pii', []))
                
                df_data.append({
                    'API': ep.get('api_title'),
                    'Method': ep.get('http_method'),
                    'Path': ep.get('endpoint_path'),
                    'Critical_PII': critical_count,
                    'High_PII': high_count,
                    'Medium_PII': medium_count,
                    'Total_PII': critical_count + high_count + medium_count
                })
            
            df = pd.DataFrame(df_data)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name="pii_analysis_export.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📋 Export Summary"):
            # Create summary report
            metrics = calculate_overall_metrics(endpoints)
            
            summary = f"""
# PII Analysis Summary Report

## Overall Statistics
- Total Endpoints: {metrics['total_endpoints']}
- Critical PII: {metrics['total_critical']}
- High PII: {metrics['total_high']}
- Medium PII: {metrics['total_medium']}
- Risk Score: {metrics['risk_score']:.1f}

## API Breakdown
"""
            
            api_groups = {}
            for ep in endpoints:
                api_title = ep.get('api_title', 'Unknown API')
                if api_title not in api_groups:
                    api_groups[api_title] = {'count': 0, 'critical': 0, 'high': 0, 'medium': 0}
                
                api_groups[api_title]['count'] += 1
                api_groups[api_title]['critical'] += len(ep.get('critical_pii', []))
                api_groups[api_title]['high'] += len(ep.get('high_pii', []))
                api_groups[api_title]['medium'] += len(ep.get('medium_pii', []))
            
            for api_title, data in api_groups.items():
                summary += f"- **{api_title}**: {data['count']} endpoints, {data['critical']} critical, {data['high']} high, {data['medium']} medium PII\n"
            
            st.download_button(
                label="📄 Download Summary",
                data=summary,
                file_name="pii_analysis_summary.md",
                mime="text/markdown"
            )


def display_endpoint_schema(endpoint: Dict[str, Any]):
    """Display JSON schema for a specific endpoint."""
    st.subheader(f"📋 JSON Schema - {endpoint['http_method']} {endpoint['endpoint_path']}")
    
    # Get all PII for highlighting
    all_pii = endpoint.get('critical_pii', []) + endpoint.get('high_pii', []) + endpoint.get('medium_pii', [])
    
    # Try to get schema from database first
    if 'endpoint_id' in endpoint:
        # Use endpoint ID for real database data
        schemas = get_schema_from_database_by_endpoint_id(endpoint['endpoint_id'])
    else:
        # Use path/method/api_id for sample data
        schemas = get_schema_from_database(
            endpoint['endpoint_path'],
            endpoint['http_method'],
            endpoint['api_id']
        )
    
    # Always show mock schema when PII is detected, even if database schema is available
    if all_pii:
        st.info("📝 Showing schema with detected PII fields highlighted...")
        
        # Generate mock schema based on detected PII
        mock_schema = generate_mock_schema_from_pii(endpoint)
        highlighted_schema = highlight_pii_in_simple_json(mock_schema, all_pii)
        
        # Display in tabs
        tab1, tab2 = st.tabs(["📤 Request Schema", "📥 Response Schema"])
        
        with tab1:
            st.json(highlighted_schema)
        
        with tab2:
            if schemas and schemas.get('response_body'):
                # Show actual response schema if available
                response_schema = generate_simple_json_schema(schemas['response_body'])
                highlighted_response = highlight_pii_in_simple_json(response_schema, all_pii)
                st.json(highlighted_response)
            else:
                # Show mock response schema
                st.json(highlighted_schema)
        
        st.success("✅ PII fields are highlighted with 🔴🟡🟠 indicators")
        
    elif schemas:
        # No PII detected, but database schema is available
        simple_schemas = {}
        
        if schemas.get('request_body'):
            simple_schemas['request_body'] = generate_simple_json_schema(schemas['request_body'])
        
        if schemas.get('response_body'):
            simple_schemas['response_body'] = generate_simple_json_schema(schemas['response_body'])
        
        # Display schemas in tabs
        tab1, tab2 = st.tabs(["📤 Request Schema", "📥 Response Schema"])
        
        with tab1:
            if simple_schemas.get('request_body'):
                st.json(simple_schemas['request_body'])
            else:
                st.info("No request body schema available")
        
        with tab2:
            if simple_schemas.get('response_body'):
                st.json(simple_schemas['response_body'])
            else:
                st.info("No response body schema available")
    
    else:
        # No PII and no database schema
        st.info("📝 No schema available for this endpoint")
        st.warning("⚠️ Neither PII data nor database schema found for this endpoint.")


def generate_mock_schema_from_pii(endpoint: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a mock JSON schema based on detected PII fields."""
    all_pii = endpoint.get('critical_pii', []) + endpoint.get('high_pii', []) + endpoint.get('medium_pii', [])
    
    if not all_pii:
        return {
            "type": "object",
            "properties": {},
            "description": "No PII detected in this endpoint"
        }
    
    # Group PII by their top-level field
    field_groups = {}
    for pii in all_pii:
        field_path = pii.get('field_path', '')
        if '.' in field_path:
            top_level = field_path.split('.')[0]
            if top_level not in field_groups:
                field_groups[top_level] = []
            field_groups[top_level].append(pii)
        else:
            if 'root' not in field_groups:
                field_groups['root'] = []
            field_groups['root'].append(pii)
    
    # If no field groups (all PII are root level), create a default structure
    if not field_groups:
        field_groups['payload'] = all_pii
    
    # Build schema structure
    properties = {}
    required = []
    
    for group_name, pii_list in field_groups.items():
        if group_name == 'root':
            # Direct properties
            for pii in pii_list:
                field_name = pii.get('field_path', 'unknown')
                pii_type = pii.get('pii_type', 'string')
                properties[field_name] = {
                    "type": "string",
                    "description": f"{pii_type.replace('_', ' ').title()} field",
                    "example": get_example_value(pii_type)
                }
                required.append(field_name)
        else:
            # Nested object
            group_properties = {}
            group_required = []
            
            for pii in pii_list:
                field_path = pii.get('field_path', '')
                field_name = field_path.split('.')[-1] if '.' in field_path else field_path
                pii_type = pii.get('pii_type', 'string')
                
                group_properties[field_name] = {
                    "type": "string",
                    "description": f"{pii_type.replace('_', ' ').title()} field",
                    "example": get_example_value(pii_type)
                }
                group_required.append(field_name)
            
            properties[group_name] = {
                "type": "object",
                "properties": group_properties,
                "required": group_required
            }
            required.append(group_name)
    
    # Add standard API response structure
    final_schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "object",
                "properties": {
                    "code": {"type": "integer", "example": 1},
                    "message": {"type": "string", "example": "Success"},
                    "reason": {"type": "string", "example": "string"},
                    "type": {"type": "string", "example": "string"},
                    "title": {"type": "string", "example": "string"}
                }
            },
            "payload": {
                "type": "object",
                "properties": properties,
                "required": required
            },
            "transactionId": {"type": "string", "example": "txn_123456789"}
        },
        "required": ["status", "payload"],
        "description": f"Mock schema for {endpoint['http_method']} {endpoint['endpoint_path']} with PII fields highlighted"
    }
    
    return final_schema


def get_example_value(pii_type: str) -> str:
    """Get example value for PII type."""
    examples = {
        "email_address": "user@example.com",
        "phone_number": "+1-555-123-4567",
        "full_name": "John Doe",
        "credit_card": "****-****-****-1234",
        "physical_address": "123 Main St, City, State 12345",
        "ssn": "***-**-1234",
        "username": "johndoe",
        "ip_address": "192.168.1.1",
        "date_of_birth": "1990-01-01",
        "passport_number": "A12345678"
    }
    return examples.get(pii_type, "example_value")
