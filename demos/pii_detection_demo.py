#!/usr/bin/env python3
"""
PII Detection Demo

This demo showcases the comprehensive PII detection capabilities of the contract
testing framework. It demonstrates detection of various PII types in API parameters,
request bodies, and response schemas.

Features demonstrated:
- Parameter PII detection
- Request/Response schema analysis
- Compliance scoring
- Security recommendations
- Report generation

Author: Contract Testing Framework
Date: 2025-01-20
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pii_detector import (
    PIIDetector,
    PIIType,
    PIISeverity,
    create_pii_summary_report
)


def create_sample_api_data():
    """Create sample API data for demonstration."""
    return {
        "user_management_api": {
            "api_id": "user-mgmt-001",
            "api_title": "User Management API",
            "endpoints": [
                {
                    "path": "/users/{user_id}",
                    "method": "GET",
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "path",
                            "type": "string",
                            "description": "Unique user identifier"
                        },
                        {
                            "name": "include_email",
                            "in": "query",
                            "type": "boolean",
                            "description": "Include email in response"
                        }
                    ],
                    "response_schemas": {
                        "200": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string"},
                                "first_name": {"type": "string"},
                                "last_name": {"type": "string"},
                                "email": {"type": "string", "format": "email"},
                                "phone": {"type": "string"},
                                "date_of_birth": {"type": "string", "format": "date"},
                                "address": {
                                    "type": "object",
                                    "properties": {
                                        "street": {"type": "string"},
                                        "city": {"type": "string"},
                                        "state": {"type": "string"},
                                        "zip_code": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    "path": "/users",
                    "method": "POST",
                    "parameters": [],
                    "request_body_schema": {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "phone_number": {"type": "string"},
                            "ssn": {
                                "type": "string",
                                "description": "Social Security Number for verification"
                            },
                            "driver_license": {"type": "string"},
                            "profile": {
                                "type": "object",
                                "properties": {
                                    "username": {"type": "string"},
                                    "display_name": {"type": "string"}
                                }
                            }
                        }
                    },
                    "response_schemas": {
                        "201": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string"},
                                "status": {"type": "string"}
                            }
                        }
                    }
                }
            ]
        },
        "payment_api": {
            "api_id": "payment-001",
            "api_title": "Payment Processing API",
            "endpoints": [
                {
                    "path": "/payments",
                    "method": "POST",
                    "parameters": [
                        {
                            "name": "customer_id",
                            "in": "header",
                            "type": "string",
                            "description": "Customer identifier"
                        }
                    ],
                    "request_body_schema": {
                        "type": "object",
                        "properties": {
                            "credit_card_number": {"type": "string"},
                            "expiry_date": {"type": "string"},
                            "cvv": {"type": "string"},
                            "cardholder_name": {"type": "string"},
                            "billing_address": {
                                "type": "object",
                                "properties": {
                                    "street": {"type": "string"},
                                    "city": {"type": "string"},
                                    "postal_code": {"type": "string"}
                                }
                            },
                            "bank_account": {
                                "type": "object",
                                "properties": {
                                    "account_number": {"type": "string"},
                                    "routing_number": {"type": "string"}
                                }
                            }
                        }
                    },
                    "response_schemas": {
                        "200": {
                            "type": "object",
                            "properties": {
                                "transaction_id": {"type": "string"},
                                "status": {"type": "string"}
                            }
                        }
                    }
                }
            ]
        },
        "public_api": {
            "api_id": "public-001",
            "api_title": "Public Product API",
            "endpoints": [
                {
                    "path": "/products",
                    "method": "GET",
                    "parameters": [
                        {
                            "name": "category",
                            "in": "query",
                            "type": "string",
                            "description": "Product category"
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "type": "integer",
                            "description": "Number of results"
                        }
                    ],
                    "response_schemas": {
                        "200": {
                            "type": "object",
                            "properties": {
                                "products": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "product_id": {"type": "string"},
                                            "name": {"type": "string"},
                                            "price": {"type": "number"},
                                            "category": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }
    }


def demonstrate_pii_detection():
    """Demonstrate comprehensive PII detection capabilities."""
    print("🔍 PII DETECTION DEMONSTRATION")
    print("=" * 60)
    
    # Initialize detector
    detector = PIIDetector()
    print("✅ PII Detector initialized")
    
    # Get sample data
    sample_apis = create_sample_api_data()
    print(f"📊 Analyzing {len(sample_apis)} sample APIs")
    
    all_results = []
    
    # Analyze each API
    for api_key, api_data in sample_apis.items():
        api_id = api_data["api_id"]
        api_title = api_data["api_title"]
        
        print(f"\n🔍 Analyzing: {api_title}")
        print("-" * 40)
        
        api_results = []
        
        # Analyze each endpoint
        for endpoint in api_data["endpoints"]:
            result = detector.analyze_endpoint_pii(
                api_id=api_id,
                api_title=api_title,
                endpoint_path=endpoint["path"],
                http_method=endpoint["method"],
                parameters=endpoint.get("parameters", []),
                request_body_schema=endpoint.get("request_body_schema"),
                response_schemas=endpoint.get("response_schemas", {})
            )
            
            api_results.append(result)
            all_results.append(result)
            
            # Display endpoint results
            print(f"   📍 {endpoint['method']} {endpoint['path']}")
            print(f"      PII Found: {result.total_pii_found}")
            print(f"      🔴 Critical: {len(result.critical_pii)}")
            print(f"      🟡 High: {len(result.high_pii)}")
            print(f"      🟠 Medium: {len(result.medium_pii)}")
            print(f"      🟢 Low: {len(result.low_pii)}")
            print(f"      📊 Compliance Score: {result.compliance_score}%")
            
            # Show critical PII details
            if result.critical_pii:
                print("      🚨 CRITICAL PII DETECTED:")
                for match in result.critical_pii:
                    print(f"         • {match.pii_type.value}: {match.field_name}")
                    print(f"           Context: {match.context}")
                    print(f"           Path: {match.field_path}")
        
        # API summary
        total_pii = sum(r.total_pii_found for r in api_results)
        avg_compliance = sum(r.compliance_score for r in api_results) / len(api_results)
        print("\n   📊 API Summary:")
        print(f"      Total PII: {total_pii}")
        print(f"      Average Compliance: {avg_compliance:.1f}%")
    
    return all_results


def demonstrate_detailed_analysis(results):
    """Demonstrate detailed PII analysis and reporting."""
    print("\n\n📋 DETAILED PII ANALYSIS")
    print("=" * 60)
    
    # Create summary report
    summary_report = create_pii_summary_report(results)
    
    # Display overall summary
    overall = summary_report["summary"]
    print("📊 OVERALL SUMMARY:")
    print(f"   Total Endpoints: {overall['total_endpoints_analyzed']}")
    print(f"   Endpoints with PII: {overall['endpoints_with_pii']}")
    print(f"   PII Exposure Rate: {overall['pii_exposure_rate']}%")
    print(f"   Average Compliance: {overall['average_compliance_score']}%")
    
    # PII breakdown
    breakdown = summary_report["pii_breakdown"]
    print("\n🔍 PII BREAKDOWN:")
    print(f"   🔴 Critical: {breakdown['critical']}")
    print(f"   🟡 High: {breakdown['high']}")
    print(f"   🟠 Medium: {breakdown['medium']}")
    print(f"   🟢 Low: {breakdown['low']}")
    print(f"   📊 Total: {breakdown['total']}")
    
    # Risk assessment
    risk = summary_report["risk_assessment"]
    print(f"\n⚠️  RISK ASSESSMENT: {risk}")
    
    # Most common PII types
    common_pii = summary_report["most_common_pii_types"]
    if common_pii:
        print("\n🔍 MOST COMMON PII TYPES:")
        for pii_type, count in common_pii[:5]:
            print(f"   • {pii_type}: {count} occurrences")
    
    # Compliance recommendations
    recommendations = summary_report["compliance_recommendations"]
    print("\n💡 COMPLIANCE RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations[:8], 1):
        print(f"   {i}. {rec}")
    
    return summary_report


def demonstrate_pii_patterns():
    """Demonstrate PII pattern matching capabilities."""
    print("\n\n🎯 PII PATTERN MATCHING DEMONSTRATION")
    print("=" * 60)
    
    detector = PIIDetector()
    
    # Test various field names
    test_fields = [
        # High-risk PII
        "ssn", "social_security_number", "tax_id",
        "credit_card", "card_number", "cc_number",
        "passport_number", "driver_license",
        "bank_account", "account_number", "routing_number",
        
        # Medium-risk PII
        "email", "email_address", "user_email",
        "phone", "phone_number", "mobile", "telephone",
        "date_of_birth", "dob", "birthday",
        "address", "street", "home_address",
        "ip_address", "client_ip",
        
        # Low-risk PII
        "first_name", "last_name", "full_name",
        "username", "user_name", "login",
        "user_id", "customer_id", "uid",
        
        # Non-PII
        "product_id", "order_status", "category",
        "price", "quantity", "description"
    ]
    
    print("🔍 Testing field name patterns:")
    print(f"{'Field Name':<20} {'PII Type':<20} {'Severity':<10} {'Match'}")
    print("-" * 65)
    
    for field in test_fields:
        pii_type = detector._match_pii_pattern(field)
        if pii_type:
            severity = detector.severity_mapping[pii_type]
            severity_icon = {
                PIISeverity.CRITICAL: "🔴",
                PIISeverity.HIGH: "🟡",
                PIISeverity.MEDIUM: "🟠",
                PIISeverity.LOW: "🟢"
            }[severity]
            print(f"{field:<20} {pii_type.value:<20} {severity.value:<10} {severity_icon}")
        else:
            print(f"{field:<20} {'None':<20} {'N/A':<10} ❌")


def demonstrate_compliance_scoring():
    """Demonstrate compliance scoring system."""
    print("\n\n📊 COMPLIANCE SCORING DEMONSTRATION")
    print("=" * 60)
    
    detector = PIIDetector()
    
    # Test different PII combinations
    test_scenarios = [
        {
            "name": "No PII",
            "matches": []
        },
        {
            "name": "Low Risk Only",
            "matches": [
                (PIIType.USER_ID, PIISeverity.LOW),
                (PIIType.USERNAME, PIISeverity.MEDIUM)
            ]
        },
        {
            "name": "Medium Risk",
            "matches": [
                (PIIType.EMAIL, PIISeverity.HIGH),
                (PIIType.FIRST_NAME, PIISeverity.MEDIUM),
                (PIIType.LAST_NAME, PIISeverity.MEDIUM)
            ]
        },
        {
            "name": "High Risk",
            "matches": [
                (PIIType.EMAIL, PIISeverity.HIGH),
                (PIIType.PHONE, PIISeverity.HIGH),
                (PIIType.ADDRESS, PIISeverity.HIGH),
                (PIIType.DATE_OF_BIRTH, PIISeverity.HIGH)
            ]
        },
        {
            "name": "Critical Risk",
            "matches": [
                (PIIType.SSN, PIISeverity.CRITICAL),
                (PIIType.CREDIT_CARD, PIISeverity.CRITICAL),
                (PIIType.EMAIL, PIISeverity.HIGH)
            ]
        }
    ]
    
    print("📊 Compliance scoring scenarios:")
    print(f"{'Scenario':<15} {'PII Count':<10} {'Score':<8} {'Assessment'}")
    print("-" * 60)
    
    for scenario in test_scenarios:
        # Create mock matches
        from core.pii_detector import PIIMatch
        matches = [
            PIIMatch(
                pii_type=pii_type,
                severity=severity,
                field_name="test_field",
                field_path="/test",
                context="test",
                description="Test match"
            )
            for pii_type, severity in scenario["matches"]
        ]
        
        score = detector._calculate_compliance_score(matches)
        
        # Determine assessment
        if score >= 90:
            assessment = "✅ Excellent"
        elif score >= 75:
            assessment = "🟡 Good"
        elif score >= 50:
            assessment = "🟠 Needs Work"
        else:
            assessment = "🔴 Critical"
        
        print(f"{scenario['name']:<15} {len(matches):<10} {score:<8.1f} {assessment}")


def save_demo_results(results, summary_report):
    """Save demo results to files."""
    print("\n\n💾 SAVING DEMO RESULTS")
    print("=" * 60)
    
    try:
        # Save detailed results
        detailed_results = []
        for result in results:
            # Serialize the result
            serialized = {
                "api_id": result.api_id,
                "api_title": result.api_title,
                "endpoint_path": result.endpoint_path,
                "http_method": result.http_method,
                "total_pii_found": result.total_pii_found,
                "compliance_score": result.compliance_score,
                "pii_breakdown": {
                    "critical": len(result.critical_pii),
                    "high": len(result.high_pii),
                    "medium": len(result.medium_pii),
                    "low": len(result.low_pii)
                },
                "recommendations": result.recommendations
            }
            detailed_results.append(serialized)
        
        # Save to JSON file
        demo_results = {
            "demo_timestamp": "2025-01-20T23:26:00",
            "summary_report": summary_report,
            "detailed_results": detailed_results
        }
        
        with open("pii_detection_demo_results.json", "w") as f:
            json.dump(demo_results, f, indent=2, default=str)
        
        print("✅ Demo results saved to: pii_detection_demo_results.json")
        
    except Exception as e:
        print(f"❌ Error saving demo results: {e}")


def main():
    """Main demo function."""
    print("🚀 Starting PII Detection Demo")
    print("=" * 60)
    
    try:
        # Run demonstrations
        results = demonstrate_pii_detection()
        summary_report = demonstrate_detailed_analysis(results)
        demonstrate_pii_patterns()
        demonstrate_compliance_scoring()
        save_demo_results(results, summary_report)
        
        print("\n\n🎉 PII DETECTION DEMO COMPLETED")
        print("=" * 60)
        print("✅ All demonstrations completed successfully")
        print("📄 Results saved to pii_detection_demo_results.json")
        print("\n💡 Next Steps:")
        print("   1. Run 'python scripts/pii_analysis.py' for real API analysis")
        print("   2. Review the generated recommendations")
        print("   3. Implement security measures for detected PII")
        print("   4. Integrate PII detection into your CI/CD pipeline")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
