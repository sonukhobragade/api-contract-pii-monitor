"""
Database Setup Module

Handles database creation, schema setup, and table creation for the OpenAPI contract testing framework.
"""
import psycopg2
import psycopg2.extras


class DatabaseSetup:
    """Handle database creation and setup"""
    
    def __init__(self, host: str, port: str, username: str, password: str):
        """
        Initialize database setup with connection parameters.
        
        Args:
            host (str): Database host
            port (str): Database port
            username (str): Database username
            password (str): Database password
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        
    def create_database(self, db_name: str = "openapi_store") -> bool:
        """
        Create a new database.
        
        Args:
            db_name (str): Name of the database to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Connect to postgres database to create new database
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database="postgres"  # Connect to default postgres db
            )
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Check if database exists
                cursor.execute("""
                    SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s
                """, (db_name,))
                
                exists = cursor.fetchone()
                if exists:
                    print(f"Database '{db_name}' already exists.")
                    return True
                
                # Create database
                cursor.execute(f'CREATE DATABASE "{db_name}"')
                print(f"Database '{db_name}' created successfully.")
                
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error creating database: {e}")
            return False
    
    def get_connection_string(self, db_name: str = "openapi_store") -> str:
        """
        Get connection string for the database.
        
        Args:
            db_name (str): Database name
            
        Returns:
            str: PostgreSQL connection string
        """
        missing = [
            name for name, value in (
                ("HOST", self.host), ("PORT", self.port),
                ("USERNAME", self.username), ("PASSWORD", self.password),
            ) if not value
        ]
        if missing:
            # Without this an empty password reaches psycopg2 and succeeds
            # against any server configured for trust authentication, which is
            # exactly the accident the config validation exists to prevent.
            raise ValueError(
                f"Missing required database settings: {', '.join(missing)}"
            )
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{db_name}"
    
    def setup_schema(self, db_name: str = "openapi_store") -> bool:
        """
        Create all tables and indexes.
        
        Args:
            db_name (str): Database name
            
        Returns:
            bool: True if successful, False otherwise
        """
        conn_str = self.get_connection_string(db_name)
        
        try:
            conn = psycopg2.connect(conn_str)
            conn.autocommit = True
            
            with conn.cursor() as cursor:
                # Enable UUID extension
                cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
                
                # Create tables
                self._create_tables(cursor)
                self._create_indexes(cursor)
                self._create_views(cursor)
                self._create_functions(cursor)
                
                print("Schema setup completed successfully.")
                
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error setting up schema: {e}")
            return False
    
    def _create_tables(self, cursor):
        """Create all tables"""
        
        # APIs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS apis (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                title VARCHAR(255) NOT NULL,
                version VARCHAR(100),
                description TEXT,
                base_url VARCHAR(500),
                server_urls JSONB,
                contact_info JSONB,
                license_info JSONB,
                raw_schema JSONB,
                release_tag VARCHAR(100),
                schema_hash VARCHAR(64),
                is_latest BOOLEAN DEFAULT TRUE,
                status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'archived')),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Endpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS endpoints (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                api_id UUID NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
                path VARCHAR(500) NOT NULL,
                method VARCHAR(10) NOT NULL,
                operation_id VARCHAR(255),
                summary TEXT,
                description TEXT,
                tags JSONB,
                deprecated BOOLEAN DEFAULT FALSE,
                security_schemes JSONB,
                servers JSONB,
                external_docs JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(api_id, path, method)
            )
        """)
        
        # Parameters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parameters (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                endpoint_id UUID NOT NULL REFERENCES endpoints(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                param_location VARCHAR(20) NOT NULL CHECK (param_location IN ('query', 'header', 'path', 'cookie')),
                data_type VARCHAR(50),
                format VARCHAR(50),
                required BOOLEAN DEFAULT FALSE,
                deprecated BOOLEAN DEFAULT FALSE,
                description TEXT,
                default_value TEXT,
                example_value TEXT,
                enum_values JSONB,
                schema_definition JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(endpoint_id, name, param_location)
            )
        """)
        
        # Request Bodies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_bodies (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                endpoint_id UUID NOT NULL REFERENCES endpoints(id) ON DELETE CASCADE,
                content_type VARCHAR(100) NOT NULL,
                required BOOLEAN DEFAULT FALSE,
                description TEXT,
                schema_definition JSONB,
                example_value JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Responses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                endpoint_id UUID NOT NULL REFERENCES endpoints(id) ON DELETE CASCADE,
                status_code VARCHAR(10) NOT NULL,
                description TEXT,
                content_type VARCHAR(100),
                schema_definition JSONB,
                headers JSONB,
                example_value JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Schema Components table (for reusable components)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_components (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                api_id UUID NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
                component_name VARCHAR(255) NOT NULL,
                component_type VARCHAR(50) NOT NULL CHECK (component_type IN ('schemas', 'responses', 'parameters', 'examples', 'requestBodies', 'headers', 'securitySchemes', 'links', 'callbacks')),
                definition JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(api_id, component_name, component_type)
            )
        """)
        
        # API Releases table (for version tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_releases (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                api_id UUID NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
                release_tag VARCHAR(100) NOT NULL,
                release_notes TEXT,
                endpoint_count INTEGER DEFAULT 0,
                breaking_changes INTEGER DEFAULT 0,
                total_changes INTEGER DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(api_id, release_tag)
            )
        """)
        
        # Schema Changes table (for tracking changes between versions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_changes (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                api_id UUID NOT NULL REFERENCES apis(id) ON DELETE CASCADE,
                endpoint_id UUID REFERENCES endpoints(id) ON DELETE CASCADE,
                release_tag VARCHAR(100) NOT NULL,
                change_type VARCHAR(50) NOT NULL,
                change_description TEXT NOT NULL,
                old_value JSONB,
                new_value JSONB,
                is_breaking BOOLEAN DEFAULT FALSE,
                detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        print("   ✅ All tables created successfully")
    
    def _create_indexes(self, cursor):
        """Create indexes for better performance"""
        
        indexes = [
            # APIs indexes
            "CREATE INDEX IF NOT EXISTS idx_apis_title ON apis(title)",
            "CREATE INDEX IF NOT EXISTS idx_apis_version ON apis(version)",
            "CREATE INDEX IF NOT EXISTS idx_apis_release_tag ON apis(release_tag)",
            "CREATE INDEX IF NOT EXISTS idx_apis_is_latest ON apis(is_latest)",
            "CREATE INDEX IF NOT EXISTS idx_apis_status ON apis(status)",
            "CREATE INDEX IF NOT EXISTS idx_apis_created_at ON apis(created_at)",
            
            # Endpoints indexes
            "CREATE INDEX IF NOT EXISTS idx_endpoints_api_id ON endpoints(api_id)",
            "CREATE INDEX IF NOT EXISTS idx_endpoints_path ON endpoints(path)",
            "CREATE INDEX IF NOT EXISTS idx_endpoints_method ON endpoints(method)",
            "CREATE INDEX IF NOT EXISTS idx_endpoints_tags ON endpoints USING GIN(tags)",
            "CREATE INDEX IF NOT EXISTS idx_endpoints_deprecated ON endpoints(deprecated)",
            
            # Parameters indexes
            "CREATE INDEX IF NOT EXISTS idx_parameters_endpoint_id ON parameters(endpoint_id)",
            "CREATE INDEX IF NOT EXISTS idx_parameters_name ON parameters(name)",
            "CREATE INDEX IF NOT EXISTS idx_parameters_location ON parameters(param_location)",
            "CREATE INDEX IF NOT EXISTS idx_parameters_required ON parameters(required)",
            
            # Request Bodies indexes
            "CREATE INDEX IF NOT EXISTS idx_request_bodies_endpoint_id ON request_bodies(endpoint_id)",
            "CREATE INDEX IF NOT EXISTS idx_request_bodies_content_type ON request_bodies(content_type)",
            
            # Responses indexes
            "CREATE INDEX IF NOT EXISTS idx_responses_endpoint_id ON responses(endpoint_id)",
            "CREATE INDEX IF NOT EXISTS idx_responses_status_code ON responses(status_code)",
            
            # Schema Components indexes
            "CREATE INDEX IF NOT EXISTS idx_schema_components_api_id ON schema_components(api_id)",
            "CREATE INDEX IF NOT EXISTS idx_schema_components_name ON schema_components(component_name)",
            "CREATE INDEX IF NOT EXISTS idx_schema_components_type ON schema_components(component_type)",
            
            # API Releases indexes
            "CREATE INDEX IF NOT EXISTS idx_api_releases_api_id ON api_releases(api_id)",
            "CREATE INDEX IF NOT EXISTS idx_api_releases_tag ON api_releases(release_tag)",
            "CREATE INDEX IF NOT EXISTS idx_api_releases_created_at ON api_releases(created_at)",
            
            # Schema Changes indexes
            "CREATE INDEX IF NOT EXISTS idx_schema_changes_api_id ON schema_changes(api_id)",
            "CREATE INDEX IF NOT EXISTS idx_schema_changes_endpoint_id ON schema_changes(endpoint_id)",
            "CREATE INDEX IF NOT EXISTS idx_schema_changes_release_tag ON schema_changes(release_tag)",
            "CREATE INDEX IF NOT EXISTS idx_schema_changes_change_type ON schema_changes(change_type)",
            "CREATE INDEX IF NOT EXISTS idx_schema_changes_is_breaking ON schema_changes(is_breaking)",
            "CREATE INDEX IF NOT EXISTS idx_schema_changes_detected_at ON schema_changes(detected_at)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print("   ✅ All indexes created successfully")
    
    def _create_views(self, cursor):
        """Create useful views"""
        
        # View for endpoint details with API info
        cursor.execute("""
            CREATE OR REPLACE VIEW endpoint_details AS
            SELECT 
                e.id as endpoint_id,
                e.path,
                e.method,
                e.operation_id,
                e.summary,
                e.description,
                e.tags,
                e.deprecated,
                a.id as api_id,
                a.title as api_title,
                a.version as api_version,
                a.release_tag,
                a.base_url,
                COUNT(p.id) as parameter_count,
                COUNT(rb.id) as request_body_count,
                COUNT(r.id) as response_count
            FROM endpoints e
            JOIN apis a ON e.api_id = a.id
            LEFT JOIN parameters p ON e.id = p.endpoint_id
            LEFT JOIN request_bodies rb ON e.id = rb.endpoint_id
            LEFT JOIN responses r ON e.id = r.endpoint_id
            GROUP BY e.id, a.id
        """)
        
        # View for API statistics
        cursor.execute("""
            CREATE OR REPLACE VIEW api_statistics AS
            SELECT 
                a.id as api_id,
                a.title,
                a.version,
                a.release_tag,
                a.status,
                COUNT(e.id) as total_endpoints,
                COUNT(CASE WHEN e.method = 'GET' THEN 1 END) as get_endpoints,
                COUNT(CASE WHEN e.method = 'POST' THEN 1 END) as post_endpoints,
                COUNT(CASE WHEN e.method = 'PUT' THEN 1 END) as put_endpoints,
                COUNT(CASE WHEN e.method = 'DELETE' THEN 1 END) as delete_endpoints,
                COUNT(CASE WHEN e.deprecated = true THEN 1 END) as deprecated_endpoints,
                0 as unique_tags,
                a.created_at,
                a.updated_at
            FROM apis a
            LEFT JOIN endpoints e ON a.id = e.api_id
            GROUP BY a.id
        """)
        
        # View for latest API versions
        cursor.execute("""
            CREATE OR REPLACE VIEW latest_apis AS
            SELECT DISTINCT ON (title)
                id,
                title,
                version,
                description,
                base_url,
                release_tag,
                status,
                created_at,
                updated_at
            FROM apis
            WHERE is_latest = true
            ORDER BY title, created_at DESC
        """)
        
        print("   ✅ All views created successfully")
    
    def _create_functions(self, cursor):
        """Create useful functions"""
        
        # Function to update the updated_at timestamp
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        # Triggers to automatically update updated_at
        tables_with_updated_at = ['apis', 'endpoints', 'parameters', 'request_bodies', 'responses']
        for table in tables_with_updated_at:
            cursor.execute(f"""
                DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
                CREATE TRIGGER update_{table}_updated_at
                    BEFORE UPDATE ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at_column();
            """)
        
        print("   ✅ All functions and triggers created successfully")
