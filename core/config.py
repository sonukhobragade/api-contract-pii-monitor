"""
Configuration Module

Handles environment variables and configuration settings for the contract testing framework.
"""
import json
import logging
import os
from typing import Dict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class that loads settings from environment variables."""
    
    def __init__(self, validate: bool = True):
        """Initialize configuration from environment variables.

        Args:
            validate: raise immediately if a required variable is missing.
                The module-level ``config`` below passes False, so importing
                this package does not require a populated environment. The
                check still runs before anything actually connects.
        """
        # Database Configuration
        self.HOST = os.getenv('HOST', 'localhost')
        self.PORT = os.getenv('PORT', '5432')
        self.USERNAME = os.getenv('USERNAME', 'postgres')
        self.PASSWORD = os.getenv('PASSWORD', '')
        self.DB_NAME = os.getenv('DB_NAME', 'openapi_store')
        
        # API Configuration
        self.QA_ENDPOINT = os.getenv('QA_ENDPOINT', '')
        self.AUTHORIZATION_TOKEN = os.getenv('AUTHORIZATION_TOKEN', '')
        self.OPENAPI_SPEC_PRIMARY = os.getenv('OPENAPI_SPEC_PRIMARY', '')
        self.OPENAPI_SPEC_SECONDARY = os.getenv('OPENAPI_SPEC_SECONDARY', '')
        
        # Slack Configuration
        self.SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
        self.SLACK_TOKEN = os.getenv('SLACK_TOKEN', '')
        self.CHANNEL_ID = os.getenv('CHANNEL_ID', '')
        
        # Validate required configuration
        if validate:
            self._validate_config()
    
    def _validate_config(self):
        """Validate that required configuration is present."""
        required_fields = ['HOST', 'PORT', 'USERNAME', 'PASSWORD', 'DB_NAME']
        missing_fields = []
        
        for field in required_fields:
            if not getattr(self, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
    
    def get_connection_string(self) -> str:
        """
        Get PostgreSQL connection string.
        
        Returns:
            str: PostgreSQL connection string
        """
        self._validate_config()
        return f"postgresql://{self.USERNAME}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.DB_NAME}"
    
    def get_database_params(self) -> Dict[str, str]:
        """
        Get database connection parameters.
        
        Returns:
            Dict[str, str]: Database connection parameters
        """
        self._validate_config()
        return {
            'host': self.HOST,
            'port': self.PORT,
            'username': self.USERNAME,
            'password': self.PASSWORD,
            'database': self.DB_NAME
        }
    
    def get_api_endpoints(self) -> Dict[str, str]:
        """
        Get all OpenAPI endpoints.
        
        Returns:
            Dict[str, str]: Dictionary of endpoint names and URLs
        """
        endpoints = {}
        
        if self.OPENAPI_SPEC_PRIMARY:
            endpoints['OPENAPI_SPEC_PRIMARY'] = self.OPENAPI_SPEC_PRIMARY
        
        if self.OPENAPI_SPEC_SECONDARY:
            endpoints['OPENAPI_SPEC_SECONDARY'] = self.OPENAPI_SPEC_SECONDARY
        
        return endpoints
    
    def get_request_headers(self) -> Dict[str, str]:
        """
        Get default request headers for API calls.
        
        Returns:
            Dict[str, str]: Request headers
        """
        # Only the two headers every JSON API needs. The set here used to be a
        # particular mobile app's contract (deviceId, osVersionCode and so on),
        # which is nobody else's contract. Add whatever yours needs with
        # EXTRA_HEADERS, a JSON object.
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        extra = os.getenv("EXTRA_HEADERS", "").strip()
        if extra:
            try:
                parsed = json.loads(extra)
                if isinstance(parsed, dict):
                    headers.update({str(k): str(v) for k, v in parsed.items()})
                else:
                    logger.warning("EXTRA_HEADERS is not a JSON object; ignoring it")
            except json.JSONDecodeError as exc:
                # Silently ignoring this would send requests without the header
                # the caller believes they configured.
                logger.warning("EXTRA_HEADERS is not valid JSON (%s); ignoring it", exc)
        
        if self.AUTHORIZATION_TOKEN:
            headers["Authorization"] = f"Bearer {self.AUTHORIZATION_TOKEN}"
        
        return headers
    
    def __str__(self) -> str:
        """String representation of configuration (without sensitive data)."""
        return f"""Configuration:
  Database: {self.HOST}:{self.PORT}/{self.DB_NAME}
  Username: {self.USERNAME}
  QA Endpoint: {self.QA_ENDPOINT}
  OpenAPI Endpoints: {len(self.get_api_endpoints())} configured
  Authorization: {'✅ Configured' if self.AUTHORIZATION_TOKEN else '❌ Not configured'}
"""


# Global configuration instance
# Importing this module must not require a configured environment: tests and
# tooling import it to read defaults. Anything that actually connects calls
# _validate_config() first and fails there with the missing names.
config = Config(validate=False)
