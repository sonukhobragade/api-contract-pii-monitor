#!/usr/bin/env python3
"""
API Contract Testing Tool
Compare actual API requests/responses against stored OpenAPI schema
"""
import psycopg2
import psycopg2.extras
import json
import requests
import jsonschema
from typing import Dict, List, Any
from datetime import datetime

from core.config import config


class ContractTester:
    """Compares live API traffic against the stored OpenAPI schema."""

    def __init__(self):
        # Built through config rather than from raw environment reads. Reading
        # the variables directly here skipped the required-field validation
        # entirely, so an empty password reached psycopg2 and succeeded against
        # any server using trust authentication.
        self.conn_str = config.get_connection_string()
        self.conn = psycopg2.connect(self.conn_str)
    
    def get_component_schema(self, component_name: str) -> Dict:
        """Get component schema definition"""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT definition 
                FROM schema_components 
                WHERE component_name = %s AND component_type = 'schemas'
                LIMIT 1
            """, (component_name,))
            
            result = cursor.fetchone()
            if result:
                if isinstance(result['definition'], str):
                    return json.loads(result['definition'])
                else:
                    return result['definition']
        return {}
    
    def resolve_schema_refs(self, schema_obj: Any) -> Any:
        """Recursively resolve $ref references in schema"""
        if isinstance(schema_obj, dict):
            if '$ref' in schema_obj:
                ref = schema_obj['$ref']
                if ref.startswith('#/components/schemas/'):
                    component_name = ref.split('/')[-1]
                    component_schema = self.get_component_schema(component_name)
                    if component_schema:
                        return self.resolve_schema_refs(component_schema)
                    else:
                        return {"error": f"Component '{component_name}' not found"}
                return schema_obj
            else:
                resolved = {}
                for key, value in schema_obj.items():
                    resolved[key] = self.resolve_schema_refs(value)
                return resolved
        elif isinstance(schema_obj, list):
            return [self.resolve_schema_refs(item) for item in schema_obj]
        else:
            return schema_obj
    
    def get_endpoint_schema(self, path: str, method: str) -> Dict:
        """Get endpoint schema including request and response schemas"""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # Get endpoint details
            cursor.execute("""
                SELECT id, path, method, operation_id, summary
                FROM endpoints 
                WHERE path = %s AND method = %s
                LIMIT 1
            """, (path, method.upper()))
            
            endpoint = cursor.fetchone()
            if not endpoint:
                return {"error": f"Endpoint not found: {method.upper()} {path}"}
            
            endpoint_id = endpoint['id']
            result = {
                "endpoint": dict(endpoint),
                "request_schema": None,
                "response_schemas": {},
                "parameters": []
            }
            
            # Get parameters
            cursor.execute("""
                SELECT name, param_location, data_type, required, schema_definition
                FROM parameters 
                WHERE endpoint_id = %s
            """, (endpoint_id,))
            
            parameters = cursor.fetchall()
            result["parameters"] = [dict(p) for p in parameters]
            
            # Get request body schema
            cursor.execute("""
                SELECT content_type, schema_definition, required
                FROM request_bodies 
                WHERE endpoint_id = %s
                LIMIT 1
            """, (endpoint_id,))
            
            request_body = cursor.fetchone()
            if request_body and request_body['schema_definition']:
                if isinstance(request_body['schema_definition'], str):
                    schema = json.loads(request_body['schema_definition'])
                else:
                    schema = request_body['schema_definition']
                
                result["request_schema"] = {
                    "content_type": request_body['content_type'],
                    "required": request_body['required'],
                    "schema": self.resolve_schema_refs(schema)
                }
            
            # Get response schemas
            cursor.execute("""
                SELECT status_code, content_type, schema_definition
                FROM responses 
                WHERE endpoint_id = %s
            """, (endpoint_id,))
            
            responses = cursor.fetchall()
            for response in responses:
                if response['schema_definition']:
                    if isinstance(response['schema_definition'], str):
                        schema = json.loads(response['schema_definition'])
                    else:
                        schema = response['schema_definition']
                    
                    result["response_schemas"][response['status_code']] = {
                        "content_type": response['content_type'],
                        "schema": self.resolve_schema_refs(schema)
                    }
            
            return result
    
    def validate_request(self, path: str, method: str, request_data: Dict, headers: Dict = None) -> Dict:
        """Validate request data against schema"""
        endpoint_schema = self.get_endpoint_schema(path, method)
        
        if "error" in endpoint_schema:
            return {"valid": False, "errors": [endpoint_schema["error"]]}
        
        errors = []
        warnings = []
        
        # Validate request body
        if endpoint_schema["request_schema"]:
            request_schema = endpoint_schema["request_schema"]["schema"]
            try:
                jsonschema.validate(request_data, request_schema)
                print("✅ Request body validation passed")
            except jsonschema.ValidationError as e:
                errors.append(f"Request body validation failed: {e.message}")
                print(f"❌ Request body validation failed: {e.message}")
        else:
            if request_data:
                warnings.append("Request body provided but no schema defined")
                print("⚠️  Request body provided but no schema defined")
        
        # Validate required parameters
        required_params = [p for p in endpoint_schema["parameters"] if p["required"]]
        if required_params and not headers:
            warnings.append("Required parameters defined but no headers provided for validation")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "schema_used": endpoint_schema["request_schema"]
        }
    
    def validate_response(self, path: str, method: str, status_code: int, response_data: Dict) -> Dict:
        """Validate response data against schema"""
        endpoint_schema = self.get_endpoint_schema(path, method)
        
        if "error" in endpoint_schema:
            return {"valid": False, "errors": [endpoint_schema["error"]]}
        
        errors = []
        warnings = []
        
        # Find matching response schema
        status_str = str(status_code)
        response_schema = None
        
        if status_str in endpoint_schema["response_schemas"]:
            response_schema = endpoint_schema["response_schemas"][status_str]
        elif "default" in endpoint_schema["response_schemas"]:
            response_schema = endpoint_schema["response_schemas"]["default"]
            warnings.append(f"Using default response schema for status {status_code}")
        
        if response_schema:
            try:
                jsonschema.validate(response_data, response_schema["schema"])
                print(f"✅ Response validation passed for status {status_code}")
            except jsonschema.ValidationError as e:
                errors.append(f"Response validation failed: {e.message}")
                print(f"❌ Response validation failed: {e.message}")
        else:
            warnings.append(f"No response schema found for status {status_code}")
            print(f"⚠️  No response schema found for status {status_code}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "schema_used": response_schema,
            "status_code": status_code
        }
    
    def test_live_api(self, base_url: str, path: str, method: str, request_data: Dict = None, headers: Dict = None) -> Dict:
        """Test live API endpoint against schema"""
        print(f"\n🧪 Testing live API: {method.upper()} {base_url}{path}")
        
        # Validate request first
        request_validation = self.validate_request(path, method, request_data or {}, headers)
        
        if not request_validation["valid"]:
            return {
                "success": False,
                "request_validation": request_validation,
                "response_validation": None,
                "api_response": None
            }
        
        # Make API call
        try:
            url = f"{base_url}{path}"
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=request_data, headers=headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=request_data, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}
            
            print(f"📡 API Response: {response.status_code}")
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError:
                # A non-JSON body is expected for error pages; a bare except
                # here also swallowed KeyboardInterrupt and MemoryError.
                response_data = {"raw_response": response.text}
            
            # Validate response
            response_validation = self.validate_response(path, method, response.status_code, response_data)
            
            return {
                "success": True,
                "request_validation": request_validation,
                "response_validation": response_validation,
                "api_response": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "data": response_data
                }
            }
            
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"API call failed: {str(e)}",
                "request_validation": request_validation,
                "response_validation": None
            }
    
    def generate_test_report(self, test_results: List[Dict]) -> str:
        """Generate a comprehensive test report"""
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.get("success") and 
                          r.get("request_validation", {}).get("valid") and 
                          r.get("response_validation", {}).get("valid"))
        
        report = f"""
=== API Contract Testing Report ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 Summary:
   Total Tests: {total_tests}
   Passed: {passed_tests}
   Failed: {total_tests - passed_tests}
   Success Rate: {(passed_tests/total_tests*100):.1f}%

📋 Detailed Results:
"""
        
        for i, result in enumerate(test_results, 1):
            report += f"\n{i}. Test: {result.get('endpoint', 'Unknown')}\n"
            
            if result.get("success"):
                req_val = result.get("request_validation", {})
                resp_val = result.get("response_validation", {})
                
                report += f"   Request Valid: {'✅' if req_val.get('valid') else '❌'}\n"
                report += f"   Response Valid: {'✅' if resp_val.get('valid') else '❌'}\n"
                
                if req_val.get("errors"):
                    report += f"   Request Errors: {', '.join(req_val['errors'])}\n"
                if resp_val.get("errors"):
                    report += f"   Response Errors: {', '.join(resp_val['errors'])}\n"
                
                api_resp = result.get("api_response", {})
                report += f"   Status Code: {api_resp.get('status_code', 'N/A')}\n"
            else:
                report += f"   ❌ Failed: {result.get('error', 'Unknown error')}\n"
        
        return report
    
    def close(self):
        """Close database connection"""
        self.conn.close()

def main():
    """Example usage of the contract tester"""
    tester = ContractTester()
    
    print("=== API Contract Testing Tool ===")
    
    # Example 1: Test request validation only
    print("\n1️⃣ Testing Request Validation for /orders")
    
    sample_request = {
        "countryCode": 91,
        "customerPhone": "+1-555-0100",
        "notifyByEmail": False
    }
    
    request_validation = tester.validate_request("/orders", "POST", sample_request)
    print(f"Request Validation Result: {request_validation}")
    
    # Example 2: Test response validation
    print("\n2️⃣ Testing Response Validation")
    
    sample_response = {
        "status": {
            "code": 200,
            "type": "success",
            "title": "OTP Sent",
            "message": "OTP sent successfully"
        },
        "transactionId": "tx_123456789",
        "payload": {}
    }
    
    response_validation = tester.validate_response("/orders", "POST", 200, sample_response)
    print(f"Response Validation Result: {response_validation}")
    
    # Example 3: Test live API (commented out - uncomment and modify for your API)
    """
    print("\n3️⃣ Testing Live API")
    
    headers = {
        "Content-Type": "application/json",
        "deviceId": "test-device",
        "language": "en"
    }
    
    live_test = tester.test_live_api(
        base_url="https://api.example.com",
        path="/orders",
        method="POST",
        request_data=sample_request,
        headers=headers
    )
    
    print(f"Live API Test Result: {live_test}")
    """
    
    tester.close()
    
    print(f"\n{'='*60}")
    print("💡 Contract Testing Usage:")
    print("1. Use validate_request() to test request data against schema")
    print("2. Use validate_response() to test response data against schema") 
    print("3. Use test_live_api() to test actual API endpoints")
    print("4. Use generate_test_report() for comprehensive reporting")

if __name__ == "__main__":
    main()
