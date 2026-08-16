#!/usr/bin/env python3
"""
Schema Viewer Component
Displays actual JSON schemas with PII field highlighting
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.openapi_querier import OpenAPIQuerier
from core.config import Config

class SchemaViewer:
    """Enhanced schema viewer with PII highlighting."""
    
    def __init__(self):
        """Initialize the schema viewer."""
        self.config = Config()
        self.querier = OpenAPIQuerier(self.config.get_connection_string())
        self.schema_cache = {}
        
    def display_enhanced_pii_analysis(self, endpoint_data: Dict[str, Any]):
        """Display enhanced PII analysis with actual JSON schemas."""
        st.subheader("🔍 Enhanced PII Analysis with Actual JSON Schemas")
        
        # Get endpoint details
        endpoint_path = endpoint_data.get('endpoint_path', '')
        http_method = endpoint_data.get('http_method', '')
        api_id = endpoint_data.get('api_id', '')
        
        st.info(f"📋 Analyzing: **{http_method} {endpoint_path}**")
        
        # Get actual schemas from database
        schemas = self._get_actual_schemas(endpoint_path, http_method, api_id)
        
        if not schemas:
            st.error("❌ Could not retrieve schemas from database")
            return
        
        # Check if this is a reconstructed schema
        endpoint_info = schemas.get('endpoint_info', {})
        summary = endpoint_info.get('summary', '') if endpoint_info else ''
        if summary and summary.startswith('Mock schema'):
            st.warning("⚠️ **Note:** This schema was reconstructed from PII analysis because the actual schema couldn't be retrieved from the database. The PII fields shown are accurate based on the analysis.")
        
        # Display schemas with PII highlighting
        self._display_schemas_with_pii_highlighting(schemas, endpoint_data)
        
        # Display PII field breakdown
        self._display_pii_field_breakdown(endpoint_data)
        
        # Display security recommendations
        self._display_security_recommendations(endpoint_data)
    
    def _get_actual_schemas(self, path: str, method: str, api_id: str) -> Optional[Dict[str, Any]]:
        """Get actual schemas from database."""
        try:
            endpoint_details = self.querier.get_endpoint_schema(path, method, api_id)
            if not endpoint_details:
                # If we can't get the actual schema, create a mock schema based on PII field paths
                return self._create_mock_schema_from_pii(path, method, api_id)
            
            schemas = {
                'request_body': None,
                'response_body': None,
                'parameters': [],
                'endpoint_info': {
                    'path': endpoint_details.get('path'),
                    'method': endpoint_details.get('method'),
                    'summary': endpoint_details.get('summary'),
                    'description': endpoint_details.get('description'),
                    'tags': endpoint_details.get('tags', [])
                }
            }
            
            # Get parameters
            if endpoint_details.get('parameters'):
                schemas['parameters'] = endpoint_details['parameters']
            
            # Get request bodies
            if endpoint_details.get('request_bodies'):
                request_body = endpoint_details['request_bodies'][0]
                if request_body.get('content'):
                    schemas['request_body'] = request_body['content']
            
            # Get responses
            if endpoint_details.get('responses'):
                for response in endpoint_details['responses']:
                    if response.get('status_code') == '200':
                        if response.get('content'):
                            schemas['response_body'] = response['content']
                        break
            
            return schemas
            
        except Exception as e:
            st.error(f"Error retrieving schemas: {e}")
            return self._create_mock_schema_from_pii(path, method, api_id)
    
    def _display_schemas_with_pii_highlighting(self, schemas: Dict[str, Any], endpoint_data: Dict[str, Any]):
        """Display schemas with PII field highlighting."""
        
        # Create tabs for different schema types
        tab1, tab2, tab3 = st.tabs(["📤 Request Schema", "📥 Response Schema", "🔧 Parameters"])
        
        with tab1:
            if schemas.get('request_body'):
                st.write("**Request Body Schema:**")
                highlighted_schema = self._highlight_pii_in_schema(
                    schemas['request_body'], 
                    endpoint_data, 
                    'request'
                )
                self._display_highlighted_json(highlighted_schema, "request")
            else:
                st.info("No request body schema available")
        
        with tab2:
            if schemas.get('response_body'):
                st.write("**Response Body Schema:**")
                highlighted_schema = self._highlight_pii_in_schema(
                    schemas['response_body'], 
                    endpoint_data, 
                    'response'
                )
                self._display_highlighted_json(highlighted_schema, "response")
            else:
                st.info("No response body schema available")
        
        with tab3:
            if schemas.get('parameters'):
                st.write("**Parameters:**")
                highlighted_params = self._highlight_pii_in_parameters(
                    schemas['parameters'], 
                    endpoint_data
                )
                self._display_highlighted_json(highlighted_params, "parameters")
            else:
                st.info("No parameters available")
    
    def _highlight_pii_in_schema(self, schema: Dict[str, Any], endpoint_data: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Add PII highlighting to schema."""
        if not schema:
            return schema
        
        # Create a copy to avoid modifying the original
        highlighted_schema = self._safe_copy_dict(schema)
        
        # Get all PII fields for this endpoint
        all_pii_fields = []
        for severity in ['critical_pii', 'high_pii', 'medium_pii', 'low_pii']:
            pii_list = endpoint_data.get(severity, [])
            for pii in pii_list:
                if pii.get('context', '').lower() == context:
                    all_pii_fields.append(pii)
        
        # Add PII annotations to the schema
        for pii in all_pii_fields:
            self._add_pii_annotation_to_schema(highlighted_schema, pii)
        
        return highlighted_schema
    
    def _highlight_pii_in_parameters(self, parameters: List[Dict[str, Any]], endpoint_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add PII highlighting to parameters."""
        if not parameters:
            return parameters
        
        highlighted_params = []
        
        for param in parameters:
            # Create a copy that handles datetime objects
            param_copy = self._safe_copy_dict(param)
            param_name = param.get('name', '')
            
            # Check if this parameter contains PII
            for severity in ['critical_pii', 'high_pii', 'medium_pii', 'low_pii']:
                pii_list = endpoint_data.get(severity, [])
                for pii in pii_list:
                    if pii.get('context', '').lower() == 'parameter' and param_name in pii.get('field_path', ''):
                        self._add_pii_annotation_to_parameter(param_copy, pii)
                        break
            
            highlighted_params.append(param_copy)
        
        return highlighted_params
    
    def _add_pii_annotation_to_schema(self, schema: Dict[str, Any], pii: Dict[str, Any]):
        """Add PII annotation to a field in the schema."""
        field_path = pii.get('field_path', '')
        if not field_path:
            return
        
        # Navigate to the field in the schema
        path_parts = field_path.split('.')
        current = schema
        
        # Navigate through the schema structure
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
            pii_type = pii.get('pii_type', 'Unknown')
            severity = pii.get('severity', 'Unknown')
            
            field_schema['_pii_info'] = {
                'pii_type': pii_type,
                'severity': severity,
                'field_path': field_path,
                'description': f"🔴 {pii_type.replace('_', ' ').title()} - {severity.upper()} PII",
                'encryption_required': True,
                'masking_recommended': True,
                'confidence': pii.get('confidence', 0),
                'pattern_matched': pii.get('pattern_matched', '')
            }
            
            # Update the description to highlight PII
            severity_icon = self._get_severity_icon(severity)
            if 'description' in field_schema:
                field_schema['description'] = f"{severity_icon} {field_schema['description']} - {severity.upper()} PII"
            else:
                field_schema['description'] = f"{severity_icon} {pii_type.replace('_', ' ').title()} - {severity.upper()} PII"
    
    def _add_pii_annotation_to_parameter(self, param: Dict[str, Any], pii: Dict[str, Any]):
        """Add PII annotation to a parameter."""
        pii_type = pii.get('pii_type', 'Unknown')
        severity = pii.get('severity', 'Unknown')
        
        param['_pii_info'] = {
            'pii_type': pii_type,
            'severity': severity,
            'description': f"🔴 {pii_type.replace('_', ' ').title()} - {severity.upper()} PII",
            'encryption_required': True,
            'masking_recommended': True
        }
        
        # Update the description
        severity_icon = self._get_severity_icon(severity)
        if 'description' in param:
            param['description'] = f"{severity_icon} {param['description']} - {severity.upper()} PII"
        else:
            param['description'] = f"{severity_icon} {pii_type.replace('_', ' ').title()} - {severity.upper()} PII"
    
    def _display_highlighted_json(self, data: Any, context: str):
        """Display JSON with Swagger UI-style PII highlighting."""
        if not data:
            st.info(f"No {context} data available")
            return
        
        # Add custom CSS for Swagger UI-style display
        st.markdown("""
        <style>
        .swagger-json {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 16px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 13px;
            line-height: 1.4;
            overflow-x: auto;
        }
        .pii-field {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 8px;
            margin: 4px 0;
            border-radius: 2px;
        }
        .pii-critical {
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
        }
        .pii-high {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
        }
        .pii-medium {
            background-color: #d1ecf1;
            border-left: 4px solid #17a2b8;
        }
        .pii-low {
            background-color: #d4edda;
            border-left: 4px solid #28a745;
        }
        .field-name {
            color: #0066cc;
            font-weight: bold;
        }
        .field-type {
            color: #6c757d;
            font-style: italic;
        }
        .pii-badge {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 8px;
        }
        .badge-critical {
            background-color: #dc3545;
            color: white;
        }
        .badge-high {
            background-color: #ffc107;
            color: #212529;
        }
        .badge-medium {
            background-color: #17a2b8;
            color: white;
        }
        .badge-low {
            background-color: #28a745;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Convert to formatted JSON with PII highlighting
        json_str = self._format_json_with_pii_highlighting(data)
        
        # Display in Swagger UI style
        st.markdown(f'<div class="swagger-json">{json_str}</div>', unsafe_allow_html=True)
    
    def _format_json_with_pii_highlighting(self, data: Any, indent: int = 0) -> str:
        """Format JSON with PII highlighting like Swagger UI."""
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                indent_str = "  " * indent
                
                # Check if this field has PII information
                pii_info = None
                if isinstance(value, dict) and '_pii_info' in value:
                    pii_info = value['_pii_info']
                
                # Format the field
                if pii_info:
                    severity = pii_info.get('severity', 'unknown').lower()
                    pii_type = pii_info.get('pii_type', 'unknown')
                    
                    # Create PII badge
                    badge_class = f"badge-{severity}"
                    badge_text = f"{severity.upper()} PII"
                    badge = f'<span class="pii-badge {badge_class}">{badge_text}</span>'
                    
                    # Create field line with PII highlighting
                    field_line = f'{indent_str}<span class="field-name">"{key}"</span>: '
                    
                    if isinstance(value, dict):
                        # Remove PII info for display
                        display_value = {k: v for k, v in value.items() if k != '_pii_info'}
                        if 'description' in display_value:
                            desc = display_value['description']
                            field_line += f'<span class="field-type">/* {desc} */</span> '
                        field_line += f'<span class="field-type">/* {pii_type.replace("_", " ").title()} */</span> {badge}'
                        
                        # Format nested object
                        nested_json = self._format_json_with_pii_highlighting(display_value, indent + 1)
                        lines.append(f'{field_line}')
                        lines.append(nested_json)
                    else:
                        field_line += f'<span class="field-type">"{value}"</span> {badge}'
                        lines.append(f'{field_line},')
                else:
                    # Regular field
                    field_line = f'{indent_str}<span class="field-name">"{key}"</span>: '
                    if isinstance(value, dict):
                        nested_json = self._format_json_with_pii_highlighting(value, indent + 1)
                        lines.append(field_line)
                        lines.append(nested_json)
                    else:
                        field_line += f'<span class="field-type">"{value}"</span>,'
                        lines.append(field_line)
            
            if indent == 0:
                return '\n'.join(lines)
            else:
                return '{\n' + '\n'.join(lines) + f'\n{"  " * (indent-1)}}}'
        
        elif isinstance(data, list):
            lines = []
            for item in data:
                if isinstance(item, dict):
                    lines.append(self._format_json_with_pii_highlighting(item, indent + 1))
                else:
                    lines.append(f'"{item}"')
            return '[\n' + ',\n'.join(lines) + f'\n{"  " * (indent-1)}]'
        
        else:
            return f'"{data}"'
    
    def _display_pii_field_breakdown(self, endpoint_data: Dict[str, Any]):
        """Display detailed PII field breakdown."""
        st.subheader("🔍 PII Field Breakdown")
        
        # Create tabs for different severities
        tab1, tab2, tab3, tab4 = st.tabs(["🔴 Critical", "🟡 High", "🟠 Medium", "🟢 Low"])
        
        with tab1:
            self._display_pii_severity_details(endpoint_data.get('critical_pii', []), "Critical")
        
        with tab2:
            self._display_pii_severity_details(endpoint_data.get('high_pii', []), "High")
        
        with tab3:
            self._display_pii_severity_details(endpoint_data.get('medium_pii', []), "Medium")
        
        with tab4:
            self._display_pii_severity_details(endpoint_data.get('low_pii', []), "Low")
    
    def _display_pii_severity_details(self, pii_list: List[Dict[str, Any]], severity: str):
        """Display details for a specific severity level."""
        if not pii_list:
            st.info(f"No {severity.lower()} PII found")
            return
        
        for i, pii in enumerate(pii_list):
            with st.expander(f"🔍 {pii.get('field_path', 'Unknown')} ({pii.get('pii_type', 'Unknown')})", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Field Path:** `{pii.get('field_path', 'Unknown')}`")
                    st.write(f"**PII Type:** {pii.get('pii_type', 'Unknown')}")
                    st.write(f"**Context:** {pii.get('context', 'Unknown')}")
                    st.write(f"**Severity:** {pii.get('severity', 'Unknown')}")
                
                with col2:
                    if pii.get('confidence'):
                        st.write(f"**Confidence:** {pii.get('confidence')}")
                    if pii.get('pattern_matched'):
                        st.write(f"**Pattern:** {pii.get('pattern_matched')}")
                    if pii.get('description'):
                        st.write(f"**Description:** {pii.get('description')}")
                
                # Show field details
                st.write("**Field Details:**")
                st.code(f"""
Field: {pii.get('field_path', 'Unknown')}
Type: {pii.get('pii_type', 'Unknown')}
Context: {pii.get('context', 'Unknown')}
Severity: {pii.get('severity', 'Unknown')}
Confidence: {pii.get('confidence', 'N/A')}
Pattern: {pii.get('pattern_matched', 'N/A')}
                """, language='text')
    
    def _display_security_recommendations(self, endpoint_data: Dict[str, Any]):
        """Display security recommendations for PII fields."""
        st.subheader("🛡️ Security Recommendations")
        
        # Collect all PII fields
        all_pii = []
        for severity in ['critical_pii', 'high_pii', 'medium_pii', 'low_pii']:
            all_pii.extend(endpoint_data.get(severity, []))
        
        if not all_pii:
            st.success("✅ No PII found - no security recommendations needed")
            return
        
        # Group recommendations by severity
        recommendations = {
            'Critical': [],
            'High': [],
            'Medium': [],
            'Low': []
        }
        
        for pii in all_pii:
            severity = pii.get('severity', 'Unknown')
            if severity in recommendations:
                recommendations[severity].append(pii)
        
        # Display recommendations by severity
        for severity, pii_list in recommendations.items():
            if pii_list:
                severity_icon = self._get_severity_icon(severity.lower())
                st.write(f"**{severity_icon} {severity} Priority Recommendations:**")
                
                for pii in pii_list:
                    with st.expander(f"🔒 {pii.get('field_path', 'Unknown')} - {pii.get('pii_type', 'Unknown')}"):
                        self._display_field_recommendations(pii)
    
    def _display_field_recommendations(self, pii: Dict[str, Any]):
        """Display security recommendations for a specific field."""
        pii_type = pii.get('pii_type', 'Unknown')
        severity = pii.get('severity', 'Unknown')
        
        # Get recommendations based on PII type
        recommendations = self._get_pii_type_recommendations(pii_type, severity)
        
        st.write("**Immediate Actions Required:**")
        for rec in recommendations['immediate']:
            st.write(f"• {rec}")
        
        st.write("**Security Measures:**")
        for rec in recommendations['security']:
            st.write(f"• {rec}")
        
        st.write("**Compliance Requirements:**")
        for rec in recommendations['compliance']:
            st.write(f"• {rec}")
    
    def _get_pii_type_recommendations(self, pii_type: str, severity: str) -> Dict[str, List[str]]:
        """Get security recommendations based on PII type and severity."""
        recommendations = {
            'immediate': [],
            'security': [],
            'compliance': []
        }
        
        # Base recommendations for all PII
        recommendations['immediate'].extend([
            "Implement field-level encryption",
            "Add data masking for logging",
            "Update API documentation to mark as sensitive"
        ])
        
        recommendations['security'].extend([
            "Use HTTPS for all API communications",
            "Implement rate limiting",
            "Add request/response validation"
        ])
        
        # Type-specific recommendations
        if 'bank_account' in pii_type.lower():
            recommendations['immediate'].extend([
                "Implement PCI DSS compliance measures",
                "Use tokenization for account numbers",
                "Add audit logging for all access"
            ])
            recommendations['compliance'].extend([
                "PCI DSS compliance required",
                "GDPR Article 32 (security measures)",
                "SOX compliance for financial data"
            ])
        
        elif 'credit_card' in pii_type.lower():
            recommendations['immediate'].extend([
                "Implement PCI DSS Level 1 compliance",
                "Use tokenization for card numbers",
                "Never store CVV codes"
            ])
            recommendations['compliance'].extend([
                "PCI DSS Level 1 compliance required",
                "GDPR Article 32 (security measures)",
                "Payment Card Industry standards"
            ])
        
        elif 'ssn' in pii_type.lower() or 'social_security' in pii_type.lower():
            recommendations['immediate'].extend([
                "Implement strict access controls",
                "Use encryption at rest and in transit",
                "Add multi-factor authentication"
            ])
            recommendations['compliance'].extend([
                "HIPAA compliance required",
                "GDPR Article 32 (security measures)",
                "State-specific privacy laws"
            ])
        
        # Severity-based recommendations
        if severity.lower() == 'critical':
            recommendations['immediate'].extend([
                "Immediate review by security team",
                "Consider API endpoint deprecation",
                "Implement additional monitoring"
            ])
        
        return recommendations
    
    def _create_mock_schema_from_pii(self, path: str, method: str, api_id: str) -> Optional[Dict[str, Any]]:
        """Create a mock schema based on PII field paths found in the endpoint."""
        try:
            # Get the endpoint data from the analysis results
            from scripts.fast_pii_analysis import FastPIIAnalyzer
            analyzer = FastPIIAnalyzer()
            results = analyzer.analyze_all_apis_fast()
            
            if not results or "error" in results:
                return None
            
            # Find the specific endpoint
            detailed_results = results.get('detailed_results', [])
            endpoint_data = None
            for ep in detailed_results:
                if ep.get('endpoint_path') == path and ep.get('http_method') == method:
                    endpoint_data = ep
                    break
            
            if not endpoint_data:
                return None
            
            # Create mock schema based on PII field paths
            mock_schema = {
                'request_body': None,
                'response_body': None,
                'parameters': [],
                'endpoint_info': {
                    'path': path,
                    'method': method,
                    'summary': f"Mock schema for {method} {path}",
                    'description': "Schema reconstructed from PII analysis",
                    'tags': []
                }
            }
            
            # Build request body schema from PII fields
            request_pii = []
            for severity in ['critical_pii', 'high_pii', 'medium_pii', 'low_pii']:
                pii_list = endpoint_data.get(severity, [])
                for pii in pii_list:
                    if 'request' in pii.get('context', '').lower():
                        request_pii.append(pii)
            
            if request_pii:
                mock_schema['request_body'] = self._build_schema_from_pii_paths(request_pii, 'request')
            
            # Build response body schema from PII fields
            response_pii = []
            for severity in ['critical_pii', 'high_pii', 'medium_pii', 'low_pii']:
                pii_list = endpoint_data.get(severity, [])
                for pii in pii_list:
                    if 'response' in pii.get('context', '').lower():
                        response_pii.append(pii)
            
            if response_pii:
                mock_schema['response_body'] = self._build_schema_from_pii_paths(response_pii, 'response')
            
            return mock_schema
            
        except Exception as e:
            st.error(f"Error creating mock schema: {e}")
            return None
    
    def _build_schema_from_pii_paths(self, pii_list: List[Dict[str, Any]], context: str) -> Dict[str, Any]:
        """Build a JSON schema from PII field paths."""
        schema = {
            "type": "object",
            "properties": {},
            "description": f"Schema reconstructed from {context} PII analysis"
        }
        
        for pii in pii_list:
            field_path = pii.get('field_path', '')
            if not field_path:
                continue
            
            # Build the schema structure from the field path
            path_parts = field_path.split('.')
            current = schema['properties']
            
            # Navigate through the path and create the structure
            for i, part in enumerate(path_parts[:-1]):
                if part not in current:
                    current[part] = {
                        "type": "object",
                        "properties": {}
                    }
                current = current[part]['properties']
            
            # Add the final field with PII information
            final_part = path_parts[-1]
            pii_type = pii.get('pii_type', 'Unknown')
            severity = pii.get('severity', 'Unknown')
            
            current[final_part] = {
                "type": "string",
                "description": f"🔴 {pii_type.replace('_', ' ').title()} - {severity.upper()} PII",
                "example": self._get_example_value(pii_type),
                "_pii_info": {
                    "pii_type": pii_type,
                    "severity": severity,
                    "field_path": field_path,
                    "context": context,
                    "confidence": pii.get('confidence', 0),
                    "pattern_matched": pii.get('pattern_matched', ''),
                    "encryption_required": True,
                    "masking_recommended": True
                }
            }
        
        return schema
    
    def _get_example_value(self, pii_type: str) -> str:
        """Get example value for PII type."""
        examples = {
            "bank_account_number": "1234567890",
            "social_security_number": "123-45-6789",
            "credit_card_number": "4111-1111-1111-1111",
            "phone_number": "+1-555-123-4567",
            "email_address": "user@example.com",
            "full_name": "John Doe",
            "user_id": "user123",
            "physical_address": "123 Main St, City, State 12345"
        }
        return examples.get(pii_type, "example_value")
    
    def _safe_copy_dict(self, obj: Any) -> Any:
        """Safely copy a dictionary, handling datetime objects."""
        if isinstance(obj, dict):
            return {key: self._safe_copy_dict(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._safe_copy_dict(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        else:
            return obj
    
    def _get_severity_icon(self, severity: str) -> str:
        """Get icon for severity level."""
        icons = {
            'critical': '🔴',
            'high': '🟡',
            'medium': '🟠',
            'low': '🟢'
        }
        return icons.get(severity.lower(), '⚪')
