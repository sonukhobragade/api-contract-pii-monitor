#!/usr/bin/env python3
"""
Improved Parameter Parser
Enhanced version of parameter parsing with duplicate prevention
"""
import json
from typing import List, Dict, Any

def parse_parameters_improved(cursor, parameters: List[Dict[str, Any]], endpoint_id: str):
    """
    Parse and insert parameter information with duplicate prevention.
    
    Args:
        cursor: Database cursor
        parameters: List of parameter definitions
        endpoint_id: UUID of the endpoint
    """
    if not parameters:
        return
    
    # First, get existing parameters for this endpoint to avoid duplicates
    cursor.execute("""
        SELECT name, param_location 
        FROM parameters 
        WHERE endpoint_id = %s
    """, (endpoint_id,))
    
    existing_params = set()
    for row in cursor.fetchall():
        existing_params.add((row[0], row[1]))  # (name, location)
    
    # Process each parameter
    inserted_count = 0
    skipped_count = 0
    
    for param in parameters:
        param_name = param.get('name', '')
        param_location = param.get('in', '')
        
        # Skip if this parameter already exists
        if (param_name, param_location) in existing_params:
            skipped_count += 1
            print(f"   ⏭️  Skipping duplicate: {param_name} ({param_location})")
            continue
        
        schema_info = param.get('schema', {})
        
        param_data = {
            'endpoint_id': endpoint_id,
            'name': param_name,
            'param_location': param_location,
            'data_type': schema_info.get('type', ''),
            'format': schema_info.get('format'),
            'required': param.get('required', False),
            'deprecated': param.get('deprecated', False),
            'description': param.get('description'),
            'default_value': str(schema_info.get('default')) if 'default' in schema_info else None,
            'example_value': str(param.get('example')) if 'example' in param else None,
            'enum_values': schema_info.get('enum', []),
            'schema_definition': json.dumps(schema_info)
        }
        
        try:
            cursor.execute("""
                INSERT INTO parameters (
                    endpoint_id, name, param_location, data_type, format, 
                    required, deprecated, description, default_value, 
                    example_value, enum_values, schema_definition
                )
                VALUES (
                    %(endpoint_id)s, %(name)s, %(param_location)s, %(data_type)s, %(format)s,
                    %(required)s, %(deprecated)s, %(description)s, %(default_value)s,
                    %(example_value)s, %(enum_values)s, %(schema_definition)s
                )
            """, param_data)
            
            inserted_count += 1
            existing_params.add((param_name, param_location))
            
        except Exception as e:
            print(f"   ❌ Error inserting parameter {param_name}: {e}")
    
    print(f"   📊 Parameters processed: {inserted_count} inserted, {skipped_count} skipped")

def parse_parameters_upsert(cursor, parameters: List[Dict[str, Any]], endpoint_id: str):
    """
    Parse and upsert parameter information (INSERT or UPDATE on conflict).
    
    Args:
        cursor: Database cursor
        parameters: List of parameter definitions
        endpoint_id: UUID of the endpoint
    """
    if not parameters:
        return
    
    inserted_count = 0
    updated_count = 0
    
    for param in parameters:
        schema_info = param.get('schema', {})
        
        param_data = {
            'endpoint_id': endpoint_id,
            'name': param.get('name', ''),
            'param_location': param.get('in', ''),
            'data_type': schema_info.get('type', ''),
            'format': schema_info.get('format'),
            'required': param.get('required', False),
            'deprecated': param.get('deprecated', False),
            'description': param.get('description'),
            'default_value': str(schema_info.get('default')) if 'default' in schema_info else None,
            'example_value': str(param.get('example')) if 'example' in param else None,
            'enum_values': schema_info.get('enum', []),
            'schema_definition': json.dumps(schema_info)
        }
        
        try:
            # Use ON CONFLICT to handle duplicates gracefully
            cursor.execute("""
                INSERT INTO parameters (
                    endpoint_id, name, param_location, data_type, format, 
                    required, deprecated, description, default_value, 
                    example_value, enum_values, schema_definition
                )
                VALUES (
                    %(endpoint_id)s, %(name)s, %(param_location)s, %(data_type)s, %(format)s,
                    %(required)s, %(deprecated)s, %(description)s, %(default_value)s,
                    %(example_value)s, %(enum_values)s, %(schema_definition)s
                )
                ON CONFLICT (endpoint_id, name, param_location) 
                DO UPDATE SET
                    data_type = EXCLUDED.data_type,
                    format = EXCLUDED.format,
                    required = EXCLUDED.required,
                    deprecated = EXCLUDED.deprecated,
                    description = EXCLUDED.description,
                    default_value = EXCLUDED.default_value,
                    example_value = EXCLUDED.example_value,
                    enum_values = EXCLUDED.enum_values,
                    schema_definition = EXCLUDED.schema_definition
                RETURNING (xmax = 0) AS inserted
            """, param_data)
            
            result = cursor.fetchone()
            if result and result[0]:  # xmax = 0 means INSERT
                inserted_count += 1
            else:  # xmax > 0 means UPDATE
                updated_count += 1
                
        except Exception as e:
            print(f"   ❌ Error upserting parameter {param.get('name', 'unknown')}: {e}")
    
    print(f"   📊 Parameters processed: {inserted_count} inserted, {updated_count} updated")

# Example usage and testing
if __name__ == "__main__":
    print("🔧 Improved Parameter Parser")
    print("=" * 40)
    print("This module provides enhanced parameter parsing functions:")
    print("1. parse_parameters_improved() - Skip duplicates")
    print("2. parse_parameters_upsert() - INSERT or UPDATE on conflict")
    print()
    print("These functions prevent duplicate parameter issues by:")
    print("- Checking for existing parameters before insertion")
    print("- Using ON CONFLICT clauses for upsert operations")
    print("- Providing detailed logging of operations")
    print()
    print("To use in ApiPostgres.py, replace the parse_parameters method")
    print("with one of these improved versions.")
