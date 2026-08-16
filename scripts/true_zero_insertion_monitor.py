#!/usr/bin/env python3
"""
True Zero-Insertion Nightly Schema Monitor for Jenkins

This version NEVER touches the database until changes are confirmed:
1. Fetches fresh schema and calculates hash
2. Compares hash with existing version hash in database
3. If hashes match: ZERO database operations
4. If hashes differ: ONLY THEN parse and insert new version
5. Completely avoids any database writes when no changes exist
"""
import sys
import os
import json
import requests
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.openapi_parser import PostgreSQLOpenAPIParser
from core.openapi_querier import OpenAPIQuerier
from core.schema_change_detector import SchemaChangeDetector
from core.notification_manager import NotificationManager


class TrueZeroInsertionMonitor:
    """Monitor that performs ZERO database operations until changes are confirmed."""
    
    def __init__(self):
        """Initialize the monitor with database connections."""
        self.conn_str = config.get_connection_string()
        self.querier = OpenAPIQuerier(self.conn_str)
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
            self._collect_endpoint_statistics()
            
            # Step 4: Always send Slack notifications (for both changes and no-changes)
            self._send_slack_notifications()
            
            # Step 5: Generate recommendations
            self._generate_recommendations()
            
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
        name_mapping = {
            'OPENAPI_SPEC_PRIMARY': 'Primary API',
            'OPENAPI_SPEC_SECONDARY': 'Secondary API'
        }
        
        expected_title = name_mapping.get(endpoint_name, endpoint_name)
        
        with self.querier.conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, title, version, release_tag, created_at, schema_hash
                FROM apis 
                WHERE title = %s 
                ORDER BY created_at DESC
            """, (expected_title,))
            
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'title': row[1],
                    'version': row[2],
                    'release_tag': row[3],
                    'created_at': row[4],
                    'schema_hash': row[5]
                }
                for row in rows
            ]
    
    def _fetch_schema_only(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch schema from URL with ZERO database operations."""
        try:
            headers = {}
            if hasattr(config, 'AUTHORIZATION_TOKEN') and config.AUTHORIZATION_TOKEN:
                headers['Authorization'] = f'Bearer {config.AUTHORIZATION_TOKEN}'
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            schema = response.json()
            print(f"   ✅ Schema fetched successfully ({len(str(schema))} characters)")
            return schema
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Failed to fetch schema: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"   ❌ Failed to parse JSON schema: {str(e)}")
            return None
    
    def _calculate_schema_hash(self, schema: Dict[str, Any]) -> str:
        """Calculate hash of schema for comparison (ZERO database operations)."""
        # Use the same hash calculation method as the parser
        schema_str = json.dumps(schema, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(schema_str.encode('utf-8')).hexdigest()
    
    def _ensure_parser_initialized(self):
        """Initialize parser only when database operations are required."""
        if self.parser is None:
            print("   🔧 Initializing parser for database operations...")
            self.parser = PostgreSQLOpenAPIParser(self.conn_str)
    
    def _ensure_detector_initialized(self):
        """Initialize detector only when change analysis is required."""
        if self.detector is None:
            print("   🔧 Initializing detector for change analysis...")
            self.detector = SchemaChangeDetector(self.conn_str)
    
    def _process_change_results(self, changes: Dict[str, Any], endpoint_name: str, 
                               previous_version: Dict, fresh_api_id: str):
        """Process and record change detection results."""
        summary = changes['summary']
        
        print("   📊 Change Analysis Results:")
        print(f"      Total Changes: {summary['total_changes']}")
        print(f"      Breaking Changes: {summary['breaking_changes']}")
        print(f"      Endpoint Changes: {summary['endpoint_changes']}")
        print(f"      Parameter Changes: {summary['parameter_changes']}")
        print(f"      Response Changes: {summary['response_changes']}")
        print(f"      Component Changes: {summary['component_changes']}")
        
        # Organize detailed changes by category for enhanced Slack notifications
        change_analysis = {
            'endpoint_changes': [],
            'parameter_changes': [],
            'response_changes': [],
            'component_changes': []
        }
        
        if changes['detailed_changes']:
            for change in changes['detailed_changes']:
                change_type = change.get('change_type', '')
                
                # Categorize changes based on type
                if change_type.startswith('endpoint_'):
                    change_analysis['endpoint_changes'].append(change)
                elif change_type.startswith('parameter_'):
                    change_analysis['parameter_changes'].append(change)
                elif change_type.startswith('response_'):
                    change_analysis['response_changes'].append(change)
                elif change_type.startswith('component_'):
                    change_analysis['component_changes'].append(change)
        
        # Create API result record with enhanced change analysis
        api_result = {
            'endpoint_name': endpoint_name,
            'api_title': previous_version['title'],
            'previous_version': previous_version['version'],
            'previous_api_id': previous_version['id'],
            'new_api_id': fresh_api_id,
            'changes_detected': summary['total_changes'] > 0,
            'total_changes': summary['total_changes'],
            'breaking_changes': summary['breaking_changes'],
            'change_summary': summary,
            'change_analysis': change_analysis,  # Enhanced categorized changes
            'sample_changes': [],  # Keep for backward compatibility
            'requires_notification': summary['breaking_changes'] > 0 or summary['total_changes'] > 10,
            'database_operations_performed': True
        }
        
        # Add sample changes for backward compatibility and console display
        if changes['detailed_changes']:
            breaking_changes = [c for c in changes['detailed_changes'] if c.get('is_breaking', False)]
            non_breaking_changes = [c for c in changes['detailed_changes'] if not c.get('is_breaking', False)]
            
            # Prioritize breaking changes
            sample_changes = breaking_changes[:5] + non_breaking_changes[:5]
            api_result['sample_changes'] = sample_changes
            
            # Show sample changes in console with enhanced categorization
            if summary['breaking_changes'] > 0:
                print("   🚨 Sample Breaking Changes:")
                for i, change in enumerate(breaking_changes[:3]):
                    change_type = change.get('change_type', 'unknown')
                    path = change.get('path', change.get('endpoint_path', 'N/A'))
                    method = change.get('method', 'N/A')
                    description = change.get('description', 'No description')
                    print(f"      {i+1}. {change_type}: {method} {path}")
                    print(f"         {description}")
            
            if summary['total_changes'] > summary['breaking_changes']:
                print("   ℹ️  Sample Non-Breaking Changes:")
                for i, change in enumerate(non_breaking_changes[:2]):
                    change_type = change.get('change_type', 'unknown')
                    path = change.get('path', change.get('endpoint_path', 'N/A'))
                    method = change.get('method', 'N/A')
                    description = change.get('description', 'No description')
                    print(f"      {i+1}. {change_type}: {method} {path}")
                    print(f"         {description}")
        
        # Update global report totals
        self.report['apis_with_changes'] += 1
        self.report['total_changes'] += summary['total_changes']
        self.report['breaking_changes'] += summary['breaking_changes']
        self.report['apis_processed'].append(api_result)
        
        print("   💾 Changes recorded for reporting and notifications")
    
    def _send_slack_notifications(self):
        """Send Slack notifications for detected changes using enhanced NotificationManager."""
        print("\n📱 Sending Slack Notifications...")
        
        try:
            # Use the enhanced NotificationManager for detailed notifications
            notification_manager = NotificationManager()
            success = notification_manager.send_slack_notification(self.report)
            
            if success:
                self.report['slack_notifications_sent'] = 1
            
        except Exception as e:
            print(f"   ❌ Error sending Slack notification: {str(e)}")
    
    def _create_slack_message(self) -> Dict[str, Any]:
        """Create Slack message for schema changes."""
        total_changes = self.report['total_changes']
        breaking_changes = self.report['breaking_changes']
        apis_with_changes = self.report['apis_with_changes']
        apis_unchanged = self.report['apis_unchanged']
        db_ops_avoided = self.report['database_operations_avoided']
        total_apis = self.report['total_apis_monitored']
        
        # Determine severity and emoji based on changes
        if breaking_changes > 0:
            severity = "🚨 CRITICAL"
            color = "danger"
            status_text = f"Breaking Changes Detected in {apis_with_changes} APIs"
        elif total_changes > 0:
            severity = "⚠️ WARNING"
            color = "warning"
            status_text = f"Changes Detected in {apis_with_changes} APIs"
        else:
            severity = "✅ SUCCESS"
            color = "good"
            status_text = f"No Changes - All {total_apis} API Schemas Unchanged"
        
        # Create API status details
        api_details = []
        
        # Add changed APIs
        for api_info in self.report.get('apis_processed', []):
            api_details.append(f"🔄 {api_info['endpoint_name']}: {api_info['total_changes']} changes ({api_info['breaking_changes']} breaking)")
        
        # Add unchanged APIs
        for api_info in self.report.get('unchanged_apis', []):
            api_details.append(f"✅ {api_info['endpoint_name']}: No changes (hash identical)")
        
        # Add endpoint statistics for showcase
        endpoint_stats = []
        for api_detail in self.report.get('api_endpoint_details', []):
            endpoint_stats.append(f"📍 {api_detail['api_title']}: {api_detail['endpoint_count']} endpoints")
        
        if endpoint_stats:
            endpoint_stats.append(f"🔢 **Total Endpoints Monitored: {self.report.get('total_endpoints_monitored', 0)}**")
            endpoint_showcase = "\n".join(endpoint_stats)
        else:
            endpoint_showcase = "Endpoint statistics not available"
        
        api_status = "\n".join(api_details) if api_details else "No API details available"
        
        # Create message
        message = {
            "text": f"{severity}: {status_text}",
            "attachments": [
                {
                    "color": color,
                    "title": "🔒 True Zero-Insertion Schema Monitoring Report",
                    "fields": [
                        {
                            "title": "📊 Summary",
                            "value": f"• Total APIs Monitored: {total_apis}\n• APIs with Changes: {apis_with_changes}\n• APIs Unchanged: {apis_unchanged}\n• Total Changes: {total_changes}\n• Breaking Changes: {breaking_changes}",
                            "short": True
                        },
                        {
                            "title": "🔒 Efficiency Metrics",
                            "value": f"• DB Operations Avoided: {db_ops_avoided}\n• Hash Comparisons: {self.report['hash_comparisons_performed']}\n• Zero-Insertion Strategy: {'✅ Working' if db_ops_avoided > 0 else '⚠️ All APIs Changed'}",
                            "short": True
                        },
                        {
                            "title": "📋 API Status Details",
                            "value": api_status,
                            "short": False
                        },
                        {
                            "title": "📍 Endpoint Coverage Showcase",
                            "value": endpoint_showcase,
                            "short": False
                        },
                        {
                            "title": "📅 Monitoring Info",
                            "value": f"• Timestamp: {self.report['timestamp']}\n• Database: {config.HOST}:{config.PORT}/{config.DB_NAME}\n• Strategy: True Zero-Insertion (no DB ops until changes confirmed)",
                            "short": False
                        }
                    ]
                }
            ]
        }
        
        return message
    
    def _generate_recommendations(self):
        """Generate recommendations based on findings."""
        if self.report['breaking_changes'] > 0:
            self.report['recommendations'].append({
                'priority': 'CRITICAL',
                'message': f"{self.report['breaking_changes']} breaking changes detected across APIs",
                'action': 'Review breaking changes immediately and plan migration strategy'
            })
        
        if self.report['total_changes'] > 100:
            self.report['recommendations'].append({
                'priority': 'HIGH',
                'message': f"High volume of changes detected ({self.report['total_changes']} total)",
                'action': 'Review change patterns and consider API versioning strategy'
            })
        
        if self.report['database_operations_avoided'] > 0:
            self.report['recommendations'].append({
                'priority': 'INFO',
                'message': f"Efficient monitoring: {self.report['database_operations_avoided']} unnecessary database operations avoided",
                'action': 'True zero-insertion strategy working correctly - no action required'
            })
        
        if self.report['apis_unchanged'] > 0:
            self.report['recommendations'].append({
                'priority': 'INFO',
                'message': f"{self.report['apis_unchanged']} APIs had no changes (hash comparison only)",
                'action': 'No action required - monitoring working efficiently'
            })
        
        if len(self.report['errors']) > 0:
            self.report['recommendations'].append({
                'priority': 'MEDIUM',
                'message': f"{len(self.report['errors'])} errors occurred during monitoring",
                'action': 'Check API endpoint accessibility and network connectivity'
            })
    
    def _create_reports(self):
        """Create all required reports."""
        print("\n📄 Creating true zero-insertion reports...")
        
        # Console report
        self._print_console_report()
        
        # JSON report for Jenkins
        self._create_json_report()
        
        # Jenkins-specific artifacts
        self._create_jenkins_artifacts()
    
    def _print_console_report(self):
        """Print detailed console report."""
        print("\n" + "=" * 60)
        print("🔒 TRUE ZERO-INSERTION NIGHTLY SCHEMA MONITORING REPORT")
        print("=" * 60)
        print(f"📅 Timestamp: {self.report['timestamp']}")
        print(f"🔗 Database: {config.HOST}:{config.PORT}/{config.DB_NAME}")
        print(f"📋 APIs Monitored: {self.report['total_apis_monitored']}")
        print(f"🔄 APIs with Changes: {self.report['apis_with_changes']}")
        print(f"✅ APIs Unchanged: {self.report['apis_unchanged']}")
        print(f"📈 Total Changes: {self.report['total_changes']}")
        print(f"⚠️  Breaking Changes: {self.report['breaking_changes']}")
        print(f"🔒 Database Operations Avoided: {self.report['database_operations_avoided']}")
        print(f"🔍 Hash Comparisons Performed: {self.report['hash_comparisons_performed']}")
        print(f"📱 Slack Notifications: {self.report['slack_notifications_sent']}")
        print(f"❌ Errors: {len(self.report['errors'])}")
        
        # Endpoint Coverage Showcase
        if self.report.get('api_endpoint_details'):
            print("\n📍 ENDPOINT COVERAGE SHOWCASE:")
            for api_detail in self.report['api_endpoint_details']:
                print(f"   📊 {api_detail['api_title']}: {api_detail['endpoint_count']} endpoints")
                print(f"      ID: {api_detail['api_id'][:8]}...")
            print(f"   🔢 TOTAL ENDPOINTS ACROSS ALL APIs: {self.report.get('total_endpoints_monitored', 0)}")
        
        # Changed APIs Details
        if self.report['apis_processed']:
            print("\n🔄 APIS WITH CHANGES (Database Operations Performed):")
            for api in self.report['apis_processed']:
                print(f"\n   🚨 {api['api_title']} ({api['endpoint_name']})")
                print(f"      Previous Version: {api['previous_version']}")
                print(f"      Changes: {api['total_changes']} (Breaking: {api['breaking_changes']})")
                print(f"      Database Operations: {'Yes' if api['database_operations_performed'] else 'No'}")
                print(f"      Notification Required: {'Yes' if api['requires_notification'] else 'No'}")
                
                if api['sample_changes']:
                    print("      Sample Changes:")
                    for change in api['sample_changes'][:3]:
                        status = "🔴" if change.get('is_breaking') else "🟢"
                        print(f"         {status} {change['change_type']}: {change['description']}")
        
        # Unchanged APIs
        if self.report['unchanged_apis']:
            print("\n✅ UNCHANGED APIS (Zero Database Operations):")
            for api in self.report['unchanged_apis']:
                status_msg = {
                    'no_changes_hash_identical': 'Hash identical - zero database operations',
                    'first_version_created': 'First version created (required)'
                }.get(api['status'], api['status'])
                
                efficiency_msg = ""
                if api.get('database_operations_avoided'):
                    efficiency_msg = " 🔒"
                
                print(f"   - {api['endpoint_name']}: {status_msg}{efficiency_msg}")
        
        # Efficiency Summary
        print("\n🔒 EFFICIENCY SUMMARY:")
        print(f"   Database Operations Avoided: {self.report['database_operations_avoided']}")
        print(f"   Hash Comparisons Performed: {self.report['hash_comparisons_performed']}")
        print("   Only performed database operations when changes confirmed")
        print("   Zero unnecessary parsing, insertion, or processing")
        
        # Recommendations
        if self.report['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in self.report['recommendations']:
                priority_icon = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "ℹ️", "INFO": "✅"}.get(rec['priority'], "📋")
                print(f"   {priority_icon} {rec['priority']}: {rec['message']}")
                print(f"      Action: {rec['action']}")
        
        # Errors
        if self.report['errors']:
            print("\n❌ ERRORS:")
            for error in self.report['errors']:
                print(f"   - {error}")
    
    def _create_json_report(self):
        """Create JSON report for Jenkins consumption."""
        json_file = f"true_zero_insertion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(json_file, 'w') as f:
            json.dump(self.report, f, indent=2, default=str)
        
        print(f"📄 JSON report saved: {json_file}")
    
    def _create_jenkins_artifacts(self):
        """Create Jenkins-specific artifacts."""
        # Exit code: 0 for no changes, 1 for changes detected
        exit_code = 1 if self.report['breaking_changes'] > 0 else 0
        with open('jenkins_exit_code.txt', 'w') as f:
            f.write(str(exit_code))
        
        # Build summary with efficiency metrics and endpoint showcase
        summary = f"APIs: {self.report['total_apis_monitored']}, Endpoints: {self.report.get('total_endpoints_monitored', 0)}, Changed: {self.report['apis_with_changes']}, Unchanged: {self.report['apis_unchanged']}, Changes: {self.report['total_changes']}, Breaking: {self.report['breaking_changes']}, DB Ops Avoided: {self.report['database_operations_avoided']}"
        with open('jenkins_build_summary.txt', 'w') as f:
            f.write(summary)
        
        # Create detailed endpoint showcase file for Jenkins
        with open('jenkins_endpoint_showcase.txt', 'w') as f:
            f.write("ENDPOINT COVERAGE SHOWCASE\n")
            f.write("=" * 30 + "\n")
            for api_detail in self.report.get('api_endpoint_details', []):
                f.write(f"API: {api_detail['api_title']}\n")
                f.write(f"   ID: {api_detail['api_id']}\n")
                f.write(f"   Total Endpoints: {api_detail['endpoint_count']}\n\n")
            f.write(f"TOTAL ENDPOINTS ACROSS ALL APIs: {self.report.get('total_endpoints_monitored', 0)}\n")
        
        print("📄 Jenkins artifacts created:")
        print(f"   - jenkins_exit_code.txt (exit code: {exit_code})")
        print("   - jenkins_build_summary.txt")
        print("   - jenkins_endpoint_showcase.txt")
        print(f"   - Efficiency: {self.report['database_operations_avoided']} database operations avoided")
        print(f"   - Endpoint Coverage: {self.report.get('total_endpoints_monitored', 0)} endpoints monitored")
    
    def _collect_endpoint_statistics(self):
        """Collect endpoint statistics for all monitored APIs."""
        try:
            print("\n📊 Collecting endpoint statistics for showcase...")
            
            # Get all latest APIs
            latest_apis = self.querier.get_latest_apis()
            total_endpoints = 0
            
            for api in latest_apis:
                # Get endpoint count for this API
                endpoints = self.querier.search_endpoints(api_id=api['id'])
                endpoint_count = len(endpoints)
                total_endpoints += endpoint_count
                
                api_detail = {
                    'api_title': api['title'],
                    'api_id': api['id'],
                    'endpoint_count': endpoint_count,
                    'version': api['version']
                }
                
                self.report['api_endpoint_details'].append(api_detail)
                print(f"   📍 {api['title']}: {endpoint_count} endpoints")
            
            self.report['total_endpoints_monitored'] = total_endpoints
            print(f"   🔢 Total endpoints across all APIs: {total_endpoints}")
            
        except Exception as e:
            print(f"   ⚠️  Error collecting endpoint statistics: {str(e)}")
            # Don't fail the entire process for statistics collection
    
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


def main():
    """Main entry point for Jenkins execution."""
    print("🔒 True Zero-Insertion Nightly Schema Monitor v1.0")
    print("ZERO database operations until changes are confirmed")
    
    monitor = TrueZeroInsertionMonitor()
    
    try:
        report = monitor.run_nightly_check()
        
        # Exit with appropriate code for Jenkins
        if report['breaking_changes'] > 0:
            print(f"\n🚨 CRITICAL: {report['breaking_changes']} breaking changes detected!")
            print("Jenkins build should be marked as UNSTABLE")
            sys.exit(1)  # Unstable build
        elif report['apis_with_changes'] > 0:
            print(f"\n⚠️  CHANGES: {report['apis_with_changes']} APIs have changes ({report['total_changes']} total)")
            print("Jenkins build marked as UNSTABLE due to changes")
            sys.exit(1)  # Unstable for any changes
        elif len(report['errors']) > 0:
            print(f"\n⚠️  WARNING: {len(report['errors'])} errors occurred during monitoring")
            print("Jenkins build should be marked as UNSTABLE")
            sys.exit(1)  # Unstable build
        else:
            print(f"\n✅ SUCCESS: No changes detected across {report['total_apis_monitored']} APIs")
            print(f"🔒 Database operations avoided: {report['database_operations_avoided']}")
            print(f"🔍 Hash comparisons performed: {report['hash_comparisons_performed']}")
            print("All APIs unchanged - zero unnecessary database operations")
            sys.exit(0)  # Success
            
    except Exception as e:
        print(f"\n❌ FAILURE: Critical error in nightly monitor: {str(e)}")
        sys.exit(2)  # Failure


if __name__ == "__main__":
    main()
