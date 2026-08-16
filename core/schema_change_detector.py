"""
Schema Change Detection Module

Detects and tracks changes between OpenAPI schema versions for contract testing.
Provides comprehensive change analysis and breaking change detection.
"""
import psycopg2
import psycopg2.extras
import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class SchemaChangeDetector:
    """Detects and analyzes schema changes between API versions."""
    
    def __init__(self, connection_string: str):
        """
        Initialize schema change detector.
        
        Args:
            connection_string (str): PostgreSQL connection string
        """
        self.conn = psycopg2.connect(connection_string)
    
    def detect_api_changes(self, old_api_id: str, new_api_id: str) -> Dict[str, Any]:
        """
        Detect changes between two API versions.
        
        Args:
            old_api_id (str): Previous API version ID
            new_api_id (str): New API version ID
            
        Returns:
            Dict[str, Any]: Comprehensive change analysis
        """
        changes = {
            'summary': {
                'total_changes': 0,
                'breaking_changes': 0,
                'endpoint_changes': 0,
                'parameter_changes': 0,
                'response_changes': 0,
                'component_changes': 0
            },
            'endpoint_changes': [],
            'parameter_changes': [],
            'response_changes': [],
            'component_changes': [],
            'detailed_changes': []
        }
        
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # Detect endpoint changes
            endpoint_changes = self._detect_endpoint_changes(cursor, old_api_id, new_api_id)
            changes['endpoint_changes'] = endpoint_changes
            changes['summary']['endpoint_changes'] = len(endpoint_changes)
            
            # Detect parameter changes
            parameter_changes = self._detect_parameter_changes(cursor, old_api_id, new_api_id)
            changes['parameter_changes'] = parameter_changes
            changes['summary']['parameter_changes'] = len(parameter_changes)
            
            # Detect response changes
            response_changes = self._detect_response_changes(cursor, old_api_id, new_api_id)
            changes['response_changes'] = response_changes
            changes['summary']['response_changes'] = len(response_changes)
            
            # Detect component changes
            component_changes = self._detect_component_changes(cursor, old_api_id, new_api_id)
            changes['component_changes'] = component_changes
            changes['summary']['component_changes'] = len(component_changes)
            
            # Calculate totals and breaking changes
            all_changes = (endpoint_changes + parameter_changes + 
                          response_changes + component_changes)
            changes['detailed_changes'] = all_changes
            changes['summary']['total_changes'] = len(all_changes)
            changes['summary']['breaking_changes'] = sum(1 for c in all_changes if c.get('is_breaking', False))
        
        return changes
    
    def _detect_endpoint_changes(self, cursor, old_api_id: str, new_api_id: str) -> List[Dict[str, Any]]:
        """Detect endpoint-level changes."""
        changes = []
        
        # Get endpoints from both versions
        cursor.execute("""
            SELECT path, method, operation_id, summary, description, deprecated, tags
            FROM endpoints WHERE api_id = %s
        """, (old_api_id,))
        old_endpoints = {f"{row['path']}:{row['method']}": dict(row) for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT path, method, operation_id, summary, description, deprecated, tags
            FROM endpoints WHERE api_id = %s
        """, (new_api_id,))
        new_endpoints = {f"{row['path']}:{row['method']}": dict(row) for row in cursor.fetchall()}
        
        # Find added endpoints
        for key, endpoint in new_endpoints.items():
            if key not in old_endpoints:
                changes.append({
                    'change_type': 'endpoint_added',
                    'path': endpoint['path'],
                    'method': endpoint['method'],
                    'description': f"New endpoint added: {endpoint['method']} {endpoint['path']}",
                    'is_breaking': False,
                    'old_value': None,
                    'new_value': endpoint
                })
        
        # Find removed endpoints
        for key, endpoint in old_endpoints.items():
            if key not in new_endpoints:
                changes.append({
                    'change_type': 'endpoint_removed',
                    'path': endpoint['path'],
                    'method': endpoint['method'],
                    'description': f"Endpoint removed: {endpoint['method']} {endpoint['path']}",
                    'is_breaking': True,  # Removing endpoints is breaking
                    'old_value': endpoint,
                    'new_value': None
                })
        
        # Find modified endpoints
        for key in old_endpoints.keys() & new_endpoints.keys():
            old_ep = old_endpoints[key]
            new_ep = new_endpoints[key]
            
            # Check for changes in endpoint properties
            if old_ep['summary'] != new_ep['summary']:
                changes.append({
                    'change_type': 'endpoint_summary_changed',
                    'path': old_ep['path'],
                    'method': old_ep['method'],
                    'description': f"Summary changed for {old_ep['method']} {old_ep['path']}",
                    'is_breaking': False,
                    'old_value': old_ep['summary'],
                    'new_value': new_ep['summary']
                })
            
            if old_ep['deprecated'] != new_ep['deprecated']:
                changes.append({
                    'change_type': 'endpoint_deprecation_changed',
                    'path': old_ep['path'],
                    'method': old_ep['method'],
                    'description': f"Deprecation status changed for {old_ep['method']} {old_ep['path']}",
                    'is_breaking': new_ep['deprecated'],  # Deprecating is potentially breaking
                    'old_value': old_ep['deprecated'],
                    'new_value': new_ep['deprecated']
                })
        
        return changes
    
    def _detect_parameter_changes(self, cursor, old_api_id: str, new_api_id: str) -> List[Dict[str, Any]]:
        """Detect parameter-level changes."""
        changes = []
        
        # Get parameters for both API versions
        cursor.execute("""
            SELECT p.*, e.path, e.method
            FROM parameters p
            JOIN endpoints e ON p.endpoint_id = e.id
            WHERE e.api_id = %s
        """, (old_api_id,))
        old_params = {}
        for row in cursor.fetchall():
            key = f"{row['path']}:{row['method']}:{row['name']}:{row['param_location']}"
            old_params[key] = dict(row)
        
        cursor.execute("""
            SELECT p.*, e.path, e.method
            FROM parameters p
            JOIN endpoints e ON p.endpoint_id = e.id
            WHERE e.api_id = %s
        """, (new_api_id,))
        new_params = {}
        for row in cursor.fetchall():
            key = f"{row['path']}:{row['method']}:{row['name']}:{row['param_location']}"
            new_params[key] = dict(row)
        
        # Find added parameters
        for key, param in new_params.items():
            if key not in old_params:
                changes.append({
                    'change_type': 'parameter_added',
                    'path': param['path'],
                    'method': param['method'],
                    'parameter_name': param['name'],
                    'parameter_location': param['param_location'],
                    'description': f"Parameter added: {param['name']} ({param['param_location']}) to {param['method']} {param['path']}",
                    'is_breaking': param['required'],  # Adding required params is breaking
                    'old_value': None,
                    'new_value': param
                })
        
        # Find removed parameters
        for key, param in old_params.items():
            if key not in new_params:
                changes.append({
                    'change_type': 'parameter_removed',
                    'path': param['path'],
                    'method': param['method'],
                    'parameter_name': param['name'],
                    'parameter_location': param['param_location'],
                    'description': f"Parameter removed: {param['name']} ({param['param_location']}) from {param['method']} {param['path']}",
                    'is_breaking': True,  # Removing parameters is always breaking
                    'old_value': param,
                    'new_value': None
                })
        
        # Find modified parameters
        for key in old_params.keys() & new_params.keys():
            old_param = old_params[key]
            new_param = new_params[key]
            
            # Check for type changes
            if old_param['data_type'] != new_param['data_type']:
                changes.append({
                    'change_type': 'parameter_type_changed',
                    'path': old_param['path'],
                    'method': old_param['method'],
                    'parameter_name': old_param['name'],
                    'parameter_location': old_param['param_location'],
                    'description': f"Parameter type changed: {old_param['name']} from {old_param['data_type']} to {new_param['data_type']}",
                    'is_breaking': True,  # Type changes are breaking
                    'old_value': old_param['data_type'],
                    'new_value': new_param['data_type']
                })
            
            # Check for required status changes
            if old_param['required'] != new_param['required']:
                changes.append({
                    'change_type': 'parameter_required_changed',
                    'path': old_param['path'],
                    'method': old_param['method'],
                    'parameter_name': old_param['name'],
                    'parameter_location': old_param['param_location'],
                    'description': f"Parameter required status changed: {old_param['name']} from {old_param['required']} to {new_param['required']}",
                    'is_breaking': new_param['required'],  # Making required is breaking
                    'old_value': old_param['required'],
                    'new_value': new_param['required']
                })
        
        return changes
    
    def _detect_response_changes(self, cursor, old_api_id: str, new_api_id: str) -> List[Dict[str, Any]]:
        """Detect response schema changes."""
        changes = []
        
        # Get responses for both API versions
        cursor.execute("""
            SELECT r.*, e.path, e.method
            FROM responses r
            JOIN endpoints e ON r.endpoint_id = e.id
            WHERE e.api_id = %s
        """, (old_api_id,))
        old_responses = {}
        for row in cursor.fetchall():
            key = f"{row['path']}:{row['method']}:{row['status_code']}:{row['content_type'] or 'no-content'}"
            old_responses[key] = dict(row)
        
        cursor.execute("""
            SELECT r.*, e.path, e.method
            FROM responses r
            JOIN endpoints e ON r.endpoint_id = e.id
            WHERE e.api_id = %s
        """, (new_api_id,))
        new_responses = {}
        for row in cursor.fetchall():
            key = f"{row['path']}:{row['method']}:{row['status_code']}:{row['content_type'] or 'no-content'}"
            new_responses[key] = dict(row)
        
        # Find added responses
        for key, response in new_responses.items():
            if key not in old_responses:
                changes.append({
                    'change_type': 'response_added',
                    'path': response['path'],
                    'method': response['method'],
                    'status_code': response['status_code'],
                    'content_type': response['content_type'],
                    'description': f"Response added: {response['status_code']} for {response['method']} {response['path']}",
                    'is_breaking': False,
                    'old_value': None,
                    'new_value': response
                })
        
        # Find removed responses
        for key, response in old_responses.items():
            if key not in new_responses:
                changes.append({
                    'change_type': 'response_removed',
                    'path': response['path'],
                    'method': response['method'],
                    'status_code': response['status_code'],
                    'content_type': response['content_type'],
                    'description': f"Response removed: {response['status_code']} for {response['method']} {response['path']}",
                    'is_breaking': True,  # Removing responses is breaking
                    'old_value': response,
                    'new_value': None
                })
        
        # Find modified responses (schema changes)
        for key in old_responses.keys() & new_responses.keys():
            old_resp = old_responses[key]
            new_resp = new_responses[key]
            
            # Compare schema definitions
            old_schema = old_resp.get('schema_definition')
            new_schema = new_resp.get('schema_definition')
            
            if old_schema != new_schema:
                changes.append({
                    'change_type': 'response_schema_changed',
                    'path': old_resp['path'],
                    'method': old_resp['method'],
                    'status_code': old_resp['status_code'],
                    'content_type': old_resp['content_type'],
                    'description': f"Response schema changed: {old_resp['status_code']} for {old_resp['method']} {old_resp['path']}",
                    'is_breaking': self._is_schema_change_breaking(old_schema, new_schema),
                    'old_value': old_schema,
                    'new_value': new_schema
                })
        
        return changes
    
    def _detect_component_changes(self, cursor, old_api_id: str, new_api_id: str) -> List[Dict[str, Any]]:
        """Detect reusable component changes."""
        changes = []
        
        # Get components for both API versions
        cursor.execute("""
            SELECT component_name, component_type, definition
            FROM schema_components WHERE api_id = %s
        """, (old_api_id,))
        old_components = {f"{row['component_type']}:{row['component_name']}": dict(row) for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT component_name, component_type, definition
            FROM schema_components WHERE api_id = %s
        """, (new_api_id,))
        new_components = {f"{row['component_type']}:{row['component_name']}": dict(row) for row in cursor.fetchall()}
        
        # Find added components
        for key, component in new_components.items():
            if key not in old_components:
                changes.append({
                    'change_type': 'component_added',
                    'component_name': component['component_name'],
                    'component_type': component['component_type'],
                    'description': f"Component added: {component['component_type']}/{component['component_name']}",
                    'is_breaking': False,
                    'old_value': None,
                    'new_value': component['definition']
                })
        
        # Find removed components
        for key, component in old_components.items():
            if key not in new_components:
                changes.append({
                    'change_type': 'component_removed',
                    'component_name': component['component_name'],
                    'component_type': component['component_type'],
                    'description': f"Component removed: {component['component_type']}/{component['component_name']}",
                    'is_breaking': True,  # Removing components is breaking
                    'old_value': component['definition'],
                    'new_value': None
                })
        
        # Find modified components
        for key in old_components.keys() & new_components.keys():
            old_comp = old_components[key]
            new_comp = new_components[key]
            
            if old_comp['definition'] != new_comp['definition']:
                changes.append({
                    'change_type': 'component_modified',
                    'component_name': old_comp['component_name'],
                    'component_type': old_comp['component_type'],
                    'description': f"Component modified: {old_comp['component_type']}/{old_comp['component_name']}",
                    'is_breaking': self._is_schema_change_breaking(old_comp['definition'], new_comp['definition']),
                    'old_value': old_comp['definition'],
                    'new_value': new_comp['definition']
                })
        
        return changes
    
    def _is_schema_change_breaking(self, old_schema: Any, new_schema: Any) -> bool:
        """
        Determine if a schema change is breaking.
        
        Args:
            old_schema: Old schema definition
            new_schema: New schema definition
            
        Returns:
            bool: True if the change is breaking
        """
        if not old_schema or not new_schema:
            return True
        
        try:
            old_dict = json.loads(old_schema) if isinstance(old_schema, str) else old_schema
            new_dict = json.loads(new_schema) if isinstance(new_schema, str) else new_schema
            
            # Simple heuristics for breaking changes
            # In a real implementation, you'd want more sophisticated schema comparison
            
            # Check if required fields were added
            old_required = set(old_dict.get('required', []))
            new_required = set(new_dict.get('required', []))
            if new_required - old_required:  # New required fields
                return True
            
            # Check if properties were removed
            old_props = set(old_dict.get('properties', {}).keys())
            new_props = set(new_dict.get('properties', {}).keys())
            if old_props - new_props:  # Removed properties
                return True
            
            # Check if types changed
            old_type = old_dict.get('type')
            new_type = new_dict.get('type')
            if old_type and new_type and old_type != new_type:
                return True
            
        except (json.JSONDecodeError, AttributeError, TypeError):
            # If we can't parse, assume it's breaking to be safe
            return True
        
        return False
    
    def save_changes_to_database(self, api_id: str, release_tag: str, changes: List[Dict[str, Any]]):
        """
        Save detected changes to the schema_changes table.
        
        Args:
            api_id (str): API ID
            release_tag (str): Release tag
            changes (List[Dict[str, Any]]): List of changes to save
        """
        with self.conn.cursor() as cursor:
            for change in changes:
                cursor.execute("""
                    INSERT INTO schema_changes 
                    (api_id, endpoint_id, release_tag, change_type, change_description, 
                     old_value, new_value, is_breaking, detected_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    api_id,
                    None,  # endpoint_id - could be enhanced to link to specific endpoints
                    release_tag,
                    change['change_type'],
                    change['description'],
                    json.dumps(change['old_value']) if change['old_value'] else None,
                    json.dumps(change['new_value']) if change['new_value'] else None,
                    change['is_breaking'],
                    datetime.now()
                ))
            
            self.conn.commit()
    
    def get_latest_api_version(self, api_title: str) -> Optional[str]:
        """
        Get the latest version ID for an API by title.
        
        Args:
            api_title (str): API title
            
        Returns:
            Optional[str]: Latest API version ID
        """
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT id FROM apis 
                WHERE title = %s AND is_latest = true
                ORDER BY created_at DESC
                LIMIT 1
            """, (api_title,))
            
            result = cursor.fetchone()
            return result[0] if result else None
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
