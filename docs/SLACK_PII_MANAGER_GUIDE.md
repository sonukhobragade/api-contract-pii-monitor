# Slack PII Manager Guide

## Overview

The `SlackPIIManager` is a specialized class designed to send comprehensive PII (Personally Identifiable Information) analysis reports to Slack with proper formatting. It integrates with the `FastPIIAnalyzer` to provide detailed insights about critical API calls and PII data found in requests, responses, parameters, and schemas.

## Features

- **Comprehensive PII Reports**: Detailed analysis of PII found across all APIs
- **Critical Alert System**: Immediate notifications for critical PII findings
- **Context-Aware Analysis**: Separates PII by request body, response body, and parameters
- **Security Recommendations**: Provides actionable security advice
- **Rich Slack Formatting**: Uses Slack Block Kit for professional presentation
- **Performance Metrics**: Includes processing time and endpoint analysis rates

## Setup

### 1. Environment Configuration

Ensure your `.env` file contains the Slack webhook URL:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 2. Installation

The `SlackPIIManager` is part of the core module and requires no additional installation:

```python
from core.slack_pii_manager import SlackPIIManager
```

## Usage

### Basic Usage

```python
from core.slack_pii_manager import SlackPIIManager
from scripts.fast_pii_analysis import FastPIIAnalyzer

# Initialize components
analyzer = FastPIIAnalyzer()
slack_manager = SlackPIIManager()

# Run PII analysis
analysis_results = analyzer.analyze_all_apis_fast()

# Send comprehensive report to Slack
success = slack_manager.send_pii_analysis_report(analysis_results)

if success:
    print("✅ Report sent successfully!")
else:
    print("❌ Failed to send report")
```

### Critical PII Alerts

For immediate alerts on critical PII findings:

```python
# Extract critical findings
critical_findings = []
for result in analysis_results.get("detailed_results", []):
    if result.get("critical_pii"):
        for pii in result["critical_pii"]:
            critical_findings.append({
                "endpoint": f"{result['api_title']} - {result['http_method']} {result['endpoint_path']}",
                "pii_type": pii["pii_type"],
                "field_name": pii["field_name"],
                "context": pii["context"]
            })

# Send critical alert
slack_manager.send_critical_pii_alert(critical_findings)
```

## Integration Scripts

### 1. Simple Integration Script

Use the provided integration script for quick PII analysis and Slack reporting:

```bash
# Analyze all APIs and send report to Slack
python scripts/send_pii_report_to_slack.py

# Analyze specific API
python scripts/send_pii_report_to_slack.py --api-id your-api-id

# Use more worker threads for faster processing
python scripts/send_pii_report_to_slack.py --workers 8

# Don't save detailed report to file
python scripts/send_pii_report_to_slack.py --no-save
```

### 2. Demo Script

Run the demo to see the Slack PII Manager in action:

```bash
# Run demo for all APIs
python demos/slack_pii_report_demo.py

# Run demo for specific API
python demos/slack_pii_report_demo.py --api-id your-api-id
```

## Report Structure

The Slack PII Manager sends comprehensive reports with the following sections:

### 1. Header Block
- **Critical Alert**: Red alert for critical PII findings
- **High-Risk Alert**: Orange alert for high-risk PII
- **Analysis Complete**: Green indicator for clean analysis

### 2. Executive Summary
- Total endpoints analyzed
- Endpoints with PII (percentage)
- Average compliance score
- Processing performance metrics
- PII breakdown by severity

### 3. Critical PII Findings
- List of endpoints with critical PII
- PII types found in each endpoint
- API information for each finding

### 4. API Breakdown
- Risk level assessment for each API
- PII counts by severity
- Compliance scores
- Endpoint counts

### 5. Detailed PII Analysis
- **Request Body PII**: PII found in request payloads
- **Response Body PII**: PII found in response schemas
- **Parameter PII**: PII found in API parameters

### 6. Security Recommendations
- Immediate actions for critical findings
- High-priority actions for high-risk findings
- General security best practices

## PII Severity Levels

The system categorizes PII by severity:

- **🔴 Critical**: SSN, Credit Cards, Passport Numbers
- **🟡 High**: Email, Phone, Date of Birth, Address
- **🟠 Medium**: Names, Usernames
- **🟢 Low**: User IDs, non-sensitive identifiers

## Slack Message Format

The manager uses Slack's Block Kit format for rich, structured messages:

```json
{
  "blocks": [
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
        "text": "*📊 EXECUTIVE SUMMARY*\n\n..."
      }
    }
  ],
  "username": "PII Security Bot",
  "icon_emoji": "🔒"
}
```

## Error Handling

The manager includes comprehensive error handling:

- **Webhook Configuration**: Checks for valid Slack webhook URL
- **Network Issues**: Handles connection timeouts and failures
- **Data Validation**: Validates analysis results before sending
- **Graceful Degradation**: Continues operation even if Slack sending fails

## Configuration Options

### Environment Variables

```bash
# Required
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Optional
SLACK_TOKEN=your-slack-token
CHANNEL_ID=your-channel-id
```

### Customization

You can customize the Slack PII Manager by extending the class:

```python
class CustomSlackPIIManager(SlackPIIManager):
    def _create_header_block(self, analysis_results):
        # Custom header logic
        pass
    
    def _create_custom_block(self, analysis_results):
        # Add custom blocks
        pass
```

## Best Practices

### 1. Regular Monitoring
- Set up automated PII analysis runs
- Configure alerts for critical findings
- Monitor compliance scores over time

### 2. Security Integration
- Integrate with CI/CD pipelines
- Add PII detection to code reviews
- Implement automated blocking for critical findings

### 3. Team Communication
- Use dedicated Slack channels for PII alerts
- Set up different notification levels
- Include actionable recommendations

### 4. Data Management
- Archive detailed reports for compliance
- Track PII findings over time
- Maintain audit trails

## Troubleshooting

### Common Issues

1. **Slack webhook not configured**
   ```
   ⚠️  Slack webhook not configured - skipping notifications
   ```
   **Solution**: Set `SLACK_WEBHOOK_URL` in your environment

2. **Network timeout**
   ```
   ❌ Failed to send PII report: 408
   ```
   **Solution**: Check network connectivity and webhook URL

3. **Invalid webhook URL**
   ```
   ❌ Failed to send PII report: 404
   ```
   **Solution**: Verify the webhook URL is correct and active

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

slack_manager = SlackPIIManager()
```

## Examples

### Example 1: Basic Integration

```python
#!/usr/bin/env python3
from core.slack_pii_manager import SlackPIIManager
from scripts.fast_pii_analysis import FastPIIAnalyzer

def main():
    analyzer = FastPIIAnalyzer()
    slack_manager = SlackPIIManager()
    
    # Run analysis
    results = analyzer.analyze_all_apis_fast()
    
    # Send report
    if slack_manager.send_pii_analysis_report(results):
        print("✅ Report sent!")
    else:
        print("❌ Failed to send report")

if __name__ == "__main__":
    main()
```

### Example 2: Scheduled Monitoring

```python
#!/usr/bin/env python3
import schedule
import time
from core.slack_pii_manager import SlackPIIManager
from scripts.fast_pii_analysis import FastPIIAnalyzer

def run_pii_monitoring():
    analyzer = FastPIIAnalyzer()
    slack_manager = SlackPIIManager()
    
    results = analyzer.analyze_all_apis_fast()
    slack_manager.send_pii_analysis_report(results)

# Schedule daily monitoring
schedule.every().day.at("09:00").do(run_pii_monitoring)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Support

For issues or questions:

1. Check the troubleshooting section
2. Review the error messages in the console output
3. Verify your Slack webhook configuration
4. Test with the demo scripts first

The Slack PII Manager is designed to be robust and user-friendly, providing comprehensive PII analysis reports with professional Slack formatting.
