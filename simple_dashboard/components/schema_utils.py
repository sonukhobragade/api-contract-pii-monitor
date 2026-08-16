#!/usr/bin/env python3
"""
Schema Utilities Component
Handles simple JSON schema generation and PII highlighting
"""

import json
import streamlit as st
from core.openapi_querier import OpenAPIQuerier
from core.config import Config


def generate_simple_json_schema(openapi_schema):
    """Generate simple, clean JSON schema from complex OpenAPI schema."""
    if not openapi_schema:
        return {}
    
    if isinstance(openapi_schema, dict) and 'type' in openapi_schema:
        return simplify_schema_object(openapi_schema)
    
    if isinstance(openapi_schema, dict):
        if 'application/json' in openapi_schema:
            schema = openapi_schema['application/json'].get('schema', {})
            return simplify_schema_object(schema)
        
        if 'schema' in openapi_schema:
            return simplify_schema_object(openapi_schema['schema'])
        
        if any(key in openapi_schema for key in ['type', 'properties', 'items']):
            return simplify_schema_object(openapi_schema)
    
    return {}


def simplify_schema_object(schema):
    """Simplify a schema object by removing OpenAPI-specific metadata."""
    if not isinstance(schema, dict):
        return schema
    
    simplified = {}
    
    if 'type' in schema:
        simplified['type'] = schema['type']
    
    if 'properties' in schema and schema.get('type') == 'object':
        simplified['type'] = 'object'
        simplified['properties'] = {}
        simplified['required'] = schema.get('required', [])
        
        for prop_name, prop_schema in schema['properties'].items():
            simplified['properties'][prop_name] = simplify_schema_object(prop_schema)
    
    elif 'items' in schema and schema.get('type') == 'array':
        simplified['type'] = 'array'
        simplified['items'] = simplify_schema_object(schema['items'])
    
    elif 'type' in schema:
        simplified['type'] = schema['type']
        
        if 'format' in schema:
            simplified['format'] = schema['format']
        
        if 'description' in schema:
            simplified['description'] = schema['description']
        
        if 'example' in schema:
            simplified['example'] = schema['example']
    
    return simplified


def highlight_pii_in_simple_json(schema, pii_fields):
    """Add PII highlighting to simple JSON schema."""
    if not schema or not pii_fields:
        return schema
    
    highlighted_schema = json.loads(json.dumps(schema))
    
    for pii in pii_fields:
        field_path = pii.get('field_path', '')
        pii_type = pii.get('pii_type', 'Unknown')
        severity = pii.get('severity', 'Unknown')
        
        add_pii_annotation_to_simple_schema(highlighted_schema, field_path, pii_type, severity)
    
    return highlighted_schema


def add_pii_annotation_to_simple_schema(schema, field_path, pii_type, severity):
    """Add PII annotation to a specific field in the simple schema."""
    if not field_path:
        return
    
    path_parts = field_path.split('.')
    current = schema
    
    for i, part in enumerate(path_parts[:-1]):
        if isinstance(current, dict):
            if 'properties' in current and part in current['properties']:
                current = current['properties']
            if part in current:
                current = current[part]
            else:
                return
    
    final_part = path_parts[-1]
    if isinstance(current, dict) and 'properties' in current and final_part in current['properties']:
        field_schema = current['properties'][final_part]
        
        severity_icon = "🔴" if severity == 'critical' else "🟡" if severity == 'high' else "🟠"
        
        field_schema['_pii_info'] = {
            'pii_type': pii_type,
            'severity': severity,
            'field_path': field_path,
            'description': f"{severity_icon} {pii_type.replace('_', ' ').title()} - {severity.upper()} PII",
            'encryption_required': True,
            'masking_recommended': True
        }
        
        if 'description' in field_schema:
            field_schema['description'] = f"{severity_icon} {field_schema['description']} - {severity.upper()} PII"
        else:
            field_schema['description'] = f"{severity_icon} {pii_type.replace('_', ' ').title()} - {severity.upper()} PII"


def get_schema_from_database(endpoint_path, http_method, api_id):
    """Get schema from database."""
    try:
        config = Config()
        querier = OpenAPIQuerier(config.get_connection_string())
        
        endpoint_details = querier.get_endpoint_schema(endpoint_path, http_method, api_id)
        
        if not endpoint_details:
            return None
        
        schemas = {
            'request_body': None,
            'response_body': None
        }
        
        if endpoint_details.get('request_bodies'):
            request_body = endpoint_details['request_bodies'][0]
            if request_body.get('content'):
                schemas['request_body'] = request_body['content']
        
        if endpoint_details.get('responses'):
            for response in endpoint_details['responses']:
                if response.get('status_code') == '200':
                    if response.get('content'):
                        schemas['response_body'] = response['content']
                    break
        
        return schemas
        
    except Exception as e:
        st.error(f"Error getting schema: {e}")
        return None


def get_schema_from_database_by_endpoint_id(endpoint_id):
    """Get schema from database using endpoint ID."""
    try:
        if not endpoint_id:
            return None
            
        config = Config()
        querier = OpenAPIQuerier(config.get_connection_string())
        
        # Get endpoint details using the available method
        endpoint_details = querier.get_endpoint_details(endpoint_id)
        if not endpoint_details:
            return None
        
        # Get schema using the endpoint details
        return get_schema_from_database(
            endpoint_details.get('path', ''),
            endpoint_details.get('method', 'GET'),
            endpoint_details.get('api_id', '')
        )
        
    except Exception as e:
        st.error(f"Error getting schema by endpoint ID: {e}")
        return None
