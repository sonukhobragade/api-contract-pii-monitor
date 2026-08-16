#!/usr/bin/env python3
"""
Schema Change Detection Demo
Shows how contract testing detects API schema changes
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ApiPostgres import OpenAPIQuerier
from src.contract_tester import ContractTester

def demonstrate_schema_change_detection():
    """Demonstrate how schema changes are detected and why it matters"""
    
    print("🔍 Schema Change Detection Demo")
    print("=" * 60)
    
    # Connect to database
    conn_string = 'postgresql://postgres:${PG_PASSWORD}@localhost:5432/openapi_store'
    querier = OpenAPIQuerier(conn_string)
    tester = ContractTester()
    
    try:
        # 1. Show current API versions and releases
        print("\n📊 Current API Releases:")
        releases = querier.get_api_releases()
        for release in releases:
            print(f"   📅 {release['release_tag']} (Hash: {release['schema_hash'][:12]}...)")
        
        # 2. Show what happens when schema changes
        print("\n🎯 Benefits of Schema Change Detection:")
        print("=" * 50)
        
        # Example 1: Field type change
        print("\n1️⃣ **Catching Data Type Changes**")
        print("   Old Schema: countryCode (integer)")
        print("   New Schema: countryCode (string)")
        print("   Impact: Existing clients will break!")
        
        # Test with wrong data type
        wrong_type_data = {
            "countryCode": "91",  # String instead of integer
            "customerPhone": "+1-555-0100",
            "notifyByEmail": False
        }
        
        result = tester.validate_request("/orders", "POST", wrong_type_data)
        if not result['valid']:
            print(f"   ✅ Contract Test Caught Error: {result['errors'][0]}")
        
        # Example 2: Missing required field
        print("\n2️⃣ **Catching Missing Required Fields**")
        print("   Old Schema: optional 'notifyByEmail'")
        print("   New Schema: required 'notifyByEmail'")
        print("   Impact: Old clients missing this field will fail!")
        
        missing_field_data = {
            "countryCode": 91,
            "customerPhone": "+1-555-0100"
            # Missing notifyByEmail field
        }
        
        result = tester.validate_request("/orders", "POST", missing_field_data)
        if not result['valid']:
            print(f"   ✅ Contract Test Caught Error: {result['errors'][0]}")
        
        # Example 3: Response structure change
        print("\n3️⃣ **Catching Response Structure Changes**")
        print("   Old Response: has 'status.type' field")
        print("   New Response: missing 'status.type' field")
        print("   Impact: Client code expecting 'type' will break!")
        
        incomplete_response = {
            "status": {
                "code": 200,
                "message": "OTP sent successfully"
                # Missing 'type' field that clients expect
            },
            "transactionId": "tx_123456",
            "payload": {}
        }
        
        result = tester.validate_response("/orders", "POST", 200, incomplete_response)
        if not result['valid']:
            print(f"   ✅ Contract Test Caught Error: {result['errors'][0]}")
        
        # 4. Show how to detect changes between versions
        print("\n🔄 How Schema Change Detection Works:")
        print("=" * 50)
        
        # Get schema changes from database
        changes = querier.get_schema_changes()
        if changes:
            print(f"   📝 Found {len(changes)} recorded schema changes:")
            for change in changes[:3]:
                print(f"      • {change['endpoint_path']} - {change['change_type']}")
                print(f"        {change['description']}")
        else:
            print("   📝 No schema changes recorded yet")
            print("   💡 Changes are detected when you run ApiPostgres.py with new schema versions")
        
        # 5. Show practical benefits
        print("\n💰 Real-World Benefits:")
        print("=" * 30)
        print("✅ **Prevent Production Bugs**: Catch breaking changes before deployment")
        print("✅ **Save Development Time**: No need to debug client-server mismatches")
        print("✅ **Maintain API Compatibility**: Ensure backward compatibility")
        print("✅ **Automated Testing**: Run in CI/CD to catch issues early")
        print("✅ **Documentation Accuracy**: Ensure API docs match implementation")
        
        # 6. Show how to use this in practice
        print("\n🚀 How to Use This in Your Workflow:")
        print("=" * 40)
        print("1. **Before Code Changes**: Run contract tests with current data")
        print("2. **After Code Changes**: Run contract tests again")
        print("3. **Compare Results**: Any new failures indicate breaking changes")
        print("4. **Fix Issues**: Update API or client code before deployment")
        print("5. **Deploy Safely**: Confident that contracts are maintained")
        
        # Example workflow
        print("\n📋 Example Workflow:")
        print("```bash")
        print("# 1. Test current implementation")
        print("python contract_testing_guide.py")
        print("")
        print("# 2. Make your API changes")
        print("# ... modify your API code ...")
        print("")
        print("# 3. Update schema in database")
        print("python ApiPostgres.py")
        print("")
        print("# 4. Test again with new schema")
        print("python contract_testing_guide.py")
        print("")
        print("# 5. Check for any new failures")
        print("# If tests pass: ✅ Safe to deploy")
        print("# If tests fail: ❌ Fix breaking changes first")
        print("```")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        querier.close()
        tester.close()

def show_schema_comparison():
    """Show how to compare schemas between versions"""
    print("\n🔍 Schema Comparison Example:")
    print("=" * 40)
    
    # Example: Old vs New schema
    old_schema = {
        "type": "object",
        "properties": {
            "countryCode": {"type": "integer"},
            "customerPhone": {"type": "string"},
            "notifyByEmail": {"type": "boolean"}  # Optional
        },
        "required": ["countryCode", "customerPhone"]
    }
    
    new_schema = {
        "type": "object", 
        "properties": {
            "countryCode": {"type": "integer"},
            "customerPhone": {"type": "string"},
            "notifyByEmail": {"type": "boolean"},  # Now required!
            "deviceId": {"type": "string"}  # New field
        },
        "required": ["countryCode", "customerPhone", "notifyByEmail"]  # Added requirement
    }
    
    print("📊 Old Schema Requirements:")
    print(f"   Required: {old_schema['required']}")
    
    print("📊 New Schema Requirements:")
    print(f"   Required: {new_schema['required']}")
    
    print("⚠️  Breaking Change Detected:")
    print("   • 'notifyByEmail' is now required (was optional)")
    print("   • Existing clients will fail if they don't send this field")
    
    print("✅ Non-Breaking Change:")
    print("   • 'deviceId' is new but optional")
    print("   • Existing clients will continue to work")

if __name__ == "__main__":
    demonstrate_schema_change_detection()
    show_schema_comparison()
