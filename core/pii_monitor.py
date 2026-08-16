"""
PII Monitoring Integration Module

This module integrates PII detection with the existing schema monitoring system.
It provides continuous monitoring of PII exposure across API changes and generates
alerts when new PII is introduced or existing PII exposure increases.

Features:
- Integration with existing schema monitoring
- PII change detection between API versions
- Slack notifications for PII alerts
- Jenkins reporting integration
- Compliance tracking over time

Author: Contract Testing Framework
Date: 2025-01-20
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .pii_detector import PIIDetector, PIIDetectionResult, PIISeverity, create_pii_summary_report
from .config import Config

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class PIIChangeResult:
    """Results of PII change analysis between API versions."""
    
    api_id: str
    api_title: str
    old_version_id: Optional[str]
    new_version_id: str
    
    # PII change metrics
    new_pii_introduced: int = 0
    pii_removed: int = 0
    pii_severity_increased: int = 0
    pii_severity_decreased: int = 0
    
    # Detailed changes
    new_critical_pii: List[str] = field(default_factory=list)
    new_high_pii: List[str] = field(default_factory=list)
    removed_pii: List[str] = field(default_factory=list)
    
    # Compliance impact
    compliance_score_change: float = 0.0
    overall_risk_change: str = "NO_CHANGE"
    
    # Recommendations
    urgent_actions: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class PIIMonitor:
    """
    PII monitoring system that integrates with schema change detection.
    
    Monitors PII exposure across API versions and provides alerts when
    privacy risks increase or new PII is introduced.
    """
    
    def __init__(self, config: Config):
        """
        Initialize PII monitor.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.pii_detector = PIIDetector()
        
        logger.info("PII Monitor initialized")
    
    def analyze_pii_changes(
        self,
        api_id: str,
        api_title: str,
        old_version_id: Optional[str],
        new_version_id: str,
        old_endpoints: List[Dict[str, Any]],
        new_endpoints: List[Dict[str, Any]]
    ) -> PIIChangeResult:
        """
        Analyze PII changes between two API versions.
        
        Args:
            api_id: API identifier
            api_title: API title
            old_version_id: Old version ID (None for new API)
            new_version_id: New version ID
            old_endpoints: Old version endpoints
            new_endpoints: New version endpoints
            
        Returns:
            PII change analysis result
        """
        logger.info(f"Analyzing PII changes for API {api_title}")
        
        result = PIIChangeResult(
            api_id=api_id,
            api_title=api_title,
            old_version_id=old_version_id,
            new_version_id=new_version_id
        )
        
        # Analyze old version PII (if exists)
        old_pii_results = []
        if old_endpoints:
            old_pii_results = self._analyze_endpoints_pii(
                api_id, api_title, old_endpoints
            )
        
        # Analyze new version PII
        new_pii_results = self._analyze_endpoints_pii(
            api_id, api_title, new_endpoints
        )
        
        # Compare PII between versions
        if old_pii_results:
            self._compare_pii_results(result, old_pii_results, new_pii_results)
        else:
            # New API - all PII is "new"
            self._analyze_new_api_pii(result, new_pii_results)
        
        # Generate recommendations
        self._generate_pii_recommendations(result, new_pii_results)
        
        logger.info(f"PII analysis complete: {result.new_pii_introduced} new PII found")
        
        return result
    
    def _analyze_endpoints_pii(
        self,
        api_id: str,
        api_title: str,
        endpoints: List[Dict[str, Any]]
    ) -> List[PIIDetectionResult]:
        """
        Analyze PII in a list of endpoints.
        
        Args:
            api_id: API identifier
            api_title: API title
            endpoints: List of endpoint data
            
        Returns:
            List of PII detection results
        """
        results = []
        
        for endpoint in endpoints:
            # Extract endpoint information
            endpoint_path = endpoint.get('path', '')
            http_method = endpoint.get('method', 'GET')
            parameters = endpoint.get('parameters', [])
            
            # Extract schemas
            request_body_schema = None
            if 'request_body' in endpoint and endpoint['request_body']:
                try:
                    request_body_schema = json.loads(
                        endpoint['request_body'].get('schema_definition')
                        or endpoint['request_body'].get('schema') or '{}')
                except (json.JSONDecodeError, TypeError):
                    request_body_schema = None
            
            response_schemas = {}
            for response in endpoint.get('responses', []):
                status_code = response.get('status_code', 'default')
                try:
                    response_schema = json.loads(
                        response.get('schema_definition')
                        or response.get('schema') or '{}')
                    response_schemas[status_code] = response_schema
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Analyze endpoint for PII
            pii_result = self.pii_detector.analyze_endpoint_pii(
                api_id=api_id,
                api_title=api_title,
                endpoint_path=endpoint_path,
                http_method=http_method,
                parameters=parameters,
                request_body_schema=request_body_schema,
                response_schemas=response_schemas
            )
            
            results.append(pii_result)
        
        return results
    
    def _compare_pii_results(
        self,
        result: PIIChangeResult,
        old_results: List[PIIDetectionResult],
        new_results: List[PIIDetectionResult]
    ) -> None:
        """
        Compare PII results between versions.
        
        Args:
            result: PII change result to populate
            old_results: Old version PII results
            new_results: New version PII results
        """
        # Create PII maps for comparison
        old_pii_map = self._create_pii_map(old_results)
        new_pii_map = self._create_pii_map(new_results)
        
        # Calculate compliance scores
        old_summary = create_pii_summary_report(old_results)
        new_summary = create_pii_summary_report(new_results)
        
        old_compliance = old_summary["summary"]["average_compliance_score"]
        new_compliance = new_summary["summary"]["average_compliance_score"]
        result.compliance_score_change = new_compliance - old_compliance
        
        # Find new PII
        for endpoint_key, new_pii in new_pii_map.items():
            old_pii = old_pii_map.get(endpoint_key, set())
            
            new_pii_items = new_pii - old_pii
            if new_pii_items:
                result.new_pii_introduced += len(new_pii_items)
                
                # Categorize by severity
                for pii_item in new_pii_items:
                    pii_type, severity, field_name = pii_item
                    if severity == PIISeverity.CRITICAL.value:
                        result.new_critical_pii.append(f"{endpoint_key}: {field_name} ({pii_type})")
                    elif severity == PIISeverity.HIGH.value:
                        result.new_high_pii.append(f"{endpoint_key}: {field_name} ({pii_type})")
        
        # Find removed PII
        for endpoint_key, old_pii in old_pii_map.items():
            new_pii = new_pii_map.get(endpoint_key, set())
            
            removed_pii_items = old_pii - new_pii
            if removed_pii_items:
                result.pii_removed += len(removed_pii_items)
                for pii_item in removed_pii_items:
                    pii_type, severity, field_name = pii_item
                    result.removed_pii.append(f"{endpoint_key}: {field_name} ({pii_type})")
        
        # Determine overall risk change
        old_breakdown = old_summary["pii_breakdown"]
        new_breakdown = new_summary["pii_breakdown"]
        
        if new_breakdown["critical"] > old_breakdown["critical"]:
            result.overall_risk_change = "INCREASED_CRITICAL"
        elif new_breakdown["high"] > old_breakdown["high"]:
            result.overall_risk_change = "INCREASED_HIGH"
        elif result.new_pii_introduced > 0:
            result.overall_risk_change = "INCREASED"
        elif result.pii_removed > 0:
            result.overall_risk_change = "DECREASED"
        else:
            result.overall_risk_change = "NO_CHANGE"
    
    def _analyze_new_api_pii(
        self,
        result: PIIChangeResult,
        new_results: List[PIIDetectionResult]
    ) -> None:
        """
        Analyze PII for a new API (no previous version).
        
        Args:
            result: PII change result to populate
            new_results: New API PII results
        """
        summary = create_pii_summary_report(new_results)
        breakdown = summary["pii_breakdown"]
        
        result.new_pii_introduced = breakdown["total"]
        result.compliance_score_change = summary["summary"]["average_compliance_score"] - 100.0
        
        # Categorize new PII
        for pii_result in new_results:
            endpoint_key = f"{pii_result.http_method} {pii_result.endpoint_path}"
            
            for match in pii_result.critical_pii:
                result.new_critical_pii.append(f"{endpoint_key}: {match.field_name} ({match.pii_type.value})")
            
            for match in pii_result.high_pii:
                result.new_high_pii.append(f"{endpoint_key}: {match.field_name} ({match.pii_type.value})")
        
        # Set risk change
        if breakdown["critical"] > 0:
            result.overall_risk_change = "NEW_CRITICAL"
        elif breakdown["high"] > 0:
            result.overall_risk_change = "NEW_HIGH"
        elif breakdown["total"] > 0:
            result.overall_risk_change = "NEW_PII"
        else:
            result.overall_risk_change = "NO_PII"
    
    def _create_pii_map(self, results: List[PIIDetectionResult]) -> Dict[str, set]:
        """
        Create a map of endpoint -> PII items for comparison.
        
        Args:
            results: List of PII detection results
            
        Returns:
            Dictionary mapping endpoint keys to sets of PII items
        """
        pii_map = {}
        
        for result in results:
            endpoint_key = f"{result.http_method} {result.endpoint_path}"
            pii_items = set()
            
            # Add all PII matches
            all_matches = (result.critical_pii + result.high_pii + 
                          result.medium_pii + result.low_pii)
            
            for match in all_matches:
                pii_item = (
                    match.pii_type.value,
                    match.severity.value,
                    match.field_name
                )
                pii_items.add(pii_item)
            
            pii_map[endpoint_key] = pii_items
        
        return pii_map
    
    def _generate_pii_recommendations(
        self,
        result: PIIChangeResult,
        new_results: List[PIIDetectionResult]
    ) -> None:
        """
        Generate PII-specific recommendations.
        
        Args:
            result: PII change result to populate
            new_results: New version PII results
        """
        # Urgent actions for critical PII
        if result.new_critical_pii:
            result.urgent_actions.extend([
                "🔴 URGENT: Review all new critical PII exposures immediately",
                "Implement data encryption for all critical PII fields",
                "Conduct security audit of affected endpoints",
                "Update privacy policies and consent mechanisms"
            ])
        
        # High priority actions
        if result.new_high_pii:
            result.urgent_actions.extend([
                "🟡 HIGH: Implement enhanced security for new high-risk PII",
                "Review data retention policies for affected fields",
                "Consider data minimization strategies"
            ])
        
        # General recommendations
        if result.new_pii_introduced > 0:
            result.recommendations.extend([
                "📋 Update data protection impact assessment (DPIA)",
                "🔒 Implement privacy by design principles",
                "📚 Provide privacy training for development teams",
                "⚖️ Ensure compliance with applicable privacy regulations",
                "🔍 Establish regular PII monitoring and auditing"
            ])
        
        # Positive changes
        if result.pii_removed > 0:
            result.recommendations.append(
                f"✅ Good: {result.pii_removed} PII fields were removed, reducing privacy risk"
            )
        
        # Compliance score changes
        if result.compliance_score_change < -10:
            result.urgent_actions.append(
                f"📊 URGENT: Compliance score decreased by {abs(result.compliance_score_change):.1f}%"
            )
        elif result.compliance_score_change > 10:
            result.recommendations.append(
                f"📈 Good: Compliance score improved by {result.compliance_score_change:.1f}%"
            )
    
    def create_pii_slack_message(self, result: PIIChangeResult) -> Dict[str, Any]:
        """
        Create Slack message for PII monitoring results.
        
        Args:
            result: PII change result
            
        Returns:
            Slack message payload
        """
        # Determine message color and icon
        if result.new_critical_pii:
            color = "#FF0000"  # Red
            icon = "🔴"
            urgency = "CRITICAL"
        elif result.new_high_pii:
            color = "#FFA500"  # Orange
            icon = "🟡"
            urgency = "HIGH"
        elif result.new_pii_introduced > 0:
            color = "#FFFF00"  # Yellow
            icon = "🟠"
            urgency = "MEDIUM"
        elif result.pii_removed > 0:
            color = "#00FF00"  # Green
            icon = "✅"
            urgency = "IMPROVED"
        else:
            color = "#808080"  # Gray
            icon = "ℹ️"
            urgency = "NO_CHANGE"
        
        # Create message
        message = {
            "text": f"{icon} PII Monitoring Alert - {urgency}",
            "attachments": [
                {
                    "color": color,
                    "fields": [
                        {
                            "title": "API Information",
                            "value": f"📊 *{result.api_title}*\nID: `{result.api_id}`",
                            "short": True
                        },
                        {
                            "title": "PII Changes",
                            "value": (
                                f"🆕 New PII: {result.new_pii_introduced}\n"
                                f"🗑️ Removed PII: {result.pii_removed}\n"
                                f"📊 Compliance Change: {result.compliance_score_change:+.1f}%"
                            ),
                            "short": True
                        }
                    ]
                }
            ]
        }
        
        # Add critical PII details
        if result.new_critical_pii:
            critical_text = "\n".join(f"• {pii}" for pii in result.new_critical_pii[:5])
            if len(result.new_critical_pii) > 5:
                critical_text += f"\n... and {len(result.new_critical_pii) - 5} more"
            
            message["attachments"][0]["fields"].append({
                "title": "🔴 New Critical PII",
                "value": critical_text,
                "short": False
            })
        
        # Add high-risk PII details
        if result.new_high_pii:
            high_text = "\n".join(f"• {pii}" for pii in result.new_high_pii[:3])
            if len(result.new_high_pii) > 3:
                high_text += f"\n... and {len(result.new_high_pii) - 3} more"
            
            message["attachments"][0]["fields"].append({
                "title": "🟡 New High-Risk PII",
                "value": high_text,
                "short": False
            })
        
        # Add urgent actions
        if result.urgent_actions:
            actions_text = "\n".join(f"• {action}" for action in result.urgent_actions[:3])
            message["attachments"][0]["fields"].append({
                "title": "⚡ Urgent Actions Required",
                "value": actions_text,
                "short": False
            })
        
        return message
    
    def create_pii_jenkins_report(self, result: PIIChangeResult) -> str:
        """
        Create Jenkins report for PII monitoring results.
        
        Args:
            result: PII change result
            
        Returns:
            Jenkins report text
        """
        report_lines = [
            "=" * 60,
            "PII MONITORING REPORT",
            "=" * 60,
            "",
            f"API: {result.api_title}",
            f"API ID: {result.api_id}",
            f"Analysis Time: {datetime.now().isoformat()}",
            "",
            "PII CHANGE SUMMARY:",
            f"  New PII Introduced: {result.new_pii_introduced}",
            f"  PII Removed: {result.pii_removed}",
            f"  Compliance Score Change: {result.compliance_score_change:+.1f}%",
            f"  Overall Risk Change: {result.overall_risk_change}",
            ""
        ]
        
        # Add critical PII details
        if result.new_critical_pii:
            report_lines.extend([
                "🔴 NEW CRITICAL PII:",
                *[f"  • {pii}" for pii in result.new_critical_pii],
                ""
            ])
        
        # Add high-risk PII details
        if result.new_high_pii:
            report_lines.extend([
                "🟡 NEW HIGH-RISK PII:",
                *[f"  • {pii}" for pii in result.new_high_pii],
                ""
            ])
        
        # Add removed PII
        if result.removed_pii:
            report_lines.extend([
                "✅ REMOVED PII:",
                *[f"  • {pii}" for pii in result.removed_pii],
                ""
            ])
        
        # Add urgent actions
        if result.urgent_actions:
            report_lines.extend([
                "⚡ URGENT ACTIONS REQUIRED:",
                *[f"  • {action}" for action in result.urgent_actions],
                ""
            ])
        
        # Add recommendations
        if result.recommendations:
            report_lines.extend([
                "💡 RECOMMENDATIONS:",
                *[f"  • {rec}" for rec in result.recommendations],
                ""
            ])
        
        report_lines.extend([
            "=" * 60,
            "END OF PII MONITORING REPORT",
            "=" * 60
        ])
        
        return "\n".join(report_lines)
    
    def should_alert_pii_changes(self, result: PIIChangeResult) -> bool:
        """
        Determine if PII changes warrant an alert.
        
        Args:
            result: PII change result
            
        Returns:
            True if alert should be sent
        """
        # Always alert for critical PII
        if result.new_critical_pii:
            return True
        
        # Alert for significant high-risk PII
        if len(result.new_high_pii) >= 3:
            return True
        
        # Alert for significant compliance score decrease
        if result.compliance_score_change <= -15:
            return True
        
        # Alert for any new PII in production environments
        # (This would be configurable based on environment)
        if result.new_pii_introduced > 0:
            return True
        
        return False
