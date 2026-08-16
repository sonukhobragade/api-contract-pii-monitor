"""
Unit Tests for Schema Change Detector

Tests the schema change detection functionality.
"""
import os
import pytest
from unittest.mock import Mock, patch
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.schema_change_detector import SchemaChangeDetector


class TestSchemaChangeDetector:
    """Test schema change detection functionality."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        
        # Set up context manager for cursor
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_cursor)
        mock_context.__exit__ = Mock(return_value=None)
        mock_conn.cursor.return_value = mock_context
        
        return mock_conn, mock_cursor
    
    @pytest.fixture
    def detector(self, mock_connection):
        """Create a SchemaChangeDetector instance with mocked connection."""
        mock_conn, mock_cursor = mock_connection
        with patch('psycopg2.connect', return_value=mock_conn):
            detector = SchemaChangeDetector("mock://connection")
            detector.conn = mock_conn
            return detector, mock_cursor
    
    def test_initialization(self):
        """Test detector initialization."""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.return_value = Mock()
            SchemaChangeDetector("test://connection")
            mock_connect.assert_called_once_with("test://connection")
    
    def test_detect_endpoint_changes_added(self, detector):
        """Test detection of added endpoints."""
        detector_instance, mock_cursor = detector
        
        # Mock old endpoints (empty)
        mock_cursor.fetchall.side_effect = [
            [],  # Old endpoints
            [{'path': '/new-endpoint', 'method': 'GET', 'operation_id': 'newOp', 
              'summary': 'New endpoint', 'description': 'Test', 'deprecated': False, 'tags': []}]  # New endpoints
        ]
        
        changes = detector_instance._detect_endpoint_changes(mock_cursor, 'old_api', 'new_api')
        
        assert len(changes) == 1
        assert changes[0]['change_type'] == 'endpoint_added'
        assert changes[0]['path'] == '/new-endpoint'
        assert changes[0]['method'] == 'GET'
        assert not changes[0]['is_breaking']
    
    def test_detect_endpoint_changes_removed(self, detector):
        """Test detection of removed endpoints."""
        detector_instance, mock_cursor = detector
        
        # Mock endpoints
        mock_cursor.fetchall.side_effect = [
            [{'path': '/old-endpoint', 'method': 'POST', 'operation_id': 'oldOp', 
              'summary': 'Old endpoint', 'description': 'Test', 'deprecated': False, 'tags': []}],  # Old endpoints
            []  # New endpoints (empty)
        ]
        
        changes = detector_instance._detect_endpoint_changes(mock_cursor, 'old_api', 'new_api')
        
        assert len(changes) == 1
        assert changes[0]['change_type'] == 'endpoint_removed'
        assert changes[0]['path'] == '/old-endpoint'
        assert changes[0]['method'] == 'POST'
        assert changes[0]['is_breaking']  # Removing endpoints is breaking
    
    def test_detect_endpoint_changes_modified(self, detector):
        """Test detection of modified endpoints."""
        detector_instance, mock_cursor = detector
        
        # Mock endpoints with changes
        old_endpoint = {'path': '/test', 'method': 'GET', 'operation_id': 'test', 
                       'summary': 'Old summary', 'description': 'Test', 'deprecated': False, 'tags': []}
        new_endpoint = {'path': '/test', 'method': 'GET', 'operation_id': 'test', 
                       'summary': 'New summary', 'description': 'Test', 'deprecated': True, 'tags': []}
        
        mock_cursor.fetchall.side_effect = [
            [old_endpoint],  # Old endpoints
            [new_endpoint]   # New endpoints
        ]
        
        changes = detector_instance._detect_endpoint_changes(mock_cursor, 'old_api', 'new_api')
        
        # Should detect summary change and deprecation change
        assert len(changes) == 2
        
        summary_change = next(c for c in changes if c['change_type'] == 'endpoint_summary_changed')
        assert summary_change['old_value'] == 'Old summary'
        assert summary_change['new_value'] == 'New summary'
        assert not summary_change['is_breaking']
        
        deprecation_change = next(c for c in changes if c['change_type'] == 'endpoint_deprecation_changed')
        assert deprecation_change['old_value'] is False
        assert deprecation_change['new_value'] is True
        assert deprecation_change['is_breaking']  # Deprecating is potentially breaking
    
    def test_detect_parameter_changes_added_required(self, detector):
        """Test detection of added required parameters."""
        detector_instance, mock_cursor = detector
        
        # Mock parameters
        new_param = {'path': '/test', 'method': 'GET', 'name': 'newParam', 
                    'param_location': 'query', 'required': True, 'data_type': 'string'}
        
        mock_cursor.fetchall.side_effect = [
            [],  # Old parameters
            [new_param]  # New parameters
        ]
        
        changes = detector_instance._detect_parameter_changes(mock_cursor, 'old_api', 'new_api')
        
        assert len(changes) == 1
        assert changes[0]['change_type'] == 'parameter_added'
        assert changes[0]['parameter_name'] == 'newParam'
        assert changes[0]['is_breaking']  # Adding required params is breaking
    
    def test_detect_parameter_changes_added_optional(self, detector):
        """Test detection of added optional parameters."""
        detector_instance, mock_cursor = detector
        
        # Mock parameters
        new_param = {'path': '/test', 'method': 'GET', 'name': 'newParam', 
                    'param_location': 'query', 'required': False, 'data_type': 'string'}
        
        mock_cursor.fetchall.side_effect = [
            [],  # Old parameters
            [new_param]  # New parameters
        ]
        
        changes = detector_instance._detect_parameter_changes(mock_cursor, 'old_api', 'new_api')
        
        assert len(changes) == 1
        assert changes[0]['change_type'] == 'parameter_added'
        assert changes[0]['parameter_name'] == 'newParam'
        assert not changes[0]['is_breaking']  # Adding optional params is not breaking
    
    def test_detect_parameter_changes_removed(self, detector):
        """Test detection of removed parameters."""
        detector_instance, mock_cursor = detector
        
        # Mock parameters
        old_param = {'path': '/test', 'method': 'GET', 'name': 'oldParam', 
                    'param_location': 'query', 'required': False, 'data_type': 'string'}
        
        mock_cursor.fetchall.side_effect = [
            [old_param],  # Old parameters
            []  # New parameters
        ]
        
        changes = detector_instance._detect_parameter_changes(mock_cursor, 'old_api', 'new_api')
        
        assert len(changes) == 1
        assert changes[0]['change_type'] == 'parameter_removed'
        assert changes[0]['parameter_name'] == 'oldParam'
        assert changes[0]['is_breaking']  # Removing parameters is always breaking
    
    def test_detect_parameter_changes_type_changed(self, detector):
        """Test detection of parameter type changes."""
        detector_instance, mock_cursor = detector
        
        # Mock parameters with type change
        old_param = {'path': '/test', 'method': 'GET', 'name': 'param', 
                    'param_location': 'query', 'required': True, 'data_type': 'string'}
        new_param = {'path': '/test', 'method': 'GET', 'name': 'param', 
                    'param_location': 'query', 'required': True, 'data_type': 'integer'}
        
        mock_cursor.fetchall.side_effect = [
            [old_param],  # Old parameters
            [new_param]   # New parameters
        ]
        
        changes = detector_instance._detect_parameter_changes(mock_cursor, 'old_api', 'new_api')
        
        assert len(changes) == 1
        assert changes[0]['change_type'] == 'parameter_type_changed'
        assert changes[0]['old_value'] == 'string'
        assert changes[0]['new_value'] == 'integer'
        assert changes[0]['is_breaking']  # Type changes are breaking
    
    def test_detect_parameter_changes_required_changed(self, detector):
        """Test detection of parameter required status changes."""
        detector_instance, mock_cursor = detector
        
        # Mock parameters with required status change
        old_param = {'path': '/test', 'method': 'GET', 'name': 'param', 
                    'param_location': 'query', 'required': False, 'data_type': 'string'}
        new_param = {'path': '/test', 'method': 'GET', 'name': 'param', 
                    'param_location': 'query', 'required': True, 'data_type': 'string'}
        
        mock_cursor.fetchall.side_effect = [
            [old_param],  # Old parameters
            [new_param]   # New parameters
        ]
        
        changes = detector_instance._detect_parameter_changes(mock_cursor, 'old_api', 'new_api')
        
        assert len(changes) == 1
        assert changes[0]['change_type'] == 'parameter_required_changed'
        assert changes[0]['old_value'] is False
        assert changes[0]['new_value'] is True
        assert changes[0]['is_breaking']  # Making required is breaking
    
    def test_is_schema_change_breaking_required_fields_added(self, detector):
        """Test breaking change detection for added required fields."""
        detector_instance, _ = detector
        
        old_schema = json.dumps({
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        })
        
        new_schema = json.dumps({
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "required": ["name", "email"]
        })
        
        is_breaking = detector_instance._is_schema_change_breaking(old_schema, new_schema)
        assert is_breaking  # Adding required fields is breaking
    
    def test_is_schema_change_breaking_properties_removed(self, detector):
        """Test breaking change detection for removed properties."""
        detector_instance, _ = detector
        
        old_schema = json.dumps({
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "required": ["name"]
        })
        
        new_schema = json.dumps({
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        })
        
        is_breaking = detector_instance._is_schema_change_breaking(old_schema, new_schema)
        assert is_breaking  # Removing properties is breaking
    
    def test_is_schema_change_breaking_type_changed(self, detector):
        """Test breaking change detection for type changes."""
        detector_instance, _ = detector
        
        old_schema = json.dumps({"type": "string"})
        new_schema = json.dumps({"type": "integer"})
        
        is_breaking = detector_instance._is_schema_change_breaking(old_schema, new_schema)
        assert is_breaking  # Type changes are breaking
    
    def test_is_schema_change_breaking_non_breaking_changes(self, detector):
        """Test non-breaking change detection."""
        detector_instance, _ = detector
        
        old_schema = json.dumps({
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        })
        
        new_schema = json.dumps({
            "type": "object",
            "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
            "required": ["name"]  # email is optional
        })
        
        is_breaking = detector_instance._is_schema_change_breaking(old_schema, new_schema)
        assert not is_breaking  # Adding optional fields is not breaking
    
    def test_save_changes_to_database(self, detector):
        """Test saving changes to database."""
        detector_instance, mock_cursor = detector
        
        changes = [
            {
                'change_type': 'endpoint_added',
                'description': 'New endpoint added',
                'old_value': None,
                'new_value': {'path': '/new'},
                'is_breaking': False
            }
        ]
        
        detector_instance.save_changes_to_database('api_id', 'v1.0.0', changes)
        
        # Verify database insert was called
        mock_cursor.execute.assert_called()
        detector_instance.conn.commit.assert_called_once()
    
    def test_get_latest_api_version(self, detector):
        """Test getting latest API version."""
        detector_instance, mock_cursor = detector
        
        mock_cursor.fetchone.return_value = ('api_id_123',)
        
        result = detector_instance.get_latest_api_version('Test API')
        
        assert result == 'api_id_123'
        # Check that execute was called with the correct parameters (ignore SQL formatting)
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args
        assert 'Test API' in call_args[0][1]
        assert 'SELECT id FROM apis' in call_args[0][0]
        assert 'is_latest = true' in call_args[0][0]
    
    def test_get_latest_api_version_not_found(self, detector):
        """Test getting latest API version when not found."""
        detector_instance, mock_cursor = detector
        
        mock_cursor.fetchone.return_value = None
        
        result = detector_instance.get_latest_api_version('Nonexistent API')
        
        assert result is None
    
    def test_detect_api_changes_integration(self, detector):
        """Test full API change detection integration."""
        detector_instance, mock_cursor = detector
        
        # Mock all the sub-method calls
        with patch.object(detector_instance, '_detect_endpoint_changes', return_value=[
            {'change_type': 'endpoint_added', 'is_breaking': False}
        ]):
            with patch.object(detector_instance, '_detect_parameter_changes', return_value=[
                {'change_type': 'parameter_removed', 'is_breaking': True}
            ]):
                with patch.object(detector_instance, '_detect_response_changes', return_value=[]):
                    with patch.object(detector_instance, '_detect_component_changes', return_value=[]):
                        
                        changes = detector_instance.detect_api_changes('old_api', 'new_api')
                        
                        assert changes['summary']['total_changes'] == 2
                        assert changes['summary']['breaking_changes'] == 1
                        assert changes['summary']['endpoint_changes'] == 1
                        assert changes['summary']['parameter_changes'] == 1
                        assert len(changes['detailed_changes']) == 2


if __name__ == "__main__":
    pytest.main([__file__])
