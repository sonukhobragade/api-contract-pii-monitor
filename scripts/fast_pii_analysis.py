#!/usr/bin/env python3
"""
Fast PII Analysis for OpenAPI Schemas
Optimized version with batch processing and efficient database queries.
"""

import argparse
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
from core.openapi_querier import OpenAPIQuerier
from core.pii_detector import PIIDetector, PIIDetectionResult, create_pii_summary_report


class FastPIIAnalyzer:
    """Fast PII analyzer with optimized processing."""
    
    def __init__(self):
        """Initialize the fast PII analyzer."""
        self.config = Config()
        self.querier = OpenAPIQuerier(self.config.get_connection_string())
        self.pii_detector = PIIDetector()
        self.schema_cache = {}  # (api_id, component_name) -> definition
        # Paths where traversal stopped at MAX_DEPTH. Anything below them was
        # not analysed and must not be presented as clean.
        self.truncated_paths = []
        
        print("🚀 Fast PII Analyzer initialized with Schema Resolution")
        print(f"📊 Database: {self.config.DB_NAME} on {self.config.HOST}")
        
        # Display non-PII fields configuration
        non_pii_fields = os.environ.get('NON_PII_FIELDS', 'user_id,id,uuid')
        print(f"🔧 Non-PII fields configured: {non_pii_fields}")
        
        # Load all component schemas into cache
        self._load_schema_components()
    
    def _load_schema_components(self):
        """Load all schema components into cache for resolution."""
        import psycopg2.extras
        try:
            with self.querier.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT api_id, component_name, definition
                    FROM schema_components
                """)

                components = cursor.fetchall()
                for component in components:
                    schema_name = component['component_name']
                    schema_def = component['definition']

                    # Keyed by (api_id, name). The table's own constraint is
                    # UNIQUE(api_id, component_name, component_type), so two
                    # APIs sharing a component name is normal and expected.
                    # Keying on the name alone meant the last row loaded won,
                    # and a $ref could quietly resolve to a DIFFERENT API's
                    # schema — analysing the wrong fields and reporting the
                    # result as though it were this API's.
                    if isinstance(schema_def, dict):
                        self.schema_cache[(str(component['api_id']), schema_name)] = schema_def
                
                print(f"    📋 Loaded {len(self.schema_cache)} schema components for resolution")
        except Exception as e:
            print(f"    ⚠️ Warning: Could not load schema components: {e}")
    
    def _resolve_schema_ref(self, schema_ref: str,
                            api_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Resolve a schema reference to its definition, within one API.

        `api_id` scopes the lookup. Without it a reference can only be resolved
        when exactly one API defines that component name, and resolving it
        against another API's schema is worse than not resolving it at all: the
        analysis looks complete and describes the wrong thing.
        """
        if not schema_ref or not isinstance(schema_ref, str):
            return None

        if not schema_ref.startswith('#/components/schemas/'):
            return None

        component_name = schema_ref.replace('#/components/schemas/', '')

        if api_id is not None:
            return self.schema_cache.get((str(api_id), component_name))

        # No API given: only safe when the name is unambiguous.
        candidates = [
            definition for (cached_api, name), definition in self.schema_cache.items()
            if name == component_name
        ]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            print(f"      ⚠️ {component_name} is defined by {len(candidates)} APIs; "
                  f"cannot resolve without an api_id")
        return None
    
    # Depth beyond this is not walked. Deep payloads are ordinary, so the
    # limit is generous and, more importantly, no longer silent: truncation is
    # recorded on self.truncated_paths so a report can say the analysis stopped
    # rather than implying it finished and found nothing.
    MAX_DEPTH = 25

    def _extract_pii_from_schema(self, schema: Dict[str, Any], context: str, base_path: str = "", visited_refs: set = None, api_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extract PII fields from a resolved schema with recursion protection."""
        pii_fields = []
        
        if not isinstance(schema, dict):
            return pii_fields
        
        # Initialize visited refs to prevent infinite recursion
        if visited_refs is None:
            visited_refs = set()
        
        # Handle schema references with recursion protection
        if '$ref' in schema:
            ref = schema['$ref']
            if ref in visited_refs:
                return pii_fields  # Avoid infinite recursion
            
            visited_refs.add(ref)
            resolved_schema = self._resolve_schema_ref(ref, api_id)
            if resolved_schema:
                result = self._extract_pii_from_schema(resolved_schema, context, base_path, visited_refs, api_id)
                visited_refs.remove(ref)
                return result
            visited_refs.remove(ref)
            return pii_fields
        
        # Extract from properties
        if 'properties' in schema:
            for prop_name, prop_schema in schema['properties'].items():
                field_path = f"{base_path}.{prop_name}" if base_path else prop_name
                
                # Check if property name matches PII patterns
                pii_type = self.pii_detector._match_pii_pattern(prop_name)
                if pii_type:
                    pii_fields.append({
                        'field_name': prop_name,
                        'field_path': field_path,
                        'pii_type': pii_type.value,
                        'context': context,
                        'pattern_matched': prop_name
                    })
                
                # Recurse. The old limit was 5 dotted segments and said nothing
                # when it stopped, so PII nested below that was reported as
                # absent rather than as unexamined.
                if isinstance(prop_schema, dict):
                    if len(field_path.split('.')) < self.MAX_DEPTH:
                        nested_pii = self._extract_pii_from_schema(
                            prop_schema, context, field_path, visited_refs, api_id)
                        pii_fields.extend(nested_pii)
                    elif prop_schema.get('properties') or prop_schema.get('$ref'):
                        self.truncated_paths.append(field_path)
        
        return pii_fields
    
    def get_all_endpoints_batch(self, api_id: str) -> List[Dict[str, Any]]:
        """Get all endpoints with their details in a single optimized query."""
        import psycopg2.extras
        with self.querier.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    e.id as endpoint_id,
                    e.path,
                    e.method,
                    -- Get parameters as JSON array
                    COALESCE(
                        json_agg(
                            DISTINCT jsonb_build_object(
                                'name', p.name,
                                'data_type', p.data_type,
                                'description', p.description,
                                'location', p.param_location
                            )
                        ) FILTER (WHERE p.id IS NOT NULL),
                        '[]'::json
                    ) as parameters,
                    -- Get request body schema
                    (array_agg(rb.schema_definition))[1] as request_body_schema,
                    -- Get response schemas as JSON object
                    COALESCE(
                        json_object_agg(
                            r.status_code::text,
                            r.schema_definition
                        ) FILTER (WHERE r.id IS NOT NULL),
                        '{}'::json
                    ) as response_schemas
                FROM endpoints e
                LEFT JOIN parameters p ON e.id = p.endpoint_id
                LEFT JOIN request_bodies rb ON e.id = rb.endpoint_id
                LEFT JOIN responses r ON e.id = r.endpoint_id
                WHERE e.api_id = %s
                GROUP BY e.id, e.path, e.method
                ORDER BY e.path, e.method
            """, (api_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def analyze_endpoint_batch(self, endpoint_data: Dict[str, Any], api_id: str, api_title: str) -> PIIDetectionResult:
        """Analyze a single endpoint with pre-fetched data and schema resolution."""
        try:
            # Extract data
            endpoint_path = endpoint_data['path']
            http_method = endpoint_data['method']
            parameters = endpoint_data['parameters'] or []
            request_body_schema = endpoint_data['request_body_schema']
            response_schemas = endpoint_data['response_schemas'] or {}
            
            # First, analyze using the original PII detector
            result = self.pii_detector.analyze_endpoint_pii(
                api_id=api_id,
                api_title=api_title,
                endpoint_path=endpoint_path,
                http_method=http_method,
                parameters=parameters,
                request_body_schema=request_body_schema,
                response_schemas=response_schemas
            )
            
            # Now enhance with schema resolution for request body
            if request_body_schema and '$ref' in request_body_schema:
                schema_ref = request_body_schema['$ref']
                resolved_schema = self._resolve_schema_ref(schema_ref, api_id)
                if resolved_schema:
                    request_pii = self._extract_pii_from_schema(
                        resolved_schema,
                        'request_body_resolved',
                        "",  # No base path - start with schema properties directly
                        api_id=api_id,
                    )

                    # Add found PII to result
                    for pii_data in request_pii:
                        from core.pii_detector import PIIMatch, PIIType, PIISeverity
                        pii_type = PIIType(pii_data['pii_type'])
                        severity = self.pii_detector.severity_mapping[pii_type]
                        
                        match = PIIMatch(
                            pii_type=pii_type,
                            severity=severity,
                            field_name=pii_data['field_name'],
                            field_path=pii_data['field_path'],
                            context=pii_data['context'],
                            description="PII detected in resolved request body schema",
                            pattern_matched=pii_data['pattern_matched'],
                            confidence=1.0,
                            recommendations=self.pii_detector.pii_recommendations.get(pii_type, [])
                        )
                        
                        # Add to appropriate severity list
                        if severity == PIISeverity.CRITICAL:
                            result.critical_pii.append(match)
                        elif severity == PIISeverity.HIGH:
                            result.high_pii.append(match)
                        elif severity == PIISeverity.MEDIUM:
                            result.medium_pii.append(match)
                        elif severity == PIISeverity.LOW:
                            result.low_pii.append(match)
            
            # Enhance with schema resolution for response schemas
            for status_code, response_schema in response_schemas.items():
                if response_schema and '$ref' in response_schema:
                    resolved_schema = self._resolve_schema_ref(
                        response_schema['$ref'], api_id)
                    if resolved_schema:
                        response_pii = self._extract_pii_from_schema(
                            resolved_schema,
                            f'response_{status_code}_resolved',
                            "",  # No base path - start with schema properties directly
                            api_id=api_id,
                        )
                        
                        # Add found PII to result
                        for pii_data in response_pii:
                            from core.pii_detector import PIIMatch, PIIType, PIISeverity
                            pii_type = PIIType(pii_data['pii_type'])
                            severity = self.pii_detector.severity_mapping[pii_type]
                            
                            match = PIIMatch(
                                pii_type=pii_type,
                                severity=severity,
                                field_name=pii_data['field_name'],
                                field_path=pii_data['field_path'],
                                context=pii_data['context'],
                                description="PII detected in resolved response schema",
                                pattern_matched=pii_data['pattern_matched'],
                                confidence=1.0,
                                recommendations=self.pii_detector.pii_recommendations.get(pii_type, [])
                            )
                            
                            # Add to appropriate severity list
                            if severity == PIISeverity.CRITICAL:
                                result.critical_pii.append(match)
                            elif severity == PIISeverity.HIGH:
                                result.high_pii.append(match)
                            elif severity == PIISeverity.MEDIUM:
                                result.medium_pii.append(match)
                            elif severity == PIISeverity.LOW:
                                result.low_pii.append(match)
            
            # Recalculate totals and compliance score
            result.total_pii_found = (len(result.critical_pii) + len(result.high_pii) + 
                                    len(result.medium_pii) + len(result.low_pii))
            
            if result.total_pii_found > 0:
                # Recalculate compliance score based on new PII findings
                penalty = (len(result.critical_pii) * 20 + len(result.high_pii) * 15 + 
                          len(result.medium_pii) * 10 + len(result.low_pii) * 5)
                result.compliance_score = max(0, 100 - penalty)
            
            return result
            
        except Exception as e:
            print(f"      ⚠️ Error in enhanced analysis: {e}")
            # Fail closed: see PIIDetectionResult.failed. A bare result would
            # report this endpoint as clean with a compliance score of 100.
            return PIIDetectionResult.failed(
                api_id=api_id,
                api_title=api_title,
                endpoint_path=endpoint_data['path'],
                http_method=endpoint_data['method'],
                error=str(e),
            )
    
    def analyze_api_fast(self, api_id: str, api_title: str, max_workers: int = 4) -> List[PIIDetectionResult]:
        """
        Fast analysis of an API using batch processing and threading.
        
        Args:
            api_id: API identifier
            api_title: API title
            max_workers: Number of worker threads
            
        Returns:
            List of PII detection results
        """
        print(f"    🚀 Using batch processing with {max_workers} workers")
        
        # Get all endpoints with their data in one query
        start_time = time.time()
        endpoints_data = self.get_all_endpoints_batch(api_id)
        query_time = time.time() - start_time
        
        total_endpoints = len(endpoints_data)
        print(f"    📋 Fetched {total_endpoints} endpoints in {query_time:.2f}s")
        
        if not endpoints_data:
            return []
        
        results = []
        processed = 0
        
        # Process endpoints in parallel batches
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_endpoint = {
                executor.submit(self.analyze_endpoint_batch, endpoint_data, api_id, api_title): endpoint_data
                for endpoint_data in endpoints_data
            }
            
            # Process completed tasks
            for future in as_completed(future_to_endpoint):
                endpoint_data = future_to_endpoint[future]
                processed += 1
                
                # Progress update every 50 endpoints
                if processed % 50 == 0 or processed == total_endpoints:
                    progress = (processed / total_endpoints) * 100
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    print(f"    ⚡ [{processed:4d}/{total_endpoints}] {progress:5.1f}% complete | {rate:.1f} endpoints/sec")
                
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    endpoint_path = endpoint_data['path']
                    http_method = endpoint_data['method']
                    print(f"      ⚠️ Error analyzing {http_method} {endpoint_path}: {e}")
        
        total_time = time.time() - start_time
        print(f"    ✅ Completed {total_endpoints} endpoints in {total_time:.2f}s ({total_endpoints/total_time:.1f} eps)")
        
        return results
    
    def analyze_all_apis_fast(self, max_workers: int = 4) -> Dict[str, Any]:
        """
        Fast analysis of all APIs in the database.
        
        Args:
            max_workers: Number of worker threads per API
            
        Returns:
            Complete analysis results
        """
        print("\n🚀 Starting FAST comprehensive PII analysis...")
        overall_start = time.time()
        
        # Get all APIs
        apis = self.querier.get_latest_apis()
        if not apis:
            print("❌ No APIs found in database")
            return {"error": "No APIs found"}
        
        print(f"📋 Found {len(apis)} APIs to analyze")
        
        all_results = []
        api_summaries = {}
        
        for api_num, api in enumerate(apis, 1):
            api_id = api['id']
            api_title = api['title']
            
            print(f"\n📊 [{api_num}/{len(apis)}] Analyzing API: {api_title} (ID: {api_id[:8]}...)")
            
            # Fast analyze this API
            api_results = self.analyze_api_fast(api_id, api_title, max_workers)
            all_results.extend(api_results)
            
            # Create API summary
            if api_results:
                summary = create_pii_summary_report(api_results)
                api_summaries[api_id] = {
                    "title": api_title,
                    "endpoints_analyzed": len(api_results),
                    "total_pii_found": sum(r.total_pii_found for r in api_results),
                    "critical_pii": sum(len(r.critical_pii) for r in api_results),
                    "high_pii": sum(len(r.high_pii) for r in api_results),
                    "medium_pii": sum(len(r.medium_pii) for r in api_results),
                    "low_pii": sum(len(r.low_pii) for r in api_results),
                    "avg_compliance_score": summary["summary"]["average_compliance_score"]
                }
        
        # Create overall summary
        overall_summary = create_pii_summary_report(all_results)
        
        total_time = time.time() - overall_start
        print(f"\n🎉 FAST Analysis completed in {total_time:.2f}s!")
        print(f"⚡ Processed {len(all_results)} endpoints at {len(all_results)/total_time:.1f} endpoints/sec")
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(total_time, 2),
            "endpoints_per_second": round(len(all_results)/total_time, 1),
            "overall_summary": overall_summary,
            "api_summaries": api_summaries,
            "detailed_results": [self._serialize_result(r) for r in all_results]
        }
    
    def analyze_specific_api_fast(self, api_id: str, max_workers: int = 4) -> Dict[str, Any]:
        """
        Fast analysis of a specific API by ID.
        
        Args:
            api_id: API identifier
            max_workers: Number of worker threads
            
        Returns:
            Analysis results for the specific API
        """
        # Get API details
        apis = self.querier.get_latest_apis()
        api = None
        for a in apis:
            if a['id'] == api_id:
                api = a
                break
        
        if not api:
            return {"error": f"API with ID {api_id} not found"}
        
        api_title = api['title']
        print(f"\n🚀 Fast analyzing specific API: {api_title}")
        
        start_time = time.time()
        
        # Fast analyze the API
        results = self.analyze_api_fast(api_id, api_title, max_workers)
        
        # Create summary
        summary = create_pii_summary_report(results)
        
        total_time = time.time() - start_time
        
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(total_time, 2),
            "endpoints_per_second": round(len(results)/total_time, 1) if total_time > 0 else 0,
            "api_info": {
                "id": api_id,
                "title": api_title,
                "version": api.get('version', 'unknown')
            },
            "summary": summary,
            "detailed_results": [self._serialize_result(r) for r in results]
        }
    
    def _serialize_result(self, result: PIIDetectionResult) -> Dict[str, Any]:
        """Serialize PIIDetectionResult to dictionary."""
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
    
    def generate_fast_summary(self, analysis_results: Dict[str, Any]) -> None:
        """Generate a quick summary report."""
        print("\n" + "="*80)
        print("🚀 FAST PII ANALYSIS SUMMARY")
        print("="*80)
        
        if "error" in analysis_results:
            print(f"❌ Error: {analysis_results['error']}")
            return
        
        # Performance metrics
        processing_time = analysis_results.get("processing_time_seconds", 0)
        eps = analysis_results.get("endpoints_per_second", 0)
        print(f"⚡ Processing Time: {processing_time}s | Speed: {eps} endpoints/sec")
        
        # Overall summary
        overall = analysis_results.get("overall_summary", {})
        summary = overall.get("summary", {})
        
        print("\n📊 RESULTS SUMMARY")
        print(f"   Total Endpoints: {summary.get('total_endpoints_analyzed', 0)}")
        print(f"   Endpoints with PII: {summary.get('endpoints_with_pii', 0)}")
        print(f"   PII Exposure Rate: {summary.get('pii_exposure_rate', 0)}%")
        print(f"   Avg Compliance Score: {summary.get('average_compliance_score', 0)}%")
        
        # PII breakdown
        breakdown = overall.get("pii_breakdown", {})
        print("\n🔍 PII SEVERITY BREAKDOWN")
        print(f"   🔴 Critical: {breakdown.get('critical', 0)}")
        print(f"   🟡 High: {breakdown.get('high', 0)}")
        print(f"   🟠 Medium: {breakdown.get('medium', 0)}")
        print(f"   🟢 Low: {breakdown.get('low', 0)}")
        print(f"   📊 Total PII: {breakdown.get('total', 0)}")
        
        # Risk assessment
        risk = overall.get("risk_assessment", "Unknown")
        print(f"\n⚠️  RISK LEVEL: {risk}")
        
        # API summaries
        api_summaries = analysis_results.get("api_summaries", {})
        if api_summaries:
            print("\n📋 API BREAKDOWN")
            for api_id, summary in api_summaries.items():
                critical = summary['critical_pii']
                high = summary['high_pii']
                total = summary['total_pii_found']
                compliance = summary['avg_compliance_score']
                
                risk_icon = "🔴" if critical > 0 else "🟡" if high > 0 else "🟢"
                print(f"   {risk_icon} {summary['title']}: {total} PII ({critical}C/{high}H) - {compliance:.0f}% compliant")
        
        print("\n" + "="*80)
    
    def generate_detailed_pii_breakdown(self, analysis_results: Dict[str, Any]) -> None:
        """Generate detailed breakdown of PII by API, endpoint, and context."""
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
            
            endpoints_with_pii = [r for r in api_results if r["total_pii_found"] > 0]
            print(f"   📊 {len(endpoints_with_pii)} out of {len(api_results)} endpoints contain PII")
            
            for result in endpoints_with_pii:
                endpoint = f"{result['http_method']} {result['endpoint_path']}"
                total_pii = result["total_pii_found"]
                compliance = result["compliance_score"]
                
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
                    context = pii["context"].lower()
                    if "parameter" in context:
                        pii_by_context["parameters"].append(pii)
                    elif "request_body" in context or "request body" in context:
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
                        field_path = pii["field_path"]
                        if result['endpoint_path'] in field_path:
                            field_path = field_path.replace(f"{result['http_method']} {result['endpoint_path']}.", "")
                        print(f"         {severity_icon} {field_path} ({pii['pii_type']}) - {pii['severity']} risk")
                
                if pii_by_context["response"]:
                    print(f"      📥 RESPONSE BODY ({len(pii_by_context['response'])} PII found):")
                    for pii in pii_by_context["response"]:
                        severity_icon = self._get_severity_icon(pii["severity"])
                        field_path = pii["field_path"]
                        if result['endpoint_path'] in field_path:
                            field_path = field_path.replace(f"{result['http_method']} {result['endpoint_path']}.", "")
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
        """Generate summary of PII types found across all APIs."""
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


def main():
    """Main function to run fast PII analysis."""
    parser = argparse.ArgumentParser(description="Fast PII Analysis for OpenAPI Schemas")
    parser.add_argument(
        "--api-id",
        help="Analyze specific API by ID (optional)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of worker threads (default: 8)"
    )
    parser.add_argument(
        "--output-file",
        default="fast_pii_analysis_report.json",
        help="Output JSON filename (default: fast_pii_analysis_report.json)"
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
    parser.add_argument(
        "--non-pii-fields",
        help="Comma-separated list of fields to exclude from PII detection (e.g., user_id,payload.lobby.gameName)"
    )
    
    args = parser.parse_args()
    
    # Set environment variable for non-PII fields if provided
    if args.non_pii_fields:
        os.environ['NON_PII_FIELDS'] = args.non_pii_fields
        print(f"🔍 Excluding fields from PII detection: {args.non_pii_fields}")
    
    try:
        analyzer = FastPIIAnalyzer()
        
        # Run fast analysis
        if args.api_id:
            results = analyzer.analyze_specific_api_fast(args.api_id, args.workers)
        else:
            results = analyzer.analyze_all_apis_fast(args.workers)
        
        # Generate summary
        analyzer.generate_fast_summary(results)
        
        # Generate detailed reports if requested
        if args.detailed:
            analyzer.generate_detailed_pii_breakdown(results)
        
        if args.pii_summary:
            analyzer.generate_pii_summary_by_type(results)
        
        # Save JSON report
        try:
            with open(args.output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"📄 JSON report saved to: {args.output_file}")
        except Exception as e:
            print(f"❌ Error saving JSON report: {e}")
        
        # Exit codes for CI/CD integration
        if "error" in results:
            sys.exit(1)
        
        # Check for critical PII
        overall = results.get("overall_summary", {})
        breakdown = overall.get("pii_breakdown", {})
        if breakdown.get("critical", 0) > 0:
            print("🚨 Critical PII detected - requires immediate attention!")
            sys.exit(2)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
