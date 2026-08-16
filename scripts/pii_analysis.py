#!/usr/bin/env python3
"""
PII Analysis Script for OpenAPI Schemas

This script analyzes stored OpenAPI schemas for PII (Personally Identifiable Information)
across all endpoints, parameters, request bodies, and responses. It generates comprehensive
reports and recommendations for privacy compliance.

Usage:
    python scripts/pii_analysis.py [--api-id API_ID] [--output-format json|console|both]

Author: Contract Testing Framework
Date: 2025-01-20
"""

import sys
import os
import json
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from core.database_setup import DatabaseSetup
from core.openapi_querier import OpenAPIQuerier
from core.pii_detector import PIIDetector, PIIDetectionResult, create_pii_summary_report


class PIIAnalyzer:
    """
    Comprehensive PII analysis system for OpenAPI schemas.
    
    Analyzes all stored APIs and endpoints for PII exposure and generates
    detailed reports with security recommendations.
    """
    
    def __init__(self):
        """Initialize PII analyzer with database connections."""
        self.config = Config()
        self.db_setup = DatabaseSetup(
            host=self.config.HOST,
            port=self.config.PORT,
            username=self.config.USERNAME,
            password=self.config.PASSWORD
        )
        self.querier = OpenAPIQuerier(self.config.get_connection_string())
        self.pii_detector = PIIDetector()
        
        print("🔍 PII Analyzer initialized")
        print(f"📊 Database: {self.config.DB_NAME} on {self.config.HOST}")
    
    def get_all_apis(self) -> List[Dict[str, Any]]:
        """Get all APIs from database."""
        return self.querier.get_latest_apis()
    
    def get_api_by_id(self, api_id: str) -> Optional[Dict[str, Any]]:
        """Get API by ID."""
        apis = self.get_all_apis()
        for api in apis:
            if api['id'] == api_id:
                return api
        return None
    
    def get_endpoints_by_api(self, api_id: str) -> List[Dict[str, Any]]:
        """Get endpoints for an API."""
        return self.querier.search_endpoints(api_id=api_id)
    
    def get_parameters_by_endpoint(self, endpoint_id: str) -> List[Dict[str, Any]]:
        """Get parameters for an endpoint."""
        endpoint_details = self.querier.get_endpoint_details(endpoint_id)
        if endpoint_details and 'parameters' in endpoint_details:
            return endpoint_details['parameters']
        return []
    
    def get_request_body_by_endpoint(self, endpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get request body for an endpoint."""
        endpoint_details = self.querier.get_endpoint_details(endpoint_id)
        if endpoint_details and 'request_bodies' in endpoint_details:
            request_bodies = endpoint_details['request_bodies']
            return request_bodies[0] if request_bodies else None
        return None
    
    def get_responses_by_endpoint(self, endpoint_id: str) -> List[Dict[str, Any]]:
        """Get responses for an endpoint."""
        endpoint_details = self.querier.get_endpoint_details(endpoint_id)
        if endpoint_details and 'responses' in endpoint_details:
            return endpoint_details['responses']
        return []
    
    def analyze_all_apis(self) -> Dict[str, Any]:
        """
        Analyze all APIs in the database for PII.
        
        Returns:
            Complete analysis results
        """
        print("\n🔍 Starting comprehensive PII analysis...")
        
        # Get all APIs
        apis = self.get_all_apis()
        if not apis:
            print(" No APIs found in database")
            return {"error": "No APIs found"}
        
        print(f" Found {len(apis)} APIs to analyze")
        
        all_results = []
        api_summaries = {}
        
        for api_num, api in enumerate(apis, 1):
            api_id = api['id']
            api_title = api['title']
            
            print(f"\n📊 [{api_num}/{len(apis)}] Analyzing API: {api_title} (ID: {api_id[:8]}...)")
            
            # Analyze this API
            api_results = self.analyze_api(api_id, api_title)
            all_results.extend(api_results)
            
            # Create API summary
            api_summaries[api_id] = {
                "title": api_title,
                "endpoints_analyzed": len(api_results),
                "total_pii_found": sum(r.total_pii_found for r in api_results),
                "critical_pii": sum(len(r.critical_pii) for r in api_results),
                "high_pii": sum(len(r.high_pii) for r in api_results),
                "medium_pii": sum(len(r.medium_pii) for r in api_results),
                "low_pii": sum(len(r.low_pii) for r in api_results),
                "avg_compliance_score": sum(r.compliance_score for r in api_results) / len(api_results) if api_results else 100.0
            }
            
            print(f"   ✅ Analyzed {len(api_results)} endpoints")
            print(f"   🔍 Found {api_summaries[api_id]['total_pii_found']} PII instances")
            print(f"   📊 Compliance Score: {api_summaries[api_id]['avg_compliance_score']:.1f}%")
        
        # Create overall summary
        overall_summary = create_pii_summary_report(all_results)
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_summary": overall_summary,
            "api_summaries": api_summaries,
            "detailed_results": [self._serialize_result(r) for r in all_results]
        }
    
    def analyze_api(self, api_id: str, api_title: str) -> List[PIIDetectionResult]:
        """
        Analyze a specific API for PII.
        
        Args:
            api_id: API identifier
            api_title: API title
            
        Returns:
            List of PII detection results for all endpoints
        """
        results = []
        
        # Get all endpoints for this API
        endpoints = self.get_endpoints_by_api(api_id)
        total_endpoints = len(endpoints)
        print(f"    📋 Found {total_endpoints} endpoints to analyze")
        
        for i, endpoint in enumerate(endpoints, 1):
            endpoint_id = endpoint['id']
            endpoint_path = endpoint['path']
            http_method = endpoint['method']
            
            # Progress indicator
            print(f"    🔍 [{i:3d}/{total_endpoints}] Analyzing {http_method:4s} {endpoint_path}")
            
            # Get endpoint details
            parameters = self.get_parameters_by_endpoint(endpoint_id)
            request_body = self.get_request_body_by_endpoint(endpoint_id)
            responses = self.get_responses_by_endpoint(endpoint_id)
            
            # Prepare schemas for analysis
            request_body_schema = None
            if request_body:
                try:
                    request_body_schema = json.loads(
                        request_body.get('schema_definition')
                        or request_body.get('schema') or '{}')
                except (json.JSONDecodeError, TypeError):
                    request_body_schema = None
            
            response_schemas = {}
            for response in responses:
                status_code = response.get('status_code', 'default')
                try:
                    response_schema = json.loads(
                        response.get('schema_definition')
                        or response.get('schema') or '{}')
                    response_schemas[status_code] = response_schema
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Analyze endpoint for PII
            try:
                result = self.pii_detector.analyze_endpoint_pii(
                    api_id=api_id,
                    api_title=api_title,
                    endpoint_path=endpoint_path,
                    http_method=http_method,
                    parameters=parameters or [],
                    request_body_schema=request_body_schema,
                    response_schemas=response_schemas or {}
                )
            except Exception as e:
                print(f"      ⚠️ Error analyzing endpoint {http_method} {endpoint_path}: {e}")
                # Fail closed. A default result carries compliance_score 100 and
                # zero findings, so this branch used to turn any exception into
                # a perfectly clean endpoint.
                from core.pii_detector import PIIDetectionResult
                result = PIIDetectionResult.failed(
                    api_id=api_id,
                    api_title=api_title,
                    endpoint_path=endpoint_path,
                    http_method=http_method,
                    error=str(e),
                )
            
            results.append(result)
        
        return results
    
    def analyze_specific_api(self, api_id: str) -> Dict[str, Any]:
        """
        Analyze a specific API by ID.
        
        Args:
            api_id: API identifier
            
        Returns:
            Analysis results for the specific API
        """
        # Get API details
        api = self.get_api_by_id(api_id)
        if not api:
            return {"error": f"API with ID {api_id} not found"}
        
        api_title = api['title']
        print(f"\n🔍 Analyzing specific API: {api_title}")
        
        # Analyze the API
        results = self.analyze_api(api_id, api_title)
        
        # Create summary
        summary = create_pii_summary_report(results)
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "api_info": {
                "id": api_id,
                "title": api_title,
                "version": api.get('version', 'unknown')
            },
            "summary": summary,
            "detailed_results": [self._serialize_result(r) for r in results]
        }
    
    def _serialize_result(self, result: PIIDetectionResult) -> Dict[str, Any]:
        """
        Serialize PIIDetectionResult to dictionary.
        
        Args:
            result: PII detection result
            
        Returns:
            Serialized result dictionary
        """
        def serialize_match(match):
            return {
                "pii_type": match.pii_type.value,
                "severity": match.severity.value,
                "field_name": match.field_name,
                "field_path": match.field_path,
                "context": match.context,
                "description": match.description,
                "pattern_matched": match.pattern_matched,
                "confidence": match.confidence,
                "recommendations": match.recommendations
            }
        
        return {
            "api_id": result.api_id,
            "api_title": result.api_title,
            "endpoint_path": result.endpoint_path,
            "http_method": result.http_method,
            "total_pii_found": result.total_pii_found,
            "critical_pii": [serialize_match(m) for m in result.critical_pii],
            "high_pii": [serialize_match(m) for m in result.high_pii],
            "medium_pii": [serialize_match(m) for m in result.medium_pii],
            "low_pii": [serialize_match(m) for m in result.low_pii],
            "compliance_score": result.compliance_score,
            "recommendations": result.recommendations
        }
    
    def generate_detailed_pii_breakdown(self, analysis_results: Dict[str, Any]) -> None:
        """
        Generate detailed breakdown of PII by API, endpoint, and context.
        
        Args:
            analysis_results: Analysis results dictionary
        """
        print("\n" + "="*100)
        print("📋 DETAILED PII BREAKDOWN BY API & ENDPOINT")
        print("="*100)
        
        if "error" in analysis_results:
            print(f"❌ Error: {analysis_results['error']}")
            return
        
        detailed_results = analysis_results.get("detailed_results", [])
        
        # Group by API
        api_groups = {}
        for result in detailed_results:
            api_title = result["api_title"]
            if api_title not in api_groups:
                api_groups[api_title] = []
            api_groups[api_title].append(result)
        
        for api_title, api_results in api_groups.items():
            print(f"\n🔷 API: {api_title}")
            print("-" * 80)
            
            # Sort endpoints by PII count (highest first)
            api_results.sort(key=lambda x: x["total_pii_found"], reverse=True)
            
            for result in api_results:
                endpoint = f"{result['http_method']} {result['endpoint_path']}"
                total_pii = result["total_pii_found"]
                compliance = result["compliance_score"]
                
                if total_pii == 0:
                    print(f"   ✅ {endpoint} - No PII detected (Compliance: {compliance}%)")
                    continue
                
                print(f"\n   🔍 {endpoint}")
                print(f"      📊 Total PII: {total_pii} | Compliance Score: {compliance}%")
                
                # Categorize PII by context (parameters, request, response)
                pii_by_context = {
                    "parameters": [],
                    "request_body": [],
                    "response": [],
                    "other": []
                }
                
                # Collect all PII matches
                all_pii = (result["critical_pii"] + result["high_pii"] + 
                          result["medium_pii"] + result["low_pii"])
                
                for pii in all_pii:
                    context = pii["context"]
                    if "parameter" in context:
                        pii_by_context["parameters"].append(pii)
                    elif "request_body" in context:
                        pii_by_context["request_body"].append(pii)
                    elif "response" in context:
                        pii_by_context["response"].append(pii)
                    else:
                        pii_by_context["other"].append(pii)
                
                # Display PII by context
                if pii_by_context["parameters"]:
                    print(f"      📝 PARAMETERS ({len(pii_by_context['parameters'])} PII found):")
                    for pii in pii_by_context["parameters"]:
                        severity_icon = self._get_severity_icon(pii["severity"])
                        print(f"         {severity_icon} {pii['field_name']} ({pii['pii_type']}) - {pii['context']}")
                
                if pii_by_context["request_body"]:
                    print(f"      📤 REQUEST BODY ({len(pii_by_context['request_body'])} PII found):")
                    for pii in pii_by_context["request_body"]:
                        severity_icon = self._get_severity_icon(pii["severity"])
                        field_path = pii["field_path"].replace(f"{result['http_method']} {result['endpoint_path']}.", "")
                        print(f"         {severity_icon} {field_path} ({pii['pii_type']}) - {pii['severity']} risk")
                
                if pii_by_context["response"]:
                    print(f"      📥 RESPONSE BODY ({len(pii_by_context['response'])} PII found):")
                    for pii in pii_by_context["response"]:
                        severity_icon = self._get_severity_icon(pii["severity"])
                        field_path = pii["field_path"].replace(f"{result['http_method']} {result['endpoint_path']}.", "")
                        print(f"         {severity_icon} {field_path} ({pii['pii_type']}) - {pii['severity']} risk")
                
                if pii_by_context["other"]:
                    print(f"      🔧 OTHER ({len(pii_by_context['other'])} PII found):")
                    for pii in pii_by_context["other"]:
                        severity_icon = self._get_severity_icon(pii["severity"])
                        print(f"         {severity_icon} {pii['field_name']} ({pii['pii_type']}) - {pii['context']}")
                
                # Show critical recommendations for this endpoint
                if result["critical_pii"] or result["high_pii"]:
                    print("      ⚠️  URGENT ACTIONS:")
                    if result["critical_pii"]:
                        print(f"         🔴 {len(result['critical_pii'])} Critical PII - Immediate security review required")
                    if result["high_pii"]:
                        print(f"         🟡 {len(result['high_pii'])} High-risk PII - Enhanced security controls needed")
    
    def _get_severity_icon(self, severity: str) -> str:
        """Get icon for PII severity level."""
        icons = {
            "critical": "🔴",
            "high": "🟡",
            "medium": "🟠",
            "low": "🟢"
        }
        return icons.get(severity, "❓")
    
    def generate_pii_summary_by_type(self, analysis_results: Dict[str, Any]) -> None:
        """
        Generate summary of PII types found across all APIs.
        
        Args:
            analysis_results: Analysis results dictionary
        """
        print("\n" + "="*80)
        print("📊 PII TYPES SUMMARY ACROSS ALL APIs")
        print("="*80)
        
        if "error" in analysis_results:
            return
        
        # Collect all PII instances
        pii_type_summary = {}
        
        detailed_results = analysis_results.get("detailed_results", [])
        
        for result in detailed_results:
            endpoint_key = f"{result['api_title']} - {result['http_method']} {result['endpoint_path']}"
            
            all_pii = (result["critical_pii"] + result["high_pii"] + 
                      result["medium_pii"] + result["low_pii"])
            
            for pii in all_pii:
                pii_type = pii["pii_type"]
                severity = pii["severity"]
                context = pii["context"]
                
                if pii_type not in pii_type_summary:
                    pii_type_summary[pii_type] = {
                        "total_count": 0,
                        "severity": severity,
                        "endpoints": set(),
                        "contexts": set()
                    }
                
                pii_type_summary[pii_type]["total_count"] += 1
                pii_type_summary[pii_type]["endpoints"].add(endpoint_key)
                pii_type_summary[pii_type]["contexts"].add(context)
        
        # Sort by severity and count
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_pii = sorted(
            pii_type_summary.items(),
            key=lambda x: (severity_order.get(x[1]["severity"], 4), -x[1]["total_count"])
        )
        
        print(f"{'PII Type':<25} {'Severity':<10} {'Count':<8} {'Endpoints':<12} {'Contexts'}")
        print("-" * 80)
        
        for pii_type, data in sorted_pii:
            severity_icon = self._get_severity_icon(data["severity"])
            contexts_str = ", ".join(list(data["contexts"])[:3])
            if len(data["contexts"]) > 3:
                contexts_str += "..."
            
            print(f"{pii_type:<25} {severity_icon} {data['severity']:<8} {data['total_count']:<8} {len(data['endpoints']):<12} {contexts_str}")
        
        print("\n📈 SUMMARY:")
        print(f"   Total PII Types Found: {len(pii_type_summary)}")
        print(f"   Most Common PII: {sorted_pii[0][0] if sorted_pii else 'None'} ({sorted_pii[0][1]['total_count']} instances)" if sorted_pii else "")
        critical_types = [pii for pii, data in sorted_pii if data["severity"] == "critical"]
        if critical_types:
            print(f"   🔴 Critical PII Types: {', '.join(critical_types)}")
    
    def generate_console_report(self, analysis_results: Dict[str, Any]) -> None:
        """
        Generate a formatted console report.
        
        Args:
            analysis_results: Analysis results dictionary
        """
        print("\n" + "="*80)
        print("🔍 PII DETECTION ANALYSIS REPORT")
        print("="*80)
        
        if "error" in analysis_results:
            print(f"❌ Error: {analysis_results['error']}")
            return
        
        # Overall summary
        overall = analysis_results.get("overall_summary", {})
        summary = overall.get("summary", {})
        
        print("\n📊 OVERALL SUMMARY")
        print(f"   Total Endpoints Analyzed: {summary.get('total_endpoints_analyzed', 0)}")
        print(f"   Endpoints with PII: {summary.get('endpoints_with_pii', 0)}")
        print(f"   PII Exposure Rate: {summary.get('pii_exposure_rate', 0)}%")
        print(f"   Average Compliance Score: {summary.get('average_compliance_score', 0)}%")
        
        # PII breakdown
        breakdown = overall.get("pii_breakdown", {})
        print("\n🔍 PII BREAKDOWN")
        print(f"   🔴 Critical: {breakdown.get('critical', 0)}")
        print(f"   🟡 High: {breakdown.get('high', 0)}")
        print(f"   🟠 Medium: {breakdown.get('medium', 0)}")
        print(f"   🟢 Low: {breakdown.get('low', 0)}")
        print(f"   📊 Total: {breakdown.get('total', 0)}")
        
        # Risk assessment
        risk = overall.get("risk_assessment", "Unknown")
        print(f"\n⚠️  RISK ASSESSMENT: {risk}")
        
        # Most common PII types
        common_pii = overall.get("most_common_pii_types", [])
        if common_pii:
            print("\n🔍 MOST COMMON PII TYPES")
            for pii_type, count in common_pii[:5]:
                print(f"   • {pii_type}: {count} occurrences")
        
        # API summaries
        api_summaries = analysis_results.get("api_summaries", {})
        if api_summaries:
            print("\n📋 API SUMMARIES")
            for api_id, summary in api_summaries.items():
                print(f"\n   📊 {summary['title']}")
                print(f"      Endpoints: {summary['endpoints_analyzed']}")
                print(f"      PII Found: {summary['total_pii_found']}")
                print(f"      Critical: {summary['critical_pii']}, High: {summary['high_pii']}")
                print(f"      Compliance Score: {summary['avg_compliance_score']:.1f}%")
        
        # Recommendations
        recommendations = overall.get("compliance_recommendations", [])
        if recommendations:
            print("\n💡 COMPLIANCE RECOMMENDATIONS")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        print("\n" + "="*80)
        print(f"📅 Analysis completed at: {analysis_results.get('analysis_timestamp', 'Unknown')}")
        print("="*80)
    
    def save_json_report(self, analysis_results: Dict[str, Any], filename: str) -> None:
        """
        Save analysis results to JSON file.
        
        Args:
            analysis_results: Analysis results dictionary
            filename: Output filename
        """
        try:
            with open(filename, 'w') as f:
                json.dump(analysis_results, f, indent=2, default=str)
            print(f"📄 JSON report saved to: {filename}")
        except Exception as e:
            print(f"❌ Error saving JSON report: {e}")


def main():
    """Main function to run PII analysis."""
    parser = argparse.ArgumentParser(description="PII Analysis for OpenAPI Schemas")
    parser.add_argument(
        "--api-id",
        help="Analyze specific API by ID (optional)"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "console", "both"],
        default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--output-file",
        default="pii_analysis_report.json",
        help="Output JSON filename (default: pii_analysis_report.json)"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Generate detailed breakdown by API and endpoint"
    )
    parser.add_argument(
        "--pii-summary",
        action="store_true",
        help="Generate summary of PII types across all APIs"
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = PIIAnalyzer()
        
        # Run analysis
        if args.api_id:
            results = analyzer.analyze_specific_api(args.api_id)
        else:
            results = analyzer.analyze_all_apis()
        
        # Generate output
        if args.output_format in ["console", "both"]:
            analyzer.generate_console_report(results)
            
            # Generate detailed reports if requested
            if args.detailed:
                analyzer.generate_detailed_pii_breakdown(results)
            
            if args.pii_summary:
                analyzer.generate_pii_summary_by_type(results)
        
        if args.output_format in ["json", "both"]:
            analyzer.save_json_report(results, args.output_file)
        
        # Exit with appropriate code
        if "error" in results:
            sys.exit(1)
        
        # Check for critical PII
        overall = results.get("overall_summary", {})
        breakdown = overall.get("pii_breakdown", {})
        if breakdown.get("critical", 0) > 0:
            print("\n🔴 WARNING: Critical PII detected! Immediate action required.")
            sys.exit(2)
        
        print("\n✅ PII analysis completed successfully")
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
