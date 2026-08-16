#!/usr/bin/env python3
"""
UI Components
Reusable UI components for the dashboard
"""

import streamlit as st


def display_metrics_row(metrics):
    """Display metrics in a row."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📋 Total Endpoints", metrics['total_endpoints'])
    with col2:
        st.metric("🔴 Critical PII", metrics['total_critical'])
    with col3:
        st.metric("🟡 High PII", metrics['total_high'])
    with col4:
        st.metric("🟢 Low PII", metrics.get('total_low', 0))
    with col5:
        st.metric("⚠️ Risk Score", f"{metrics['risk_score']:.1f}")


def display_endpoint_metrics(endpoint):
    """Display metrics for a single endpoint."""
    critical_pii = endpoint.get('critical_pii', [])
    high_pii = endpoint.get('high_pii', [])
    medium_pii = endpoint.get('medium_pii', [])
    low_pii = endpoint.get('low_pii', [])
    
    all_pii = critical_pii + high_pii + medium_pii + low_pii
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🔴 Critical", len(critical_pii))
    with col2:
        st.metric("🟡 High", len(high_pii))
    with col3:
        st.metric("🟠 Medium", len(medium_pii))
    with col4:
        st.metric("🟢 Low", len(low_pii))
    with col5:
        st.metric("📊 Total", len(all_pii))


def display_api_breakdown(api_groups):
    """Display API breakdown with expandable sections."""
    for api_title, api_endpoints in api_groups.items():
        api_critical = sum(len(ep.get('critical_pii', [])) for ep in api_endpoints)
        api_high = sum(len(ep.get('high_pii', [])) for ep in api_endpoints)
        
        with st.expander(f"🌐 {api_title} ({len(api_endpoints)} endpoints)", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("🔴 Critical", api_critical)
            with col2:
                st.metric("🟡 High", api_high)
            with col3:
                st.metric("📋 Endpoints", len(api_endpoints))
            
            # Show endpoints in this API
            for ep in api_endpoints:
                critical_count = len(ep.get('critical_pii', []))
                high_count = len(ep.get('high_pii', []))
                
                if critical_count > 0 or high_count > 0:
                    severity_icon = "🔴" if critical_count > 0 else "🟡"
                    st.write(f"{severity_icon} **{ep['http_method']}** `{ep['endpoint_path']}` (🔴{critical_count} 🟡{high_count})")
                else:
                    st.write(f"✅ **{ep['http_method']}** `{ep['endpoint_path']}` (No PII)")


def display_pii_endpoints_list(endpoints):
    """Display list of endpoints with PII."""
    pii_endpoints = [ep for ep in endpoints if ep.get('critical_pii') or ep.get('high_pii') or ep.get('medium_pii') or ep.get('low_pii')]
    
    if pii_endpoints:
        for ep in pii_endpoints:
            critical_count = len(ep.get('critical_pii', []))
            high_count = len(ep.get('high_pii', []))
            medium_count = len(ep.get('medium_pii', []))
            low_count = len(ep.get('low_pii', []))
            
            # Determine severity icon
            if critical_count > 0:
                severity_icon = "🔴"
            elif high_count > 0:
                severity_icon = "🟡"
            elif medium_count > 0:
                severity_icon = "🟠"
            elif low_count > 0:
                severity_icon = "🟢"
            else:
                severity_icon = "✅"
            
            with st.expander(f"{severity_icon} {ep['http_method']} {ep['endpoint_path']} (🔴{critical_count} 🟡{high_count} 🟠{medium_count} 🟢{low_count})"):
                # Show PII details
                if ep.get('critical_pii'):
                    st.write("**🔴 Critical PII:**")
                    for pii in ep['critical_pii']:
                        st.write(f"  - `{pii['field_path']}` ({pii['pii_type']})")
                
                if ep.get('high_pii'):
                    st.write("**🟡 High PII:**")
                    for pii in ep['high_pii']:
                        st.write(f"  - `{pii['field_path']}` ({pii['pii_type']})")
                
                if ep.get('medium_pii'):
                    st.write("**🟠 Medium PII:**")
                    for pii in ep['medium_pii']:
                        st.write(f"  - `{pii['field_path']}` ({pii['pii_type']})")
                
                if ep.get('low_pii'):
                    st.write("**🟢 Low PII:**")
                    for pii in ep['low_pii']:
                        st.write(f"  - `{pii['field_path']}` ({pii['pii_type']})")
    else:
        st.success("✅ No endpoints with PII found!")


def create_endpoint_selector(endpoints):
    """Create endpoint selector dropdown."""
    endpoint_options = []
    
    for ep in endpoints:
        critical_count = len(ep.get('critical_pii', []))
        high_count = len(ep.get('high_pii', []))
        medium_count = len(ep.get('medium_pii', []))
        
        # Create risk indicator
        if critical_count > 0:
            risk_indicator = "🔴"
        elif high_count > 0:
            risk_indicator = "🟡"
        elif medium_count > 0:
            risk_indicator = "🟠"
        else:
            risk_indicator = "✅"
        
        option_text = f"{risk_indicator} {ep['http_method']} {ep['endpoint_path']} (🔴{critical_count} 🟡{high_count} 🟠{medium_count})"
        endpoint_options.append(option_text)
    
    selected_endpoint = st.selectbox(
        "Choose an endpoint:",
        endpoint_options,
        help="Select an endpoint to view its detailed PII analysis"
    )
    
    # Find selected endpoint data
    selected_endpoint_data = None
    for ep in endpoints:
        critical_count = len(ep.get('critical_pii', []))
        high_count = len(ep.get('high_pii', []))
        medium_count = len(ep.get('medium_pii', []))
        
        if critical_count > 0:
            risk_indicator = "🔴"
        elif high_count > 0:
            risk_indicator = "🟡"
        elif medium_count > 0:
            risk_indicator = "🟠"
        else:
            risk_indicator = "✅"
        
        option_text = f"{risk_indicator} {ep['http_method']} {ep['endpoint_path']} (🔴{critical_count} 🟡{high_count} 🟠{medium_count})"
        if option_text == selected_endpoint:
            selected_endpoint_data = ep
            break
    
    return selected_endpoint_data


def display_schema_tabs(simple_schemas, all_pii, highlight_pii_func):
    """Display schema tabs with PII highlighting."""
    tab1, tab2 = st.tabs(["📤 Request", "📥 Response"])
    
    with tab1:
        if simple_schemas.get('request_body'):
            highlighted_request = highlight_pii_func(simple_schemas['request_body'], all_pii)
            st.json(highlighted_request)
        else:
            st.info("No request body schema")
    
    with tab2:
        if simple_schemas.get('response_body'):
            highlighted_response = highlight_pii_func(simple_schemas['response_body'], all_pii)
            st.json(highlighted_response)
        else:
            st.info("No response body schema")


def display_pii_fields_fallback(all_pii):
    """Display PII fields when schema is not available."""
    st.subheader("🔴 PII Fields Detected")
    for pii in all_pii:
        severity_icon = "🔴" if pii.get('severity') == 'critical' else "🟡" if pii.get('severity') == 'high' else "🟠"
        st.write(f"{severity_icon} `{pii.get('field_path')}` - {pii.get('pii_type')} ({pii.get('severity')})")
