#!/usr/bin/env python3
"""
Slack PII Report Demo

Demonstrates how to use the SlackPIIManager to send comprehensive PII analysis reports
to Slack with proper formatting for critical API calls and PII data found in requests,
responses, parameters, and schemas.
"""

import sys
import os
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.slack_pii_manager import SlackPIIManager
from scripts.fast_pii_analysis import FastPIIAnalyzer


def run_slack_pii_demo():
    """Run the Slack PII report demo."""
    print("🚀 Slack PII Report Demo")
    print("=" * 50)
    
    try:
        # Initialize the PII analyzer
        print("📊 Initializing Fast PII Analyzer...")
        analyzer = FastPIIAnalyzer()
        
        # Initialize the Slack PII manager
        print("📱 Initializing Slack PII Manager...")
        slack_manager = SlackPIIManager()
        
        # Run PII analysis on all APIs
        print("\n🔍 Running comprehensive PII analysis...")
        analysis_results = analyzer.analyze_all_apis_fast(max_workers=4)
        
        if "error" in analysis_results:
            print(f"❌ Analysis failed: {analysis_results['error']}")
            return False
        
        # Generate console summary
        print("\n📋 Generating analysis summary...")
        analyzer.generate_fast_summary(analysis_results)
        
        # Send comprehensive report to Slack
        print("\n📤 Sending comprehensive PII report to Slack...")
        success = slack_manager.send_pii_analysis_report(analysis_results)
        
        if success:
            print("✅ Comprehensive PII report sent successfully!")
        else:
            print("❌ Failed to send comprehensive PII report")
        
        # Check for critical PII and send immediate alert if needed
        overall = analysis_results.get("overall_summary", {})
        breakdown = overall.get("pii_breakdown", {})
        critical_count = breakdown.get("critical", 0)
        
        if critical_count > 0:
            print(f"\n🚨 {critical_count} Critical PII instances detected!")
            print("📤 Sending critical PII alert...")
            
            # Extract critical findings for immediate alert
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
        
        # Save detailed report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"slack_pii_report_{timestamp}.json"
        
        try:
            with open(report_filename, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            print(f"📄 Detailed report saved to: {report_filename}")
        except Exception as e:
            print(f"❌ Error saving report: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False


def run_specific_api_demo(api_id: str):
    """Run demo for a specific API."""
    print(f"🚀 Slack PII Report Demo for API: {api_id}")
    print("=" * 60)
    
    try:
        # Initialize components
        analyzer = FastPIIAnalyzer()
        slack_manager = SlackPIIManager()
        
        # Run analysis on specific API
        print(f"🔍 Analyzing API: {api_id}")
        analysis_results = analyzer.analyze_specific_api_fast(api_id, max_workers=4)
        
        if "error" in analysis_results:
            print(f"❌ Analysis failed: {analysis_results['error']}")
            return False
        
        # Generate console summary
        analyzer.generate_fast_summary(analysis_results)
        
        # Send report to Slack
        print("\n📤 Sending API-specific PII report to Slack...")
        success = slack_manager.send_pii_analysis_report(analysis_results)
        
        if success:
            print("✅ API-specific PII report sent successfully!")
        else:
            print("❌ Failed to send API-specific PII report")
        
        return True
        
    except Exception as e:
        print(f"❌ API-specific demo failed: {e}")
        return False


def main():
    """Main function to run the demo."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Slack PII Report Demo")
    parser.add_argument(
        "--api-id",
        help="Analyze specific API by ID (optional)"
    )
    
    args = parser.parse_args()
    
    if args.api_id:
        success = run_specific_api_demo(args.api_id)
    else:
        success = run_slack_pii_demo()
    
    if success:
        print("\n🎉 Demo completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Demo failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
