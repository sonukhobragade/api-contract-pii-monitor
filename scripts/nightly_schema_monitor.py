#!/usr/bin/env python3
"""
Nightly Schema Monitor Entry Point

Lightweight entry point for the True Zero-Insertion Schema Monitor.
This script orchestrates the modular components to perform nightly schema monitoring.
"""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.schema_monitor import TrueZeroInsertionSchemaMonitor  # noqa: E402  (needs the sys.path insert above)


def main():
    """Main entry point for nightly schema monitoring."""
    print("🚀 Nightly Schema Monitor")
    print("=" * 60)
    print("📦 Using modular architecture:")
    print("   - core/schema_monitor.py - Main orchestration")
    print("   - core/endpoint_statistics.py - Endpoint statistics")
    print("   - core/notification_manager.py - Slack notifications")
    print("   - core/report_generator.py - Report generation")
    print("=" * 60)
    
    try:
        # Initialize and run the monitor
        monitor = TrueZeroInsertionSchemaMonitor()
        report = monitor.run_nightly_check()
        
        # Determine exit code based on results
        exit_code = determine_exit_code(report)
        
        print(f"\n🏁 Monitoring completed with exit code: {exit_code}")
        print_exit_code_explanation(exit_code)
        
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"💥 Critical error in nightly schema monitor: {str(e)}")
        print("🔧 This indicates a system-level issue that needs investigation")
        sys.exit(2)  # System error


def determine_exit_code(report: dict) -> int:
    """
    Determine appropriate exit code for Jenkins integration.
    
    Args:
        report (dict): Complete monitoring report
        
    Returns:
        int: Exit code (0=success/no changes, 1=changes detected, 2=errors)
    """
    # Check for critical errors first
    if report.get('errors'):
        return 2  # System/processing errors
    
    # Check for schema changes
    if report.get('apis_with_changes', 0) > 0:
        return 1  # Changes detected
    
    # Check for breaking changes specifically
    if report.get('breaking_changes', 0) > 0:
        return 1  # Breaking changes detected
    
    # All good - no changes detected
    return 0  # Success, no changes


def print_exit_code_explanation(exit_code: int):
    """Print explanation of exit code for Jenkins logs."""
    explanations = {
        0: "✅ SUCCESS: No schema changes detected - all APIs unchanged",
        1: "🔄 CHANGES: Schema changes detected - review required",
        2: "❌ ERROR: System errors occurred - investigation needed"
    }
    
    explanation = explanations.get(exit_code, "❓ UNKNOWN: Unexpected exit code")
    print(f"📋 Exit Code Meaning: {explanation}")
    
    if exit_code == 0:
        print("   💡 This is the expected result for stable APIs")
        print("   🔒 Zero database operations were performed")
    elif exit_code == 1:
        print("   📧 Slack notifications have been sent")
        print("   📄 Review Jenkins artifacts for change details")
    elif exit_code == 2:
        print("   🚨 Check logs for error details")
        print("   🔧 System maintenance may be required")


if __name__ == "__main__":
    main()
