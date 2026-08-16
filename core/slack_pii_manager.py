"""
Slack PII Manager Module

Handles Slack notifications specifically for PII analysis reports with proper formatting
for critical API calls and PII data found in requests, responses, parameters, and schemas.
"""
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from core.config import Config


class SlackPIIManager:
    """Manages Slack notifications for PII analysis reports."""
    
    def __init__(self):
        """Initialize the Slack PII manager."""
        self.config = Config()
        self.webhook_url = self.config.SLACK_WEBHOOK_URL
        self.bot_token = self.config.SLACK_TOKEN
        self.channel_id = self.config.CHANNEL_ID
        
        # Determine which method to use
        if self.bot_token and self.channel_id:
            self.use_bot_token = True
            print(f"🤖 Using Slack Bot Token with channel ID: {self.channel_id}")
        # elif self.webhook_url and self.webhook_url != 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL':
        #     self.use_bot_token = False
        #     print("🔗 Using Slack Webhook (limited to one channel)")
        else:
            self.use_bot_token = False
            print("⚠️  No Slack configuration found")
        
    def send_pii_analysis_report(self, analysis_results: Dict[str, Any]) -> bool:
        """
        Send comprehensive PII analysis report to Slack.
        
        Args:
            analysis_results: Results from fast_pii_analysis
            
        Returns:
            bool: True if notification sent successfully, False otherwise
        """
        print("\n📱 Sending PII Analysis Report to Slack...")
        
        try:
            # Check if Slack is configured
            if not self.use_bot_token and not self.webhook_url:
                print("   ⚠️  Slack not configured - skipping notifications")
                return False
            
            # Create comprehensive PII report blocks
            message_blocks = self._create_pii_report_blocks(analysis_results)
            
            # Send the message using appropriate method
            if self.use_bot_token:
                return self._send_with_bot_token(message_blocks)
            else:
                return self._send_with_webhook(message_blocks)
                
        except Exception as e:
            print(f"   ❌ Error sending PII report: {str(e)}")
            return False
    
    def _send_with_bot_token(self, message_blocks: List[Dict[str, Any]]) -> bool:
        """Send message using bot token."""
        try:
            payload = {
                "channel": self.channel_id,
                "blocks": message_blocks,
                "username": "PII Security Bot",
                "icon_emoji": "🔒"
            }
            
            response = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self.bot_token}"},
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    print(f"   ✅ PII Analysis report sent successfully to Slack (Channel: {self.channel_id})")
                    return True
                else:
                    print(f"   ❌ Slack API Error: {data.get('error')}")
                    return False
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error sending with bot token: {e}")
            return False
    
    def _send_with_webhook(self, message_blocks: List[Dict[str, Any]]) -> bool:
        """Send message using webhook."""
        try:
            message = {
                "blocks": message_blocks,
                "username": "PII Security Bot",
                "icon_emoji": "🔒"
            }
            
            response = requests.post(self.webhook_url, json=message, timeout=30)
            
            if response.status_code == 200:
                print("   ✅ PII Analysis report sent successfully to Slack")
                return True
            else:
                print(f"   ❌ Failed to send PII report: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error sending with webhook: {e}")
            return False
    
    def _create_pii_report_blocks(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create comprehensive Slack blocks for PII analysis report.
        
        Args:
            analysis_results: Results from fast_pii_analysis
            
        Returns:
            List of Slack message blocks
        """
        blocks = []
        
        # Block 1: Header with critical alert
        header_block = self._create_header_block(analysis_results)
        blocks.append(header_block)
        
        # Block 2: Executive Summary
        summary_block = self._create_summary_block(analysis_results)
        blocks.append(summary_block)
        
        # Block 3: Critical PII Findings
        critical_block = self._create_critical_pii_block(analysis_results)
        if critical_block:
            blocks.append(critical_block)
        
        # Block 4: API Breakdown
        api_breakdown_block = self._create_api_breakdown_block(analysis_results)
        if api_breakdown_block:
            blocks.append(api_breakdown_block)
        
        # Block 5: Detailed PII Analysis
        detailed_blocks = self._create_detailed_pii_blocks(analysis_results)
        blocks.extend(detailed_blocks)
        
        # Block 6: Recommendations
        recommendations_block = self._create_recommendations_block(analysis_results)
        if recommendations_block:
            blocks.append(recommendations_block)
        
        return blocks
    
    def _create_header_block(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create header block with critical alert."""
        # Determine severity level
        overall = analysis_results.get("overall_summary", {})
        breakdown = overall.get("pii_breakdown", {})
        critical_count = breakdown.get("critical", 0)
        high_count = breakdown.get("high", 0)
        
        if critical_count > 0:
            title = "🚨 CRITICAL PII SECURITY ALERT"
            _color = "#FF0000"  # Red
        elif high_count > 0:
            title = "⚠️ HIGH-RISK PII DETECTED"
            _color = "#FFA500"  # Orange
        else:
            title = "🔍 PII ANALYSIS COMPLETE"
            _color = "#00AA00"  # Green
        
        _timestamp = datetime.fromisoformat(analysis_results.get("analysis_timestamp", datetime.now().isoformat())).strftime("%B %d, %Y at %I:%M %p")
        
        return {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title
            }
        }
    
    def _create_summary_block(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create executive summary block."""
        overall = analysis_results.get("overall_summary", {})
        summary = overall.get("summary", {})
        breakdown = overall.get("pii_breakdown", {})
        
        total_endpoints = summary.get("total_endpoints_analyzed", 0)
        endpoints_with_pii = summary.get("endpoints_with_pii", 0)
        avg_compliance = summary.get("average_compliance_score", 0)
        
        critical = breakdown.get("critical", 0)
        high = breakdown.get("high", 0)
        medium = breakdown.get("medium", 0)
        low = breakdown.get("low", 0)
        total_pii = breakdown.get("total", 0)
        
        processing_time = analysis_results.get("processing_time_seconds", 0)
        eps = analysis_results.get("endpoints_per_second", 0)
        
        summary_text = "*📊 EXECUTIVE SUMMARY*\n\n"
        summary_text += f"• *Total Endpoints Analyzed:* {total_endpoints}\n"
        summary_text += f"• *Endpoints with PII:* {endpoints_with_pii} ({endpoints_with_pii/total_endpoints*100:.1f}%)\n"
        summary_text += f"• *Average Compliance Score:* {avg_compliance:.1f}%\n"
        summary_text += f"• *Processing Time:* {processing_time}s ({eps:.1f} endpoints/sec)\n\n"
        
        summary_text += "*🔍 PII BREAKDOWN:*\n"
        summary_text += f"• 🔴 Critical: {critical}\n"
        summary_text += f"• 🟡 High: {high}\n"
        summary_text += f"• 🟠 Medium: {medium}\n"
        summary_text += f"• 🟢 Low: {low}\n"
        summary_text += f"• *Total PII Found:* {total_pii}\n"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": summary_text
            }
        }
    
    def _create_critical_pii_block(self, analysis_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create block highlighting critical PII findings."""
        detailed_results = analysis_results.get("detailed_results", [])
        critical_endpoints = []
        
        for result in detailed_results:
            if result.get("critical_pii"):
                critical_endpoints.append({
                    "api_title": result["api_title"],
                    "endpoint": f"{result['http_method']} {result['endpoint_path']}",
                    "critical_count": len(result["critical_pii"]),
                    "pii_details": result["critical_pii"]
                })
        
        if not critical_endpoints:
            return None
        
        # Sort by critical PII count
        critical_endpoints.sort(key=lambda x: x["critical_count"], reverse=True)
        
        critical_text = "*🚨 CRITICAL PII FINDINGS*\n\n"
        critical_text += f"*{len(critical_endpoints)} endpoints contain critical PII:*\n\n"
        
        for endpoint in critical_endpoints[:5]:  # Show top 5
            critical_text += f"• *{endpoint['endpoint']}*\n"
            critical_text += f"  API: {endpoint['api_title']}\n"
            critical_text += f"  Critical PII: {endpoint['critical_count']} instances\n"
            
            # Show PII types found
            pii_types = set()
            for pii in endpoint["pii_details"]:
                pii_types.add(pii["pii_type"])
            
            critical_text += f"  Types: {', '.join(pii_types)}\n\n"
        
        if len(critical_endpoints) > 5:
            critical_text += f"*... and {len(critical_endpoints) - 5} more critical endpoints*\n"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": critical_text
            }
        }
    
    def _create_api_breakdown_block(self, analysis_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create block showing PII breakdown by API."""
        api_summaries = analysis_results.get("api_summaries", {})
        
        if not api_summaries:
            return None
        
        # Sort APIs by critical PII count
        sorted_apis = sorted(
            api_summaries.items(),
            key=lambda x: (x[1]["critical_pii"], x[1]["high_pii"]),
            reverse=True
        )
        
        api_text = "*📋 API BREAKDOWN*\n\n"
        
        for api_id, summary in sorted_apis[:5]:  # Show top 5
            api_title = summary["title"]
            critical = summary["critical_pii"]
            high = summary["high_pii"]
            total = summary["total_pii_found"]
            compliance = summary["avg_compliance_score"]
            endpoints = summary["endpoints_analyzed"]
            
            # Risk indicator
            if critical > 0:
                risk_icon = "🔴"
                risk_level = "CRITICAL"
            elif high > 0:
                risk_icon = "🟡"
                risk_level = "HIGH"
            else:
                risk_icon = "🟢"
                risk_level = "LOW"
            
            api_text += f"{risk_icon} *{api_title}*\n"
            api_text += f"  • Risk Level: {risk_level}\n"
            api_text += f"  • Endpoints: {endpoints}\n"
            api_text += f"  • PII Found: {total} ({critical}C/{high}H)\n"
            api_text += f"  • Compliance: {compliance:.1f}%\n\n"
        
        if len(sorted_apis) > 5:
            api_text += f"*... and {len(sorted_apis) - 5} more APIs*\n"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": api_text
            }
        }
    
    def _create_detailed_pii_blocks(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create detailed blocks showing PII by context (request, response, parameters)."""
        detailed_results = analysis_results.get("detailed_results", [])
        blocks = []
        
        # Group PII by context
        pii_by_context = {
            "request_body": [],
            "response": [],
            "parameters": [],
            "other": []
        }
        
        for result in detailed_results:
            if result["total_pii_found"] == 0:
                continue
                
            endpoint_key = f"{result['api_title']} - {result['http_method']} {result['endpoint_path']}"
            
            # Collect all PII matches
            all_pii = (result["critical_pii"] + result["high_pii"] + 
                      result["medium_pii"] + result["low_pii"])
            
            for pii in all_pii:
                context = pii["context"].lower()
                pii_info = {
                    "endpoint": endpoint_key,
                    "pii_type": pii["pii_type"],
                    "severity": pii["severity"],
                    "field_name": pii["field_name"],
                    "field_path": pii["field_path"],
                    "description": pii["description"]
                }
                
                if "request_body" in context:
                    pii_by_context["request_body"].append(pii_info)
                elif "response" in context:
                    pii_by_context["response"].append(pii_info)
                elif "parameter" in context:
                    pii_by_context["parameters"].append(pii_info)
                else:
                    pii_by_context["other"].append(pii_info)
        
        # Create blocks for each context
        if pii_by_context["request_body"]:
            blocks.append(self._create_context_block("📤 REQUEST BODY PII", pii_by_context["request_body"]))
        
        if pii_by_context["response"]:
            blocks.append(self._create_context_block("📥 RESPONSE BODY PII", pii_by_context["response"]))
        
        if pii_by_context["parameters"]:
            blocks.append(self._create_context_block("📋 PARAMETER PII", pii_by_context["parameters"]))
        
        return blocks
    
    def _create_context_block(self, title: str, pii_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a block for PII in a specific context."""
        # Sort by severity and limit to top findings
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_pii = sorted(pii_list, key=lambda x: (severity_order.get(x["severity"], 4), x["pii_type"]))
        
        context_text = f"*{title}*\n\n"
        
        # Group by endpoint for better organization
        endpoint_groups = {}
        for pii in sorted_pii[:10]:  # Limit to top 10
            endpoint = pii["endpoint"]
            if endpoint not in endpoint_groups:
                endpoint_groups[endpoint] = []
            endpoint_groups[endpoint].append(pii)
        
        for endpoint, pii_items in endpoint_groups.items():
            context_text += f"*{endpoint}*\n"
            
            for pii in pii_items:
                severity_icon = self._get_severity_icon(pii["severity"])
                context_text += f"  {severity_icon} {pii['field_name']} ({pii['pii_type']})\n"
                context_text += f"    Path: {pii['field_path']}\n"
            
            context_text += "\n"
        
        if len(sorted_pii) > 10:
            context_text += f"*... and {len(sorted_pii) - 10} more PII instances*\n"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": context_text
            }
        }
    
    def _create_recommendations_block(self, analysis_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create block with security recommendations."""
        overall = analysis_results.get("overall_summary", {})
        breakdown = overall.get("pii_breakdown", {})
        _risk_assessment = overall.get("risk_assessment", "Unknown")
        
        critical = breakdown.get("critical", 0)
        high = breakdown.get("high", 0)
        
        if critical == 0 and high == 0:
            return None
        
        recommendations_text = "*🔒 SECURITY RECOMMENDATIONS*\n\n"
        
        if critical > 0:
            recommendations_text += "*🚨 IMMEDIATE ACTIONS REQUIRED:*\n"
            recommendations_text += f"• Review all {critical} critical PII findings\n"
            recommendations_text += "• Implement encryption for sensitive data transmission\n"
            recommendations_text += "• Add data masking for PII in logs and responses\n"
            recommendations_text += "• Conduct security audit of affected endpoints\n\n"
        
        if high > 0:
            recommendations_text += "*⚠️ HIGH PRIORITY ACTIONS:*\n"
            recommendations_text += f"• Review {high} high-risk PII instances\n"
            recommendations_text += "• Implement proper data validation\n"
            recommendations_text += "• Add rate limiting for PII endpoints\n"
            recommendations_text += "• Update API documentation with privacy notices\n\n"
        
        recommendations_text += "*📋 GENERAL RECOMMENDATIONS:*\n"
        recommendations_text += "• Implement GDPR/CCPA compliance measures\n"
        recommendations_text += "• Add PII detection to CI/CD pipeline\n"
        recommendations_text += "• Regular PII audits and monitoring\n"
        recommendations_text += "• Staff training on data privacy best practices\n"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": recommendations_text
            }
        }
    
    def _get_severity_icon(self, severity: str) -> str:
        """Get icon for PII severity level."""
        icons = {
            "critical": "🔴",
            "high": "🟡",
            "medium": "🟠",
            "low": "🟢"
        }
        return icons.get(severity, "❓")
    
    def send_critical_pii_alert(self, critical_findings: List[Dict[str, Any]]) -> bool:
        """
        Send immediate alert for critical PII findings.
        
        Args:
            critical_findings: List of critical PII findings
            
        Returns:
            bool: True if alert sent successfully, False otherwise
        """
        if not critical_findings:
            return True
        
        try:
            # Check if Slack is configured
            if not self.use_bot_token and not self.webhook_url:
                print("❌ Slack not configured - cannot send critical alert")
                return False
            
            alert_blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🚨 CRITICAL PII SECURITY ALERT"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{len(critical_findings)} Critical PII instances detected!*\n\nImmediate action required."
                    }
                }
            ]
            
            # Add critical findings
            for finding in critical_findings[:5]:  # Limit to top 5
                finding_text = f"*{finding['endpoint']}*\n"
                finding_text += f"• PII Type: {finding['pii_type']}\n"
                finding_text += f"• Field: {finding['field_name']}\n"
                finding_text += f"• Context: {finding['context']}\n"
                
                alert_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": finding_text
                    }
                })
            
            # Send using appropriate method
            if self.use_bot_token:
                return self._send_alert_with_bot_token(alert_blocks)
            else:
                return self._send_alert_with_webhook(alert_blocks)
            
        except Exception as e:
            print(f"Error sending critical PII alert: {e}")
            return False
    
    def _send_alert_with_bot_token(self, alert_blocks: List[Dict[str, Any]]) -> bool:
        """Send critical alert using bot token."""
        try:
            payload = {
                "channel": self.channel_id,
                "blocks": alert_blocks,
                "username": "PII Security Alert",
                "icon_emoji": "🚨"
            }
            
            response = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {self.bot_token}"},
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    print(f"✅ Critical PII alert sent successfully (Channel: {self.channel_id})")
                    return True
                else:
                    print(f"❌ Slack API Error: {data.get('error')}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending alert with bot token: {e}")
            return False
    
    def _send_alert_with_webhook(self, alert_blocks: List[Dict[str, Any]]) -> bool:
        """Send critical alert using webhook."""
        try:
            message = {
                "blocks": alert_blocks,
                "username": "PII Security Alert",
                "icon_emoji": "🚨"
            }
            
            response = requests.post(self.webhook_url, json=message, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Error sending alert with webhook: {e}")
            return False
