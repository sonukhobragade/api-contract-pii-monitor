#!/usr/bin/env python3
"""
PII Dashboard - Main Application
Interactive Streamlit dashboard for visualizing PII analysis results.
"""

import streamlit as st
import pandas as pd
import json
import sys
import plotly.express as px
import os
import ast
import re
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv


# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Load environment variables from .env file
env_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Define color map for severity levels
color_map = {
    "Critical": "#FF0000",  # Red
    "High": "#FF8C00",      # Dark Orange
    "Medium": "#FFD700",    # Gold
    "Low": "#32CD32"        # Lime Green
}

# Get non-PII fields from environment variable
non_pii_env = os.environ.get('NON_PII_FIELDS', '["user_id","id","uuid"]')

try:
    # Try to parse as array
    non_pii_identifiers = ast.literal_eval(non_pii_env)
    if not isinstance(non_pii_identifiers, list):
        # If not a list, fall back to default
        non_pii_identifiers = ["user_id", "id", "uuid"]
except (SyntaxError, ValueError):
    # If parsing fails, fall back to comma-separated format
    non_pii_identifiers = [field.strip() for field in non_pii_env.split(',')]

# Compile regex patterns for faster matching
non_pii_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in non_pii_identifiers]

# File uploader outside of cached function
def get_uploaded_file():
    """
    Get uploaded file from user.
    
    Returns:
        Uploaded file object or None
    """
    return st.file_uploader("Upload PII analysis report (JSON)", type="json")

@st.cache_data
def load_pii_data(file_path, uploaded_file=None):
    """
    Load PII analysis data from JSON file with caching.
    
    Args:
        file_path: Path to the JSON file
        uploaded_file: Uploaded file object from st.file_uploader
        
    Returns:
        Dictionary containing the PII analysis data
    """
    try:
        if uploaded_file is not None:
            # If user uploads a file, use that
            data = json.load(uploaded_file)
        else:
            # Otherwise try to load from file path
            with open(file_path, 'r') as f:
                data = json.load(f)
                
        return data
    except Exception:
        return {}

def create_dataframes(data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    """
    Create pandas DataFrames from PII analysis data.
    
    Args:
        data: Dictionary containing the PII analysis data
        
    Returns:
        Dictionary of DataFrames for different aspects of the data
    """
    dataframes = {}
    
    # Create API summary DataFrame
    if "api_summaries" in data:
        api_data = []
        for api_id, summary in data["api_summaries"].items():
            summary["api_id"] = api_id
            api_data.append(summary)
        
        if api_data:
            api_df = pd.DataFrame(api_data)
            # Remove duplicates based on api_name if it exists
            if "api_name" in api_df.columns:
                api_df = api_df.drop_duplicates(subset=["api_name"])
            dataframes["api_summary"] = api_df
    
    # Extract detailed results
    if "detailed_results" in data:
        detailed_results = []
        pii_matches = []
        
        # Non-PII patterns already loaded at the top of the file
        
        # Handle detailed_results as a list of objects
        if isinstance(data["detailed_results"], list):
            for endpoint_data in data["detailed_results"]:
                # Create endpoint record
                endpoint_record = {
                    "api_name": endpoint_data.get("api_title", ""),  # Use api_title as api_name
                    "endpoint_path": endpoint_data.get("endpoint_path", ""),
                    "http_method": endpoint_data.get("http_method", ""),
                    "total_pii_found": endpoint_data.get("total_pii_found", 0),
                    "compliance_score": endpoint_data.get("compliance_score", 0)
                }
                detailed_results.append(endpoint_record)
                
                # Process PII matches from different severity categories
                for severity in ["critical_pii", "high_pii", "medium_pii", "low_pii"]:
                    severity_level = severity.split("_")[0]  # Extract severity level (critical, high, etc.)
                    
                    if severity in endpoint_data and isinstance(endpoint_data[severity], list):
                        for match in endpoint_data[severity]:
                            # Skip fields matching non-PII regex patterns unless they're in parameters
                            pii_type = match.get("pii_type", "").lower()
                            field_path = match.get("field_path", "")
                            
                            # Check if field path or pii_type matches any non-PII regex pattern
                            is_non_pii = False
                            for pattern in non_pii_patterns:
                                if pattern.search(field_path) or pattern.search(pii_type):
                                    is_non_pii = True
                                    break
                                    
                            if is_non_pii and "parameter" not in match.get("context", "").lower():
                                continue
                            
                            # Add severity level to match data
                            match_with_severity = match.copy()
                            match_with_severity["severity_level"] = severity_level
                            
                            # Format PII data as JSON for better display
                            pii_data = {
                                "api_name": endpoint_data.get("api_title", ""),
                                "endpoint_path": endpoint_data.get("endpoint_path", ""),
                                "http_method": endpoint_data.get("http_method", ""),
                                "pii_type": match.get("pii_type", ""),
                                "severity_level": severity_level,
                                "field_path": match.get("field_path", ""),
                                "context": match.get("context", ""),
                                "pii_data": json.dumps(match_with_severity, indent=2)  # Store full PII data as JSON
                            }
                            pii_matches.append(pii_data)
        # Handle detailed_results as a dictionary (for backward compatibility)
        elif isinstance(data["detailed_results"], dict):
            for api_name, endpoints in data["detailed_results"].items():
                for endpoint_path, endpoint_data in endpoints.items():
                    # Create endpoint record
                    endpoint_record = {
                        "api_name": api_name,
                        "endpoint_path": endpoint_path,
                        "http_method": endpoint_data.get("http_method", ""),
                        "total_pii_found": endpoint_data.get("total_pii_found", 0),
                        "compliance_score": endpoint_data.get("compliance_score", 0)
                    }
                    detailed_results.append(endpoint_record)
                    
                    # Process PII matches
                    if "pii_matches" in endpoint_data and endpoint_data["pii_matches"]:
                        for match in endpoint_data["pii_matches"]:
                            # Skip fields matching non-PII regex patterns unless they're in parameters
                            pii_type = match.get("pii_type", "").lower()
                            field_path = match.get("field_path", "")
                            
                            # Check if field path or pii_type matches any non-PII regex pattern
                            is_non_pii = False
                            for pattern in non_pii_patterns:
                                if pattern.search(field_path) or pattern.search(pii_type):
                                    is_non_pii = True
                                    break
                                    
                            if is_non_pii and "parameter" not in match.get("context", "").lower():
                                continue
                            
                            # Format PII data as JSON for better display
                            pii_data = {
                                "api_name": api_name,
                                "endpoint_path": endpoint_path,
                                "http_method": endpoint_data.get("http_method", ""),
                                "pii_type": match.get("pii_type", ""),
                                "severity_level": match.get("severity_level", ""),
                                "field_path": match.get("field_path", ""),
                                "context": match.get("context", ""),
                                "pii_data": json.dumps(match, indent=2)  # Store full PII data as JSON
                            }
                            pii_matches.append(pii_data)
        
        if detailed_results:
            dataframes["detailed_results"] = pd.DataFrame(detailed_results)
        
        if pii_matches:
            # Create DataFrame and drop duplicates
            pii_df = pd.DataFrame(pii_matches)
            # Drop duplicates based on endpoint_path, http_method, pii_type, field_path
            pii_df = pii_df.drop_duplicates(subset=["endpoint_path", "http_method", "pii_type", "field_path"])
            dataframes["pii_matches"] = pii_df
    
    # Extract PII breakdown
    if "overall_summary" in data and "pii_breakdown" in data["overall_summary"]:
        pii_breakdown = data["overall_summary"]["pii_breakdown"]
        dataframes["pii_breakdown"] = pii_breakdown
    
    return dataframes

def main():
    """Main function to run the Streamlit app."""
    # Set page title and layout
    st.set_page_config(
        page_title="PII API Analyzer Dashboard",
        page_icon="🔒",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # No helper functions needed for basic dashboard

    # Display header
    st.title("🔒 PII Analysis Dashboard")
    st.markdown("This dashboard provides interactive visualization of Personally Identifiable Information (PII) detected in API schemas. Use the filters in the sidebar to explore different aspects of the data.")
    
    # Sidebar for file selection and filters
    st.sidebar.header("📊 Dashboard Controls")
    
    # Default file path
    default_file = "fast_pii_analysis_report.json"
    
    # Check if file path is provided as command line argument
    if len(sys.argv) > 1 and sys.argv[1] == '--file':
        if len(sys.argv) > 2:
            default_file = sys.argv[2]
    
    # File selection
    file_path = st.sidebar.text_input("PII Analysis File Path", value=default_file)
    
    # Get uploaded file (outside of cached function)
    uploaded_file = get_uploaded_file()
    
    # Load PII data
    data = load_pii_data(file_path, uploaded_file)
    
    if not data:
        st.error("Error loading PII data. Please check the file path or upload a file.")
        st.warning("No data loaded. Please check the file path or upload a file.")
        return
    
    st.success("PII data loaded successfully!")
    
    # Create dataframes
    dataframes = create_dataframes(data)
    
    # Display analysis timestamp and performance metrics
    if "analysis_timestamp" in data:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Analysis Date", datetime.fromisoformat(data["analysis_timestamp"]).strftime("%Y-%m-%d %H:%M"))
        with col2:
            st.metric("Processing Time", f"{data.get('processing_time_seconds', 0):.2f} seconds")
        with col3:
            st.metric("Endpoints/Second", f"{data.get('endpoints_per_second', 0):.1f}")
    
    # Display overall summary
    st.header("📈 Overall Summary")
    if "overall_summary" in data:
        # Extract summary data with fallbacks for different JSON structures
        if "summary" in data["overall_summary"]:
            summary = data["overall_summary"]["summary"]
        else:
            summary = {}
            
        if "pii_breakdown" in data["overall_summary"]:
            pii_breakdown = data["overall_summary"]["pii_breakdown"]
        else:
            pii_breakdown = {}
        
        # Calculate metrics from dataframes if available
        total_apis = 0
        total_endpoints = 0
        total_pii = 0
        avg_compliance = 0
        
        # Try to get metrics from summary first
        total_apis = summary.get("total_apis", data.get("total_apis_analyzed", 0))
        total_endpoints = summary.get("total_endpoints_analyzed", summary.get("total_endpoints", 0))
        total_pii = pii_breakdown.get("total", summary.get("total_pii_found", 0))
        avg_compliance = summary.get("average_compliance_score", summary.get("avg_compliance_score", 0))
        
        # If metrics are still 0, calculate from dataframes
        if "detailed_results" in dataframes and total_apis == 0:
            # Count unique APIs
            if "api_name" in dataframes["detailed_results"].columns:
                total_apis = dataframes["detailed_results"]["api_name"].nunique()
                
        if "detailed_results" in dataframes and total_endpoints == 0:
            # Count total endpoints
            total_endpoints = len(dataframes["detailed_results"])
            
        if "pii_matches" in dataframes and total_pii == 0:
            # Count total PII findings
            total_pii = len(dataframes["pii_matches"])
            
        if "detailed_results" in dataframes and avg_compliance == 0 and "compliance_score" in dataframes["detailed_results"].columns:
            # Calculate average compliance score
            avg_compliance = dataframes["detailed_results"]["compliance_score"].mean()
            if pd.isna(avg_compliance):
                avg_compliance = 0
        
        # Display metrics with enhanced styling
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total APIs", int(total_apis))
        with col2:
            st.metric("Total Endpoints", int(total_endpoints))
        with col3:
            st.metric("Total PII Found", int(total_pii))
        with col4:
            st.metric("Avg. Compliance Score", f"{avg_compliance:.1f}/100")
            
        # No custom styling needed for basic dashboard
        
        # Simple sidebar header
        with st.sidebar:
            st.subheader("PII Security")
            st.info("This dashboard helps you identify and analyze PII in your API schemas.")
        
        # PII breakdown chart
        st.subheader("PII Severity Breakdown")
        
        # Get counts from pii_breakdown first
        critical_count = pii_breakdown.get("critical", pii_breakdown.get("critical_pii", 0))
        high_count = pii_breakdown.get("high", pii_breakdown.get("high_pii", 0))
        medium_count = pii_breakdown.get("medium", pii_breakdown.get("medium_pii", 0))
        low_count = pii_breakdown.get("low", pii_breakdown.get("low_pii", 0))
        
        # If all counts are 0, try to calculate from pii_matches dataframe
        if critical_count == 0 and high_count == 0 and medium_count == 0 and low_count == 0:
            if "pii_matches" in dataframes and not dataframes["pii_matches"].empty:
                # Count occurrences of each severity level
                severity_counts = dataframes["pii_matches"]["severity_level"].value_counts()
                critical_count = severity_counts.get("critical", 0)
                high_count = severity_counts.get("high", 0)
                medium_count = severity_counts.get("medium", 0)
                low_count = severity_counts.get("low", 0)
        
        pii_df = pd.DataFrame({
            "Severity": ["Critical", "High", "Medium", "Low"],
            "Count": [
                critical_count,
                high_count,
                medium_count,
                low_count
            ]
        })
        
        fig = px.bar(
            pii_df,
            x="Severity",
            y="Count",
            color="Severity",
            color_discrete_map=color_map,
            title="PII Findings by Severity Level (Click to Filter)",
            labels={"Count": "Number of Findings", "Severity": "Severity Level"}
        )
        
        # Add severity filter for PII chart
        severity_options = ["All", "Critical", "High", "Medium", "Low"]
        selected_severity = st.selectbox("Filter by Severity", options=severity_options, key="chart_severity_filter")
        
        # Show the chart first with a unique key
        st.plotly_chart(fig, use_container_width=True, key="severity_breakdown_chart")
        
        # Show filtered data based on severity selection
        if selected_severity != "All" and "pii_matches" in dataframes:
            # Use the selected severity from the dropdown
            severity_lower = selected_severity.lower()
            
            # Filter PII matches by the selected severity
            severity_filtered_df = dataframes["pii_matches"][dataframes["pii_matches"]["severity_level"] == severity_lower]
            
            # Show the filtered data
            st.subheader(f"Selected: {selected_severity} Severity PII Findings")
            
            if not severity_filtered_df.empty:
                # Use simple dataframe display
                st.dataframe(
                    severity_filtered_df[['endpoint_path', 'http_method', 'pii_type', 'field_path', 'context']],
                    use_container_width=True
                )
            else:
                st.info(f"No {selected_severity} severity PII findings found.")
        # No else needed since we're always showing the chart
        
        # Most common PII types
        st.subheader("Most Common PII Types")
        if "most_common_pii_types" in data["overall_summary"]:
            most_common = data["overall_summary"]["most_common_pii_types"]
            
            # Handle list of lists format: [["pii_type", count], ...]
            if isinstance(most_common, list):
                if most_common and isinstance(most_common[0], list) and len(most_common[0]) == 2:
                    # Convert list of lists to DataFrame with proper columns
                    pii_types_df = pd.DataFrame(most_common, columns=["pii_type", "count"])
                elif most_common and isinstance(most_common[0], dict):
                    # If it's a list of dictionaries with 'PII Type' and 'Count' keys
                    pii_types_df = pd.DataFrame(most_common)
                    pii_types_df.columns = [col.lower() for col in pii_types_df.columns]
                    if "pii type" in pii_types_df.columns:
                        pii_types_df.rename(columns={"pii type": "pii_type"}, inplace=True)
                    if "count" not in pii_types_df.columns and "pii_type" in pii_types_df.columns:
                        pii_types_df["count"] = range(len(pii_types_df), 0, -1)
                else:
                    # If it's just a list of PII types without counts
                    pii_types_df = pd.DataFrame({"pii_type": most_common, "count": range(len(most_common), 0, -1)})
            elif isinstance(most_common, dict):
                # If it's a dictionary with PII types as keys and counts as values
                pii_types_df = pd.DataFrame({
                    "pii_type": list(most_common.keys()),
                    "count": list(most_common.values())
                })
            else:
                st.warning("Unexpected format for most common PII types")
                return
            
            # Create the chart with the correct column names
            fig = px.bar(
                pii_types_df,
                x="pii_type",
                y="count",
                title="Most Common PII Types",
                labels={"count": "Number of Occurrences", "pii_type": "PII Type"}
            )
            
            st.plotly_chart(fig, use_container_width=True, key="common_pii_types_chart")
    
    # API-level analysis
    st.header("🔍 API-Level Analysis")
    if "api_summary" in dataframes:
        api_df = dataframes["api_summary"]
        
        # API selection
        selected_api = st.selectbox(
            "Select API to analyze",
            options=api_df["title"].tolist(),
            format_func=lambda x: f"{x} ({api_df[api_df['title'] == x]['endpoints_analyzed'].values[0]} endpoints)",
            key="api_selection"
        )
        
        # Filter data for selected API
        api_data = api_df[api_df["title"] == selected_api].iloc[0]
        
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
            "Count": [api_data["critical_pii"], api_data["high_pii"], api_data["medium_pii"], api_data["low_pii"]]
        })
        
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
        
        st.plotly_chart(fig, use_container_width=True, key="api_pii_chart")
    
    # Endpoint-level analysis - Main section with PII findings
    st.header("🔌 Endpoint Analysis")
    
    # Skip the duplicate filters here since we'll use the ones in the 'Endpoints with PII' section below
    if "detailed_results" in dataframes and "pii_matches" in dataframes:
        detailed_df = dataframes["detailed_results"]
        matches_df = dataframes["pii_matches"]
        
        # Initialize filtered dataframes
        filtered_detailed_df = detailed_df.copy()
        filtered_matches_df = matches_df.copy()
        
        # Display endpoint table
        st.subheader("Endpoints with PII")
        display_columns = ["endpoint_path", "http_method", "total_pii_found", "compliance_score"]
        if "api_name" in filtered_detailed_df.columns:
            display_columns = ["api_name"] + display_columns
    
    # Continue with endpoint table display from previous section
        api_options = ["All"]
        if "api_name" in detailed_df.columns:
            api_options += sorted(detailed_df["api_name"].unique().tolist())
            
        selected_api_filter = st.selectbox("Filter by API", options=api_options)
        
        filtered_detailed_df = detailed_df.copy()
        filtered_matches_df = matches_df.copy()
            
        if selected_api_filter != "All":
            filtered_detailed_df = filtered_detailed_df[filtered_detailed_df["api_name"] == selected_api_filter]
            filtered_matches_df = filtered_matches_df[filtered_matches_df["api_name"] == selected_api_filter]
            
        # Filter by severity
        severity_options = ["All", "Critical", "High", "Medium", "Low"]
        selected_severity = st.selectbox("Filter by Severity", options=severity_options)
        
        if selected_severity != "All":
            severity_lower = selected_severity.lower()
            # Filter PII matches by severity
            filtered_matches_df = filtered_matches_df[filtered_matches_df["severity_level"] == severity_lower]
                
            # Get unique endpoints with the selected severity
            endpoints_with_severity = filtered_matches_df[["api_name", "endpoint_path"]].drop_duplicates()
                
            # Filter detailed_df to only show endpoints with the selected severity
            if not endpoints_with_severity.empty:
                filtered_detailed_df = pd.merge(
                    filtered_detailed_df,
                    endpoints_with_severity,
                    on=["api_name", "endpoint_path"],
                    how="inner"
                )
        
        # Display endpoint table
        st.subheader("Endpoints with PII")
        display_columns = ["endpoint_path", "http_method", "total_pii_found", "compliance_score"]
        if "api_name" in filtered_detailed_df.columns:
            display_columns = ["api_name"] + display_columns
                
        st.dataframe(
            filtered_detailed_df[display_columns],
            use_container_width=True
        )
        
        # Display PII matches in a simple table
        st.subheader("PII Matches")
        
        if not filtered_matches_df.empty:
            st.dataframe(
                filtered_matches_df[['endpoint_path', 'http_method', 'pii_type', 'severity_level', 'field_path', 'context']],
                use_container_width=True
            )
            
            # Show a few PII details in expandable sections
            st.subheader("PII Details")
            for _, row in filtered_matches_df.head(5).iterrows():
                with st.expander(f"{row['endpoint_path']} - {row['pii_type']}"):
                    st.json(json.loads(row['pii_data']) if isinstance(row['pii_data'], str) else row['pii_data'])
                    
            if len(filtered_matches_df) > 5:
                st.info(f"Showing details for 5 of {len(filtered_matches_df)} matches.")
        else:
            st.info("No PII matches found with the current filters.")
            
        # Add PII type filter with endpoint filtering capability
        if not filtered_matches_df.empty:
            st.subheader("Filter by PII Type")
            pii_types = ["All"] + sorted(filtered_matches_df["pii_type"].unique().tolist())
            selected_pii_type = st.selectbox("Select PII Type", options=pii_types, key="pii_type_filter")
                
            if selected_pii_type != "All":
                # Filter matches by PII type
                filtered_by_type_df = filtered_matches_df[filtered_matches_df["pii_type"] == selected_pii_type]
                
                # Get unique endpoints containing this PII type
                endpoints_with_pii_type = filtered_by_type_df[["api_name", "endpoint_path", "http_method"]].drop_duplicates()
                
                # Display endpoints with this PII type
                st.subheader(f"Endpoints with {selected_pii_type} PII")
                st.dataframe(endpoints_with_pii_type, use_container_width=True)
                
                # Display detailed matches for this PII type
                st.subheader(f"Detailed {selected_pii_type} PII Matches")
                st.dataframe(
                    filtered_by_type_df[["endpoint_path", "http_method", "field_path", "context", "severity_level"]],
                    use_container_width=True
                )
                
                # Add a download button for the filtered data
                csv = filtered_by_type_df.to_csv(index=False)
                st.download_button(
                    label=f"Download {selected_pii_type} PII data",
                    data=csv,
                    file_name=f"{selected_pii_type.lower()}_pii_data.csv",
                    mime="text/csv"
                )
        
        # PII type filter is already implemented in the interactive tabs above
    
    # Compliance recommendations
    st.header("📋 Compliance Recommendations")
    if "overall_summary" in data and "compliance_recommendations" in data["overall_summary"]:
        recommendations = data["overall_summary"]["compliance_recommendations"]
        
        for rec in recommendations:
            st.markdown(f"- {rec}")
    
    # Risk assessment
    if "overall_summary" in data and "risk_assessment" in data["overall_summary"]:
        risk = data["overall_summary"]["risk_assessment"]
        
        st.header("⚠️ Risk Assessment")
        st.info(risk)
    
    # Footer
    st.markdown("---")
    st.markdown("PII Analysis Dashboard | Created with Streamlit")

if __name__ == "__main__":
    main()
