#!/usr/bin/env python3
"""
PII-Only Report Generator

This script takes a full PII analysis report and generates a clean, 
filtered JSON containing only endpoints with PII findings.

Features:
- Filters out endpoints with zero PII
- Cleans up confusing field paths
- Categorizes PII by location (parameters, request body, response body)
- Provides summary statistics
- Limits recommendations to keep file size manageable

Usage:
    python scripts/generate_pii_only_report.py [input_file] [output_file]
    
Example:
    python scripts/generate_pii_only_report.py fast_pii_analysis_report.json clean_pii_only.json
"""

import json
import sys
import argparse
from typing import Dict, Any


def clean_field_path(field_path: str, field_name: str) -> str:
    """
    Clean up confusing field paths that contain HTTP methods and endpoints.
    
    Args:
        field_path: Original field path from PII detection
        field_name: Field name
        
    Returns:
        Cleaned field path
    """
    if not field_path or field_path == field_name:
        return field_name
    
    # Remove HTTP method and endpoint from path
    if ' /' in field_path:
        parts = field_path.split('.')
        if len(parts) > 1:
            # Keep only the meaningful part after the endpoint
            clean_parts = []
            for part in parts:
                if not (' /' in part or part.startswith('POST') or part.startswith('GET') 
                       or part.startswith('PUT') or part.startswith('DELETE')):
                    clean_parts.append(part)
            if clean_parts:
                return '.'.join(clean_parts)
    
    return field_path


def generate_pii_only_report(input_file: str, output_file: str) -> Dict[str, Any]:
    """
    Generate a clean PII-only report from a full PII analysis report.
    
    Args:
        input_file: Path to the full PII analysis report
        output_file: Path for the output PII-only report
        
    Returns:
        Dictionary containing the generated report
    """
    # Load the full report
    try:
        with open(input_file, 'r') as f:
            full_report = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Input file '{input_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in '{input_file}'")
        sys.exit(1)
    
    # Create clean PII-only report structure
    pii_only_report = {
        'analysis_timestamp': full_report.get('analysis_timestamp', ''),
        'processing_time_seconds': full_report.get('processing_time_seconds', 0),
        'summary': {
            'total_pii_instances': 0,
            'endpoints_with_pii': 0,
            'pii_by_severity': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
            'pii_by_location': {'parameters': 0, 'request_body': 0, 'response_body': 0}
        },
        'pii_findings': []
    }
    
    # Process endpoints with PII
    detailed_results = full_report.get('detailed_results', [])
    
    for endpoint in detailed_results:
        if endpoint.get('total_pii_found', 0) > 0:
            pii_only_report['summary']['endpoints_with_pii'] += 1
            
            # Collect all PII from this endpoint
            all_pii = (endpoint.get('critical_pii', []) + 
                      endpoint.get('high_pii', []) + 
                      endpoint.get('medium_pii', []) + 
                      endpoint.get('low_pii', []))
            
            pii_only_report['summary']['total_pii_instances'] += len(all_pii)
            
            # Create endpoint entry
            endpoint_entry = {
                'api_title': endpoint.get('api_title', ''),
                'endpoint_path': endpoint.get('endpoint_path', ''),
                'http_method': endpoint.get('http_method', ''),
                'total_pii_found': endpoint.get('total_pii_found', 0),
                'compliance_score': endpoint.get('compliance_score', 100.0),
                'pii_by_location': {
                    'parameters': [],
                    'request_body': [],
                    'response_body': []
                }
            }
            
            # Process each PII finding
            for pii in all_pii:
                # Clean the field path
                clean_path = clean_field_path(pii.get('field_path', ''), pii.get('field_name', ''))
                
                pii_detail = {
                    'field_name': pii.get('field_name', ''),
                    'field_path': clean_path,
                    'pii_type': pii.get('pii_type', ''),
                    'severity': pii.get('severity', ''),
                    'context': pii.get('context', ''),
                    'pattern_matched': pii.get('pattern_matched', ''),
                    'recommendations': pii.get('recommendations', [])[:2]  # Limit to 2 recommendations
                }
                
                # Count by severity
                severity = pii.get('severity', 'low')
                if severity in pii_only_report['summary']['pii_by_severity']:
                    pii_only_report['summary']['pii_by_severity'][severity] += 1
                
                # Categorize by location
                context_lower = pii.get('context', '').lower()
                if 'parameter' in context_lower:
                    endpoint_entry['pii_by_location']['parameters'].append(pii_detail)
                    pii_only_report['summary']['pii_by_location']['parameters'] += 1
                elif 'request' in context_lower:
                    endpoint_entry['pii_by_location']['request_body'].append(pii_detail)
                    pii_only_report['summary']['pii_by_location']['request_body'] += 1
                elif 'response' in context_lower:
                    endpoint_entry['pii_by_location']['response_body'].append(pii_detail)
                    pii_only_report['summary']['pii_by_location']['response_body'] += 1
            
            pii_only_report['pii_findings'].append(endpoint_entry)
    
    # Save the clean PII-only report
    try:
        with open(output_file, 'w') as f:
            json.dump(pii_only_report, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving output file: {e}")
        sys.exit(1)
    
    return pii_only_report


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Generate clean PII-only JSON report from full PII analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_pii_only_report.py fast_pii_analysis_report.json clean_pii_only.json
  python scripts/generate_pii_only_report.py --input report.json --output pii_findings.json
        """
    )
    
    parser.add_argument(
        'input_file',
        nargs='?',
        default='fast_pii_analysis_report.json',
        help='Input PII analysis report file (default: fast_pii_analysis_report.json)'
    )
    
    parser.add_argument(
        'output_file',
        nargs='?',
        default='clean_pii_only.json',
        help='Output PII-only report file (default: clean_pii_only.json)'
    )
    
    parser.add_argument(
        '--input', '-i',
        dest='input_file_alt',
        help='Alternative way to specify input file'
    )
    
    parser.add_argument(
        '--output', '-o',
        dest='output_file_alt',
        help='Alternative way to specify output file'
    )
    
    args = parser.parse_args()
    
    # Use alternative arguments if provided
    input_file = args.input_file_alt or args.input_file
    output_file = args.output_file_alt or args.output_file
    
    print("🚀 Generating PII-only report...")
    print(f"📄 Input:  {input_file}")
    print(f"📄 Output: {output_file}")
    print()
    
    # Generate the report
    report = generate_pii_only_report(input_file, output_file)
    
    # Print summary
    print("✅ Clean PII-only JSON report generated successfully!")
    print()
    print("📊 SUMMARY:")
    print(f"   📋 Endpoints with PII: {report['summary']['endpoints_with_pii']}")
    print(f"   🔍 Total PII instances: {report['summary']['total_pii_instances']}")
    print()
    print("🚨 PII by Severity:")
    for severity, count in report['summary']['pii_by_severity'].items():
        icon = {'critical': '🔴', 'high': '🟡', 'medium': '🟠', 'low': '🟢'}.get(severity, '⚪')
        print(f"   {icon} {severity.capitalize()}: {count}")
    print()
    print("📍 PII by Location:")
    for location, count in report['summary']['pii_by_location'].items():
        icon = {'parameters': '🔧', 'request_body': '📤', 'response_body': '📥'}.get(location, '📋')
        print(f"   {icon} {location.replace('_', ' ').title()}: {count}")
    print()
    print(f"💾 Report saved to: {output_file}")


if __name__ == "__main__":
    main()
