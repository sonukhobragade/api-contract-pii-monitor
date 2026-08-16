#!/usr/bin/env python3
"""
Details Component
Displays detailed PII findings and endpoint information
"""

import streamlit as st
import pandas as pd
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.openapi_querier import OpenAPIQuerier
from core.config import Config

def generate_simple_json_schema(openapi_schema):
    """
    Generate a simple, clean JSON schema from complex OpenAPI schema.
    
    Args:
        openapi_schema (dict): Raw OpenAPI schema from database
        
    Returns:
        dict: Simplified JSON schema
    """
    if not openapi_schema:
        return {}
    
    # If it's already a simple schema, return as is
    if isinstance(openapi_schema, dict) and 'type' in openapi_schema:
        return simplify_schema_object(openapi_schema)
    
    # Handle OpenAPI content structure
    if isinstance(openapi_schema, dict):
        # Look for application/json content
        if 'application/json' in openapi_schema:
            schema = openapi_schema['application/json'].get('schema', {})
            return simplify_schema_object(schema)
        
        # If it's a direct schema object
        if 'schema' in openapi_schema:
            return simplify_schema_object(openapi_schema['schema'])
        
        # If it's already a schema-like object
        if any(key in openapi_schema for key in ['type', 'properties', 'items']):
            return simplify_schema_object(openapi_schema)
    
    return {}

def simplify_schema_object(schema):
    """
    Simplify a schema object by removing OpenAPI-specific metadata.
    
    Args:
        schema (dict): Schema object to simplify
        
    Returns:
        dict: Simplified schema
    """
    if not isinstance(schema, dict):
        return schema
    
    simplified = {}
    
    # Copy basic type information
    if 'type' in schema:
        simplified['type'] = schema['type']
    
    # Handle object properties
    if 'properties' in schema and schema.get('type') == 'object':
        simplified['type'] = 'object'
        simplified['properties'] = {}
        simplified['required'] = schema.get('required', [])
        
        for prop_name, prop_schema in schema['properties'].items():
            simplified['properties'][prop_name] = simplify_schema_object(prop_schema)
    
    # Handle array items
    elif 'items' in schema and schema.get('type') == 'array':
        simplified['type'] = 'array'
        simplified['items'] = simplify_schema_object(schema['items'])
    
    # Handle primitive types with additional info
    elif 'type' in schema:
        simplified['type'] = schema['type']
        
        # Add format if it's meaningful
        if 'format' in schema:
            simplified['format'] = schema['format']
        
        # Add description if available
        if 'description' in schema:
            simplified['description'] = schema['description']
        
        # Add example if available
        if 'example' in schema:
            simplified['example'] = schema['example']
        
        # Add enum values if available
        if 'enum' in schema:
            simplified['enum'] = schema['enum']
    
    # Handle $ref references (simplify to just the reference name)
    elif '$ref' in schema:
        ref_path = schema['$ref']
        # Extract just the component name from the reference
        if '#' in ref_path and '/components/' in ref_path:
            component_name = ref_path.split('/')[-1]
            simplified['$ref'] = f"#/components/{component_name}"
        else:
            simplified['$ref'] = ref_path
    
    # Handle oneOf, anyOf, allOf
    elif 'oneOf' in schema:
        simplified['oneOf'] = [simplify_schema_object(item) for item in schema['oneOf']]
    elif 'anyOf' in schema:
        simplified['anyOf'] = [simplify_schema_object(item) for item in schema['anyOf']]
    elif 'allOf' in schema:
        simplified['allOf'] = [simplify_schema_object(item) for item in schema['allOf']]
    
    return simplified

def display_simple_json_schema(endpoint, pii):
    """Display simple, clean JSON schema for the endpoint with PII highlighting."""
    endpoint_path = endpoint.get('endpoint_path', '')
    http_method = endpoint.get('http_method', '')
    api_id = endpoint.get('api_id', '')
    context = pii.get('context', '').lower()
    
    try:
        # Initialize OpenAPI querier with config
        config = Config()
        querier = OpenAPIQuerier(config.get_connection_string())
        
        # Get actual schemas
        schemas = get_actual_schemas(querier, api_id, endpoint_path, http_method)
        
        if schemas:
            # Generate simple schemas
            simple_schemas = {}
            
            if schemas.get('request_body'):
                simple_schemas['request_body'] = generate_simple_json_schema(schemas['request_body'])
            
            if schemas.get('response_body'):
                simple_schemas['response_body'] = generate_simple_json_schema(schemas['response_body'])
            
            # Display based on context
            if 'request' in context and simple_schemas.get('request_body'):
                st.write("**📤 Request Body Schema:**")
                highlighted_schema = highlight_pii_in_simple_json(simple_schemas['request_body'], [pii])
                st.json(highlighted_schema)
            
            elif 'response' in context and simple_schemas.get('response_body'):
                st.write("**📥 Response Body Schema:**")
                highlighted_schema = highlight_pii_in_simple_json(simple_schemas['response_body'], [pii])
                st.json(highlighted_schema)
            
            else:
                # Show both if context is unclear
                if simple_schemas.get('request_body'):
                    st.write("**📤 Request Body Schema:**")
                    highlighted_schema = highlight_pii_in_simple_json(simple_schemas['request_body'], [pii])
                    st.json(highlighted_schema)
                
                if simple_schemas.get('response_body'):
                    st.write("**📥 Response Body Schema:**")
                    highlighted_schema = highlight_pii_in_simple_json(simple_schemas['response_body'], [pii])
                    st.json(highlighted_schema)
        else:
            st.warning("⚠️ Could not retrieve schemas from database")
            
    except Exception as e:
        st.error(f"Error displaying schema: {e}")

def highlight_pii_in_simple_json(schema, pii_fields):
    """Add PII highlighting to simple JSON schema."""
    if not schema or not pii_fields:
        return schema
    
    # Create a copy to avoid modifying the original
    highlighted_schema = json.loads(json.dumps(schema))
    
    # Add PII annotations to the schema
    for pii in pii_fields:
        field_path = pii.get('field_path', '')
        pii_type = pii.get('pii_type', 'Unknown')
        severity = pii.get('severity', 'Unknown')
        
        # Navigate to the field and add PII information
        add_pii_annotation_to_simple_schema(highlighted_schema, field_path, pii_type, severity)
    
    return highlighted_schema

def add_pii_annotation_to_simple_schema(schema, field_path, pii_type, severity):
    """Add PII annotation to a specific field in the simple schema."""
    if not field_path:
        return
    
    path_parts = field_path.split('.')
    current = schema
    
    # Navigate to the field
    for i, part in enumerate(path_parts[:-1]):
        if isinstance(current, dict):
            if 'properties' in current and part in current['properties']:
                current = current['properties']
            if part in current:
                current = current[part]
            else:
                return
    
    # Add PII annotation to the final field
    final_part = path_parts[-1]
    if isinstance(current, dict) and 'properties' in current and final_part in current['properties']:
        field_schema = current['properties'][final_part]
        
        # Add PII information
        field_schema['_pii_info'] = {
            'pii_type': pii_type,
            'severity': severity,
            'field_path': field_path,
            'description': f"🔴 {pii_type.replace('_', ' ').title()} - {severity.upper()} PII",
            'encryption_required': True,
            'masking_recommended': True
        }
        
        # Update the description to highlight PII
        if 'description' in field_schema:
            field_schema['description'] = f"🔴 {field_schema['description']} - {severity.upper()} PII"
        else:
            field_schema['description'] = f"🔴 {pii_type.replace('_', ' ').title()} - {severity.upper()} PII"

def display_critical_pii_details(results, filters=None):
    """Display detailed critical PII findings."""
    if not results:
        return
    
    detailed_results = results.get('detailed_results', [])
    critical_endpoints = []
    
    for endpoint in detailed_results:
        if endpoint.get('critical_pii'):
            critical_endpoints.append(endpoint)
    
    if not critical_endpoints:
        st.success("✅ No critical PII found!")
        return
    
    st.subheader("🚨 Critical PII Endpoints")
    
    for endpoint in critical_endpoints:
        with st.expander(f"🔴 {endpoint['http_method']} {endpoint['endpoint_path']} ({len(endpoint.get('critical_pii', []))} critical PII)", expanded=True):
            # Display simple PII details
            display_simple_pii_details(endpoint)

def display_endpoint_details_with_schemas(endpoint):
    """Display detailed information for a single endpoint with actual JSON schemas."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**API:** {endpoint.get('api_title', 'Unknown')}")
        st.write(f"**Compliance Score:** {endpoint.get('compliance_score', 0)}%")
        st.write(f"**Total PII Found:** {endpoint.get('total_pii_found', 0)}")
    
    with col2:
        st.write(f"**Critical PII:** {len(endpoint.get('critical_pii', []))}")
        st.write(f"**High PII:** {len(endpoint.get('high_pii', []))}")
        st.write(f"**Medium PII:** {len(endpoint.get('medium_pii', []))}")
    
    # Display PII details by severity with actual JSON schemas
    display_pii_by_severity_with_schemas(endpoint)

def display_pii_by_severity_with_schemas(endpoint):
    """Display PII details organized by severity with actual JSON schemas."""
    severities = [
        ('critical_pii', '🔴 Critical PII'),
        ('high_pii', '🟡 High PII'),
        ('medium_pii', '🟠 Medium PII'),
        ('low_pii', '🟢 Low PII')
    ]
    
    for pii_list_name, severity_label in severities:
        pii_list = endpoint.get(pii_list_name, [])
        if pii_list:
            st.write(f"**{severity_label}:**")
            for pii in pii_list:
                display_pii_item_with_schema(pii, endpoint)

def display_pii_item_with_schema(pii, endpoint):
    """Display a single PII item with actual JSON schema."""
    field_path = pii.get('field_path', '')
    pii_type = pii.get('pii_type', 'Unknown')
    severity = pii.get('severity', 'Unknown')
    context = pii.get('context', 'Unknown')
    
    # Create expandable section for each PII field
    with st.expander(f"🔴 {field_path} ({pii_type})", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Field Path:** `{field_path}`")
            st.write(f"**PII Type:** {pii_type}")
            st.write(f"**Severity:** {severity}")
            st.write(f"**Context:** {context}")
            
            # Show additional details if available
            if pii.get('pattern_matched'):
                st.write(f"**Pattern:** {pii.get('pattern_matched')}")
            if pii.get('confidence'):
                st.write(f"**Confidence:** {pii.get('confidence')}")
            if pii.get('description'):
                st.write(f"**Description:** {pii.get('description')}")
        
        with col2:
            # Display actual JSON schema for this endpoint
            display_actual_json_schema(endpoint, pii)

def display_actual_json_schema(endpoint, pii):
    """Display simple, clean JSON schema for the endpoint with PII highlighting."""
    # Use the new simple schema display function
    display_simple_json_schema(endpoint, pii)

def get_actual_schemas(querier, api_id, endpoint_path, http_method):
    """Get actual request/response schemas from database."""
    try:
        # Get endpoint details using path, method, and api_id
        endpoint_details = querier.get_endpoint_schema(endpoint_path, http_method, api_id)
        
        if not endpoint_details:
            return None
        
        schemas = {
            'request_body': None,
            'response_body': None,
            'parameters': []
        }
        
        # Get parameters
        if endpoint_details.get('parameters'):
            schemas['parameters'] = endpoint_details['parameters']
        
        # Get request bodies
        if endpoint_details.get('request_bodies'):
            # Get the first request body
            request_body = endpoint_details['request_bodies'][0]
            if request_body.get('content'):
                schemas['request_body'] = request_body['content']
        
        # Get responses
        if endpoint_details.get('responses'):
            # Find 200 response
            for response in endpoint_details['responses']:
                if response.get('status_code') == '200':
                    if response.get('content'):
                        schemas['response_body'] = response['content']
                    break
        
        return schemas
        
    except Exception as e:
        st.error(f"Error getting schemas: {e}")
        return None

def highlight_pii_in_json(schema, pii_fields):
    """Add PII highlighting information to JSON schema."""
    if not schema or not pii_fields:
        return schema
    
    # Create a copy to avoid modifying the original
    import json
    highlighted_schema = json.loads(json.dumps(schema))
    
    # Add PII annotations to the schema
    for pii in pii_fields:
        field_path = pii.get('field_path', '')
        pii_type = pii.get('pii_type', 'Unknown')
        severity = pii.get('severity', 'Unknown')
        
        # Navigate to the field and add PII information
        add_pii_annotation(highlighted_schema, field_path, pii_type, severity)
    
    return highlighted_schema

def add_pii_annotation(schema, field_path, pii_type, severity):
    """Add PII annotation to a specific field in the schema."""
    if not field_path:
        return
    
    path_parts = field_path.split('.')
    current = schema
    
    # Navigate to the field
    for i, part in enumerate(path_parts[:-1]):
        if isinstance(current, dict):
            if 'properties' in current and part in current['properties']:
                current = current['properties']
            if part in current:
                current = current[part]
            else:
                return
    
    # Add PII annotation to the final field
    final_part = path_parts[-1]
    if isinstance(current, dict) and 'properties' in current and final_part in current['properties']:
        field_schema = current['properties'][final_part]
        
        # Add PII information
        field_schema['_pii_info'] = {
            'pii_type': pii_type,
            'severity': severity,
            'field_path': field_path,
            'description': f"🔴 {pii_type.replace('_', ' ').title()} - {severity.upper()} PII",
            'encryption_required': True,
            'masking_recommended': True
        }
        
        # Update the description to highlight PII
        if 'description' in field_schema:
            field_schema['description'] = f"🔴 {field_schema['description']} - {severity.upper()} PII"
        else:
            field_schema['description'] = f"🔴 {pii_type.replace('_', ' ').title()} - {severity.upper()} PII"

def display_high_pii_summary(results, filters=None):
    """Display high PII endpoints summary."""
    if not results:
        return
    
    detailed_results = results.get('detailed_results', [])
    high_endpoints = [ep for ep in detailed_results if ep.get('high_pii')]
    
    if not high_endpoints:
        return
    
    st.subheader("⚠️ High PII Endpoints Summary")
    
    # Create a summary table
    high_data = []
    for endpoint in high_endpoints[:20]:  # Show top 20
        high_data.append({
            'Method': endpoint['http_method'],
            'Path': endpoint['endpoint_path'],
            'API': endpoint.get('api_title', 'Unknown'),
            'High PII Count': len(endpoint.get('high_pii', [])),
            'Compliance Score': f"{endpoint.get('compliance_score', 0)}%"
        })
    
    df = pd.DataFrame(high_data)
    st.dataframe(df, use_container_width=True)
    
    if len(high_endpoints) > 20:
        st.info(f"Showing top 20 of {len(high_endpoints)} high PII endpoints")

def display_endpoint_details(endpoint):
    """Display detailed information for a single endpoint."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**API:** {endpoint.get('api_title', 'Unknown')}")
        st.write(f"**Compliance Score:** {endpoint.get('compliance_score', 0)}%")
        st.write(f"**Total PII Found:** {endpoint.get('total_pii_found', 0)}")
    
    with col2:
        st.write(f"**Critical PII:** {len(endpoint.get('critical_pii', []))}")
        st.write(f"**High PII:** {len(endpoint.get('high_pii', []))}")
        st.write(f"**Medium PII:** {len(endpoint.get('medium_pii', []))}")
    
    # Display PII details by severity
    display_pii_by_severity(endpoint)

def display_pii_by_severity(endpoint):
    """Display PII details organized by severity."""
    severities = [
        ('critical_pii', '🔴 Critical PII'),
        ('high_pii', '🟡 High PII'),
        ('medium_pii', '🟠 Medium PII'),
        ('low_pii', '🟢 Low PII')
    ]
    
    for pii_list_name, severity_label in severities:
        pii_list = endpoint.get(pii_list_name, [])
        if pii_list:
            st.write(f"**{severity_label}:**")
            for pii in pii_list:
                display_pii_item(pii)

def display_pii_item(pii):
    """Display a single PII item."""
    st.write(f"- **{pii.get('pii_type', 'Unknown')}** in `{pii.get('field_name', 'Unknown')}`")
    st.write(f"  - Path: `{pii.get('field_path', 'Unknown')}`")
    st.write(f"  - Context: {pii.get('context', 'Unknown')}")
    
    # Show additional details if available
    if pii.get('pattern_matched'):
        st.write(f"  - Pattern: {pii.get('pattern_matched')}")
    if pii.get('confidence'):
        st.write(f"  - Confidence: {pii.get('confidence')}")
    if pii.get('description'):
        st.write(f"  - Description: {pii.get('description')}")

def display_filtered_endpoints(filtered_endpoints, sort_options):
    """Display filtered and sorted endpoints."""
    if not filtered_endpoints:
        st.info("No endpoints match the current filters")
        return
    
    st.subheader(f"📊 Filtered Results ({len(filtered_endpoints)} endpoints)")
    
    # Create summary table
    summary_data = []
    for endpoint in filtered_endpoints:
        summary_data.append({
            'Method': endpoint['http_method'],
            'Path': endpoint['endpoint_path'],
            'API': endpoint.get('api_title', 'Unknown'),
            'Critical': len(endpoint.get('critical_pii', [])),
            'High': len(endpoint.get('high_pii', [])),
            'Medium': len(endpoint.get('medium_pii', [])),
            'Low': len(endpoint.get('low_pii', [])),
            'Total PII': endpoint.get('total_pii_found', 0),
            'Compliance': f"{endpoint.get('compliance_score', 0)}%"
        })
    
    df = pd.DataFrame(summary_data)
    st.dataframe(df, use_container_width=True)
    
    # Show detailed view for each endpoint
    for endpoint in filtered_endpoints:
        with st.expander(f"{endpoint['http_method']} {endpoint['endpoint_path']} ({endpoint.get('total_pii_found', 0)} PII)"):
            display_endpoint_details(endpoint)

def display_priority_summary(results):
    """Display priority-based summary of findings."""
    if not results:
        return
    
    detailed_results = results.get('detailed_results', [])
    
    # Count by priority
    priority_counts = {
        'Critical': 0,
        'High': 0,
        'Medium': 0,
        'Low': 0
    }
    
    for endpoint in detailed_results:
        if endpoint.get('critical_pii'):
            priority_counts['Critical'] += 1
        if endpoint.get('high_pii'):
            priority_counts['High'] += 1
        if endpoint.get('medium_pii'):
            priority_counts['Medium'] += 1
        if endpoint.get('low_pii'):
            priority_counts['Low'] += 1
    
    st.subheader("🎯 Priority Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Critical Endpoints", priority_counts['Critical'])
    
    with col2:
        st.metric("High Endpoints", priority_counts['High'])
    
    with col3:
        st.metric("Medium Endpoints", priority_counts['Medium'])
    
    with col4:
        st.metric("Low Endpoints", priority_counts['Low'])

def display_compliance_breakdown(results):
    """Display compliance score breakdown."""
    if not results:
        return
    
    detailed_results = results.get('detailed_results', [])
    
    # Group by compliance ranges
    compliance_ranges = {
        '0-25%': 0,
        '26-50%': 0,
        '51-75%': 0,
        '76-90%': 0,
        '91-100%': 0
    }
    
    for endpoint in detailed_results:
        score = endpoint.get('compliance_score', 0)
        if score <= 25:
            compliance_ranges['0-25%'] += 1
        elif score <= 50:
            compliance_ranges['26-50%'] += 1
        elif score <= 75:
            compliance_ranges['51-75%'] += 1
        elif score <= 90:
            compliance_ranges['76-90%'] += 1
        else:
            compliance_ranges['91-100%'] += 1
    
    st.subheader("📊 Compliance Score Breakdown")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("0-25%", compliance_ranges['0-25%'])
    
    with col2:
        st.metric("26-50%", compliance_ranges['26-50%'])
    
    with col3:
        st.metric("51-75%", compliance_ranges['51-75%'])
    
    with col4:
        st.metric("76-90%", compliance_ranges['76-90%'])
    
    with col5:
        st.metric("91-100%", compliance_ranges['91-100%'])

def display_simple_pii_details(endpoint):
    """Display simple PII details for an endpoint using the new simple schema system."""
    # Show simple JSON schema with PII highlighting
    st.subheader("📋 Simple JSON Schema with PII Detection")
    try:
        from core.openapi_querier import OpenAPIQuerier
        from core.config import Config
        from components.details import generate_simple_json_schema, highlight_pii_in_simple_json, get_actual_schemas
        
        config = Config()
        querier = OpenAPIQuerier(config.get_connection_string())
        
        # Get actual schemas using the new function
        schemas = get_actual_schemas(
            querier, 
            endpoint['api_id'], 
            endpoint['endpoint_path'], 
            endpoint['http_method']
        )
        
        if schemas:
            # Generate simple schemas
            simple_schemas = {}
            
            if schemas.get('request_body'):
                simple_schemas['request_body'] = generate_simple_json_schema(schemas['request_body'])
            
            if schemas.get('response_body'):
                simple_schemas['response_body'] = generate_simple_json_schema(schemas['response_body'])
            
            # Collect all PII fields for highlighting
            all_pii = []
            all_pii.extend(endpoint.get('critical_pii', []))
            all_pii.extend(endpoint.get('high_pii', []))
            all_pii.extend(endpoint.get('medium_pii', []))
            
            # Create tabs for different schema parts
            tab1, tab2, tab3 = st.tabs(["📤 Request Body", "📥 Response Body", "📍 Parameters"])
            
            with tab1:
                if simple_schemas.get('request_body'):
                    # Highlight PII in request body
                    highlighted_request = highlight_pii_in_simple_json(simple_schemas['request_body'], all_pii)
                    st.json(highlighted_request)
                else:
                    st.info("No request body schema available")
            
            with tab2:
                if simple_schemas.get('response_body'):
                    # Highlight PII in response body
                    highlighted_response = highlight_pii_in_simple_json(simple_schemas['response_body'], all_pii)
                    st.json(highlighted_response)
                else:
                    st.info("No response body schema available")
            
            with tab3:
                if schemas.get('parameters'):
                    st.json(schemas['parameters'])
                else:
                    st.info("No parameters schema available")
        else:
            st.warning("⚠️ Could not retrieve schema from database")
            
    except Exception as e:
        st.error(f"Error retrieving schema: {str(e)}")
