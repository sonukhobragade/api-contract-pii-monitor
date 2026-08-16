"""
Backward Compatibility Module for ApiPostgres

This module maintains backward compatibility while using the new modular structure.
All original functionality is preserved through imports from the modular components.
"""

# Import all modular components
import os
from .database_setup import DatabaseSetup
from .openapi_parser import PostgreSQLOpenAPIParser
from .openapi_querier import OpenAPIQuerier

# Re-export for backward compatibility
__all__ = ['DatabaseSetup', 'PostgreSQLOpenAPIParser', 'OpenAPIQuerier']


def main():
    """
    Main function demonstrating the OpenAPI PostgreSQL integration.
    This maintains the same functionality as the original ApiPostgres.py main function.
    """
    # Database configuration
    HOST = os.getenv("HOST", "localhost")
    PORT = os.getenv("PORT", "5432")
    USERNAME = os.getenv("USERNAME", "postgres")
    PASSWORD = os.getenv("PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "openapi_store")
    
    print("🚀 Starting OpenAPI PostgreSQL Integration")
    print("=" * 50)
    
    # Step 1: Setup database
    print("\n=== Database Setup ===")
    db_setup = DatabaseSetup(HOST, PORT, USERNAME, PASSWORD)
    
    # Create database
    if db_setup.create_database(DB_NAME):
        print(f"✅ Database '{DB_NAME}' is ready")
        
        # Setup schema
        if db_setup.setup_schema(DB_NAME):
            print("✅ Database schema created successfully")
            
            # Step 2: Parse OpenAPI schema
            conn_str = db_setup.get_connection_string(DB_NAME)
            parser = PostgreSQLOpenAPIParser(conn_str)
            
            print("\n=== Fetching and Parsing API Schema ===")
            api_id = parser.fetch_and_parse_schema("https://api.example.com/api/openapi-proxy")
            
            if api_id:
                print(f"✅ API schema parsed successfully with ID: {api_id}")
                
                # Step 3: Test queries
                querier = OpenAPIQuerier(conn_str)
                
                print("\n=== API Statistics ===")
                stats = querier.get_api_stats(api_id)
                print(f"Total endpoints: {stats.get('total_endpoints', 0)}")
                print(f"GET: {stats.get('get_endpoints', 0)}, POST: {stats.get('post_endpoints', 0)}")
                print(f"PUT: {stats.get('put_endpoints', 0)}, DELETE: {stats.get('delete_endpoints', 0)}")
                print(f"Deprecated: {stats.get('deprecated_endpoints', 0)}")
                print(f"Unique tags: {stats.get('unique_tags', 0)}")
                
                print("\n=== Sample Endpoints ===")
                sample_endpoints = querier.search_endpoints()[:10]
                for endpoint in sample_endpoints:
                    print(f"{endpoint['method']} {endpoint['path']} - {endpoint['summary'] or 'No summary'}")
                
                print("\n=== POST Endpoints ===")
                post_endpoints = querier.search_endpoints(method="POST")[:5]
                for endpoint in post_endpoints:
                    print(f"POST {endpoint['path']} - {endpoint['summary'] or 'No summary'}")
                
                print("\n=== API Release Information ===")
                releases = querier.get_api_releases(api_id)
                if releases:
                    latest_release = releases[0]
                    print(f"Latest Release: {latest_release['release_tag']}")
                    print(f"Release Date: {latest_release['created_at']}")
                    print(f"Endpoint Count: {latest_release['endpoint_count']}")
                    print(f"Breaking Changes: {latest_release['breaking_changes']}")
                    print(f"Total Changes: {latest_release['total_changes']}")
                
                print("\n=== Schema Changes ===")
                changes = querier.get_schema_changes(api_id=api_id)
                if changes:
                    print(f"Total schema changes detected: {len(changes)}")
                    for change in changes[:5]:  # Show first 5 changes
                        print(f"  - {change['change_type']}: {change['change_description']}")
                        print(f"    Release: {change['release_tag']}, Date: {change['detected_at']}")
                else:
                    print("No schema changes detected")
                
                print("\n=== Latest APIs Summary ===")
                latest_apis = querier.get_latest_apis()
                for api in latest_apis:
                    print(f"API: {api['title']} v{api['version']} (Release: {api['release_tag']})")
                    print(f"  Status: {api['status']}, Endpoints: {api.get('endpoint_count', 0)}, Changes: {api.get('total_changes', 0)}")
                
                querier.close()
            else:
                print("❌ Failed to parse API schema")
            
            parser.close()
        else:
            print("❌ Failed to setup database schema")
    else:
        print("❌ Failed to create database")
    
    print("\n=== Setup Complete ===")
    print(f"Connection string: postgresql://{USERNAME}:***@{HOST}:{PORT}/{DB_NAME}")
    print("You can now use the querier to search and analyze your API endpoints!")


if __name__ == "__main__":
    main()
