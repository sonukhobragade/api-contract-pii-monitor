#!/usr/bin/env python3
"""
Filters Component
Handles filtering and sorting of PII data
"""

import streamlit as st

def create_priority_filters():
    """Create priority and severity filters in sidebar."""
    st.sidebar.subheader("🎯 Priority Filters")
    
    # Priority level filter
    priority_levels = st.sidebar.multiselect(
        "Priority Level",
        ["Critical", "High", "Medium", "Low"],
        default=["Critical", "High"],
        help="Select priority levels to display"
    )
    
    # API filter
    api_options = st.sidebar.multiselect(
        "API",
        ["Orders API", "Billing API"],
        default=["Orders API", "Billing API"],
        help="Select APIs to analyze"
    )
    
    # Compliance score filter
    min_compliance = st.sidebar.slider(
        "Minimum Compliance Score (%)",
        min_value=0,
        max_value=100,
        value=0,
        help="Filter endpoints by minimum compliance score"
    )
    
    # PII type filter
    pii_types = st.sidebar.multiselect(
        "PII Types",
        ["bank_account_number", "phone_number", "email_address", "full_name", "user_id", "physical_address"],
        default=["bank_account_number", "phone_number", "email_address"],
        help="Select PII types to focus on"
    )
    
    return {
        'priority_levels': priority_levels,
        'api_options': api_options,
        'min_compliance': min_compliance,
        'pii_types': pii_types
    }

def filter_endpoints_by_priority(results, filters):
    """Filter endpoints based on priority filters."""
    if not results or not filters:
        return results.get('detailed_results', [])
    
    detailed_results = results.get('detailed_results', [])
    filtered_results = []
    
    for endpoint in detailed_results:
        # Check API filter
        if endpoint.get('api_title') not in filters['api_options']:
            continue
        
        # Check compliance score filter
        if endpoint.get('compliance_score', 100) < filters['min_compliance']:
            continue
        
        # Check priority levels
        has_priority_pii = False
        for priority in filters['priority_levels']:
            if priority.lower() == 'critical' and endpoint.get('critical_pii'):
                has_priority_pii = True
                break
            elif priority.lower() == 'high' and endpoint.get('high_pii'):
                has_priority_pii = True
                break
            elif priority.lower() == 'medium' and endpoint.get('medium_pii'):
                has_priority_pii = True
                break
            elif priority.lower() == 'low' and endpoint.get('low_pii'):
                has_priority_pii = True
                break
        
        if not has_priority_pii:
            continue
        
        # Check PII types filter
        if filters['pii_types']:
            has_target_pii = False
            all_pii = (endpoint.get('critical_pii', []) + 
                      endpoint.get('high_pii', []) + 
                      endpoint.get('medium_pii', []) + 
                      endpoint.get('low_pii', []))
            
            for pii in all_pii:
                if pii.get('pii_type') in filters['pii_types']:
                    has_target_pii = True
                    break
            
            if not has_target_pii:
                continue
        
        filtered_results.append(endpoint)
    
    return filtered_results

def create_sorting_options():
    """Create sorting options in sidebar."""
    st.sidebar.subheader("📊 Sort Options")
    
    sort_by = st.sidebar.selectbox(
        "Sort by",
        ["Priority (Critical First)", "Compliance Score", "Total PII", "Endpoint Path"],
        help="Choose how to sort the results"
    )
    
    sort_order = st.sidebar.selectbox(
        "Sort Order",
        ["Descending", "Ascending"],
        help="Choose sort order"
    )
    
    return {
        'sort_by': sort_by,
        'sort_order': sort_order
    }

def sort_endpoints(endpoints, sort_options):
    """Sort endpoints based on sort options."""
    if not endpoints or not sort_options:
        return endpoints
    
    reverse = sort_options['sort_order'] == 'Descending'
    
    if sort_options['sort_by'] == "Priority (Critical First)":
        return sorted(endpoints, 
                     key=lambda x: (len(x.get('critical_pii', [])), 
                                  len(x.get('high_pii', [])), 
                                  len(x.get('medium_pii', []))), 
                     reverse=reverse)
    
    elif sort_options['sort_by'] == "Compliance Score":
        return sorted(endpoints, 
                     key=lambda x: x.get('compliance_score', 0), 
                     reverse=reverse)
    
    elif sort_options['sort_by'] == "Total PII":
        return sorted(endpoints, 
                     key=lambda x: x.get('total_pii_found', 0), 
                     reverse=reverse)
    
    elif sort_options['sort_by'] == "Endpoint Path":
        return sorted(endpoints, 
                     key=lambda x: x.get('endpoint_path', ''), 
                     reverse=reverse)
    
    return endpoints
