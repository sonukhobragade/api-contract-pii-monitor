"""
Unit tests for DatabaseSetup module
"""
from unittest.mock import Mock, patch, MagicMock
from core.database_setup import DatabaseSetup


class TestDatabaseSetup:
    """Test cases for DatabaseSetup class."""

    def test_init(self):
        """Test DatabaseSetup initialization."""
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        
        assert db_setup.host == "localhost"
        assert db_setup.port == "5432"
        assert db_setup.username == "user"
        assert db_setup.password == "pass"

    def test_get_connection_string(self):
        """Test connection string generation."""
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        
        conn_str = db_setup.get_connection_string("test_db")
        expected = "postgresql://user:pass@localhost:5432/test_db"
        
        assert conn_str == expected

    def test_get_connection_string_default_db(self):
        """Test connection string with default database name."""
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        
        conn_str = db_setup.get_connection_string()
        expected = "postgresql://user:pass@localhost:5432/openapi_store"
        
        assert conn_str == expected

    @patch('core.database_setup.psycopg2.connect')
    def test_create_database_success(self, mock_connect):
        """Test successful database creation."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        mock_cursor.fetchone.return_value = None  # Database doesn't exist
        
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        result = db_setup.create_database("test_db")
        
        assert result is True
        mock_connect.assert_called_once_with(
            host="localhost",
            port="5432",
            user="user",
            password="pass",
            database="postgres"
        )
        mock_cursor.execute.assert_any_call('CREATE DATABASE "test_db"')

    @patch('core.database_setup.psycopg2.connect')
    def test_create_database_already_exists(self, mock_connect):
        """Test database creation when database already exists."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        mock_cursor.fetchone.return_value = (1,)  # Database exists
        
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        result = db_setup.create_database("test_db")
        
        assert result is True
        # Should not try to create database
        create_calls = [call for call in mock_cursor.execute.call_args_list 
                       if 'CREATE DATABASE' in str(call)]
        assert len(create_calls) == 0

    @patch('core.database_setup.psycopg2.connect')
    def test_create_database_failure(self, mock_connect):
        """Test database creation failure."""
        mock_connect.side_effect = Exception("Connection failed")
        
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        result = db_setup.create_database("test_db")
        
        assert result is False

    @patch('core.database_setup.psycopg2.connect')
    def test_setup_schema_success(self, mock_connect):
        """Test successful schema setup."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        result = db_setup.setup_schema("test_db")
        
        assert result is True
        # Verify UUID extension is enabled
        mock_cursor.execute.assert_any_call('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    @patch('core.database_setup.psycopg2.connect')
    def test_setup_schema_failure(self, mock_connect):
        """Test schema setup failure."""
        mock_connect.side_effect = Exception("Connection failed")
        
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        result = db_setup.setup_schema("test_db")
        
        assert result is False

    @patch('core.database_setup.psycopg2.connect')
    def test_create_tables(self, mock_connect):
        """Test table creation."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        db_setup._create_tables(mock_cursor)
        
        # Verify that table creation SQL was executed
        execute_calls = mock_cursor.execute.call_args_list
        table_creates = [call for call in execute_calls 
                        if 'CREATE TABLE IF NOT EXISTS' in str(call)]
        
        # Should create multiple tables
        assert len(table_creates) >= 7  # apis, endpoints, parameters, etc.

    @patch('core.database_setup.psycopg2.connect')
    def test_create_indexes(self, mock_connect):
        """Test index creation."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        db_setup._create_indexes(mock_cursor)
        
        # Verify that index creation SQL was executed
        execute_calls = mock_cursor.execute.call_args_list
        index_creates = [call for call in execute_calls 
                        if 'CREATE INDEX IF NOT EXISTS' in str(call)]
        
        # Should create multiple indexes
        assert len(index_creates) >= 10

    @patch('core.database_setup.psycopg2.connect')
    def test_create_views(self, mock_connect):
        """Test view creation."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        db_setup._create_views(mock_cursor)
        
        # Verify that view creation SQL was executed
        execute_calls = mock_cursor.execute.call_args_list
        view_creates = [call for call in execute_calls 
                       if 'CREATE OR REPLACE VIEW' in str(call)]
        
        # Should create multiple views
        assert len(view_creates) >= 3

    @patch('core.database_setup.psycopg2.connect')
    def test_create_functions(self, mock_connect):
        """Test function creation."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value = mock_conn
        mock_cursor_context = MagicMock()
        mock_cursor_context.__enter__.return_value = mock_cursor
        mock_cursor_context.__exit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor_context
        
        db_setup = DatabaseSetup("localhost", "5432", "user", "pass")
        db_setup._create_functions(mock_cursor)
        
        # Verify that function creation SQL was executed
        execute_calls = mock_cursor.execute.call_args_list
        function_creates = [call for call in execute_calls 
                           if 'CREATE OR REPLACE FUNCTION' in str(call)]
        
        # Should create at least one function
        assert len(function_creates) >= 1
