"""
OpenAPI Parser Module

Handles parsing and inserting OpenAPI schemas into PostgreSQL database.
"""
import psycopg2
import psycopg2.extras
import requests
import json
import uuid
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from .config import config


class PostgreSQLOpenAPIParser:
    """Main parser class for OpenAPI schemas"""
    
    def __init__(self, connection_string: str):
        """
        Initialize parser with database connection.
        
        Args:
            connection_string (str): PostgreSQL connection string
        """
        self.conn = psycopg2.connect(connection_string)
        self.conn.autocommit = False
        
    def fetch_and_parse_schema_optimized(self, url: str, api_title: str = None) -> Optional[str]:
        """
        Optimized fetch that checks schema hash before parsing to avoid unnecessary DB operations.
        
        Args:
            url (str): URL to fetch OpenAPI schema from
            api_title (str): Expected API title for hash comparison
            
        Returns:
            Optional[str]: API ID if successful, None otherwise
        """
        try:
            print("🌐 Fetching fresh schema (zero database operations)...")
            headers = config.get_request_headers()
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            schema = response.json()
            schema_size = len(json.dumps(schema))
            print(f"✅ Schema fetched successfully ({schema_size} characters)")
            
            # Generate hash for comparison
            schema_str = json.dumps(schema, sort_keys=True)
            fresh_hash = hashlib.sha256(schema_str.encode()).hexdigest()
            
            # Get API title from schema if not provided
            if not api_title:
                api_title = schema.get('info', {}).get('title', 'Unknown API')
            
            # Check if this exact schema already exists
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, schema_hash FROM apis 
                    WHERE title = %s AND is_latest = TRUE
                    ORDER BY created_at DESC LIMIT 1
                """, (api_title,))
                
                current_api = cursor.fetchone()
                
                if current_api:
                    current_hash = current_api['schema_hash']
                    print(f"🔐 Current Hash: {current_hash[:16]}...")
                    print(f"🔐 Fresh Hash:   {fresh_hash[:16]}...")
                    
                    if current_hash == fresh_hash:
                        print("✅ Hashes match - no changes detected!")
                        print("💾 Zero database operations performed")
                        return str(current_api['id'])
                    else:
                        print("🚨 Hashes differ - changes confirmed!")
                        print("🔓 NOW performing custom parsing with database operations...")
                else:
                    print("ℹ️  No existing version found - will create first version")
            
            # If we reach here, schema has changed or is new - do full parsing
            return self._parse_schema_with_full_operations(schema, url)
            
        except requests.RequestException as e:
            print(f"❌ Error fetching schema: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            return None
        except Exception as e:
            print(f"❌ Error in optimized fetch: {e}")
            return None
    
    def _parse_schema_with_full_operations(self, schema: Dict[str, Any], url: str) -> Optional[str]:
        """
        Perform full schema parsing with database operations.
        
        Args:
            schema (Dict[str, Any]): OpenAPI schema
            url (str): Source URL
            
        Returns:
            Optional[str]: API ID if successful, None otherwise
        """
        try:
            print("🔧 Custom parsing - inserting new schema version...")
            
            # Generate release tag based on current timestamp
            release_tag = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Insert API information
                api_id = self.insert_api_info(cursor, schema, release_tag)
                
                # Parse components (reusable schemas)
                if 'components' in schema:
                    self.parse_components(cursor, schema['components'], api_id)
                
                # Parse paths (endpoints)
                if 'paths' in schema:
                    self.parse_paths(cursor, schema['paths'], api_id)
                
                # Create API release record
                self.create_api_release(cursor, api_id, release_tag, f"Automated import from {url}")
                
                # Commit transaction
                self.conn.commit()
                print("✅ Schema parsing completed successfully")
                
                return api_id
                
        except Exception as e:
            print(f"❌ Error in full parsing: {e}")
            self.conn.rollback()
            return None

    def fetch_and_parse_schema(self, url: str) -> Optional[str]:
        """
        Fetch OpenAPI schema from URL and parse into PostgreSQL.
        
        Args:
            url (str): URL to fetch OpenAPI schema from
            
        Returns:
            Optional[str]: API ID if successful, None otherwise
        """
        try:
            print(f"🌐 Fetching schema from: {url}")
            headers = config.get_request_headers()
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            schema = response.json()
            print("   ✅ Schema fetched successfully")
            
            # Generate release tag based on current timestamp
            release_tag = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Insert API information
                api_id = self.insert_api_info(cursor, schema, release_tag)
                
                # Parse components (reusable schemas)
                if 'components' in schema:
                    self.parse_components(cursor, schema['components'], api_id)
                
                # Parse paths (endpoints)
                if 'paths' in schema:
                    self.parse_paths(cursor, schema['paths'], api_id)
                
                # Create API release record
                self.create_api_release(cursor, api_id, release_tag, f"Automated import from {url}")
                
                # Commit transaction
                self.conn.commit()
                print("   ✅ Schema parsing completed successfully")
                
                return api_id
                
        except requests.RequestException as e:
            print(f"   ❌ Error fetching schema: {e}")
            self.conn.rollback()
            return None
        except json.JSONDecodeError as e:
            print(f"   ❌ Error parsing JSON: {e}")
            self.conn.rollback()
            return None
        except Exception as e:
            print(f"   ❌ Error parsing schema: {e}")
            self.conn.rollback()
            return None
    
    def insert_api_info(self, cursor, schema: Dict[str, Any], release_tag: str = None) -> str:
        """
        Insert API information and return API ID.
        
        Args:
            cursor: Database cursor
            schema (Dict[str, Any]): OpenAPI schema
            release_tag (str): Release tag for this version
            
        Returns:
            str: API ID
        """
        info = schema.get('info', {})
        title = info.get('title', 'Unknown API')
        version = info.get('version', '1.0.0')
        description = info.get('description', '')
        
        # Extract server information
        servers = schema.get('servers', [])
        base_url = servers[0].get('url') if servers else None
        server_urls = json.dumps(servers) if servers else None
        
        # Extract contact and license info
        contact_info = json.dumps(info.get('contact', {})) if info.get('contact') else None
        license_info = json.dumps(info.get('license', {})) if info.get('license') else None
        
        # Generate schema hash for change detection
        schema_str = json.dumps(schema, sort_keys=True)
        schema_hash = hashlib.sha256(schema_str.encode()).hexdigest()
        
        # Check if this exact schema already exists
        cursor.execute("""
            SELECT id FROM apis WHERE schema_hash = %s AND title = %s
        """, (schema_hash, title))
        
        existing = cursor.fetchone()
        if existing:
            print(f"   ⚠️  Schema with same hash already exists: {existing['id']}")
            return str(existing['id'])
        
        # Mark previous versions as not latest
        cursor.execute("""
            UPDATE apis SET is_latest = FALSE WHERE title = %s AND is_latest = TRUE
        """, (title,))
        
        # Insert new API version
        api_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO apis (
                id, title, version, description, base_url, server_urls, 
                contact_info, license_info, raw_schema, release_tag, schema_hash, is_latest
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            api_id, title, version, description, base_url, server_urls,
            contact_info, license_info, json.dumps(schema), release_tag, schema_hash, True
        ))
        
        # Add change log entry
        cursor.execute("""
            INSERT INTO schema_changes (api_id, release_tag, change_type, change_description)
            VALUES (%s, %s, %s, %s)
        """, (api_id, release_tag, 'api_created', f"New API '{title}' version {version} added"))
        
        print(f"   ✅ API inserted successfully with ID: {api_id}")
        return api_id
    
    def parse_components(self, cursor, components: Dict[str, Any], api_id: str):
        """
        Parse and insert reusable components with batching.
        
        Args:
            cursor: Database cursor
            components (Dict[str, Any]): Components section from OpenAPI schema
            api_id (str): API ID
        """
        batch_size = 50
        component_batch = []
        
        print(f"   🔍 Found {len(components)} component types: {list(components.keys())}")
        
        for component_type, definitions in components.items():
            if isinstance(definitions, dict):
                print(f"   🔧 Processing {component_type}: {len(definitions)} items")
                
                for i, (name, definition) in enumerate(definitions.items()):
                    component_batch.append((api_id, name, component_type, json.dumps(definition)))
                    
                    # Process batch when it reaches batch_size or at the end
                    if len(component_batch) >= batch_size or i == len(definitions) - 1:
                        print(f"      💾 Inserting batch of {len(component_batch)} {component_type} components...")
                        
                        cursor.executemany("""
                            INSERT INTO schema_components (api_id, component_name, component_type, definition)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (api_id, component_name, component_type) DO UPDATE SET
                            definition = EXCLUDED.definition
                        """, component_batch)
                        
                        component_batch = []
        
        print("   ✅ Components parsed successfully")
    
    def parse_paths(self, cursor, paths: Dict[str, Any], api_id: str):
        """
        Parse and insert endpoint information with batching.
        
        Args:
            cursor: Database cursor
            paths (Dict[str, Any]): Paths section from OpenAPI schema
            api_id (str): API ID
        """
        total_endpoints = sum(len([m for m in methods.keys() if m.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace']]) 
                            for methods in paths.values() if isinstance(methods, dict))
        
        print(f"   🛣️  Processing {len(paths)} paths with {total_endpoints} total endpoints")
        
        processed = 0
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
                
            # OpenAPI allows `parameters` on the Path Item itself, and every
            # operation under that path inherits them. They were skipped
            # entirely, so a path-level `email` or `national_id` query parameter
            # reached no operation and was never analysed for PII.
            shared_parameters = methods.get('parameters') or []
            if not isinstance(shared_parameters, list):
                shared_parameters = []

            for method, details in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace']:
                    continue

                if shared_parameters:
                    details = self._merge_path_parameters(details, shared_parameters)

                self.insert_endpoint(cursor, path, method.upper(), details, api_id)
                processed += 1
                
                if processed % 10 == 0:
                    print(f"      📊 Processed {processed}/{total_endpoints} endpoints...")
        
        print(f"   ✅ All {processed} endpoints processed successfully")
    
    @staticmethod
    def _merge_path_parameters(
        details: Dict[str, Any], shared_parameters: list
    ) -> Dict[str, Any]:
        """
        Combine path-level parameters with an operation's own.

        Per the OpenAPI specification an operation-level parameter overrides an
        inherited one when name and location match; anything else is additive.
        The merge returns a copy, so one operation's parameters never leak into
        its siblings under the same path.
        """
        if not isinstance(details, dict):
            return details

        own = details.get('parameters') or []
        if not isinstance(own, list):
            own = []

        own_keys = {
            (p.get('name'), p.get('in'))
            for p in own if isinstance(p, dict)
        }
        inherited = [
            p for p in shared_parameters
            if isinstance(p, dict) and (p.get('name'), p.get('in')) not in own_keys
        ]

        if not inherited:
            return details

        merged = dict(details)
        merged['parameters'] = inherited + own
        return merged

    def insert_endpoint(self, cursor, path: str, method: str, details: Dict[str, Any], api_id: str) -> str:
        """
        Insert endpoint and return endpoint ID.
        
        Args:
            cursor: Database cursor
            path (str): Endpoint path
            method (str): HTTP method
            details (Dict[str, Any]): Endpoint details from OpenAPI schema
            api_id (str): API ID
            
        Returns:
            str: Endpoint ID
        """
        endpoint_id = str(uuid.uuid4())
        
        # Extract endpoint information
        operation_id = details.get('operationId')
        summary = details.get('summary')
        description = details.get('description')
        tags = json.dumps(details.get('tags', []))
        deprecated = details.get('deprecated', False)
        security_schemes = json.dumps(details.get('security', []))
        servers = json.dumps(details.get('servers', []))
        external_docs = json.dumps(details.get('externalDocs', {})) if details.get('externalDocs') else None
        
        # Insert endpoint
        cursor.execute("""
            INSERT INTO endpoints (
                id, api_id, path, method, operation_id, summary, description,
                tags, deprecated, security_schemes, servers, external_docs
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (api_id, path, method) DO UPDATE SET
                operation_id = EXCLUDED.operation_id,
                summary = EXCLUDED.summary,
                description = EXCLUDED.description,
                tags = EXCLUDED.tags,
                deprecated = EXCLUDED.deprecated,
                security_schemes = EXCLUDED.security_schemes,
                servers = EXCLUDED.servers,
                external_docs = EXCLUDED.external_docs,
                updated_at = NOW()
            RETURNING id
        """, (endpoint_id, api_id, path, method, operation_id, summary, description,
              tags, deprecated, security_schemes, servers, external_docs))
        
        result = cursor.fetchone()
        if result:
            endpoint_id = str(result['id'])
        
        # Parse parameters
        if 'parameters' in details:
            self.parse_parameters(cursor, details['parameters'], endpoint_id)
        
        # Parse request body
        if 'requestBody' in details:
            self.parse_request_body(cursor, details['requestBody'], endpoint_id)
        
        # Parse responses
        if 'responses' in details:
            self.parse_responses(cursor, details['responses'], endpoint_id)
        
        return endpoint_id
    
    def parse_parameters(self, cursor, parameters: List[Dict[str, Any]], endpoint_id: str):
        """
        Parse and insert parameter information.
        
        Args:
            cursor: Database cursor
            parameters (List[Dict[str, Any]]): Parameters from OpenAPI schema
            endpoint_id (str): Endpoint ID
        """
        for param in parameters:
            schema_info = param.get('schema', {})
            
            param_data = {
                'endpoint_id': endpoint_id,
                'name': param.get('name', ''),
                'param_location': param.get('in', ''),
                'data_type': schema_info.get('type', ''),
                'format': schema_info.get('format'),
                'required': param.get('required', False),
                'deprecated': param.get('deprecated', False),
                'description': param.get('description'),
                'default_value': str(schema_info.get('default')) if 'default' in schema_info else None,
                'example_value': str(param.get('example')) if 'example' in param else None,
                'enum_values': json.dumps(schema_info.get('enum', [])),
                'schema_definition': json.dumps(schema_info)
            }
            
            cursor.execute("""
                INSERT INTO parameters (endpoint_id, name, param_location, data_type, format, required, deprecated, description, default_value, example_value, enum_values, schema_definition)
                VALUES (%(endpoint_id)s, %(name)s, %(param_location)s, %(data_type)s, %(format)s, %(required)s, %(deprecated)s, %(description)s, %(default_value)s, %(example_value)s, %(enum_values)s, %(schema_definition)s)
                ON CONFLICT (endpoint_id, name, param_location) DO UPDATE SET
                    data_type = EXCLUDED.data_type,
                    format = EXCLUDED.format,
                    required = EXCLUDED.required,
                    deprecated = EXCLUDED.deprecated,
                    description = EXCLUDED.description,
                    default_value = EXCLUDED.default_value,
                    example_value = EXCLUDED.example_value,
                    enum_values = EXCLUDED.enum_values,
                    schema_definition = EXCLUDED.schema_definition
            """, param_data)
    
    def parse_request_body(self, cursor, request_body: Dict[str, Any], endpoint_id: str):
        """
        Parse and insert request body information.
        
        Args:
            cursor: Database cursor
            request_body (Dict[str, Any]): Request body from OpenAPI schema
            endpoint_id (str): Endpoint ID
        """
        required = request_body.get('required', False)
        description = request_body.get('description', '')
        content = request_body.get('content', {})
        
        for content_type, content_info in content.items():
            schema_def = content_info.get('schema', {})
            example = content_info.get('example')
            
            cursor.execute("""
                INSERT INTO request_bodies (endpoint_id, content_type, required, description, schema_definition, example_value)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (endpoint_id, content_type, required, description, json.dumps(schema_def), json.dumps(example) if example else None))
    
    def parse_responses(self, cursor, responses: Dict[str, Any], endpoint_id: str):
        """
        Parse and insert response information.
        
        Args:
            cursor: Database cursor
            responses (Dict[str, Any]): Responses from OpenAPI schema
            endpoint_id (str): Endpoint ID
        """
        for status_code, response_info in responses.items():
            description = response_info.get('description', '')
            headers = response_info.get('headers', {})
            content = response_info.get('content', {})
            
            if content:
                for content_type, content_info in content.items():
                    schema_def = content_info.get('schema', {})
                    example = content_info.get('example')
                    
                    cursor.execute("""
                        INSERT INTO responses (endpoint_id, status_code, description, content_type, schema_definition, headers, example_value)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (endpoint_id, status_code, description, content_type, 
                          json.dumps(schema_def), json.dumps(headers), json.dumps(example) if example else None))
            else:
                # Response without content (like 204 No Content)
                cursor.execute("""
                    INSERT INTO responses (endpoint_id, status_code, description, headers)
                    VALUES (%s, %s, %s, %s)
                """, (endpoint_id, status_code, description, json.dumps(headers)))
    
    def create_api_release(self, cursor, api_id: str, release_tag: str, release_notes: str = ""):
        """
        Create an API release record.
        
        Args:
            cursor: Database cursor
            api_id (str): API ID
            release_tag (str): Release tag
            release_notes (str): Release notes
        """
        # Count endpoints for this API
        cursor.execute("""
            SELECT COUNT(*) as endpoint_count FROM endpoints WHERE api_id = %s
        """, (api_id,))
        
        endpoint_count = cursor.fetchone()['endpoint_count']
        
        # Count changes for this release
        cursor.execute("""
            SELECT 
                COUNT(*) as total_changes,
                COUNT(CASE WHEN is_breaking = true THEN 1 END) as breaking_changes
            FROM schema_changes 
            WHERE api_id = %s AND release_tag = %s
        """, (api_id, release_tag))
        
        changes = cursor.fetchone()
        total_changes = changes['total_changes']
        breaking_changes = changes['breaking_changes']
        
        cursor.execute("""
            INSERT INTO api_releases (api_id, release_tag, release_notes, endpoint_count, breaking_changes, total_changes)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (api_id, release_tag) DO UPDATE SET
                release_notes = EXCLUDED.release_notes,
                endpoint_count = EXCLUDED.endpoint_count,
                breaking_changes = EXCLUDED.breaking_changes,
                total_changes = EXCLUDED.total_changes
        """, (api_id, release_tag, release_notes, endpoint_count, breaking_changes, total_changes))
        
        print(f"   📋 Release '{release_tag}' created: {endpoint_count} endpoints, {total_changes} changes ({breaking_changes} breaking)")
    
    def detect_endpoint_changes(self, cursor, endpoint_id: str, old_endpoint: Dict, new_endpoint: Dict, release_tag: str):
        """
        Detect and record changes in endpoint schema.
        
        Args:
            cursor: Database cursor
            endpoint_id (str): Endpoint ID
            old_endpoint (Dict): Previous endpoint definition
            new_endpoint (Dict): New endpoint definition
            release_tag (str): Release tag
        """
        changes = []
        
        # Check for summary changes
        if old_endpoint.get('summary') != new_endpoint.get('summary'):
            changes.append({
                'type': 'summary_changed',
                'description': f"Summary changed from '{old_endpoint.get('summary')}' to '{new_endpoint.get('summary')}'",
                'old_value': old_endpoint.get('summary'),
                'new_value': new_endpoint.get('summary'),
                'is_breaking': False
            })
        
        # Check for deprecation changes
        if old_endpoint.get('deprecated', False) != new_endpoint.get('deprecated', False):
            is_breaking = new_endpoint.get('deprecated', False)  # Deprecating is breaking
            changes.append({
                'type': 'deprecation_changed',
                'description': f"Endpoint {'deprecated' if new_endpoint.get('deprecated') else 'un-deprecated'}",
                'old_value': old_endpoint.get('deprecated', False),
                'new_value': new_endpoint.get('deprecated', False),
                'is_breaking': is_breaking
            })
        
        # Record all detected changes
        for change in changes:
            cursor.execute("""
                INSERT INTO schema_changes (
                    api_id, endpoint_id, release_tag, change_type, change_description,
                    old_value, new_value, is_breaking
                ) VALUES (
                    (SELECT api_id FROM endpoints WHERE id = %s),
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (endpoint_id, endpoint_id, release_tag, change['type'], change['description'],
                  json.dumps(change['old_value']), json.dumps(change['new_value']), change['is_breaking']))
        
        if changes:
            print(f"   🔍 Detected {len(changes)} changes for endpoint {endpoint_id}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
