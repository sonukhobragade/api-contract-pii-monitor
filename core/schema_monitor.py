"""
Schema Monitor Module

Main orchestration logic for True Zero-Insertion Schema Monitoring.
"""
import hashlib
import json
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

from core.config import config
from core.openapi_parser import PostgreSQLOpenAPIParser
from core.openapi_querier import OpenAPIQuerier
from core.schema_change_detector import SchemaChangeDetector
from core.endpoint_statistics import EndpointStatisticsCollector
from core.notification_manager import NotificationManager
from core.report_generator import ReportGenerator


class TrueZeroInsertionSchemaMonitor:
    """Main schema monitor that performs ZERO database operations until changes are confirmed."""
    
    def __init__(self):
        """Initialize the monitor with database connections."""
        self.conn_str = config.get_connection_string()
        self.querier = OpenAPIQuerier(self.conn_str)
        
        # Initialize modular components
        self.endpoint_stats = EndpointStatisticsCollector(self.querier)
        self.notification_manager = NotificationManager()
        self.report_generator = ReportGenerator()
        
        # Only create parser and detector when we need to insert data
        self.parser = None
        self.detector = None
        
        self.report = {
            'timestamp': datetime.now().isoformat(),
            'total_apis_monitored': 0,
            'apis_with_changes': 0,
            'apis_unchanged': 0,
            'total_changes': 0,
            'breaking_changes': 0,
            'apis_processed': [],
            'unchanged_apis': [],
            'errors': [],
            'recommendations': [],
            'slack_notifications_sent': 0,
            'database_operations_avoided': 0,
            'hash_comparisons_performed': 0,
            'total_endpoints_monitored': 0,
            'api_endpoint_details': []
        }
    
    def run_nightly_check(self) -> Dict[str, Any]:
        """
        Run the complete nightly schema monitoring process.
        ZERO database operations unless changes are confirmed.
        
        Returns:
            Dict[str, Any]: Complete monitoring report
        """
        print("🔒 Starting True Zero-Insertion Nightly Schema Monitor")
        print("=" * 60)
        print(f"📅 Timestamp: {self.report['timestamp']}")
        print(f"🔗 Database: {config.HOST}:{config.PORT}/{config.DB_NAME}")
        print("💡 Strategy: ZERO database operations until changes confirmed")
        
        try:
            # Step 1: Get API endpoints from config
            api_endpoints = config.get_api_endpoints()
            self.report['total_apis_monitored'] = len(api_endpoints)
            
            print(f"\n📋 Found {len(api_endpoints)} APIs to monitor:")
            for name, url in api_endpoints.items():
                print(f"   - {name}: {url}")
            
            # Step 2: Process each API endpoint with true zero-insertion logic
            for endpoint_name, endpoint_url in api_endpoints.items():
                print(f"\n🔍 Processing {endpoint_name}")
                print(f"   URL: {endpoint_url}")
                
                try:
                    self._process_single_api_true_zero_insertion(endpoint_name, endpoint_url)
                    
                except Exception as e:
                    error_msg = f"Error processing {endpoint_name}: {str(e)}"
                    print(f"   ❌ {error_msg}")
                    self.report['errors'].append(error_msg)
            
            # Step 3: Collect endpoint statistics for showcase
            endpoint_statistics = self.endpoint_stats.collect_api_endpoint_statistics()
            self.report.update(endpoint_statistics)
            
            # Step 4: Always send Slack notifications (for both changes and no-changes)
            success = self.notification_manager.send_slack_notification(self.report)
            if success:
                self.report['slack_notifications_sent'] = 1
            
            # Step 5: Generate recommendations
            self.report['recommendations'] = self.report_generator.generate_recommendations(self.report)
            
            # Step 6: Create reports
            self._create_reports()
            
            print("\n✅ True zero-insertion monitoring completed successfully")
            print(f"🔒 Database operations avoided: {self.report['database_operations_avoided']}")
            print(f"🔍 Hash comparisons performed: {self.report['hash_comparisons_performed']}")
            
        except Exception as e:
            error_msg = f"Critical error in nightly monitor: {str(e)}"
            print(f"❌ {error_msg}")
            self.report['errors'].append(error_msg)
        
        finally:
            self._cleanup()
        
        return self.report
    
    def _process_single_api_true_zero_insertion(self, endpoint_name: str, endpoint_url: str):
        """Process a single API endpoint with absolutely zero database operations until changes confirmed."""
        
        # Step 1: Get current version of this API (READ-ONLY operation)
        current_versions = self._get_api_versions_by_endpoint_readonly(endpoint_name)
        
        if not current_versions:
            print(f"   ℹ️  No existing version found for {endpoint_name}")
            print("   📝 Creating first version (this requires database insertion)...")
            
            # For first version, we must insert - but this is not a "change"
            self._ensure_parser_initialized()
            # Use optimized method even for first version
            fresh_api_id = self.parser.fetch_and_parse_schema_optimized(endpoint_url, endpoint_name)
            if fresh_api_id:
                self.report['unchanged_apis'].append({
                    'endpoint_name': endpoint_name,
                    'status': 'first_version_created',
                    'api_id': fresh_api_id,
                    'database_operations_required': True
                })
                print(f"   ✅ First version created: {fresh_api_id}")
            return
        
        current_version = current_versions[0]  # Most recent
        print(f"   📊 Current version: {current_version['title']} v{current_version['version']}")
        print(f"   📋 Current ID: {current_version['id']}")
        print(f"   🔐 Current Hash: {current_version['schema_hash'][:16]}...")
        print(f"   📅 Created: {current_version['created_at']}")
        
        # Step 2: Fetch fresh schema WITHOUT any database operations
        print("   🌐 Fetching fresh schema (zero database operations)...")
        fresh_schema = self._fetch_schema_only(endpoint_url)
        
        if not fresh_schema:
            self.report['errors'].append(f"Failed to fetch fresh schema for {endpoint_name}")
            return
        
        # Step 3: Calculate hash of fresh schema (NO database operations)
        fresh_hash = self._calculate_schema_hash(fresh_schema)
        print(f"   🔐 Fresh Hash:   {fresh_hash[:16]}...")
        
        # Step 4: Compare hashes - CRITICAL DECISION POINT
        self.report['hash_comparisons_performed'] += 1
        
        if fresh_hash == current_version['schema_hash']:
            print("   ✅ Hashes match - ZERO changes detected")
            print("   🔒 ZERO database operations performed")
            print("   💾 No parsing, no insertion, no processing")
            
            self.report['apis_unchanged'] += 1
            self.report['database_operations_avoided'] += 1
            self.report['unchanged_apis'].append({
                'endpoint_name': endpoint_name,
                'api_title': current_version['title'],
                'current_version': current_version['version'],
                'status': 'no_changes_hash_identical',
                'hash_comparison': 'identical',
                'database_operations_avoided': True,
                'last_check': datetime.now().isoformat()
            })
            return
        
        print("   🚨 Hashes differ - changes confirmed!")
        print("   🔓 NOW initializing database operations...")
        
        # Step 5: ONLY NOW do we initialize parser and perform database operations
        self._ensure_parser_initialized()
        self._ensure_detector_initialized()
        
        print("   📝 Parsing and inserting new version...")
        # Use optimized method that will check hash first and avoid duplicate insertion
        api_title = current_version.get('title', endpoint_name)
        fresh_api_id = self.parser.fetch_and_parse_schema_optimized(endpoint_url, api_title)
        
        if not fresh_api_id:
            self.report['errors'].append(f"Failed to parse fresh schema for {endpoint_name}")
            return
        
        # Check if the returned API ID is the same as current (meaning no changes)
        if fresh_api_id == current_version['id']:
            print("   ✅ Optimized method confirmed: ZERO changes detected")
            print(f"   🔒 Returned existing API ID: {fresh_api_id}")
            print("   💾 No new version created, no database operations performed")
            
            self.report['apis_unchanged'] += 1
            self.report['database_operations_avoided'] += 1
            self.report['unchanged_apis'].append({
                'endpoint_name': endpoint_name,
                'api_title': current_version['title'],
                'current_version': current_version['version'],
                'status': 'no_changes_optimized_detection',
                'hash_comparison': 'identical_via_optimized_method',
                'database_operations_avoided': True,
                'last_check': datetime.now().isoformat()
            })
            return
        
        print(f"   ✅ New version created: {fresh_api_id}")
        print(f"   📝 Previous ID: {current_version['id']}")
        print(f"   📝 New ID:      {fresh_api_id}")
        
        # Step 6: Analyze the changes
        print("   🔍 Analyzing changes between versions...")
        changes = self.detector.detect_api_changes(current_version['id'], fresh_api_id)
        
        # Step 7: Process and record results
        self._process_change_results(changes, endpoint_name, current_version, fresh_api_id)
    
    def _get_api_versions_by_endpoint_readonly(self, endpoint_name: str) -> List[Dict[str, Any]]:
        """Get all versions of an API by endpoint name (READ-ONLY operation)."""
        try:
            # Map config endpoint names to actual API titles in database
            endpoint_to_title_map = {
                'OPENAPI_SPEC_PRIMARY': 'Primary API',
                'OPENAPI_SPEC_SECONDARY': 'Secondary API'
            }
            
            api_title = endpoint_to_title_map.get(endpoint_name, endpoint_name)
            
            with self.querier.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, version, schema_hash, created_at, is_latest
                    FROM apis 
                    WHERE title = %s 
                    ORDER BY created_at DESC
                """, (api_title,))
                
                results = cursor.fetchall()
                if results:
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in results]
                return []
        except Exception as e:
            print(f"   ❌ Error fetching API versions: {str(e)}")
            return []
    
    def _fetch_schema_only(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch schema from URL with ZERO database operations."""
        try:
            headers = config.get_request_headers()
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   ❌ Error fetching schema: {str(e)}")
            return None
    
    def _calculate_schema_hash(self, schema: Dict[str, Any]) -> str:
        """Calculate hash of schema for comparison (ZERO database operations)."""
        schema_str = json.dumps(schema, sort_keys=True)
        return hashlib.sha256(schema_str.encode()).hexdigest()
    
    def _ensure_parser_initialized(self):
        """Initialize parser only when database operations are required."""
        if not self.parser:
            print("   🔧 Initializing parser for database operations...")
            self.parser = PostgreSQLOpenAPIParser(self.conn_str)
    
    def _ensure_detector_initialized(self):
        """Initialize detector only when change analysis is required."""
        if not self.detector:
            print("   🔧 Initializing detector for change analysis...")
            self.detector = SchemaChangeDetector(self.conn_str)
    
    def _process_change_results(self, changes: Dict[str, Any], endpoint_name: str, 
                               previous_version: Dict, fresh_api_id: str):
        """Process and record change detection results."""
        # Extract change counts from the summary or fallback to direct counts
        summary = changes.get('summary', {})
        total_changes = summary.get('total_changes', 0) or len(changes.get('detailed_changes', []))
        breaking_changes = summary.get('breaking_changes', 0)
        endpoint_changes = summary.get('endpoint_changes', 0) or len(changes.get('endpoint_changes', []))
        parameter_changes = summary.get('parameter_changes', 0) or len(changes.get('parameter_changes', []))
        response_changes = summary.get('response_changes', 0) or len(changes.get('response_changes', []))
        component_changes = summary.get('component_changes', 0) or len(changes.get('component_changes', []))
        
        print("   📊 Change Analysis Results:")
        print(f"      Total Changes: {total_changes}")
        print(f"      Breaking Changes: {breaking_changes}")
        print(f"      Endpoint Changes: {endpoint_changes}")
        print(f"      Parameter Changes: {parameter_changes}")
        print(f"      Response Changes: {response_changes}")
        print(f"      Component Changes: {component_changes}")
        
        # Update report totals
        self.report['total_changes'] += total_changes
        self.report['breaking_changes'] += breaking_changes
        self.report['apis_with_changes'] += 1
        
        # Enhance sample changes with more detailed information
        enhanced_sample_changes = self._enhance_sample_changes(changes.get('sample_changes', []) or changes.get('detailed_changes', [])[:10])
        
        # Create change analysis structure for detailed Slack reporting
        change_analysis = {
            'endpoint_changes': changes.get('endpoint_changes', []),
            'parameter_changes': changes.get('parameter_changes', []),
            'response_changes': changes.get('response_changes', []),
            'component_changes': changes.get('component_changes', [])
        }
        
        # Record API processing details
        self.report['apis_processed'].append({
            'endpoint_name': endpoint_name,
            'api_title': previous_version['title'],
            'previous_version': previous_version['version'],
            'fresh_api_id': fresh_api_id,
            'total_changes': total_changes,
            'breaking_changes': breaking_changes,
            'database_operations_performed': True,
            'requires_notification': breaking_changes > 0 or total_changes > 10,
            'sample_changes': enhanced_sample_changes[:10],  # First 10 changes with details
            'endpoint_changes': endpoint_changes,
            'parameter_changes': parameter_changes,
            'response_changes': response_changes,
            'component_changes': component_changes,
            # Add the full change analysis data for detailed Slack reporting
            'change_analysis': change_analysis
        })
        
        print("   💾 Changes recorded for reporting and notifications")
    
    def _enhance_sample_changes(self, sample_changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance sample changes with additional formatting and information."""
        enhanced_changes = []
        
        for change in sample_changes:
            enhanced_change = change.copy()
            
            # Ensure all required fields exist
            enhanced_change.setdefault('change_type', 'unknown')
            enhanced_change.setdefault('endpoint_path', 'N/A')
            enhanced_change.setdefault('description', 'No description available')
            enhanced_change.setdefault('is_breaking', False)
            enhanced_change.setdefault('old_value', 'N/A')
            enhanced_change.setdefault('new_value', 'N/A')
            
            # Format values for better display
            if enhanced_change['old_value'] and len(str(enhanced_change['old_value'])) > 100:
                enhanced_change['old_value'] = str(enhanced_change['old_value'])[:97] + "..."
            
            if enhanced_change['new_value'] and len(str(enhanced_change['new_value'])) > 100:
                enhanced_change['new_value'] = str(enhanced_change['new_value'])[:97] + "..."
            
            # Add severity level
            if enhanced_change['is_breaking']:
                enhanced_change['severity'] = 'BREAKING'
            elif enhanced_change['change_type'] in ['endpoint_removed', 'parameter_removed']:
                enhanced_change['severity'] = 'HIGH'
            elif enhanced_change['change_type'] in ['endpoint_added', 'parameter_added']:
                enhanced_change['severity'] = 'LOW'
            else:
                enhanced_change['severity'] = 'MEDIUM'
            
            enhanced_changes.append(enhanced_change)
        
        return enhanced_changes
    
    def _create_reports(self):
        """Create all required reports using the report generator."""
        print("\n📄 Creating true zero-insertion reports...")
        
        # Console report
        self.report_generator.print_console_report(self.report)
        
        # JSON report for Jenkins
        self.report_generator.create_json_report(self.report)
        
        # Jenkins-specific artifacts
        self.report_generator.create_jenkins_artifacts(self.report)
        
        # Create endpoint showcase file
        self.endpoint_stats.create_jenkins_endpoint_showcase_file(self.report)
    
    def _cleanup(self):
        """Cleanup resources."""
        try:
            if hasattr(self, 'querier') and self.querier.conn:
                self.querier.conn.close()
            if self.detector and hasattr(self.detector, 'conn') and self.detector.conn:
                self.detector.conn.close()
            if self.parser and hasattr(self.parser, 'conn') and self.parser.conn:
                self.parser.conn.close()
        except Exception:
            pass
