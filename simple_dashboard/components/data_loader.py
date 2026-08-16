#!/usr/bin/env python3
"""
Data Loader Component
Handles loading and filtering PII analysis data
"""

import streamlit as st
import json
from pathlib import Path
from typing import List, Dict, Any


def load_real_pii_data():
    """Load real PII analysis data from JSON files."""
    try:
        # Try to load from clean_pii_only.json first
        pii_file = Path("clean_pii_only.json")
        if not pii_file.exists():
            pii_file = Path("clean_pii_findings.json")
        
        if not pii_file.exists():
            st.error("PII data file not found. Expected: clean_pii_only.json or clean_pii_findings.json")
            return load_sample_data()
        
        with open(pii_file, 'r') as f:
            data = json.load(f)
        
        # Transform the data to match dashboard format
        endpoints = []
        
        for finding in data.get('pii_findings', []):
            # Extract PII by severity
            critical_pii = []
            high_pii = []
            medium_pii = []
            low_pii = []
            
            # Process PII by location
            for location, pii_list in finding.get('pii_by_location', {}).items():
                for pii_item in pii_list:
                    pii_entry = {
                        "field_path": pii_item.get('field_path', ''),
                        "pii_type": pii_item.get('pii_type', ''),
                        "severity": pii_item.get('severity', ''),
                        "field_name": pii_item.get('field_name', ''),
                        "location": location,
                        "recommendations": pii_item.get('recommendations', [])
                    }
                    
                    severity = pii_item.get('severity', '').lower()
                    if severity == 'critical':
                        critical_pii.append(pii_entry)
                    elif severity == 'high':
                        high_pii.append(pii_entry)
                    elif severity == 'medium':
                        medium_pii.append(pii_entry)
                    elif severity == 'low':
                        low_pii.append(pii_entry)
            
            endpoint = {
                "http_method": finding.get('http_method', ''),
                "endpoint_path": finding.get('endpoint_path', ''),
                "api_id": finding.get('api_id', ''),
                "api_title": finding.get('api_title', ''),
                "total_pii_found": finding.get('total_pii_found', 0),
                "compliance_score": finding.get('compliance_score', 0),
                "critical_pii": critical_pii,
                "high_pii": high_pii,
                "medium_pii": medium_pii,
                "low_pii": low_pii
            }
            
            endpoints.append(endpoint)
        
        st.success(f"Loaded {len(endpoints)} endpoints with PII data from {pii_file.name}")
        return endpoints
        
    except Exception as e:
        st.error(f"Error loading PII data: {str(e)}")
        return load_sample_data()


def load_sample_data():
    """Load sample PII analysis data (fallback)."""
    return [
        {
            "http_method": "POST",
            "endpoint_path": "/customers/addresses",
            "api_id": "11111111-2222-3333-4444-555555555555",
            "api_title": "Deals API",
            "critical_pii": [
                {
                    "field_path": "payload.userAddress.firstLine",
                    "pii_type": "physical_address",
                    "severity": "critical"
                },
                {
                    "field_path": "payload.userAddress.secondLine", 
                    "pii_type": "physical_address",
                    "severity": "critical"
                }
            ],
            "high_pii": [
                {
                    "field_path": "payload.userAddress.name",
                    "pii_type": "full_name",
                    "severity": "high"
                },
                {
                    "field_path": "payload.userAddress.emailId",
                    "pii_type": "email_address",
                    "severity": "high"
                },
                {
                    "field_path": "payload.userAddress.mobileNumber",
                    "pii_type": "phone_number",
                    "severity": "high"
                }
            ]
        },
        {
            "http_method": "POST",
            "endpoint_path": "/console/updateGameOrder",
            "api_id": "11111111-2222-3333-4444-555555555555",
            "api_title": "Console API",
            "critical_pii": [
                {
                    "field_path": "user.payment.cardNumber",
                    "pii_type": "credit_card",
                    "severity": "critical"
                }
            ],
            "high_pii": [
                {
                    "field_path": "user.email",
                    "pii_type": "email_address",
                    "severity": "high"
                }
            ]
        },
        {
            "http_method": "GET",
            "endpoint_path": "/user/profile",
            "api_id": "11111111-2222-3333-4444-555555555555",
            "api_title": "User API",
            "critical_pii": [],
            "high_pii": [
                {
                    "field_path": "profile.email",
                    "pii_type": "email_address",
                    "severity": "high"
                },
                {
                    "field_path": "profile.phone",
                    "pii_type": "phone_number",
                    "severity": "high"
                }
            ]
        },
        {
            "http_method": "POST",
            "endpoint_path": "/auth/login",
            "api_id": "11111111-2222-3333-4444-555555555555",
            "api_title": "Auth API",
            "critical_pii": [],
            "high_pii": [],
            "medium_pii": [
                {
                    "field_path": "credentials.username",
                    "pii_type": "username",
                    "severity": "medium"
                }
            ]
        },
        {
            "http_method": "GET",
            "endpoint_path": "/health/status",
            "api_id": "11111111-2222-3333-4444-555555555555",
            "api_title": "Health API",
            "critical_pii": [],
            "high_pii": [],
            "medium_pii": []
        },
        {
            "http_method": "POST",
            "endpoint_path": "/payment/process",
            "api_id": "11111111-2222-3333-4444-555555555555",
            "api_title": "Payment API",
            "critical_pii": [
                {
                    "field_path": "payment.cardNumber",
                    "pii_type": "credit_card",
                    "severity": "critical"
                },
                {
                    "field_path": "payment.cvv",
                    "pii_type": "credit_card_cvv",
                    "severity": "critical"
                }
            ],
            "high_pii": [
                {
                    "field_path": "customer.email",
                    "pii_type": "email_address",
                    "severity": "high"
                }
            ]
        },
        {
            "http_method": "POST",
            "endpoint_path": "/auth/register",
            "api_id": "11111111-2222-3333-4444-555555555555",
            "api_title": "Auth API",
            "critical_pii": [],
            "high_pii": [
                {
                    "field_path": "user.email",
                    "pii_type": "email_address",
                    "severity": "high"
                },
                {
                    "field_path": "user.password",
                    "pii_type": "password",
                    "severity": "high"
                }
            ],
            "medium_pii": [
                {
                    "field_path": "user.username",
                    "pii_type": "username",
                    "severity": "medium"
                }
            ]
        }
    ]


def generate_large_scale_data(num_apis: int = 1300) -> List[Dict[str, Any]]:
    """Generate large-scale data for testing with 1300+ APIs."""
    import random
    
    api_templates = [
        {"title": "User Management API", "base_path": "/users", "methods": ["GET", "POST", "PUT", "DELETE"]},
        {"title": "Payment Processing API", "base_path": "/payments", "methods": ["POST", "GET"]},
        {"title": "Authentication API", "base_path": "/auth", "methods": ["POST", "GET"]},
        {"title": "Product Catalog API", "base_path": "/products", "methods": ["GET", "POST", "PUT", "DELETE"]},
        {"title": "Order Management API", "base_path": "/orders", "methods": ["GET", "POST", "PUT"]},
        {"title": "Inventory API", "base_path": "/inventory", "methods": ["GET", "PUT"]},
        {"title": "Customer Support API", "base_path": "/support", "methods": ["GET", "POST"]},
        {"title": "Analytics API", "base_path": "/analytics", "methods": ["GET", "POST"]},
        {"title": "Notification API", "base_path": "/notifications", "methods": ["POST", "GET"]},
        {"title": "File Upload API", "base_path": "/files", "methods": ["POST", "GET", "DELETE"]},
    ]
    
    pii_types = [
        {"type": "email_address", "severity": "high"},
        {"type": "phone_number", "severity": "high"},
        {"type": "full_name", "severity": "high"},
        {"type": "credit_card", "severity": "critical"},
        {"type": "ssn", "severity": "critical"},
        {"type": "physical_address", "severity": "critical"},
        {"type": "username", "severity": "medium"},
        {"type": "ip_address", "severity": "medium"},
        {"type": "date_of_birth", "severity": "high"},
        {"type": "passport_number", "severity": "critical"},
    ]
    
    endpoints = []
    
    for i in range(num_apis):
        template = random.choice(api_templates)
        method = random.choice(template["methods"])
        path_suffix = f"/{random.randint(1, 1000)}" if random.random() > 0.5 else ""
        
        # Determine PII based on API type and randomness
        critical_pii = []
        high_pii = []
        medium_pii = []
        
        if "payment" in template["title"].lower():
            # Payment APIs more likely to have critical PII
            if random.random() > 0.3:
                critical_pii.append({
                    "field_path": f"payment.{random.choice(['cardNumber', 'cvv', 'accountNumber'])}",
                    "pii_type": "credit_card",
                    "severity": "critical"
                })
        
        if "user" in template["title"].lower() or "auth" in template["title"].lower():
            # User/Auth APIs more likely to have high PII
            if random.random() > 0.2:
                pii_type = random.choice([p for p in pii_types if p["severity"] in ["high", "medium"]])
                high_pii.append({
                    "field_path": f"user.{pii_type['type']}",
                    "pii_type": pii_type["type"],
                    "severity": pii_type["severity"]
                })
        
        # Add some random PII for variety
        if random.random() > 0.7:
            pii_type = random.choice(pii_types)
            if pii_type["severity"] == "critical":
                critical_pii.append({
                    "field_path": f"data.{pii_type['type']}",
                    "pii_type": pii_type["type"],
                    "severity": pii_type["severity"]
                })
            elif pii_type["severity"] == "high":
                high_pii.append({
                    "field_path": f"data.{pii_type['type']}",
                    "pii_type": pii_type["type"],
                    "severity": pii_type["severity"]
                })
            else:
                medium_pii.append({
                    "field_path": f"data.{pii_type['type']}",
                    "pii_type": pii_type["type"],
                    "severity": pii_type["severity"]
                })
        
        endpoints.append({
            "http_method": method,
            "endpoint_path": f"{template['base_path']}{path_suffix}",
            "api_id": f"api-{i:04d}",
            "api_title": template["title"],
            "critical_pii": critical_pii,
            "high_pii": high_pii,
            "medium_pii": medium_pii
        })
    
    return endpoints


def filter_endpoints_by_risk(endpoints, risk_filter):
    """Filter endpoints based on risk level."""
    filtered_endpoints = []
    
    for ep in endpoints:
        critical_count = len(ep.get('critical_pii', []))
        high_count = len(ep.get('high_pii', []))
        medium_count = len(ep.get('medium_pii', []))
        low_count = len(ep.get('low_pii', []))
        
        if risk_filter == "All Endpoints":
            filtered_endpoints.append(ep)
        elif risk_filter == "🔴 Critical Risk" and critical_count > 0:
            filtered_endpoints.append(ep)
        elif risk_filter == "🟡 High Risk" and high_count > 0:
            filtered_endpoints.append(ep)
        elif risk_filter == "🟠 Medium Risk" and medium_count > 0:
            filtered_endpoints.append(ep)
        elif risk_filter == "🟢 Low Risk" and low_count > 0:
            filtered_endpoints.append(ep)
        elif risk_filter == "✅ No Risk" and critical_count == 0 and high_count == 0 and medium_count == 0 and low_count == 0:
            filtered_endpoints.append(ep)
    
    return filtered_endpoints


def filter_endpoints_advanced(endpoints, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Advanced filtering for large-scale data."""
    filtered = endpoints
    
    # Filter by API title
    if filters.get('api_title'):
        filtered = [ep for ep in filtered if filters['api_title'].lower() in ep.get('api_title', '').lower()]
    
    # Filter by HTTP method
    if filters.get('http_method'):
        filtered = [ep for ep in filtered if ep.get('http_method') == filters['http_method']]
    
    # Filter by path contains
    if filters.get('path_contains'):
        filtered = [ep for ep in filtered if filters['path_contains'].lower() in ep.get('endpoint_path', '').lower()]
    
    # Filter by PII type
    if filters.get('pii_type'):
        filtered = [ep for ep in filtered if any(
            pii.get('pii_type') == filters['pii_type'] 
            for pii in ep.get('critical_pii', []) + ep.get('high_pii', []) + ep.get('medium_pii', [])
        )]
    
    # Filter by risk level
    if filters.get('risk_level'):
        filtered = filter_endpoints_by_risk(filtered, filters['risk_level'])
    
    # Filter by minimum PII count
    if filters.get('min_pii_count'):
        filtered = [ep for ep in filtered if (
            len(ep.get('critical_pii', [])) + 
            len(ep.get('high_pii', [])) + 
            len(ep.get('medium_pii', []))
        ) >= filters['min_pii_count']]
    
    return filtered


def paginate_endpoints(endpoints: List[Dict[str, Any]], page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    """Paginate endpoints for large datasets."""
    total = len(endpoints)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    paginated_endpoints = endpoints[start_idx:end_idx]
    total_pages = (total + page_size - 1) // page_size
    
    return {
        'endpoints': paginated_endpoints,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'start_idx': start_idx + 1,
        'end_idx': min(end_idx, total)
    }


def get_endpoint_risk_level(endpoint):
    """Get the risk level of an endpoint."""
    critical_count = len(endpoint.get('critical_pii', []))
    high_count = len(endpoint.get('high_pii', []))
    medium_count = len(endpoint.get('medium_pii', []))
    low_count = len(endpoint.get('low_pii', []))
    
    if critical_count > 0:
        return "🔴", "Critical"
    elif high_count > 0:
        return "🟡", "High"
    elif medium_count > 0:
        return "🟠", "Medium"
    elif low_count > 0:
        return "🟢", "Low"
    else:
        return "✅", "No Risk"


def calculate_overall_metrics(endpoints):
    """Calculate overall metrics from endpoints."""
    total_endpoints = len(endpoints)
    total_critical = sum(len(ep.get('critical_pii', [])) for ep in endpoints)
    total_high = sum(len(ep.get('high_pii', [])) for ep in endpoints)
    total_medium = sum(len(ep.get('medium_pii', [])) for ep in endpoints)
    total_low = sum(len(ep.get('low_pii', [])) for ep in endpoints)
    
    # Calculate risk score (weighted average)
    risk_score = 0
    if total_endpoints > 0:
        risk_score = ((total_critical * 4) + (total_high * 3) + (total_medium * 2) + (total_low * 1)) / total_endpoints
    
    return {
        'total_endpoints': total_endpoints,
        'total_critical': total_critical,
        'total_high': total_high,
        'total_medium': total_medium,
        'total_low': total_low,
        'risk_score': risk_score
    }


def group_endpoints_by_api(endpoints):
    """Group endpoints by API title."""
    api_groups = {}
    
    for ep in endpoints:
        api_title = ep.get('api_title', 'Unknown API')
        if api_title not in api_groups:
            api_groups[api_title] = []
        api_groups[api_title].append(ep)
    
    return api_groups


def get_unique_values(endpoints: List[Dict[str, Any]], field: str) -> List[str]:
    """Get unique values for a field (for filter dropdowns)."""
    values = set()
    for ep in endpoints:
        if field == 'api_title':
            values.add(ep.get('api_title', 'Unknown API'))
        elif field == 'http_method':
            values.add(ep.get('http_method', 'Unknown'))
        elif field == 'pii_type':
            all_pii = ep.get('critical_pii', []) + ep.get('high_pii', []) + ep.get('medium_pii', [])
            for pii in all_pii:
                values.add(pii.get('pii_type', 'Unknown'))
    
    return sorted(list(values))


def search_endpoints(endpoints: List[Dict[str, Any]], search_term: str) -> List[Dict[str, Any]]:
    """Search endpoints by path, API title, or PII type."""
    if not search_term:
        return endpoints
    
    search_term = search_term.lower()
    results = []
    
    for ep in endpoints:
        # Search in endpoint path
        if search_term in ep.get('endpoint_path', '').lower():
            results.append(ep)
            continue
        
        # Search in API title
        if search_term in ep.get('api_title', '').lower():
            results.append(ep)
            continue
        
        # Search in PII types
        all_pii = ep.get('critical_pii', []) + ep.get('high_pii', []) + ep.get('medium_pii', [])
        for pii in all_pii:
            if search_term in pii.get('pii_type', '').lower():
                results.append(ep)
                break
    
    return results
