"""
Notification Manager Module

Handles Slack notifications and message formatting for schema monitoring.
"""
import requests
from typing import Dict, Any
from core.config import config


class NotificationManager:
    """Manages Slack notifications for schema monitoring."""
    
    def __init__(self):
        """Initialize the notification manager."""
        pass
    
    def send_slack_notification(self, report: Dict[str, Any]) -> bool:
        """
        Send Slack notification with monitoring report.
        
        Args:
            report (Dict[str, Any]): Monitoring report data
            
        Returns:
            bool: True if notification sent successfully, False otherwise
        """
        print("\n📱 Sending Slack Notifications...")
        
        try:
            # Check if Slack webhook is configured
            slack_webhook = getattr(config, 'SLACK_WEBHOOK_URL', None)
            if not slack_webhook or slack_webhook == 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL':
                print("   ⚠️  Slack webhook not configured - skipping notifications")
                return False
            
            # Create multiple message blocks to split the large content
            message_blocks = self._create_split_slack_blocks(report)
            
            # Use Block Kit format with multiple blocks
            message = {
                "blocks": message_blocks,
                "username": "API Monitor Bot",
                "icon_emoji": "🤖"
            }
            # Send notification
            response = requests.post(slack_webhook, json=message, timeout=10)
            
            if response.status_code == 200:
                print("   ✅ Slack notification sent successfully")
                return True
            else:
                print(f"   ❌ Failed to send Slack notification: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error sending Slack notification: {str(e)}")
            return False
            
    def _create_split_slack_blocks(self, report: Dict[str, Any]) -> list:
        """
        Create multiple Slack blocks to split large content and avoid size limitations.
        
        Args:
            report (Dict[str, Any]): Monitoring report data
            
        Returns:
            list: List of Slack message blocks
        """
        from datetime import datetime
        
        # Extract key metrics
        timestamp = datetime.fromisoformat(report.get('timestamp', datetime.now().isoformat())).strftime("%b %d, %Y at %I:%M %p")
        apis_monitored = report.get('total_apis_monitored', 0)
        apis_changed = report.get('apis_with_changes', 0)
        total_changes = report.get('total_changes', 0)
        breaking_changes = report.get('breaking_changes', 0)
        db_ops_avoided = report.get('database_operations_avoided', 0)
        hash_comparisons = report.get('hash_comparisons_performed', 0)
        errors = len(report.get('errors', [])) if isinstance(report.get('errors', []), list) else report.get('errors', 0)
        
        # Determine status
        if breaking_changes > 0:
            status = "BREAKING CHANGES DETECTED"
        elif total_changes > 0:
            status = "CHANGES DETECTED"
        else:
            status = "ALL STABLE"
        
        blocks = []
        
        # Block 1: Header and Summary
        header_content = "```\n✅ Schema Monitor Report\n\n"
        header_content += f"📅 Timestamp: {timestamp}\n"
        header_content += f"📊 Status: {status}\n"
        header_content += f"📋 APIs Monitored: {apis_monitored}\n"
        header_content += f"🔄 APIs Changed: {apis_changed}\n"
        header_content += f"✅ APIs Unchanged: {apis_monitored - apis_changed}\n"
        header_content += f"📈 Total Changes: {total_changes}\n"
        header_content += f"⚠️ Breaking Changes: {breaking_changes}\n"
        header_content += f"❌ Errors: {errors}\n```"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": header_content
            }
        })
        
        # Block 2: Detailed Changes (if any)
        if total_changes > 0:
            detailed_changes = self._format_detailed_changes_for_blocks(report)
            for change_block in detailed_changes:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```\n{change_block}\n```"
                    }
                })
        
        # Block 3: Endpoint Coverage
        endpoint_showcase = self._format_endpoint_showcase_code_block(report)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```\n{endpoint_showcase}```"
            }
        })
        
        # Block 4: Efficiency Metrics
        efficiency_content = "🔒 Efficiency Metrics:\n"
        efficiency_content += f"   • Database Operations Avoided: {db_ops_avoided}\n"
        efficiency_content += f"   • Hash Comparisons: {hash_comparisons}\n"
        efficiency_content += "   • Strategy: Zero DB operations until changes confirmed"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```\n{efficiency_content}\n```"
            }
        })
        
        return blocks
        
    def _format_detailed_changes_for_blocks(self, report: Dict[str, Any]) -> list:
        """Format detailed changes split into multiple blocks to avoid size limits."""
        change_blocks = []
        
        # Get the detailed changes content
        detailed_changes = self._format_detailed_changes(report)
        
        if not detailed_changes or detailed_changes == "✅ No changes detected in any monitored APIs":
            return [detailed_changes]
        
        # Split by APIs (each API gets its own block)
        api_sections = detailed_changes.split('\n\n')
        current_block = ""
        
        for section in api_sections:
            # If adding this section would make the block too long (>2000 chars), start a new block
            if len(current_block) + len(section) > 2000 and current_block:
                change_blocks.append(current_block.strip())
                current_block = section + "\n\n"
            else:
                current_block += section + "\n\n"
        
        # Add the last block if it has content
        if current_block.strip():
            change_blocks.append(current_block.strip())
        
        return change_blocks
    
    def _create_slack_message_payload(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create comprehensive Slack message payload with monitoring details.
        
        Args:
            report (Dict[str, Any]): Monitoring report data
            
        Returns:
            Dict[str, Any]: Slack message payload
        """
        timestamp = report.get('timestamp', 'Unknown')
        apis_monitored = report.get('total_apis_monitored', 0)
        apis_changed = report.get('apis_with_changes', 0)
        apis_unchanged = report.get('apis_unchanged', 0)
        total_changes = report.get('total_changes', 0)
        breaking_changes = report.get('breaking_changes', 0)
        errors = len(report.get('errors', []))
        
        # Determine severity and emoji based on changes
        if breaking_changes > 0:
            color = "danger"
            status_emoji = "🚨"
            status_text = f"Breaking Changes Detected in {apis_changed} APIs"
        elif total_changes > 0:
            color = "warning"
            status_emoji = "⚠️"
            status_text = f"Changes Detected in {apis_changed} APIs"
        else:
            color = "#00AA00"  # Green for no changes
            status_emoji = "✅"
            status_text = "ALL STABLE"
        
        # Create endpoint coverage showcase
        endpoint_showcase = self._format_endpoint_showcase(report)
        
        # Build comprehensive message
        message_blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji} True Zero-Insertion Schema Monitor Report"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*📅 Timestamp:*\n{timestamp}"},
                    {"type": "mrkdwn", "text": f"*📊 Status:*\n{status_text}"},
                    {"type": "mrkdwn", "text": f"*📋 APIs Monitored:*\n{apis_monitored}"},
                    {"type": "mrkdwn", "text": f"*🔄 APIs Changed:*\n{apis_changed}"},
                    {"type": "mrkdwn", "text": f"*✅ APIs Unchanged:*\n{apis_unchanged}"},
                    {"type": "mrkdwn", "text": f"*📈 Total Changes:*\n{total_changes}"},
                    {"type": "mrkdwn", "text": f"*⚠️ Breaking Changes:*\n{breaking_changes}"},
                    {"type": "mrkdwn", "text": f"*❌ Errors:*\n{errors}"}
                ]
            }
        ]
        
        # Add detailed change information if changes detected
        if total_changes > 0:
            change_details = self._format_detailed_changes(report)
            if change_details:
                message_blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🔍 Detailed Changes:*\n{change_details}"
                    }
                })
        
        # Add endpoint coverage showcase
        if endpoint_showcase:
            message_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📍 Endpoint Coverage Showcase:*\n{endpoint_showcase}"
                }
            })
        
        # Add efficiency metrics
        db_ops_avoided = report.get('database_operations_avoided', 0)
        hash_comparisons = report.get('hash_comparisons_performed', 0)
        
        message_blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🔒 Efficiency Metrics:*\n• Database Operations Avoided: {db_ops_avoided}\n• Hash Comparisons: {hash_comparisons}\n• Strategy: Zero DB operations until changes confirmed"
            }
        })
        
        # Add error details if any
        if errors > 0:
            error_list = "\n".join([f"• {error}" for error in report.get('errors', [])])
            message_blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*❌ Error Details:*\n{error_list}"
                }
            })
        
        return {
            "attachments": [
                {
                    "color": color,
                    "blocks": message_blocks
                }
            ]
        }
    
    def _create_unicode_slack_message(self, report: Dict[str, Any]) -> str:
        """
        Create code block formatted Slack message with Unicode emojis.
        
        Args:
            report (Dict[str, Any]): Monitoring report data
            
        Returns:
            str: Formatted Slack message in code block format with all content inside a single code block
        """
        from datetime import datetime
        
        # Extract key metrics
        timestamp = report.get('timestamp', datetime.now().isoformat())
        apis_monitored = report.get('total_apis_monitored', 0)
        apis_changed = report.get('apis_with_changes', 0)
        total_changes = report.get('total_changes', 0)
        breaking_changes = report.get('breaking_changes', 0)
        db_ops_avoided = report.get('database_operations_avoided', 0)
        hash_comparisons = report.get('hash_comparisons_performed', 0)
        errors = len(report.get('errors', [])) if isinstance(report.get('errors', []), list) else report.get('errors', 0)
        
        # Determine status
        if breaking_changes > 0:
            status = "BREAKING CHANGES DETECTED"
        elif total_changes > 0:
            status = "CHANGES DETECTED"
        else:
            status = "ALL STABLE"
        
        # Start building the message content first without code block markers
        # We'll add the code block markers at the very beginning and end
        message_content = "✅ True Zero-Insertion Schema Monitor Report\n\n"
        message_content += f"📅 Timestamp: {timestamp}\n"
        message_content += f"📊 Status: {status}\n"
        message_content += f"📋 APIs Monitored: {apis_monitored}\n"
        message_content += f"🔄 APIs Changed: {apis_changed}\n"
        message_content += f"✅ APIs Unchanged: {apis_monitored - apis_changed}\n"
        message_content += f"📈 Total Changes: {total_changes}\n"
        message_content += f"⚠️ Breaking Changes: {breaking_changes}\n"
        message_content += f"❌ Errors: {errors}\n\n"
        
        # Add detailed change information if changes detected
        if total_changes > 0:
            detailed_changes = self._format_detailed_changes(report)
            if detailed_changes:
                # Add the detailed changes directly to the message content
                message_content += detailed_changes
        
        # Add endpoint coverage showcase
        message_content += self._format_endpoint_showcase_code_block(report)
        
        # Add efficiency metrics
        message_content += "🔒 Efficiency Metrics:\n"
        message_content += f"   • Database Operations Avoided: {db_ops_avoided}\n"
        message_content += f"   • Hash Comparisons: {hash_comparisons}\n"
        message_content += "   • Strategy: Zero DB operations until changes confirmed\n"
        
        # For Slack, we'll use a special code block format
        # Add a specific language identifier that Slack recognizes
        final_message = "```\n" + message_content + "\n```"
        
        return final_message
    
    def _format_detailed_changes(self, report: Dict[str, Any]) -> str:
        """Format API-by-API change summary in clean, concise format to avoid Slack truncation."""
        api_summaries = []
        
        # Process each API with changes
        for api_info in report.get('apis_processed', []):
            endpoint_name = api_info.get('endpoint_name', 'Unknown API')
            api_title = api_info.get('api_title', endpoint_name)
            total_changes = api_info.get('total_changes', 0)
            breaking_changes = api_info.get('breaking_changes', 0)
            
            # Skip APIs with no changes
            if total_changes == 0:
                continue
            
            # Get detailed change analysis from the report
            change_analysis = api_info.get('change_analysis', {})
            
            # Count changes by type
            endpoint_changes = len(change_analysis.get('endpoint_changes', []))
            parameter_changes = len(change_analysis.get('parameter_changes', []))
            response_changes = len(change_analysis.get('response_changes', []))
            component_changes = len(change_analysis.get('component_changes', []))
            
            # Create API section 
            api_summary = f"📊 Total Changes: {total_changes}\n"
            if breaking_changes > 0:
                api_summary += f"⚠️ Breaking Changes: {breaking_changes}\n"
            api_summary += "\n"
            
            # Change breakdown section
            api_summary += "📍 Change Breakdown:\n"
            api_summary += f"   🔗 Endpoints: {'✅ Changed' if endpoint_changes > 0 else '❌ No Changes'} ({endpoint_changes})\n"
            api_summary += f"   📋 Parameters: {'✅ Changed' if parameter_changes > 0 else '❌ No Changes'} ({parameter_changes})\n"
            api_summary += f"   📤 Responses: {'✅ Changed' if response_changes > 0 else '❌ No Changes'} ({response_changes})\n"
            api_summary += f"   🧩 Components: {'✅ Changed' if component_changes > 0 else '❌ No Changes'} ({component_changes})\n"
            
            # Endpoint changes section
            if endpoint_changes > 0:
                api_summary += "\n🔗 ENDPOINT CHANGES:\n"
                for change in change_analysis.get('endpoint_changes', []):
                    change_type = change.get('change_type', 'unknown')
                    path = change.get('endpoint', change.get('path', 'N/A'))
                    method = change.get('method', 'N/A')
                    description = change.get('description', 'No description')
                    
                    if change_type == 'endpoint_added':
                        api_summary += f"   ➕ ADDED: {method} {path}\n"
                        api_summary += "      └─ New endpoint\n"
                    else:
                        api_summary += f"   📝 MODIFIED: {method} {path}\n"
                        api_summary += f"      └─ {description}\n"
            
            # Parameter changes section (most important for breaking changes)
            if parameter_changes > 0:
                api_summary += "\n📋 PARAMETER CHANGES:\n"
                # Include both API title and ID/URI for better traceability
                # An API seen for the first time has no stored id yet. Printing the
                # internal marker verbatim made a new API look like a broken one in
                # the alert, so say what it means instead.
                api_id = api_info.get('api_id') or api_info.get('fresh_api_id') or ''
                if not api_id or api_id == 'unknown-id':
                    api_id = 'Newly Added (no ID recorded yet)'
                api_summary += f"   📌 API: {api_title} (URI: {api_id})\n"
                for change in change_analysis.get('parameter_changes', []):
                    param_name = change.get('parameter_name', 'N/A')
                    # Use 'in' for parameter location if not specified
                    path = change.get('endpoint', change.get('path', 'N/A'))
                    method = change.get('method', 'N/A')
                    is_breaking = change.get('is_breaking', False)
                    new_value = change.get('new_value', {})
                    old_value = change.get('old_value', {})
                    
                    # Get data type from either new_value or old_value
                    if isinstance(new_value, dict):
                        data_type = new_value.get('data_type', new_value.get('type', 'parameter'))
                        required = new_value.get('required', False)
                        default_value = new_value.get('default_value', new_value.get('default'))
                    elif isinstance(old_value, dict):
                        data_type = old_value.get('data_type', old_value.get('type', 'parameter'))
                        required = old_value.get('required', False)
                        default_value = old_value.get('default_value', old_value.get('default'))
                    else:
                        data_type = 'parameter'
                        required = False
                        default_value = None
                    
                    breaking_indicator = "⚠️ BREAKING" if is_breaking else "➕ ADDED"
                    requirement = "Required" if required else "Optional"
                    default_text = f", default: {default_value}" if default_value else ""
                    
                    api_summary += f"   {breaking_indicator}: {param_name}\n"
                    api_summary += f"      └─ Type: {requirement} {data_type}{default_text}\n"
                    
                    # Add impact warning for breaking changes
                    if is_breaking:
                        api_summary += "      └─ 🚨 **IMPACT**: BREAKING - Existing clients will fail without updates\n"
                    
                    # Format endpoint display to avoid N/A values
                    if method != 'N/A' and path != 'N/A':
                        api_summary += f"      └─ Endpoint: {method} {path}\n"
                    method = change.get('method', '')
                    old_value = change.get('old_value')
                    new_value = change.get('new_value')
                    status_code = change.get('status_code', '200')
                    
                    if change_type == 'response_added':
                        schema_ref = new_value.get('$ref', 'New schema') if isinstance(new_value, dict) else 'New schema'
                        schema_name = schema_ref.split('/')[-1] if '/' in str(schema_ref) else str(schema_ref)
                        # Format endpoint display to avoid empty values
                        if method and path:
                            api_summary += f"   ➕ NEW RESPONSE: {method} {path}\n"
                        elif path:
                            api_summary += f"   ➕ NEW RESPONSE: {path}\n"
                        else:
                            api_summary += f"   ➕ NEW RESPONSE: Status {status_code}\n"
                        api_summary += f"      └─ Schema: {schema_name}\n"
                    elif change_type == 'response_schema_changed':
                        # Get better descriptions of old and new schemas
                        if isinstance(old_value, dict):
                            old_type = old_value.get('type', '')
                            if old_type == 'object' and 'properties' in old_value:
                                prop_count = len(old_value.get('properties', {}))
                                _old_desc = f"{old_type} with {prop_count} properties"
                            else:
                                _old_desc = old_value.get('$ref', old_type or 'Simple schema')
                        else:
                            _old_desc = 'Simple schema'
                            
                        if isinstance(new_value, dict):
                            new_type = new_value.get('type', '')
                            if new_type == 'object' and 'properties' in new_value:
                                prop_count = len(new_value.get('properties', {}))
                                _new_desc = f"{new_type} with {prop_count} properties"
                            else:
                                _new_desc = new_value.get('$ref', new_type or 'Updated schema')
                        else:
                            _new_desc = 'Updated schema'
                        
                        # Extract schema name from references or infer from endpoint/context
                        schema_name = "Unknown Schema"
                        
                        # Try to get schema name from $ref if available
                        if isinstance(old_value, dict) and '$ref' in old_value:
                            ref = old_value.get('$ref', '')
                            if '/' in ref:
                                schema_name = ref.split('/')[-1]
                        elif isinstance(new_value, dict) and '$ref' in new_value:
                            ref = new_value.get('$ref', '')
                            if '/' in ref:
                                schema_name = ref.split('/')[-1]
                        
                        # If no $ref, try to infer schema name from endpoint path
                        elif path:
                            # Extract resource name from path (e.g., /products/{id} -> ProductResponse)
                            parts = [p for p in path.split('/') if p and not p.startswith('{')]
                            if parts:
                                resource = parts[-1].title()
                                schema_name = f"{resource}Response"
                        
                        # Format response schema changes in a clear, detailed format similar to component changes
                        if method and path:
                            api_summary += f"   🔄 UPDATED SCHEMA: {schema_name} ({method} {path})\n"
                        elif path:
                            api_summary += f"   🔄 UPDATED SCHEMA: {schema_name} ({path})\n"
                        else:
                            api_summary += f"   🔄 UPDATED SCHEMA: {schema_name} (Status {status_code})\n"
                        
                        # Add description of changes
                        description = change.get('description', 'Response schema updated with new fields')
                        api_summary += f"      └─ Changes: {description}\n"
                        
                        # Extract and show property differences in a clear, detailed format
                        change_details = change.get('change_details', {})
                        
                        # If change_details is provided, use it
                        if change_details:
                            added_props = change_details.get('added_properties', [])
                            modified_props = change_details.get('modified_properties', [])
                            removed_props = change_details.get('removed_properties', [])
                            
                            # Format required/optional fields like in component changes
                            if added_props:
                                # Try to determine which are required vs optional
                                if isinstance(new_value, dict) and 'required' in new_value:
                                    required = set(new_value.get('required', []))
                                    required_added = [p for p in added_props if p in required]
                                    optional_added = [p for p in added_props if p not in required]
                                    
                                    if required_added:
                                        props_text = ', '.join(required_added)
                                        api_summary += f"      └─ Added required fields: {props_text}\n"
                                    
                                    if optional_added:
                                        props_text = ', '.join(optional_added)
                                        api_summary += f"      └─ Added optional fields: {props_text}\n"
                                else:
                                    # If we can't determine required vs optional, just list them
                                    props_text = ', '.join(added_props)
                                    api_summary += f"      └─ Added fields: {props_text}\n"
                            
                            if modified_props:
                                props_text = ', '.join(modified_props)
                                api_summary += f"      └─ Modified fields: {props_text}\n"
                            
                            if removed_props:
                                props_text = ', '.join(removed_props)
                                api_summary += f"      └─ Removed fields: {props_text}\n"
                        
                        # If no change_details but we have old and new values with properties, extract differences
                        elif isinstance(old_value, dict) and isinstance(new_value, dict):
                            old_props = set(old_value.get('properties', {}).keys())
                            new_props = set(new_value.get('properties', {}).keys())
                            
                            # Calculate property differences
                            added_props = list(new_props - old_props)
                            removed_props = list(old_props - new_props)
                            
                            # Try to determine which added fields are required vs optional
                            if added_props and 'required' in new_value:
                                required = set(new_value.get('required', []))
                                required_added = [p for p in added_props if p in required]
                                optional_added = [p for p in added_props if p not in required]
                                
                                if required_added:
                                    props_text = ', '.join(required_added)
                                    api_summary += f"      └─ Added required fields: {props_text}\n"
                                
                                if optional_added:
                                    props_text = ', '.join(optional_added)
                                    api_summary += f"      └─ Added optional fields: {props_text}\n"
                            elif added_props:
                                props_text = ', '.join(added_props)
                                api_summary += f"      └─ Added fields: {props_text}\n"
                            
                            if removed_props:
                                props_text = ', '.join(removed_props)
                                api_summary += f"      └─ Removed fields: {props_text}\n"
                        
                        # Add affected endpoints section
                        affected_endpoints = change.get('affected_endpoints', [])
                        if affected_endpoints:
                            api_summary += f"      └─ Affects {len(affected_endpoints)} endpoint(s):\n"
                            for endpoint in affected_endpoints[:2]:  # Show first 2
                                e_method = endpoint.get('method', 'N/A')
                                e_path = endpoint.get('path', path)
                                usage_type = endpoint.get('usage_type', 'response')
                                api_summary += f"         • {e_method} {e_path} ({usage_type})\n"
                            if len(affected_endpoints) > 2:
                                api_summary += f"         • +{len(affected_endpoints)-2} more endpoints\n"
                api_summary += "\n"
            
            # Response changes section with detailed information
            if response_changes > 0:
                api_summary += "📤 RESPONSE CHANGES:\n"
                # Add API name for component changes section
                # Include both API title and ID/URI for better traceability
                # An API seen for the first time has no stored id yet. Printing the
                # internal marker verbatim made a new API look like a broken one in
                # the alert, so say what it means instead.
                api_id = api_info.get('api_id') or api_info.get('fresh_api_id') or ''
                if not api_id or api_id == 'unknown-id':
                    api_id = 'Newly Added (no ID recorded yet)'
                api_summary += f"   📌 API: {api_title} (URI: {api_id})\n"
                
                for change in change_analysis.get('response_changes', []):
                    change_type = change.get('change_type', 'unknown')
                    component_name = change.get('component_name', 'N/A')
                    
                    if change_type == 'response_added':
                        api_summary += f"   ➕ NEW RESPONSE: {component_name}\n"
                        
                        # Add purpose/description
                        description = change.get('description', f'New {component_name.lower()} response with detailed information')
                        api_summary += f"      └─ Purpose: {description}\n"
                        
                        # Show required and optional fields from schema
                        new_value = change.get('new_value', {})
                        if isinstance(new_value, dict):
                            required_fields = new_value.get('required', [])
                            properties = new_value.get('properties', {})
                            optional_fields = [prop for prop in properties.keys() if prop not in required_fields]
                            
                            if required_fields:
                                if len(required_fields) <= 3:
                                    api_summary += f"      └─ Required fields: {', '.join(required_fields)}\n"
                                else:
                                    api_summary += f"      └─ Required fields: {', '.join(required_fields[:2])}, +{len(required_fields)-2} more\n"
                            
                            if optional_fields:
                                api_summary += f"      └─ Optional fields: {len(optional_fields)} additional fields\n"
                        
                        # Show affected endpoints
                        affected_endpoints = change.get('affected_endpoints', [])
                        if affected_endpoints:
                            api_summary += f"      └─ Used by {len(affected_endpoints)} endpoint(s):\n"
                            for endpoint in affected_endpoints[:2]:  # Show first 2
                                method = endpoint.get('method', 'N/A')
                                path = endpoint.get('path', 'N/A')
                                usage_type = endpoint.get('usage_type', 'response')
                                api_summary += f"         • {method} {path} ({usage_type})\n"
                            if len(affected_endpoints) > 2:
                                api_summary += f"         • +{len(affected_endpoints)-2} more endpoints\n"
                    
                    elif change_type in ['response_modified', 'response_schema_changed']:
                        # Extract schema name from references or infer from endpoint/context
                        schema_name = "Unknown Schema"
                        path = change.get('endpoint', '')
                        method = change.get('method', '')
                        
                        # Try to get schema name from $ref if available
                        old_value = change.get('old_value', {})
                        new_value = change.get('new_value', {})
                        
                        if isinstance(old_value, dict) and '$ref' in old_value:
                            ref = old_value.get('$ref', '')
                            if '/' in ref:
                                schema_name = ref.split('/')[-1]
                        elif isinstance(new_value, dict) and '$ref' in new_value:
                            ref = new_value.get('$ref', '')
                            if '/' in ref:
                                schema_name = ref.split('/')[-1]
                        
                        # If no $ref, try to infer schema name from endpoint path
                        elif path:
                            # Extract resource name from path (e.g., /products/{id} -> ProductResponse)
                            parts = [p for p in path.split('/') if p and not p.startswith('{')]
                            if parts:
                                resource = parts[-1].title()
                                schema_name = f"{resource}Response"
                        
                        # Format response schema changes in a clear, detailed format
                        if method and path:
                            api_summary += f"   🔄 UPDATED SCHEMA: {schema_name} ({method} {path})\n"
                        elif path:
                            api_summary += f"   🔄 UPDATED SCHEMA: {schema_name} ({path})\n"
                        else:
                            api_summary += f"   🔄 UPDATED SCHEMA: {schema_name}\n"
                        
                        # Add description of changes
                        description = change.get('description', 'Response schema updated with new fields')
                        api_summary += f"      └─ Changes: {description}\n"
                        
                        # Show what changed in this component
                        old_value = change.get('old_value', {})
                        new_value = change.get('new_value', {})
                        
                        if isinstance(old_value, dict) and isinstance(new_value, dict):
                            old_props = set(old_value.get('properties', {}).keys())
                            new_props = set(new_value.get('properties', {}).keys())
                            added_props = new_props - old_props
                            
                            new_required = set(new_value.get('required', []))
                            
                            # Show added fields with their requirement status
                            if added_props:
                                field_details = []
                                for prop in list(added_props)[:3]:  # Show first 3
                                    req_status = 'required' if prop in new_required else 'optional'
                                    field_details.append(f"{prop} ({req_status})")
                                
                                api_summary += f"      └─ Added fields: {', '.join(field_details)}"
                                if len(added_props) > 3:
                                    api_summary += f", +{len(added_props)-3} more"
                                api_summary += "\n"
                            
                            # Show modified properties if available
                            common_props = old_props & new_props
                            if common_props:
                                # For simplicity, show some common props as "modified"
                                modified_list = list(common_props)[:2]
                                if modified_list:
                                    api_summary += f"      └─ Modified properties: {', '.join(modified_list)}\n"
                        
                        # Show affected endpoints
                        affected_endpoints = change.get('affected_endpoints', [])
                        if affected_endpoints:
                            api_summary += f"      └─ Affects {len(affected_endpoints)} endpoint(s):\n"
                            for endpoint in affected_endpoints[:3]:  # Show first 3
                                method = endpoint.get('method', 'N/A')
                                path = endpoint.get('path', 'N/A')
                                usage_type = endpoint.get('usage_type', 'response')
                                api_summary += f"         • {method} {path} ({usage_type})\n"
                            if len(affected_endpoints) > 3:
                                api_summary += f"         • +{len(affected_endpoints)-3} more endpoints\n"
            
            # Component changes section with detailed information
            if component_changes > 0:
                api_summary += "🧩 SCHEMA COMPONENTS:\n"
                # Add API name for component changes section
                # Include both API title and ID/URI for better traceability
                # An API seen for the first time has no stored id yet. Printing the
                # internal marker verbatim made a new API look like a broken one in
                # the alert, so say what it means instead.
                api_id = api_info.get('api_id') or api_info.get('fresh_api_id') or ''
                if not api_id or api_id == 'unknown-id':
                    api_id = 'Newly Added (no ID recorded yet)'
                api_summary += f"   📌 API: {api_title} (URI: {api_id})\n"
                
                for change in change_analysis.get('component_changes', []):
                    change_type = change.get('change_type', 'unknown')
                    component_name = change.get('component_name', 'N/A')
                    
                    if change_type == 'component_added':
                        api_summary += f"   ➕ NEW SCHEMA: {component_name}\n"
                        
                        # Add purpose/description
                        description = change.get('description', f'New {component_name.lower()} schema with detailed information')
                        api_summary += f"      └─ Purpose: {description}\n"
                        
                        # Show required and optional fields from schema
                        new_value = change.get('new_value', {})
                        if isinstance(new_value, dict):
                            required_fields = new_value.get('required', [])
                            properties = new_value.get('properties', {})
                            optional_fields = [prop for prop in properties.keys() if prop not in required_fields]
                            
                            if required_fields:
                                if len(required_fields) <= 3:
                                    api_summary += f"      └─ Required fields: {', '.join(required_fields)}\n"
                                else:
                                    api_summary += f"      └─ Required fields: {', '.join(required_fields[:2])}, +{len(required_fields)-2} more\n"
                            
                            if optional_fields:
                                api_summary += f"      └─ Optional fields: {len(optional_fields)} additional fields\n"
                        
                        # Show affected endpoints
                        affected_endpoints = change.get('affected_endpoints', [])
                        if affected_endpoints:
                            api_summary += f"      └─ Used by {len(affected_endpoints)} endpoint(s):\n"
                            for endpoint in affected_endpoints[:2]:  # Show first 2
                                method = endpoint.get('method', 'N/A')
                                path = endpoint.get('path', 'N/A')
                                usage_type = endpoint.get('usage_type', 'response')
                                api_summary += f"         • {method} {path} ({usage_type})\n"
                            if len(affected_endpoints) > 2:
                                api_summary += f"         • +{len(affected_endpoints)-2} more endpoints\n"
                    
                    elif change_type == 'component_modified':
                        api_summary += f"   🔧 UPDATED SCHEMA: {component_name}\n"
                        
                        # Add description of changes
                        description = change.get('description', f'Enhanced {component_name.lower()} with new metadata')
                        api_summary += f"      └─ Changes: {description}\n"
                        
                        # Show what changed in this component
                        old_value = change.get('old_value', {})
                        new_value = change.get('new_value', {})
                        
                        if isinstance(old_value, dict) and isinstance(new_value, dict):
                            old_props = set(old_value.get('properties', {}).keys())
                            new_props = set(new_value.get('properties', {}).keys())
                            added_props = new_props - old_props
                            
                            _old_required = set(old_value.get('required', []))
                            new_required = set(new_value.get('required', []))
                            
                            # Show added fields with their requirement status
                            if added_props:
                                field_details = []
                                for prop in list(added_props)[:3]:  # Show first 3
                                    req_status = 'required' if prop in new_required else 'optional'
                                    field_details.append(f"{prop} ({req_status})")
                                
                                api_summary += f"      └─ Added fields: {', '.join(field_details)}"
                                if len(added_props) > 3:
                                    api_summary += f", +{len(added_props)-3} more"
                                api_summary += "\n"
                            
                            # Show modified properties if available
                            common_props = old_props & new_props
                            if common_props:
                                # For simplicity, show some common props as "modified"
                                modified_list = list(common_props)[:2]
                                if modified_list:
                                    api_summary += f"      └─ Modified properties: {', '.join(modified_list)}\n"
                        
                        # Show affected endpoints
                        affected_endpoints = change.get('affected_endpoints', [])
                        if affected_endpoints:
                            api_summary += f"      └─ Affects {len(affected_endpoints)} endpoint(s):\n"
                            for endpoint in affected_endpoints[:3]:  # Show first 3
                                method = endpoint.get('method', 'N/A')
                                path = endpoint.get('path', 'N/A')
                                usage_type = endpoint.get('usage_type', 'response')
                                api_summary += f"         • {method} {path} ({usage_type})\n"
                            if len(affected_endpoints) > 3:
                                api_summary += f"         • +{len(affected_endpoints)-3} more endpoints\n"
            
            api_summaries.append(api_summary)
        
        if not api_summaries:
            return "✅ No changes detected in any monitored APIs"
        
        # Add overall summary header
        total_apis_changed = len(api_summaries)
        total_breaking = sum(api_info.get('breaking_changes', 0) for api_info in report.get('apis_processed', []))
        
        header = f"📊 CHANGE SUMMARY ({total_apis_changed} API{'s' if total_apis_changed != 1 else ''} affected)\n"
        if total_breaking > 0:
            header += f"⚠️ {total_breaking} BREAKING CHANGE{'S' if total_breaking != 1 else ''} DETECTED\n\n"
        else:
            header += "✅ No breaking changes detected\n\n"
        
        # Join all API summaries with a single newline between them
        # This prevents excessive spacing that might break code block formatting
        return header + "\n".join(api_summaries)
    
    def _format_endpoint_showcase(self, report: Dict[str, Any]) -> str:
        """Format endpoint coverage showcase for Slack notifications."""
        showcase_lines = []
        
        # Add individual API endpoint counts
        for api_detail in report.get('api_endpoint_details', []):
            api_title = api_detail.get('api_title', 'Unknown API')
            endpoint_count = api_detail.get('endpoint_count', 0)
            api_id = api_detail.get('api_id', 'unknown')
            
            # Truncate API ID for display
            short_id = api_id[:8] + "..." if len(api_id) > 8 else api_id
            showcase_lines.append(f"📊 **{api_title}**: {endpoint_count} endpoints")
            showcase_lines.append(f"   ID: {short_id}")
        
        # Add total
        total_endpoints = report.get('total_endpoints_monitored', 0)
        if total_endpoints > 0:
            showcase_lines.append(f"\n🔢 **TOTAL ENDPOINTS ACROSS ALL APIs: {total_endpoints}**")
        
        return "\n".join(showcase_lines) if showcase_lines else "Endpoint statistics not available"
    
    def _format_endpoint_showcase_code_block(self, report: Dict[str, Any]) -> str:
        """Format endpoint coverage showcase for code block format."""
        showcase_text = "📍 Endpoint Coverage Showcase:\n"
        
        # Add individual API endpoint counts
        for api_detail in report.get('api_endpoint_details', []):
            api_title = api_detail.get('api_title', 'Unknown API')
            endpoint_count = api_detail.get('endpoint_count', 0)
            api_id = api_detail.get('api_id', 'unknown')
            
            # Truncate API ID for display
            short_id = api_id[:8] + "..." if len(api_id) > 8 else api_id
            showcase_text += f"   📊 {api_title}: {endpoint_count} endpoints (ID: {short_id})\n"
        
        # Add total
        total_endpoints = report.get('total_endpoints_monitored', 0)
        if total_endpoints > 0:
            showcase_text += f"   🔢 TOTAL ENDPOINTS: {total_endpoints}\n"
        
        return showcase_text
        
    def _convert_emoji_shortcodes_to_unicode(self, text: str) -> str:
        """Convert Slack emoji shortcodes to Unicode emojis."""
        emoji_map = {
            ":white_check_mark:": "✅",
            ":bar_chart:": "📊",
            ":date:": "📅",
            ":clipboard:": "📋",
            ":arrows_counterclockwise:": "🔄",
            ":chart_with_upwards_trend:": "📈",
            ":warning:": "⚠️",
            ":x:": "❌",
            ":round_pushpin:": "📍",
            ":link:": "🔗",
            ":outbox_tray:": "📤",
            ":jigsaw:": "🧩",
            ":heavy_plus_sign:": "➕",
            ":memo:": "📝",
            ":pushpin:": "📌",
            ":rotating_light:": "🚨",
            ":wrench:": "🔧",
            ":1234:": "🔢",
            ":lock:": "🔒",
            ":robot_face:": "🤖"
        }
        
        for shortcode, unicode_emoji in emoji_map.items():
            text = text.replace(shortcode, unicode_emoji)
            
        return text
