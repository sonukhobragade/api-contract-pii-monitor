#!/usr/bin/env python
"""
Comprehensive test script to verify all scenarios of API changes in Slack notifications.
This script creates a mock report with various types of changes and sends it to Slack.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.notification_manager import NotificationManager

def create_comprehensive_test_report():
    """
    Create a comprehensive test report with all types of API changes.
    """
    # Create a comprehensive mock report with multiple change types
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_apis_monitored": 3,
        "apis_with_changes": 2,
        "apis_unchanged": 1,
        "total_changes": 30,
        "breaking_changes": 5,
        "database_operations_avoided": 1,
        "hash_comparisons_performed": 3,
        "errors": [],
        "api_endpoint_details": [
            {"api_title": "E-commerce API", "endpoint_count": 178, "api_id": "https://api.example.com/ecommerce/v2"},
            {"api_title": "User Management API", "endpoint_count": 42, "api_id": "https://api.example.com/users/v1"},
            {"api_title": "Analytics API", "endpoint_count": 35, "api_id": "https://api.example.com/analytics/v3"}
        ],
        "total_endpoints_monitored": 255,
        "apis_processed": [
            {
                "api_id": "https://api.example.com/ecommerce/v2",
                "api_title": "E-commerce API",
                "api_type": "OPENAPI_SPEC_PRIMARY",
                "change_detected": True,
                "breaking_changes": 3,
                "total_changes": 20,
                "change_analysis": {
                    "summary": "20 changes detected (3 breaking)",
                    "endpoint_changes": [
                        {
                            "change_type": "endpoint_added",
                            "endpoint": "/products/recommendations",
                            "method": "GET",
                            "description": "New endpoint for product recommendations",
                            "is_breaking": False,
                            "old_value": None,
                            "new_value": {"path": "/products/recommendations", "method": "GET"}
                        },
                        {
                            "change_type": "endpoint_removed",
                            "endpoint": "/products/legacy-search",
                            "method": "GET",
                            "description": "Legacy search endpoint removed",
                            "is_breaking": True,
                            "old_value": {"path": "/products/legacy-search", "method": "GET"},
                            "new_value": None
                        }
                    ],
                    "parameter_changes": [
                        {
                            "change_type": "parameter_added",
                            "endpoint": "/products/search",
                            "parameter_name": "sort_by",
                            "description": "New optional parameter for sorting results",
                            "is_breaking": False,
                            "old_value": None,
                            "new_value": {"name": "sort_by", "required": False}
                        },
                        {
                            "change_type": "parameter_removed",
                            "endpoint": "/orders/{id}",
                            "parameter_name": "api_key",
                            "description": "Required parameter removed",
                            "is_breaking": True,
                            "old_value": {"name": "api_key", "required": True},
                            "new_value": None
                        }
                    ],
                    "response_changes": [
                        # Scenario 1: Simple schema change with added optional field
                        {
                            "change_type": "response_schema_changed",
                            "endpoint": "/products/{id}",
                            "method": "GET",
                            "status_code": "200",
                            "description": "Product response enhanced with category information",
                            "is_breaking": False,
                            "old_value": {
                                "type": "object", 
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "price": {"type": "number"}
                                },
                                "required": ["id", "name", "price"]
                            },
                            "new_value": {
                                "type": "object", 
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "price": {"type": "number"},
                                    "category": {"type": "string"}
                                },
                                "required": ["id", "name", "price"]
                            },
                            "affected_endpoints": [
                                {"method": "GET", "path": "/products/{id}", "usage_type": "response"}
                            ]
                        },
                        # Scenario 2: Breaking change with new required field
                        {
                            "change_type": "response_schema_changed",
                            "endpoint": "/orders",
                            "method": "POST",
                            "status_code": "201",
                            "description": "Order creation response now requires status field",
                            "is_breaking": True,
                            "old_value": {
                                "type": "object", 
                                "properties": {
                                    "order_id": {"type": "string"},
                                    "created_at": {"type": "string", "format": "date-time"}
                                },
                                "required": ["order_id"]
                            },
                            "new_value": {
                                "type": "object", 
                                "properties": {
                                    "order_id": {"type": "string"},
                                    "created_at": {"type": "string", "format": "date-time"},
                                    "status": {"type": "string", "enum": ["pending", "processing", "completed"]}
                                },
                                "required": ["order_id", "status"]
                            },
                            "affected_endpoints": [
                                {"method": "POST", "path": "/orders", "usage_type": "response"}
                            ]
                        },
                        # Scenario 3: Multiple fields added and removed
                        {
                            "change_type": "response_schema_changed",
                            "endpoint": "/products/search",
                            "method": "GET",
                            "status_code": "200",
                            "description": "Search response updated with pagination and filters",
                            "is_breaking": False,
                            "old_value": {
                                "type": "object", 
                                "properties": {
                                    "results": {"type": "array"},
                                    "count": {"type": "integer"},
                                    "query": {"type": "string"}
                                },
                                "required": ["results", "count"]
                            },
                            "new_value": {
                                "type": "object", 
                                "properties": {
                                    "results": {"type": "array"},
                                    "count": {"type": "integer"},
                                    "page": {"type": "integer"},
                                    "total_pages": {"type": "integer"},
                                    "filters_applied": {"type": "object"}
                                },
                                "required": ["results", "count", "page"]
                            },
                            "affected_endpoints": [
                                {"method": "GET", "path": "/products/search", "usage_type": "response"},
                                {"method": "GET", "path": "/products/featured", "usage_type": "response"}
                            ]
                        },
                        # Scenario 4: Response with $ref
                        {
                            "change_type": "response_schema_changed",
                            "endpoint": "/cart/{id}",
                            "method": "GET",
                            "status_code": "200",
                            "description": "Cart response updated with shipping options",
                            "is_breaking": False,
                            "old_value": {
                                "$ref": "#/components/schemas/Cart"
                            },
                            "new_value": {
                                "$ref": "#/components/schemas/CartWithShipping"
                            },
                            "affected_endpoints": [
                                {"method": "GET", "path": "/cart/{id}", "usage_type": "response"}
                            ]
                        }
                    ],
                    "component_changes": [
                        {
                            "change_type": "component_added",
                            "component_name": "ProductRecommendation",
                            "description": "New schema for product recommendations",
                            "is_breaking": False,
                            "old_value": None,
                            "new_value": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "string"},
                                    "confidence_score": {"type": "number"},
                                    "reason": {"type": "string"}
                                },
                                "required": ["product_id", "confidence_score"]
                            },
                            "affected_endpoints": [
                                {"method": "GET", "path": "/products/recommendations", "usage_type": "response"}
                            ]
                        },
                        {
                            "change_type": "component_property_added",
                            "component": "Product",
                            "property": "is_featured",
                            "description": "Added featured flag to products",
                            "is_breaking": False,
                            "old_value": None,
                            "new_value": {"type": "boolean", "default": False}
                        },
                        {
                            "change_type": "component_property_required_added",
                            "component": "ShippingAddress",
                            "property": "country_code",
                            "description": "Country code is now required",
                            "is_breaking": True,
                            "old_value": {"required": ["street", "city", "postal_code"]},
                            "new_value": {"required": ["street", "city", "postal_code", "country_code"]}
                        }
                    ]
                }
            },
            {
                "api_id": "https://api.example.com/users/v1",
                "api_title": "User Management API",
                "api_type": "OPENAPI_SPEC_PRIMARY",
                "change_detected": True,
                "breaking_changes": 2,
                "total_changes": 10,
                "change_analysis": {
                    "summary": "10 changes detected (2 breaking)",
                    "endpoint_changes": [
                        {
                            "change_type": "endpoint_added",
                            "endpoint": "/users/preferences",
                            "method": "GET",
                            "description": "New endpoint for user preferences",
                            "is_breaking": False,
                            "old_value": None,
                            "new_value": {"path": "/users/preferences", "method": "GET"}
                        }
                    ],
                    "parameter_changes": [
                        {
                            "change_type": "parameter_type_changed",
                            "endpoint": "/users/search",
                            "parameter_name": "age",
                            "description": "Parameter type changed from integer to string range",
                            "is_breaking": True,
                            "old_value": {"name": "age", "schema": {"type": "integer"}},
                            "new_value": {"name": "age", "schema": {"type": "string"}}
                        }
                    ],
                    "response_changes": [
                        # Scenario 5: Response with multiple affected endpoints
                        {
                            "change_type": "response_schema_changed",
                            "endpoint": "/users/{id}",
                            "method": "GET",
                            "status_code": "200",
                            "description": "User profile enhanced with preferences and settings",
                            "is_breaking": False,
                            "old_value": {
                                "type": "object", 
                                "properties": {
                                    "id": {"type": "string"},
                                    "username": {"type": "string"},
                                    "email": {"type": "string"}
                                },
                                "required": ["id", "username", "email"]
                            },
                            "new_value": {
                                "type": "object", 
                                "properties": {
                                    "id": {"type": "string"},
                                    "username": {"type": "string"},
                                    "email": {"type": "string"},
                                    "preferences": {"type": "object"},
                                    "settings": {"type": "object"},
                                    "last_login": {"type": "string", "format": "date-time"}
                                },
                                "required": ["id", "username", "email"]
                            },
                            "affected_endpoints": [
                                {"method": "GET", "path": "/users/{id}", "usage_type": "response"},
                                {"method": "GET", "path": "/users/me", "usage_type": "response"},
                                {"method": "GET", "path": "/users/profile", "usage_type": "response"},
                                {"method": "GET", "path": "/admin/users/{id}", "usage_type": "response"}
                            ]
                        },
                        # Scenario 6: Response status added
                        {
                            "change_type": "response_status_added",
                            "endpoint": "/users/authenticate",
                            "method": "POST",
                            "status_code": "429",
                            "description": "Rate limit response added",
                            "is_breaking": False,
                            "old_value": None,
                            "new_value": {"description": "Too Many Requests"}
                        }
                    ],
                    "component_changes": [
                        {
                            "change_type": "component_modified",
                            "component_name": "UserPreferences",
                            "description": "Enhanced user preferences schema",
                            "is_breaking": False,
                            "old_value": {
                                "type": "object",
                                "properties": {
                                    "theme": {"type": "string"},
                                    "notifications_enabled": {"type": "boolean"}
                                }
                            },
                            "new_value": {
                                "type": "object",
                                "properties": {
                                    "theme": {"type": "string"},
                                    "notifications_enabled": {"type": "boolean"},
                                    "language": {"type": "string"},
                                    "timezone": {"type": "string"}
                                }
                            },
                            "affected_endpoints": [
                                {"method": "GET", "path": "/users/preferences", "usage_type": "response"},
                                {"method": "PUT", "path": "/users/preferences", "usage_type": "request"}
                            ]
                        }
                    ]
                }
            },
            {
                "api_id": "https://api.example.com/analytics/v3",
                "api_title": "Analytics API",
                "api_type": "OPENAPI_SPEC_PRIMARY",
                "change_detected": False,
                "breaking_changes": 0,
                "total_changes": 0
            }
        ]
    }
    
    return report

def main():
    """
    Main function to test all scenarios of API changes in Slack notifications.
    """
    print("🧪 Testing All API Change Scenarios in Slack")
    print("===========================================")
    
    # Create comprehensive test report
    report = create_comprehensive_test_report()
    print(f"📋 Created comprehensive test report with {report['total_changes']} changes ({report['breaking_changes']} breaking)")
    
    # Initialize notification manager
    notification_manager = NotificationManager()
    
    # Send notification
    print("📱 Sending test notification to Slack...")
    success = notification_manager.send_slack_notification(report)
    
    if success:
        print("✅ Test notification sent successfully")
        print("📝 Please check your Slack channel for the comprehensive change report")
        print("   The notification should include:")
        print("   - Multiple API change scenarios")
        print("   - Various response schema change formats")
        print("   - Breaking vs non-breaking changes")
        print("   - Required vs optional field distinctions")
        print("   - Multiple affected endpoints")
    else:
        print("❌ Failed to send test notification")
    
    print("\n🔍 Report Summary:")
    print(f"   Total Changes: {report['total_changes']}")
    print(f"   Breaking Changes: {report['breaking_changes']}")
    print(f"   APIs with Changes: {report['apis_with_changes']}")
    print(f"   APIs Monitored: {report['total_apis_monitored']}")
    print(f"   Total Endpoints: {report['total_endpoints_monitored']}")

if __name__ == "__main__":
    main()
