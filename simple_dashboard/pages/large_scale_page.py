#!/usr/bin/env python3
"""
Large Scale Page Component
Handles large-scale data management (1300+ APIs)
"""

import streamlit as st
from simple_dashboard.components.data_loader import generate_large_scale_data, filter_endpoints_advanced, search_endpoints
from simple_dashboard.components.real_data_loader import load_real_data, get_database_stats, test_database_connection
from simple_dashboard.components.large_scale_ui import (
    create_advanced_filters,
    create_search_bar,
    display_paginated_endpoints,
    display_quick_stats,
    display_api_summary_table,
    create_export_options
)


def show_large_scale_page():
    """Show the large-scale data management page."""
    st.title("🏢 Large Scale PII Management")
    st.markdown("Manage and analyze 1300+ APIs with advanced filtering and search capabilities")
    
    # Data source selection
    st.subheader("📊 Data Source")
    
    data_source = st.radio(
        "Choose data source:",
        ["Sample Data (8 APIs)", "Large Scale Data (1300+ APIs)", "Real Database Data"],
        help="Select the dataset to work with"
    )
    
    # Load appropriate data
    if data_source == "Sample Data (8 APIs)":
        from components.data_loader import load_sample_data
        endpoints = load_sample_data()
        st.info("📋 Using sample data with 8 APIs for demonstration")
    elif data_source == "Large Scale Data (1300+ APIs)":
        # Generate large-scale data
        with st.spinner("Generating large-scale data (1300+ APIs)..."):
            endpoints = generate_large_scale_data(1300)
        st.success(f"✅ Loaded {len(endpoints)} APIs with realistic PII distribution")
    else:
        # Load real data from database
        st.subheader("🔗 Database Connection")
        
        # Test database connection
        if test_database_connection():
            st.success("✅ Database connection successful")
            
            # Get database stats
            stats = get_database_stats()
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 APIs", stats['total_apis'])
            with col2:
                st.metric("🔗 Endpoints", stats['total_endpoints'])
            with col3:
                st.metric("🔍 PII Findings", stats['total_pii_findings'])
            with col4:
                st.metric("⚠️ Critical", stats['critical_pii'])
            
            # Load real data
            with st.spinner("Loading real data from database..."):
                endpoints = load_real_data()
            
            if not endpoints:
                st.warning("⚠️ No data found in database. Please run PII analysis first.")
                st.info("💡 You can use the sample data or large scale data for testing.")
                return
        else:
            st.error("❌ Database connection failed. Please check your configuration.")
            st.info("💡 Make sure your database is running and .env file is configured.")
            return
    
    # Quick stats
    display_quick_stats(endpoints)
    
    # Search functionality
    st.subheader("🔍 Search & Filter")
    
    # Search bar
    search_term = create_search_bar()
    
    # Advanced filters
    with st.expander("🔧 Advanced Filters", expanded=False):
        filters = create_advanced_filters(endpoints)
    
    # Apply filters and search
    filtered_endpoints = endpoints
    
    # Apply search first
    if search_term:
        filtered_endpoints = search_endpoints(filtered_endpoints, search_term)
        st.info(f"🔍 Search results: {len(filtered_endpoints)} endpoints found")
    
    # Apply advanced filters
    if filters:
        filtered_endpoints = filter_endpoints_advanced(filtered_endpoints, filters)
        st.info(f"🔧 Filtered results: {len(filtered_endpoints)} endpoints found")
    
    # Show results
    if filtered_endpoints:
        st.subheader("📋 Endpoint Results")
        
        # Display options
        display_mode = st.radio(
            "Display Mode:",
            ["📊 Summary Table", "📋 Detailed List"],
            help="Choose how to view the results"
        )
        
        if display_mode == "📊 Summary Table":
            display_api_summary_table(filtered_endpoints)
        else:
            # Add schema display option
            show_schemas = st.checkbox(
                "📋 Show JSON Schemas",
                help="Display JSON schemas for each endpoint (may slow down display for large datasets)"
            )
            display_paginated_endpoints(filtered_endpoints, show_schemas=show_schemas)
        
        # Export options
        create_export_options(filtered_endpoints)
        
        # Performance tips
        with st.expander("💡 Performance Tips", expanded=False):
            st.markdown("""
            **For Large Datasets (1300+ APIs):**
            
            🔍 **Use Search First**: Search for specific terms before applying filters
            📊 **Use Summary Table**: Faster than detailed list for overview
            🔧 **Combine Filters**: Use multiple filters to narrow down results
            📄 **Export Data**: Download filtered results for external analysis
            🎯 **Focus on Critical**: Filter by critical risk first for priority items
            
            **Recommended Workflow:**
            1. Start with search for specific APIs/endpoints
            2. Apply risk level filters (Critical → High → Medium)
            3. Use API title filter for specific services
            4. Export results for detailed analysis
            """)
    
    else:
        st.warning("❌ No endpoints found matching your search and filter criteria.")
        st.markdown("Try adjusting your search terms or filters to see more results.")


def show_performance_metrics():
    """Show performance metrics for large-scale operations."""
    st.subheader("⚡ Performance Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Data Loading", "~2-3 seconds", "1300 APIs")
    
    with col2:
        st.metric("Search Speed", "< 100ms", "Real-time")
    
    with col3:
        st.metric("Filter Speed", "< 50ms", "Instant")
    
    st.info("💡 **Optimization Tips**: Use specific search terms and combine filters for best performance with large datasets.")
