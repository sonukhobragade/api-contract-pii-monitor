#!/usr/bin/env python3
"""
Charts Component
Handles all chart visualizations and graphs
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def create_pii_severity_chart(results):
    """Create PII severity breakdown chart."""
    if not results:
        return
    
    pii_breakdown = results.get('overall_summary', {}).get('pii_breakdown', {})
    
    # Prepare data for chart
    severity_data = {
        'Severity': ['Critical', 'High', 'Medium', 'Low'],
        'Count': [
            pii_breakdown.get('critical', 0),
            pii_breakdown.get('high', 0),
            pii_breakdown.get('medium', 0),
            pii_breakdown.get('low', 0)
        ],
        'Color': ['#d32f2f', '#ff9800', '#ffc107', '#4caf50']
    }
    
    df = pd.DataFrame(severity_data)
    
    fig = px.bar(
        df,
        x='Severity',
        y='Count',
        color='Color',
        title="PII Severity Distribution",
        color_discrete_map={
            '#d32f2f': '#d32f2f',
            '#ff9800': '#ff9800',
            '#ffc107': '#ffc107',
            '#4caf50': '#4caf50'
        }
    )
    
    fig.update_layout(
        xaxis_title="PII Severity",
        yaxis_title="Count",
        showlegend=False,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_api_breakdown_chart(results):
    """Create API breakdown chart."""
    if not results:
        return
    
    api_summaries = results.get('api_summaries', {})
    
    if not api_summaries:
        return
    
    # Prepare data for chart
    api_data = []
    for api_id, api_info in api_summaries.items():
        api_data.append({
            'API': api_info.get('title', api_id),
            'Endpoints': api_info.get('endpoints_analyzed', 0),
            'Total PII': api_info.get('total_pii_found', 0),
            'Critical PII': api_info.get('critical_pii', 0),
            'High PII': api_info.get('high_pii', 0),
            'Compliance Score': api_info.get('avg_compliance_score', 0)
        })
    
    df = pd.DataFrame(api_data)
    
    # Create subplot with multiple charts
    fig = go.Figure()
    
    # Add bar chart for PII counts
    fig.add_trace(go.Bar(
        name='Total PII',
        x=df['API'],
        y=df['Total PII'],
        marker_color='#ff6b6b'
    ))
    
    fig.add_trace(go.Bar(
        name='Critical PII',
        x=df['API'],
        y=df['Critical PII'],
        marker_color='#d32f2f'
    ))
    
    fig.add_trace(go.Bar(
        name='High PII',
        x=df['API'],
        y=df['High PII'],
        marker_color='#ff9800'
    ))
    
    fig.update_layout(
        title="PII Distribution by API",
        xaxis_title="API",
        yaxis_title="PII Count",
        barmode='stack',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_compliance_gauge(results):
    """Create compliance score gauge chart."""
    if not results:
        return
    
    compliance = results.get('overall_summary', {}).get('summary', {}).get('average_compliance_score', 0)
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=compliance,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Overall Compliance Score"},
        delta={'reference': 100},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 75], 'color': "yellow"},
                {'range': [75, 90], 'color': "lightgreen"},
                {'range': [90, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

def create_pii_type_analysis(results):
    """Create PII type analysis chart."""
    if not results:
        return
    
    detailed_results = results.get('detailed_results', [])
    
    # Collect all PII types
    pii_types = {}
    for endpoint in detailed_results:
        for pii_list in [endpoint.get('critical_pii', []), 
                        endpoint.get('high_pii', []), 
                        endpoint.get('medium_pii', []), 
                        endpoint.get('low_pii', [])]:
            for pii in pii_list:
                pii_type = pii.get('pii_type', 'Unknown')
                pii_types[pii_type] = pii_types.get(pii_type, 0) + 1
    
    if not pii_types:
        return
    
    # Create pie chart
    fig = px.pie(
        values=list(pii_types.values()),
        names=list(pii_types.keys()),
        title="PII Types Distribution"
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def create_priority_timeline_chart(results):
    """Create priority timeline chart showing PII by priority."""
    if not results:
        return
    
    detailed_results = results.get('detailed_results', [])
    
    # Collect priority data
    priority_data = []
    for endpoint in detailed_results:
        critical_count = len(endpoint.get('critical_pii', []))
        high_count = len(endpoint.get('high_pii', []))
        medium_count = len(endpoint.get('medium_pii', []))
        low_count = len(endpoint.get('low_pii', []))
        
        if critical_count > 0 or high_count > 0:
            priority_data.append({
                'Endpoint': f"{endpoint['http_method']} {endpoint['endpoint_path']}",
                'Critical': critical_count,
                'High': high_count,
                'Medium': medium_count,
                'Low': low_count,
                'Total': endpoint.get('total_pii_found', 0),
                'Compliance': endpoint.get('compliance_score', 0)
            })
    
    if not priority_data:
        return
    
    df = pd.DataFrame(priority_data)
    df = df.sort_values(['Critical', 'High', 'Medium'], ascending=[False, False, False])
    
    # Create horizontal bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Critical',
        y=df['Endpoint'],
        x=df['Critical'],
        orientation='h',
        marker_color='#d32f2f'
    ))
    
    fig.add_trace(go.Bar(
        name='High',
        y=df['Endpoint'],
        x=df['High'],
        orientation='h',
        marker_color='#ff9800'
    ))
    
    fig.add_trace(go.Bar(
        name='Medium',
        y=df['Endpoint'],
        x=df['Medium'],
        orientation='h',
        marker_color='#ffc107'
    ))
    
    fig.update_layout(
        title="PII Priority by Endpoint",
        xaxis_title="PII Count",
        yaxis_title="Endpoint",
        barmode='stack',
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
