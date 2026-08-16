"""
Unit Tests for Configuration Module

Tests the configuration loading and validation functionality.
"""
import os
import pytest
from unittest.mock import patch
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config


class TestConfig:
    """Test configuration module functionality."""
    
    def test_config_initialization_with_env_vars(self):
        """Test configuration initialization with environment variables."""
        with patch.dict(os.environ, {
            'HOST': 'localhost',
            'PORT': '5432',
            'USERNAME': 'postgres',
            'PASSWORD': 'test-password',
            'DB_NAME': 'openapi_store',
            'QA_ENDPOINT': 'https://qa-api.example.com',
            'AUTHORIZATION_TOKEN': 'test-token',
            'OPENAPI_SPEC_PRIMARY': 'https://api.example.com/api/openapi-proxy',
            'OPENAPI_SPEC_SECONDARY': 'https://api.example.com/api/openapi-proxy-modular'
        }):
            config = Config()
            
            # Test database configuration
            assert config.HOST == 'localhost'
            assert config.PORT == '5432'
            assert config.USERNAME == 'postgres'
            assert config.PASSWORD == 'test-password'
            assert config.DB_NAME == 'openapi_store'
            
            # Test API configuration
            assert config.QA_ENDPOINT == 'https://qa-api.example.com'
            assert config.AUTHORIZATION_TOKEN == 'test-token'
            assert config.OPENAPI_SPEC_PRIMARY == 'https://api.example.com/api/openapi-proxy'
            assert config.OPENAPI_SPEC_SECONDARY == 'https://api.example.com/api/openapi-proxy-modular'
    
    def test_config_defaults(self):
        """Test configuration defaults when environment variables are not set."""
        with patch.dict(os.environ, {
            'USERNAME': 'postgres',
            'PASSWORD': 'test',
            'DB_NAME': 'test_db'
        }, clear=True):
            config = Config()
            
            # Test defaults
            assert config.HOST == 'localhost'
            assert config.PORT == '5432'
            assert config.QA_ENDPOINT == ''
            assert config.AUTHORIZATION_TOKEN == ''
    
    def test_config_validation_missing_required(self):
        """Test configuration validation with missing required fields."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                Config()
            
            assert "Missing required environment variables" in str(exc_info.value)
    
    def test_get_connection_string(self):
        """Test connection string generation."""
        with patch.dict(os.environ, {
            'HOST': 'localhost',
            'PORT': '5432',
            'USERNAME': 'testuser',
            'PASSWORD': 'testpass',
            'DB_NAME': 'testdb'
        }):
            config = Config()
            conn_str = config.get_connection_string()
            
            expected = "postgresql://testuser:testpass@localhost:5432/testdb"
            assert conn_str == expected
    
    def test_get_database_params(self):
        """Test database parameters dictionary."""
        with patch.dict(os.environ, {
            'HOST': 'testhost',
            'PORT': '5433',
            'USERNAME': 'testuser',
            'PASSWORD': 'testpass',
            'DB_NAME': 'testdb'
        }):
            config = Config()
            params = config.get_database_params()
            
            expected = {
                'host': 'testhost',
                'port': '5433',
                'username': 'testuser',
                'password': 'testpass',
                'database': 'testdb'
            }
            assert params == expected
    
    def test_get_api_endpoints(self):
        """Test API endpoints dictionary."""
        with patch.dict(os.environ, {
            'HOST': 'localhost',
            'PORT': '5432',
            'USERNAME': 'postgres',
            'PASSWORD': 'test',
            'DB_NAME': 'test',
            'OPENAPI_SPEC_PRIMARY': 'https://api.example.com/openapi.json',
            'OPENAPI_SPEC_SECONDARY': 'https://api.example.com/openapi-modular.json'
        }):
            config = Config()
            endpoints = config.get_api_endpoints()
            
            expected = {
                'OPENAPI_SPEC_PRIMARY': 'https://api.example.com/openapi.json',
                'OPENAPI_SPEC_SECONDARY': 'https://api.example.com/openapi-modular.json'
            }
            assert endpoints == expected
    
    def test_get_api_endpoints_partial(self):
        """Test API endpoints with only one endpoint configured."""
        with patch.dict(os.environ, {
            'HOST': 'localhost',
            'PORT': '5432',
            'USERNAME': 'postgres',
            'PASSWORD': 'test',
            'DB_NAME': 'test',
            'OPENAPI_SPEC_PRIMARY': 'https://api.example.com/openapi.json'
        }, clear=True):
            config = Config()
            endpoints = config.get_api_endpoints()
            
            expected = {
                'OPENAPI_SPEC_PRIMARY': 'https://api.example.com/openapi.json'
            }
            assert endpoints == expected
    
    def test_get_request_headers_with_token(self):
        """Test request headers with authorization token."""
        with patch.dict(os.environ, {
            'HOST': 'localhost',
            'PORT': '5432',
            'USERNAME': 'postgres',
            'PASSWORD': 'test',
            'DB_NAME': 'test',
            'AUTHORIZATION_TOKEN': 'TestToken123'
        }):
            config = Config()
            headers = config.get_request_headers()
            
            expected = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "Bearer TestToken123"
            }
            assert headers == expected
    
    def test_get_request_headers_without_token(self):
        """Test request headers without authorization token."""
        with patch.dict(os.environ, {
            'HOST': 'localhost',
            'PORT': '5432',
            'USERNAME': 'postgres',
            'PASSWORD': 'test',
            'DB_NAME': 'test'
        }, clear=True):
            config = Config()
            headers = config.get_request_headers()
            
            expected = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            assert headers == expected

    def test_extra_headers_are_merged(self):
        """The default set is deliberately minimal, so a caller whose API needs
        more must be able to add them."""
        with patch.dict(os.environ, {
            'HOST': 'localhost', 'PORT': '5432', 'USERNAME': 'postgres',
            'PASSWORD': 'test', 'DB_NAME': 'test',
            'EXTRA_HEADERS': '{"X-Tenant": "acme"}',
        }, clear=True):
            assert Config().get_request_headers()["X-Tenant"] == "acme"

    def test_malformed_extra_headers_do_not_crash_the_run(self):
        """Bad JSON must not take down an analysis, but it must not pass
        unnoticed either: the header the caller thinks they set is absent."""
        with patch.dict(os.environ, {
            'HOST': 'localhost', 'PORT': '5432', 'USERNAME': 'postgres',
            'PASSWORD': 'test', 'DB_NAME': 'test',
            'EXTRA_HEADERS': 'not-json',
        }, clear=True):
            headers = Config().get_request_headers()
            assert headers == {"Content-Type": "application/json",
                               "Accept": "application/json"}
    
    def test_config_string_representation(self):
        """Test string representation of configuration."""
        with patch.dict(os.environ, {
            'HOST': 'testhost',
            'PORT': '5432',
            'USERNAME': 'testuser',
            'PASSWORD': 'testpass',
            'DB_NAME': 'testdb',
            'QA_ENDPOINT': 'https://qa.example.com',
            'AUTHORIZATION_TOKEN': 'token123',
            'OPENAPI_SPEC_PRIMARY': 'https://api.example.com/openapi.json'
        }, clear=True):
            config = Config()
            config_str = str(config)
            
            assert "testhost:5432/testdb" in config_str
            assert "testuser" in config_str
            assert "https://qa.example.com" in config_str
            assert "✅ Configured" in config_str  # Authorization configured
            assert "1 configured" in config_str  # One API endpoint


if __name__ == "__main__":
    pytest.main([__file__])
