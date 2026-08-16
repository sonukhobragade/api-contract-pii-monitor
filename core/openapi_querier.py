"""
OpenAPI Querier Module

Handles querying and retrieving data from the OpenAPI database.
"""
import psycopg2
import psycopg2.extras
from typing import Dict, Any, List, Optional


class OpenAPIQuerier:
    """Class for querying the stored OpenAPI data"""
    
    def __init__(self, connection_string: str):
        """
        Initialize querier with database connection.
        
        Args:
            connection_string (str): PostgreSQL connection string
        """
        self.conn = psycopg2.connect(connection_string)
    
    def search_endpoints(self, search_term: str = "", method: str = "", 
                        tag: str = "", api_id: str = "") -> List[Dict[str, Any]]:
        """
        Search endpoints with various filters.
        
        Args:
            search_term (str): Search in path, summary, or description
            method (str): HTTP method filter
            tag (str): Tag filter
            api_id (str): API ID filter
            
        Returns:
            List[Dict[str, Any]]: List of matching endpoints
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            query = """
                SELECT 
                    e.id, e.path, e.method, e.operation_id, e.summary, e.description,
                    e.tags, e.deprecated, a.title as api_title, a.version as api_version
                FROM endpoints e
                JOIN apis a ON e.api_id = a.id
                WHERE 1=1
            """
            params = []
            
            if search_term:
                query += " AND (e.path ILIKE %s OR e.summary ILIKE %s OR e.description ILIKE %s)"
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            if method:
                query += " AND e.method = %s"
                params.append(method.upper())
            
            if tag:
                query += " AND e.tags::jsonb ? %s"
                params.append(tag)
            
            if api_id:
                query += " AND e.api_id = %s"
                params.append(api_id)
            
            query += " ORDER BY e.path, e.method"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_endpoint_details(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific endpoint.
        
        Args:
            endpoint_id (str): Endpoint ID
            
        Returns:
            Optional[Dict[str, Any]]: Endpoint details or None if not found
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    e.*,
                    a.title as api_title,
                    a.version as api_version,
                    a.base_url
                FROM endpoints e
                JOIN apis a ON e.api_id = a.id
                WHERE e.id = %s
            """, (endpoint_id,))
            
            endpoint = cursor.fetchone()
            if not endpoint:
                return None
            
            endpoint = dict(endpoint)
            
            # Get parameters
            cursor.execute("""
                SELECT * FROM parameters WHERE endpoint_id = %s ORDER BY name
            """, (endpoint_id,))
            endpoint['parameters'] = [dict(row) for row in cursor.fetchall()]
            
            # Get request bodies
            cursor.execute("""
                SELECT * FROM request_bodies WHERE endpoint_id = %s
            """, (endpoint_id,))
            endpoint['request_bodies'] = [dict(row) for row in cursor.fetchall()]
            
            # Get responses
            cursor.execute("""
                SELECT * FROM responses WHERE endpoint_id = %s ORDER BY status_code
            """, (endpoint_id,))
            endpoint['responses'] = [dict(row) for row in cursor.fetchall()]
            
            return endpoint
    
    def get_api_stats(self, api_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific API.
        
        Args:
            api_id (str): API ID
            
        Returns:
            Dict[str, Any]: API statistics
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM api_statistics WHERE api_id = %s
            """, (api_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else {}
    
    def get_schema_changes(self, api_id: str = "", endpoint_id: str = "", 
                          release_tag: str = "", is_breaking: bool = None) -> List[Dict[str, Any]]:
        """
        Get schema changes with various filters.
        
        Args:
            api_id (str): API ID filter
            endpoint_id (str): Endpoint ID filter
            release_tag (str): Release tag filter
            is_breaking (bool): Filter for breaking changes
            
        Returns:
            List[Dict[str, Any]]: List of schema changes
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            query = """
                SELECT 
                    sc.*,
                    a.title as api_title,
                    a.version as api_version,
                    e.path as endpoint_path,
                    e.method as endpoint_method
                FROM schema_changes sc
                JOIN apis a ON sc.api_id = a.id
                LEFT JOIN endpoints e ON sc.endpoint_id = e.id
                WHERE 1=1
            """
            params = []
            
            if api_id:
                query += " AND sc.api_id = %s"
                params.append(api_id)
            
            if endpoint_id:
                query += " AND sc.endpoint_id = %s"
                params.append(endpoint_id)
            
            if release_tag:
                query += " AND sc.release_tag = %s"
                params.append(release_tag)
            
            if is_breaking is not None:
                query += " AND sc.is_breaking = %s"
                params.append(is_breaking)
            
            query += " ORDER BY sc.detected_at DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_api_releases(self, api_id: str) -> List[Dict[str, Any]]:
        """
        Get all releases for a specific API.
        
        Args:
            api_id (str): API ID
            
        Returns:
            List[Dict[str, Any]]: List of API releases
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM api_releases 
                WHERE api_id = %s 
                ORDER BY created_at DESC
            """, (api_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_latest_apis(self) -> List[Dict[str, Any]]:
        """
        Get all latest API versions.
        
        Returns:
            List[Dict[str, Any]]: List of latest APIs with statistics
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    la.*,
                    COALESCE(stats.total_endpoints, 0) as endpoint_count,
                    COALESCE(changes.total_changes, 0) as total_changes
                FROM latest_apis la
                LEFT JOIN api_statistics stats ON la.id = stats.api_id
                LEFT JOIN (
                    SELECT api_id, COUNT(*) as total_changes
                    FROM schema_changes
                    GROUP BY api_id
                ) changes ON la.id = changes.api_id
                ORDER BY la.title
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_api_change_summary(self, api_id: str) -> Dict[str, Any]:
        """
        Get a summary of changes for a specific API.
        
        Args:
            api_id (str): API ID
            
        Returns:
            Dict[str, Any]: Change summary
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_changes,
                    COUNT(CASE WHEN is_breaking = true THEN 1 END) as breaking_changes,
                    COUNT(DISTINCT release_tag) as total_releases,
                    COUNT(DISTINCT endpoint_id) as affected_endpoints,
                    MIN(detected_at) as first_change,
                    MAX(detected_at) as last_change
                FROM schema_changes
                WHERE api_id = %s
            """, (api_id,))
            
            summary = dict(cursor.fetchone())
            
            # Get change types breakdown
            cursor.execute("""
                SELECT 
                    change_type,
                    COUNT(*) as count,
                    COUNT(CASE WHEN is_breaking = true THEN 1 END) as breaking_count
                FROM schema_changes
                WHERE api_id = %s
                GROUP BY change_type
                ORDER BY count DESC
            """, (api_id,))
            
            summary['change_types'] = [dict(row) for row in cursor.fetchall()]
            
            return summary
    
    def get_components(self, api_id: str, component_type: str = "") -> List[Dict[str, Any]]:
        """
        Get reusable components for an API.
        
        Args:
            api_id (str): API ID
            component_type (str): Component type filter
            
        Returns:
            List[Dict[str, Any]]: List of components
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            query = """
                SELECT * FROM schema_components 
                WHERE api_id = %s
            """
            params = [api_id]
            
            if component_type:
                query += " AND component_type = %s"
                params.append(component_type)
            
            query += " ORDER BY component_type, component_name"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def search_by_parameter(self, parameter_name: str, parameter_location: str = "") -> List[Dict[str, Any]]:
        """
        Search endpoints by parameter name.
        
        Args:
            parameter_name (str): Parameter name to search for
            parameter_location (str): Parameter location filter (query, header, path, cookie)
            
        Returns:
            List[Dict[str, Any]]: List of endpoints with matching parameters
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            query = """
                SELECT DISTINCT
                    e.id, e.path, e.method, e.summary,
                    a.title as api_title, a.version as api_version,
                    p.name as parameter_name, p.param_location, p.required, p.data_type
                FROM endpoints e
                JOIN apis a ON e.api_id = a.id
                JOIN parameters p ON e.id = p.endpoint_id
                WHERE p.name ILIKE %s
            """
            params = [f"%{parameter_name}%"]
            
            if parameter_location:
                query += " AND p.param_location = %s"
                params.append(parameter_location)
            
            query += " ORDER BY e.path, e.method"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_endpoint_schema(self, path: str, method: str, api_id: str = "") -> Optional[Dict[str, Any]]:
        """
        Get complete schema for a specific endpoint.
        
        Args:
            path (str): Endpoint path
            method (str): HTTP method
            api_id (str): API ID (optional, uses latest if not provided)
            
        Returns:
            Optional[Dict[str, Any]]: Complete endpoint schema or None if not found
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            query = """
                SELECT e.id
                FROM endpoints e
                JOIN apis a ON e.api_id = a.id
                WHERE e.path = %s AND e.method = %s
            """
            params = [path, method.upper()]
            
            if api_id:
                query += " AND a.id = %s"
                params.append(api_id)
            else:
                query += " AND a.is_latest = true"
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            if not result:
                return None
            
            return self.get_endpoint_details(result['id'])
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
