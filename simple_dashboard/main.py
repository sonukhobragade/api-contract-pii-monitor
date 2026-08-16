#!/usr/bin/env python3
"""
Simple PII Dashboard - Main
Modular dashboard with clean components
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from simple_dashboard.components.data_loader import load_real_pii_data
from simple_dashboard.pages.overview_page import show_overview_page
from simple_dashboard.pages.analysis_page import show_analysis_page
from simple_dashboard.pages.large_scale_page import show_large_scale_page

# Page configuration
st.set_page_config(
    page_title="Simple PII Dashboard",
    page_icon="🔒",
    layout="wide"
)


def main():
    """Main dashboard function with page navigation."""
    st.sidebar.title("🔒 PII Dashboard")
    
    # Page navigation
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["📊 Overview", "🔍 Analysis", "🏢 Large Scale"],
        help="Select which view you want to see"
    )
    
    # Load real PII data
    endpoints = load_real_pii_data()
    
    # Show selected page
    if page == "📊 Overview":
        show_overview_page(endpoints)
    elif page == "🔍 Analysis":
        show_analysis_page(endpoints)
    elif page == "🏢 Large Scale":
        show_large_scale_page()


if __name__ == "__main__":
    main()
