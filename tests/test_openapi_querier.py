"""
Unit tests for OpenAPIQuerier module
"""
from unittest.mock import Mock, patch, MagicMock
from core.openapi_querier import OpenAPIQuerier


class TestOpenAPIQuerier:
    """Test cases for OpenAPIQuerier class."""

    @patch('core.openapi_querier.psycopg2.connect')
    def test_init(self, mock_connect):
        """Test OpenAPIQuerier initialization."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        
        assert querier.conn == mock_conn
        mock_connect.assert_called_once_with("postgresql://user:pass@host:5432/db")

    @patch('core.openapi_querier.psycopg2.connect')
    def test_search_endpoints_no_filters(self, mock_connect):
        """Test searching endpoints without filters."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        # Mock query results
        mock_cursor.fetchall.return_value = [
            {
                'id': 'endpoint-1',
                'path': '/api/test',
                'method': 'GET',
                'summary': 'Test endpoint',
                'api_title': 'Test API'
            }
        ]
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        results = querier.search_endpoints()
        
        assert len(results) == 1
        assert results[0]['path'] == '/api/test'
        assert results[0]['method'] == 'GET'

    @patch('core.openapi_querier.psycopg2.connect')
    def test_search_endpoints_with_filters(self, mock_connect):
        """Test searching endpoints with filters."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        mock_cursor.fetchall.return_value = []
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        _results = querier.search_endpoints(
            search_term="auth",
            method="POST",
            tag="authentication",
            api_id="api-123"
        )
        
        # Verify the query was called with filters
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        # Check that filters are in the query
        assert "ILIKE" in query  # search term filter
        assert "e.method = %s" in query  # method filter
        assert "e.tags::jsonb ? %s" in query  # tag filter
        assert "e.api_id = %s" in query  # api_id filter
        
        # Check parameters
        assert "%auth%" in params
        assert "POST" in params
        assert "authentication" in params
        assert "api-123" in params

    @patch('core.openapi_querier.psycopg2.connect')
    def test_get_endpoint_details_found(self, mock_connect):
        """Test getting endpoint details when endpoint exists."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        # Mock endpoint data
        endpoint_data = {
            'id': 'endpoint-1',
            'path': '/api/test',
            'method': 'GET',
            'summary': 'Test endpoint',
            'api_title': 'Test API'
        }
        
        # Mock the sequence of fetchone calls
        mock_cursor.fetchone.side_effect = [
            endpoint_data,  # Main endpoint query
        ]
        
        # Mock fetchall for related data
        mock_cursor.fetchall.side_effect = [
            [{'name': 'param1', 'required': True}],  # parameters
            [{'content_type': 'application/json'}],   # request_bodies
            [{'status_code': '200'}]                  # responses
        ]
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        result = querier.get_endpoint_details("endpoint-1")
        
        assert result is not None
        assert result['path'] == '/api/test'
        assert 'parameters' in result
        assert 'request_bodies' in result
        assert 'responses' in result

    @patch('core.openapi_querier.psycopg2.connect')
    def test_get_endpoint_details_not_found(self, mock_connect):
        """Test getting endpoint details when endpoint doesn't exist."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        mock_cursor.fetchone.return_value = None
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        result = querier.get_endpoint_details("nonexistent")
        
        assert result is None

    @patch('core.openapi_querier.psycopg2.connect')
    def test_get_api_stats(self, mock_connect):
        """Test getting API statistics."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        stats_data = {
            'api_id': 'api-1',
            'total_endpoints': 10,
            'get_endpoints': 5,
            'post_endpoints': 3,
            'put_endpoints': 1,
            'delete_endpoints': 1,
            'deprecated_endpoints': 0,
            'unique_tags': 3
        }
        
        mock_cursor.fetchone.return_value = stats_data
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        result = querier.get_api_stats("api-1")
        
        assert result['total_endpoints'] == 10
        assert result['get_endpoints'] == 5
        assert result['post_endpoints'] == 3

    @patch('core.openapi_querier.psycopg2.connect')
    def test_get_schema_changes(self, mock_connect):
        """Test getting schema changes."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        changes_data = [
            {
                'id': 'change-1',
                'change_type': 'endpoint_added',
                'change_description': 'New endpoint added',
                'api_title': 'Test API'
            }
        ]
        
        mock_cursor.fetchall.return_value = changes_data
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        result = querier.get_schema_changes(api_id="api-1")
        
        assert len(result) == 1
        assert result[0]['change_type'] == 'endpoint_added'

    @patch('core.openapi_querier.psycopg2.connect')
    def test_get_api_releases(self, mock_connect):
        """Test getting API releases."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        releases_data = [
            {
                'id': 'release-1',
                'release_tag': 'v1.0.0',
                'endpoint_count': 10,
                'breaking_changes': 0
            }
        ]
        
        mock_cursor.fetchall.return_value = releases_data
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        result = querier.get_api_releases("api-1")
        
        assert len(result) == 1
        assert result[0]['release_tag'] == 'v1.0.0'

    @patch('core.openapi_querier.psycopg2.connect')
    def test_get_latest_apis(self, mock_connect):
        """Test getting latest APIs."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        apis_data = [
            {
                'id': 'api-1',
                'title': 'Test API',
                'version': '1.0.0',
                'endpoint_count': 10
            }
        ]
        
        mock_cursor.fetchall.return_value = apis_data
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        result = querier.get_latest_apis()
        
        assert len(result) == 1
        assert result[0]['title'] == 'Test API'

    @patch('core.openapi_querier.psycopg2.connect')
    def test_get_endpoint_schema_found(self, mock_connect):
        """Test getting endpoint schema when endpoint exists."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        # Mock the sequence of calls
        mock_cursor.fetchone.side_effect = [
            {'id': 'endpoint-1'},  # First query to find endpoint
        ]
        
        # Mock fetchall for related data (from get_endpoint_details)
        mock_cursor.fetchall.side_effect = [
            [{'name': 'param1'}],     # parameters
            [{'content_type': 'application/json'}],  # request_bodies
            [{'status_code': '200'}]  # responses
        ]
        
        # Mock get_endpoint_details call
        with patch.object(OpenAPIQuerier, 'get_endpoint_details') as mock_get_details:
            mock_get_details.return_value = {
                'id': 'endpoint-1',
                'path': '/api/test',
                'method': 'GET'
            }
            
            querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
            result = querier.get_endpoint_schema("/api/test", "GET")
            
            assert result is not None
            assert result['path'] == '/api/test'

    @patch('core.openapi_querier.psycopg2.connect')
    def test_get_endpoint_schema_not_found(self, mock_connect):
        """Test getting endpoint schema when endpoint doesn't exist."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        mock_cursor.fetchone.return_value = None
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        result = querier.get_endpoint_schema("/api/nonexistent", "GET")
        
        assert result is None

    @patch('core.openapi_querier.psycopg2.connect')
    def test_close_connection(self, mock_connect):
        """Test closing database connection."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        querier = OpenAPIQuerier("postgresql://user:pass@host:5432/db")
        querier.close()
        
        mock_conn.close.assert_called_once()
