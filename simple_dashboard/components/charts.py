#!/usr/bin/env python3
"""
Charts Component
Visualizations for PII dashboard
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def create_pii_severity_chart(endpoints):
    """Create a pie chart showing PII severity distribution."""
    critical_count = sum(len(ep.get('critical_pii', [])) for ep in endpoints)
    high_count = sum(len(ep.get('high_pii', [])) for ep in endpoints)
    medium_count = sum(len(ep.get('medium_pii', [])) for ep in endpoints)
    low_count = sum(len(ep.get('low_pii', [])) for ep in endpoints)
    
    data = {
        'Severity': ['Critical', 'High', 'Medium', 'Low'],
        'Count': [critical_count, high_count, medium_count, low_count],
        'Color': ['#FF4444', '#FFAA00', '#FF8800', '#44FF44']
    }
    
    df = pd.DataFrame(data)
    
    fig = px.pie(
        df, 
        values='Count', 
        names='Severity',
        title='PII Severity Distribution',
        color_discrete_sequence=['#FF4444', '#FFAA00', '#FF8800', '#44FF44']
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400)
    
    return fig


def create_api_risk_chart(endpoints):
    """Create a bar chart showing risk levels by API."""
    api_groups = {}
    
    for ep in endpoints:
        api_title = ep.get('api_title', 'Unknown API')
        if api_title not in api_groups:
            api_groups[api_title] = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        api_groups[api_title]['critical'] += len(ep.get('critical_pii', []))
        api_groups[api_title]['high'] += len(ep.get('high_pii', []))
        api_groups[api_title]['medium'] += len(ep.get('medium_pii', []))
        api_groups[api_title]['low'] += len(ep.get('low_pii', []))
    
    # Prepare data for plotting
    api_names = list(api_groups.keys())
    critical_data = [api_groups[api]['critical'] for api in api_names]
    high_data = [api_groups[api]['high'] for api in api_names]
    medium_data = [api_groups[api]['medium'] for api in api_names]
    low_data = [api_groups[api]['low'] for api in api_names]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Critical',
        x=api_names,
        y=critical_data,
        marker_color='#FF4444'
    ))
    
    fig.add_trace(go.Bar(
        name='High',
        x=api_names,
        y=high_data,
        marker_color='#FFAA00'
    ))
    
    fig.add_trace(go.Bar(
        name='Medium',
        x=api_names,
        y=medium_data,
        marker_color='#FF8800'
    ))
    
    fig.add_trace(go.Bar(
        name='Low',
        x=api_names,
        y=low_data,
        marker_color='#44FF44'
    ))
    
    fig.update_layout(
        title='PII Risk by API',
        xaxis_title='API',
        yaxis_title='PII Count',
        barmode='stack',
        height=400
    )
    
    return fig


def create_endpoint_risk_scatter(endpoints):
    """Create a scatter plot showing endpoint risk levels."""
    data = []
    
    for ep in endpoints:
        critical_count = len(ep.get('critical_pii', []))
        high_count = len(ep.get('high_pii', []))
        medium_count = len(ep.get('medium_pii', []))
        low_count = len(ep.get('low_pii', []))
        
        # Calculate risk score
        risk_score = (critical_count * 4) + (high_count * 3) + (medium_count * 2) + (low_count * 1)
        
        # Determine risk level
        if critical_count > 0:
            risk_level = 'Critical'
            color = '#FF4444'
        elif high_count > 0:
            risk_level = 'High'
            color = '#FFAA00'
        elif medium_count > 0:
            risk_level = 'Medium'
            color = '#FF8800'
        elif low_count > 0:
            risk_level = 'Low'
            color = '#44FF44'
        else:
            risk_level = 'No Risk'
            color = '#00AA00'
        
        data.append({
            'Endpoint': f"{ep['http_method']} {ep['endpoint_path']}",
            'Risk Score': risk_score,
            'Risk Level': risk_level,
            'Critical': critical_count,
            'High': high_count,
            'Medium': medium_count,
            'Low': low_count,
            'Color': color
        })
    
    df = pd.DataFrame(data)
    
    fig = px.scatter(
        df,
        x='Risk Score',
        y='Endpoint',
        color='Risk Level',
        size='Critical',
        title='Endpoint Risk Distribution',
        color_discrete_map={
            'Critical': '#FF4444',
            'High': '#FFAA00',
            'Medium': '#FF8800',
            'Low': '#44FF44',
            'No Risk': '#00AA00'
        }
    )
    
    fig.update_layout(height=500)
    
    return fig


def create_pii_type_chart(endpoints):
    """Create a chart showing PII types distribution."""
    pii_types = {}
    
    for ep in endpoints:
        all_pii = ep.get('critical_pii', []) + ep.get('high_pii', []) + ep.get('medium_pii', []) + ep.get('low_pii', [])
        
        for pii in all_pii:
            pii_type = pii.get('pii_type', 'Unknown')
            if pii_type not in pii_types:
                pii_types[pii_type] = 0
            pii_types[pii_type] += 1
    
    if not pii_types:
        return None
    
    # Prepare data
    types = list(pii_types.keys())
    counts = list(pii_types.values())
    
    fig = px.bar(
        x=types,
        y=counts,
        title='PII Types Distribution',
        labels={'x': 'PII Type', 'y': 'Count'},
        color=counts,
        color_continuous_scale='Reds'
    )
    
    fig.update_layout(height=400)
    
    return fig


def create_risk_trend_chart(endpoints):
    """Create a line chart showing risk trends (mock data for now)."""
    # For now, we'll create a mock trend based on endpoint count
    # In a real scenario, this would show risk over time
    
    risk_data = {
        'Period': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
        'Critical Risk': [2, 3, 2, 3],
        'High Risk': [5, 6, 7, 5],
        'Medium Risk': [1, 2, 1, 1]
    }
    
    df = pd.DataFrame(risk_data)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['Period'],
        y=df['Critical Risk'],
        mode='lines+markers',
        name='Critical Risk',
        line=dict(color='#FF4444', width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Period'],
        y=df['High Risk'],
        mode='lines+markers',
        name='High Risk',
        line=dict(color='#FFAA00', width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=df['Period'],
        y=df['Medium Risk'],
        mode='lines+markers',
        name='Medium Risk',
        line=dict(color='#FF8800', width=3)
    ))
    
    fig.update_layout(
        title='PII Risk Trends (Last 4 Weeks)',
        xaxis_title='Time Period',
        yaxis_title='PII Count',
        height=400
    )
    
    return fig
