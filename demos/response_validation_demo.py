#!/usr/bin/env python3
"""
Response Validation Demo
Shows how contract testing validates API responses against schemas
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.contract_tester import ContractTester
import json

def demonstrate_response_validation():
    """Show how response validation catches API implementation issues"""
    
    print("📥 Response Validation Demo")
    print("=" * 40)
    
    tester = ContractTester()
    
    # Test 1: Valid Response
    print("\n✅ Test 1: Valid Response")
    print("-" * 30)
    
    valid_response = {
        "status": {
            "code": 200,
            "type": "SUCCESS",
            "message": "OTP sent successfully"
        },
        "transactionId": "tx_123456789",
        "payload": {}
    }
    
    result = tester.validate_response("/orders", "POST", 200, valid_response)
    print(f"📊 Response: {json.dumps(valid_response, indent=2)}")
    print(f"🔍 Validation Result: {'✅ VALID' if result['valid'] else '❌ INVALID'}")
    if result['errors']:
        print(f"❌ Errors: {result['errors']}")
    
    # Test 2: Missing Required Field
    print("\n❌ Test 2: Missing Required Field")
    print("-" * 35)
    
    missing_field_response = {
        "status": {
            "code": 200,
            # Missing "type" field - this will break mobile apps!
            "message": "OTP sent successfully"
        },
        "transactionId": "tx_123456789",
        "payload": {}
    }
    
    result = tester.validate_response("/orders", "POST", 200, missing_field_response)
    print(f"📊 Response: {json.dumps(missing_field_response, indent=2)}")
    print(f"🔍 Validation Result: {'✅ VALID' if result['valid'] else '❌ INVALID'}")
    if result['errors']:
        print(f"❌ Errors: {result['errors']}")
        print("💡 This would crash mobile apps expecting 'status.type'!")
    
    # Test 3: Wrong Data Type
    print("\n❌ Test 3: Wrong Data Type")
    print("-" * 28)
    
    wrong_type_response = {
        "status": {
            "code": "200",  # Should be integer, not string!
            "type": "SUCCESS",
            "message": "OTP sent successfully"
        },
        "transactionId": "tx_123456789",
        "payload": {}
    }
    
    result = tester.validate_response("/orders", "POST", 200, wrong_type_response)
    print(f"📊 Response: {json.dumps(wrong_type_response, indent=2)}")
    print(f"🔍 Validation Result: {'✅ VALID' if result['valid'] else '❌ INVALID'}")
    if result['errors']:
        print(f"❌ Errors: {result['errors']}")
        print("💡 Mobile apps expecting integer will fail!")
    
    # Test 4: Extra Fields (Usually OK)
    print("\n⚠️  Test 4: Extra Fields")
    print("-" * 25)
    
    extra_fields_response = {
        "status": {
            "code": 200,
            "type": "SUCCESS", 
            "message": "OTP sent successfully"
        },
        "transactionId": "tx_123456789",
        "payload": {},
        "extraField": "This is new",  # Extra field - usually OK
        "debugInfo": {"timestamp": "2025-01-20T10:00:00Z"}  # More extra data
    }
    
    result = tester.validate_response("/orders", "POST", 200, extra_fields_response)
    print(f"📊 Response: {json.dumps(extra_fields_response, indent=2)}")
    print(f"🔍 Validation Result: {'✅ VALID' if result['valid'] else '❌ INVALID'}")
    if result['warnings']:
        print(f"⚠️  Warnings: {result['warnings']}")
    print("💡 Extra fields usually don't break clients (they ignore them)")
    
    # Test 5: Different Status Codes
    print("\n🔢 Test 5: Different Status Codes")
    print("-" * 35)
    
    error_response = {
        "status": {
            "code": 400,
            "type": "ERROR",
            "message": "Invalid mobile number"
        },
        "errors": ["Mobile number must be 10 digits"]
    }
    
    result = tester.validate_response("/orders", "POST", 400, error_response)
    print(f"📊 Error Response (400): {json.dumps(error_response, indent=2)}")
    print(f"🔍 Validation Result: {'✅ VALID' if result['valid'] else '❌ INVALID'}")
    if result['warnings']:
        print(f"⚠️  Warnings: {result['warnings']}")
    
    tester.close()

def show_response_validation_benefits():
    """Show why response validation is crucial"""
    
    print("\n🎯 Why Response Validation is Critical")
    print("=" * 45)
    
    print("\n🚨 Real-World Scenarios:")
    print("-" * 25)
    
    print("1️⃣ **API Returns Wrong Data Type**")
    print("   • Schema says: status.code = integer")
    print("   • API returns: status.code = '200' (string)")
    print("   • Mobile app crashes when parsing integer")
    print("   ✅ Response validation catches this!")
    
    print("\n2️⃣ **Missing Required Fields**")
    print("   • Schema says: status.type is required")
    print("   • API returns: status without 'type' field")
    print("   • Mobile app crashes: NullPointerException")
    print("   ✅ Response validation catches this!")
    
    print("\n3️⃣ **Wrong Response Structure**")
    print("   • Schema says: errors = array of strings")
    print("   • API returns: errors = single string")
    print("   • Mobile app expects array, gets string")
    print("   ✅ Response validation catches this!")
    
    print("\n4️⃣ **Status Code Mismatch**")
    print("   • API returns 200 with error message")
    print("   • Should return 400 for client errors")
    print("   • Mobile app thinks request succeeded")
    print("   ✅ Response validation catches this!")
    
    print("\n💰 Business Impact:")
    print("-" * 20)
    print("❌ Without Response Validation:")
    print("   • App crashes in production")
    print("   • Bad user reviews")
    print("   • Emergency hotfixes")
    print("   • Lost revenue")
    print("   • Developer stress")
    
    print("\n✅ With Response Validation:")
    print("   • Bugs caught in development")
    print("   • Stable app releases")
    print("   • Happy users")
    print("   • Confident deployments")
    print("   • Better sleep!")

def show_validation_workflow():
    """Show how to use response validation in practice"""
    
    print("\n🔄 Response Validation Workflow")
    print("=" * 40)
    
    print("1️⃣ **During Development**:")
    print("   ```python")
    print("   # Test your API response")
    print("   from src.contract_tester import ContractTester")
    print("   tester = ContractTester()")
    print("   ")
    print("   # Your API returns this")
    print("   api_response = get_api_response()")
    print("   ")
    print("   # Validate against schema")
    print("   result = tester.validate_response(")
    print("       '/orders', 'POST', 200, api_response")
    print("   )")
    print("   ")
    print("   if not result['valid']:")
    print("       print('❌ API response violates schema!')")
    print("       print(result['errors'])")
    print("   ```")
    
    print("\n2️⃣ **In Unit Tests**:")
    print("   ```python")
    print("   def test_otp_endpoint_response():")
    print("       response = call_otp_api()")
    print("       ")
    print("       # Validate response structure")
    print("       result = tester.validate_response(")
    print("           '/orders', 'POST', 200, response.json()")
    print("       )")
    print("       ")
    print("       assert result['valid'], f'Invalid response: {result[\"errors\"]}'")
    print("   ```")
    
    print("\n3️⃣ **In CI/CD Pipeline**:")
    print("   ```bash")
    print("   # Run contract tests")
    print("   python contract_testing_guide.py")
    print("   ")
    print("   # If any response validation fails:")
    print("   # ❌ Pipeline fails")
    print("   # ✅ Fix API before deployment")
    print("   ```")
    
    print("\n4️⃣ **With Live API Testing**:")
    print("   ```python")
    print("   # Test against actual API")
    print("   result = tester.test_live_api(")
    print("       base_url='https://your-api.com',")
    print("       path='/orders',")
    print("       method='POST',")
    print("       request_data=test_data")
    print("   )")
    print("   ")
    print("   # Automatically validates both request AND response!")
    print("   print(f'Request valid: {result[\"request_validation\"][\"valid\"]}')") 
    print("   print(f'Response valid: {result[\"response_validation\"][\"valid\"]}')") 
    print("   ```")

if __name__ == "__main__":
    demonstrate_response_validation()
    show_response_validation_benefits()
    show_validation_workflow()
