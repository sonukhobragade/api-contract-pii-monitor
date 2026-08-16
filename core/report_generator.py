"""
Report Generator Module

Handles generation of console, JSON, and Jenkins reports for schema monitoring.
"""
import json
from datetime import datetime
from typing import Dict, Any
from core.config import config


class ReportGenerator:
    """Generates various types of reports for schema monitoring."""
    
    def __init__(self):
        """Initialize the report generator."""
        pass
    
    def print_console_report(self, report: Dict[str, Any]):
        """
        Print detailed console report.
        
        Args:
            report (Dict[str, Any]): Monitoring report data
        """
        print("\n" + "=" * 60)
        print("🔒 TRUE ZERO-INSERTION NIGHTLY SCHEMA MONITORING REPORT")
        print("=" * 60)
        print(f"📅 Timestamp: {report['timestamp']}")
        print(f"🔗 Database: {config.HOST}:{config.PORT}/{config.DB_NAME}")
        print(f"📋 APIs Monitored: {report['total_apis_monitored']}")
        print(f"🔄 APIs with Changes: {report['apis_with_changes']}")
        print(f"✅ APIs Unchanged: {report['apis_unchanged']}")
        print(f"📈 Total Changes: {report['total_changes']}")
        print(f"⚠️  Breaking Changes: {report['breaking_changes']}")
        print(f"🔒 Database Operations Avoided: {report['database_operations_avoided']}")
        print(f"🔍 Hash Comparisons Performed: {report['hash_comparisons_performed']}")
        print(f"📱 Slack Notifications: {report['slack_notifications_sent']}")
        print(f"❌ Errors: {len(report['errors'])}")
        
        # Endpoint Coverage Showcase
        if report.get('api_endpoint_details'):
            print("\n📍 ENDPOINT COVERAGE SHOWCASE:")
            for api_detail in report['api_endpoint_details']:
                print(f"   📊 {api_detail['api_title']}: {api_detail['endpoint_count']} endpoints")
                print(f"      ID: {api_detail['api_id'][:8]}...")
            print(f"   🔢 TOTAL ENDPOINTS ACROSS ALL APIs: {report.get('total_endpoints_monitored', 0)}")
        
        # Changed APIs Details
        if report['apis_processed']:
            print("\n🔄 APIS WITH CHANGES:")
            for api in report['apis_processed']:
                print(f"   - {api['endpoint_name']}: {api['total_changes']} changes ({api['breaking_changes']} breaking)")
                print(f"     API Title: {api.get('api_title', 'Unknown')}")
                print(f"     Previous Version: {api.get('previous_version', 'N/A')}")
                print(f"     New Version ID: {api.get('fresh_api_id', 'N/A')}")
                
                if api.get('sample_changes'):
                    print("     🔍 Detailed Changes (showing first 5):")
                    for i, change in enumerate(api['sample_changes'][:5], 1):
                        status = "🔴" if change.get('is_breaking') else "🟢"
                        endpoint_path = change.get('endpoint_path', 'N/A')
                        change_type = change.get('change_type', 'unknown')
                        description = change.get('description', 'No description')
                        
                        print(f"        {i}. {status} {change_type} - {endpoint_path}")
                        print(f"           {description}")
                        
                        # Show old/new values if available
                        old_value = change.get('old_value')
                        new_value = change.get('new_value')
                        if old_value and old_value != 'N/A':
                            print(f"           Old: {old_value}")
                        if new_value and new_value != 'N/A':
                            print(f"           New: {new_value}")
                    
                    if len(api['sample_changes']) > 5:
                        remaining = len(api['sample_changes']) - 5
                        print(f"        ... and {remaining} more changes (see Jenkins detailed report)")
                print("")
        
        # Unchanged APIs
        if report['unchanged_apis']:
            print("\n✅ UNCHANGED APIS (Zero Database Operations):")
            for api in report['unchanged_apis']:
                status_msg = {
                    'no_changes_hash_identical': 'Hash identical - zero database operations',
                    'first_version_created': 'First version created (required)',
                    'no_changes_optimized_detection': 'Optimized detection - zero database operations'
                }.get(api['status'], api['status'])
                
                efficiency_msg = ""
                if api.get('database_operations_avoided'):
                    efficiency_msg = " 🔒"
                
                print(f"   - {api['endpoint_name']}: {status_msg}{efficiency_msg}")
        
        # Efficiency Summary
        print("\n🔒 EFFICIENCY SUMMARY:")
        print(f"   Database Operations Avoided: {report['database_operations_avoided']}")
        print(f"   Hash Comparisons Performed: {report['hash_comparisons_performed']}")
        print("   Only performed database operations when changes confirmed")
        print("   Zero unnecessary parsing, insertion, or processing")
        
        # Recommendations
        if report['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in report['recommendations']:
                priority_icon = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "ℹ️", "INFO": "✅"}.get(rec['priority'], "📋")
                print(f"   {priority_icon} {rec['priority']}: {rec['message']}")
                print(f"      Action: {rec['action']}")
        
        # Errors
        if report['errors']:
            print("\n❌ ERRORS:")
            for error in report['errors']:
                print(f"   - {error}")
    
    def create_json_report(self, report: Dict[str, Any]) -> str:
        """
        Create JSON report for Jenkins consumption.
        
        Args:
            report (Dict[str, Any]): Monitoring report data
            
        Returns:
            str: Filename of created JSON report
        """
        json_file = f"true_zero_insertion_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 JSON report saved: {json_file}")
        return json_file
    
    def create_jenkins_artifacts(self, report: Dict[str, Any]):
        """
        Create Jenkins-specific artifacts.
        
        Args:
            report (Dict[str, Any]): Monitoring report data
        """
        # Exit code: 0 for no changes, 1 for changes detected
        exit_code = 1 if report['breaking_changes'] > 0 else 0
        with open('jenkins_exit_code.txt', 'w') as f:
            f.write(str(exit_code))
        
        # Build summary with efficiency metrics and endpoint showcase
        summary = f"APIs: {report['total_apis_monitored']}, Endpoints: {report.get('total_endpoints_monitored', 0)}, Changed: {report['apis_with_changes']}, Unchanged: {report['apis_unchanged']}, Changes: {report['total_changes']}, Breaking: {report['breaking_changes']}, DB Ops Avoided: {report['database_operations_avoided']}"
        with open('jenkins_build_summary.txt', 'w') as f:
            f.write(summary)
        
        # Create detailed changes report if changes detected
        if report.get('total_changes', 0) > 0:
            self._create_jenkins_detailed_changes_report(report)
        
        print("📄 Jenkins artifacts created:")
        print(f"   - jenkins_exit_code.txt (exit code: {exit_code})")
        print("   - jenkins_build_summary.txt")
        print("   - jenkins_endpoint_showcase.txt")
        if report.get('total_changes', 0) > 0:
            print("   - jenkins_detailed_changes.txt")
        print(f"   - Efficiency: {report['database_operations_avoided']} database operations avoided")
        print(f"   - Endpoint Coverage: {report.get('total_endpoints_monitored', 0)} endpoints monitored")
    
    def generate_recommendations(self, report: Dict[str, Any]) -> list:
        """
        Generate recommendations based on monitoring findings.
        
        Args:
            report (Dict[str, Any]): Monitoring report data
            
        Returns:
            list: List of recommendations
        """
        recommendations = []
        
        if report['breaking_changes'] > 0:
            recommendations.append({
                'priority': 'CRITICAL',
                'message': f"{report['breaking_changes']} breaking changes detected across APIs",
                'action': 'Review breaking changes immediately and plan migration strategy'
            })
        
        if report['total_changes'] > 100:
            recommendations.append({
                'priority': 'HIGH',
                'message': f"High volume of changes detected ({report['total_changes']} total)",
                'action': 'Review change patterns and consider API versioning strategy'
            })
        
        if report['database_operations_avoided'] > 0:
            recommendations.append({
                'priority': 'INFO',
                'message': f"Efficient monitoring: {report['database_operations_avoided']} unnecessary database operations avoided",
                'action': 'True zero-insertion strategy working correctly - no action required'
            })
        
        if report['apis_unchanged'] > 0:
            recommendations.append({
                'priority': 'INFO',
                'message': f"{report['apis_unchanged']} APIs had no changes (hash comparison only)",
                'action': 'No action required - monitoring working efficiently'
            })
        
        if len(report['errors']) > 0:
            recommendations.append({
                'priority': 'MEDIUM',
                'message': f"{len(report['errors'])} errors occurred during monitoring",
                'action': 'Check API endpoint accessibility and network connectivity'
            })
        
        return recommendations
    
    def _create_jenkins_detailed_changes_report(self, report: Dict[str, Any]):
        """
        Create detailed changes report for Jenkins.
        
        Args:
            report (Dict[str, Any]): Monitoring report data
        """
        with open('jenkins_detailed_changes.txt', 'w') as f:
            f.write("TRUE ZERO-INSERTION SCHEMA MONITOR - DETAILED CHANGES REPORT\n")
            f.write("=" * 70 + "\n")
            f.write(f"Timestamp: {report.get('timestamp', 'Unknown')}\n")
            f.write(f"Total APIs Monitored: {report.get('total_apis_monitored', 0)}\n")
            f.write(f"APIs with Changes: {report.get('apis_with_changes', 0)}\n")
            f.write(f"Total Changes: {report.get('total_changes', 0)}\n")
            f.write(f"Breaking Changes: {report.get('breaking_changes', 0)}\n")
            f.write("\n")
            
            # Process each API with changes
            for api_info in report.get('apis_processed', []):
                endpoint_name = api_info.get('endpoint_name', 'Unknown API')
                api_title = api_info.get('api_title', endpoint_name)
                total_changes = api_info.get('total_changes', 0)
                breaking_changes = api_info.get('breaking_changes', 0)
                
                f.write(f"API: {api_title} ({endpoint_name})\n")
                f.write("-" * 50 + "\n")
                f.write(f"Total Changes: {total_changes}\n")
                f.write(f"Breaking Changes: {breaking_changes}\n")
                f.write(f"Previous Version ID: {api_info.get('previous_version', 'N/A')}\n")
                f.write(f"New Version ID: {api_info.get('fresh_api_id', 'N/A')}\n")
                f.write("\n")
                
                # Detailed changes
                sample_changes = api_info.get('sample_changes', [])
                if sample_changes:
                    f.write("DETAILED CHANGES:\n")
                    for i, change in enumerate(sample_changes, 1):
                        change_type = change.get('change_type', 'unknown')
                        endpoint_path = change.get('endpoint_path', 'N/A')
                        description = change.get('description', 'No description')
                        is_breaking = change.get('is_breaking', False)
                        old_value = change.get('old_value', 'N/A')
                        new_value = change.get('new_value', 'N/A')
                        
                        breaking_indicator = "[BREAKING]" if is_breaking else "[NON-BREAKING]"
                        f.write(f"\n{i}. {breaking_indicator} {change_type}\n")
                        f.write(f"   Endpoint: {endpoint_path}\n")
                        f.write(f"   Description: {description}\n")
                        if old_value != 'N/A':
                            f.write(f"   Old Value: {old_value}\n")
                        if new_value != 'N/A':
                            f.write(f"   New Value: {new_value}\n")
                    
                    if len(sample_changes) > 10:
                        remaining = len(sample_changes) - 10
                        f.write(f"\n... and {remaining} more changes (see full report for details)\n")
                else:
                    f.write("No detailed change information available\n")
                
                f.write("\n" + "=" * 70 + "\n\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 20 + "\n")
            f.write("This report shows detailed changes detected by the True Zero-Insertion Schema Monitor.\n")
            f.write("Breaking changes require immediate attention and may affect API consumers.\n")
            f.write("Non-breaking changes are informational and typically safe.\n")
            f.write("\nFor questions, contact the API team or check the monitoring documentation.\n")
