"""
Endpoint Statistics Module

Handles collection and management of endpoint statistics for schema monitoring.
"""
from typing import Dict, Any
from core.openapi_querier import OpenAPIQuerier


class EndpointStatisticsCollector:
    """Collects and manages endpoint statistics for monitored APIs."""
    
    def __init__(self, querier: OpenAPIQuerier):
        """
        Initialize the endpoint statistics collector.
        
        Args:
            querier (OpenAPIQuerier): Database querier instance
        """
        self.querier = querier
    
    def collect_api_endpoint_statistics(self) -> Dict[str, Any]:
        """
        Collect endpoint statistics for all monitored APIs.
        
        Returns:
            Dict[str, Any]: Statistics including total endpoints and per-API breakdown
        """
        try:
            print("\n📊 Collecting endpoint statistics for showcase...")
            
            # Get all latest APIs
            latest_apis = self.querier.get_latest_apis()
            total_endpoints = 0
            api_endpoint_details = []
            
            for api in latest_apis:
                # Get endpoint count for this API
                endpoints = self.querier.search_endpoints(api_id=api['id'])
                endpoint_count = len(endpoints)
                total_endpoints += endpoint_count
                
                api_detail = {
                    'api_title': api['title'],
                    'api_id': api['id'],
                    'endpoint_count': endpoint_count,
                    'version': api['version']
                }
                
                api_endpoint_details.append(api_detail)
                print(f"   📍 {api['title']}: {endpoint_count} endpoints")
            
            print(f"   🔢 Total endpoints across all APIs: {total_endpoints}")
            
            return {
                'total_endpoints_monitored': total_endpoints,
                'api_endpoint_details': api_endpoint_details
            }
            
        except Exception as e:
            print(f"   ⚠️  Error collecting endpoint statistics: {str(e)}")
            # Return empty statistics on error
            return {
                'total_endpoints_monitored': 0,
                'api_endpoint_details': []
            }
    
    def format_endpoint_showcase(self, statistics: Dict[str, Any]) -> str:
        """
        Format endpoint statistics for display.
        
        Args:
            statistics (Dict[str, Any]): Endpoint statistics
            
        Returns:
            str: Formatted showcase string
        """
        showcase_lines = []
        
        for api_detail in statistics.get('api_endpoint_details', []):
            showcase_lines.append(f"📍 {api_detail['api_title']}: {api_detail['endpoint_count']} endpoints")
        
        if showcase_lines:
            showcase_lines.append(f"🔢 **Total Endpoints Monitored: {statistics.get('total_endpoints_monitored', 0)}**")
            return "\n".join(showcase_lines)
        else:
            return "Endpoint statistics not available"
    
    def create_jenkins_endpoint_showcase_file(self, statistics: Dict[str, Any], filename: str = 'jenkins_endpoint_showcase.txt'):
        """
        Create Jenkins endpoint showcase file.
        
        Args:
            statistics (Dict[str, Any]): Endpoint statistics
            filename (str): Output filename
        """
        with open(filename, 'w') as f:
            f.write("ENDPOINT COVERAGE SHOWCASE\n")
            f.write("=" * 30 + "\n")
            
            for api_detail in statistics.get('api_endpoint_details', []):
                f.write(f"API: {api_detail['api_title']}\n")
                f.write(f"   ID: {api_detail['api_id']}\n")
                f.write(f"   Total Endpoints: {api_detail['endpoint_count']}\n\n")
            
            f.write(f"TOTAL ENDPOINTS ACROSS ALL APIs: {statistics.get('total_endpoints_monitored', 0)}\n")
