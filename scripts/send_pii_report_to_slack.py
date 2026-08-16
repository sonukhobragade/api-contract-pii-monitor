#!/usr/bin/env python3
"""
Send PII Report to Slack

Simple integration script that runs fast PII analysis and sends comprehensive reports
to Slack with proper formatting for critical API calls and PII data found in requests,
responses, parameters, and schemas.
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.slack_pii_manager import SlackPIIManager
from scripts.fast_pii_analysis import FastPIIAnalyzer


def send_pii_report_to_slack(api_id: str = None, max_workers: int = 4, save_report: bool = True):
    """
    Run PII analysis and send report to Slack.
    
    Args:
        api_id: Optional specific API ID to analyze
        max_workers: Number of worker threads
        save_report: Whether to save detailed report to file
        
    Returns:
        bool: True if successful, False otherwise
    """
    print("🚀 PII Analysis and Slack Report")
    print("=" * 50)
    
    try:
        # Initialize components
        print("📊 Initializing Fast PII Analyzer...")
        analyzer = FastPIIAnalyzer()
        
        print("📱 Initializing Slack PII Manager...")
        slack_manager = SlackPIIManager()
        
        # Run PII analysis
        if api_id:
            print(f"🔍 Analyzing specific API: {api_id}")
            analysis_results = analyzer.analyze_specific_api_fast(api_id, max_workers)
        else:
            print("🔍 Running comprehensive PII analysis on all APIs...")
            analysis_results = analyzer.analyze_all_apis_fast(max_workers)
        
        if "error" in analysis_results:
            print(f"❌ Analysis failed: {analysis_results['error']}")
            return False
        
        # Generate console summary
        print("\n📋 Analysis Summary:")
        analyzer.generate_fast_summary(analysis_results)
        
        # Send comprehensive report to Slack
        print("\n📤 Sending PII report to Slack...")
        success = slack_manager.send_pii_analysis_report(analysis_results)
        
        if success:
            print("✅ PII report sent successfully to Slack!")
        else:
            print("❌ Failed to send PII report to Slack")
            print("   Make sure SLACK_WEBHOOK_URL is configured in your environment")
        
        # Send critical alert if needed
        overall = analysis_results.get("overall_summary", {})
        breakdown = overall.get("pii_breakdown", {})
        critical_count = breakdown.get("critical", 0)
        
        if critical_count > 0:
            print(f"\n🚨 {critical_count} Critical PII instances detected!")
            print("📤 Sending critical PII alert...")
            
            # Extract critical findings
            critical_findings = []
            detailed_results = analysis_results.get("detailed_results", [])
            
            for result in detailed_results:
                if result.get("critical_pii"):
                    for pii in result["critical_pii"]:
                        critical_findings.append({
                            "endpoint": f"{result['api_title']} - {result['http_method']} {result['endpoint_path']}",
                            "pii_type": pii["pii_type"],
                            "field_name": pii["field_name"],
                            "context": pii["context"]
                        })
            
            alert_success = slack_manager.send_critical_pii_alert(critical_findings)
            
            if alert_success:
                print("✅ Critical PII alert sent successfully!")
            else:
                print("❌ Failed to send critical PII alert")
        
        # Save detailed report if requested
        if save_report:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            api_suffix = f"_{api_id[:8]}" if api_id else ""
            report_filename = f"pii_slack_report{api_suffix}_{timestamp}.json"
            
            try:
                with open(report_filename, 'w') as f:
                    json.dump(analysis_results, f, indent=2, default=str)
                print(f"📄 Detailed report saved to: {report_filename}")
            except Exception as e:
                print(f"❌ Error saving report: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Process failed: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Run PII analysis and send report to Slack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all APIs and send report to Slack
  python scripts/send_pii_report_to_slack.py
  
  # Analyze specific API and send report to Slack
  python scripts/send_pii_report_to_slack.py --api-id your-api-id
  
  # Use more worker threads for faster processing
  python scripts/send_pii_report_to_slack.py --workers 8
  
  # Don't save detailed report to file
  python scripts/send_pii_report_to_slack.py --no-save
        """
    )
    
    parser.add_argument(
        "--api-id",
        help="Analyze specific API by ID (optional)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of worker threads (default: 4)"
    )
    
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save detailed report to file"
    )
    
    args = parser.parse_args()
    
    success = send_pii_report_to_slack(
        api_id=args.api_id,
        max_workers=args.workers,
        save_report=not args.no_save
    )
    
    if success:
        print("\n🎉 PII analysis and Slack reporting completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Process failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
