# PII Detection System Guide

## Overview

The PII (Personally Identifiable Information) Detection System is a comprehensive privacy compliance tool that analyzes OpenAPI schemas to identify potential privacy risks and ensure regulatory compliance (GDPR, CCPA, etc.).

## Features

### 🔍 Comprehensive PII Detection
- **15+ PII Types Detected**: SSN, Credit Cards, Email, Phone, Address, Names, and more
- **Multi-Context Analysis**: Parameters, request bodies, response schemas, and component references
- **Pattern-Based Matching**: Advanced regex patterns for field names and descriptions
- **Nested Schema Support**: Deep analysis of complex object structures and arrays

### 📊 Risk Assessment & Compliance
- **4-Tier Severity Classification**: Critical, High, Medium, Low
- **Compliance Scoring**: 0-100% score based on PII exposure and severity
- **Risk Assessment**: Overall risk evaluation with actionable insights
- **Security Recommendations**: Specific guidance for each PII type detected

### 🔄 Integration & Monitoring
- **Database Integration**: Works with existing PostgreSQL OpenAPI schema storage
- **Schema Change Monitoring**: Detects PII changes between API versions
- **CI/CD Pipeline Support**: Command-line tools with appropriate exit codes
- **Slack Notifications**: Real-time alerts for PII exposure changes
- **Jenkins Reporting**: Comprehensive reports for build artifacts

## Architecture

### Core Components

```
core/
├── pii_detector.py      # Main PII detection engine
├── pii_monitor.py       # Schema change monitoring integration
└── config.py           # Configuration management

scripts/
└── pii_analysis.py     # Command-line analysis tool

demos/
└── pii_detection_demo.py # Interactive demonstration

tests/
└── test_pii_detector.py # Comprehensive unit tests
```

### Data Flow

```
OpenAPI Schema → PII Detector → Analysis Results → Reports/Alerts
     ↓              ↓               ↓              ↓
  Database    Pattern Matching  Compliance    Slack/Jenkins
  Storage     & Classification   Scoring       Notifications
```

## PII Types Detected

### 🔴 Critical Risk PII
- **Social Security Number** (`ssn`, `social_security_number`, `tax_id`)
- **Credit Card Number** (`credit_card`, `card_number`, `cc_number`)
- **Passport Number** (`passport`, `passport_number`, `passport_id`)
- **Driver License** (`driver_license`, `drivers_license`, `dl_number`)
- **Bank Account** (`bank_account`, `account_number`, `routing_number`)

### 🟡 High Risk PII
- **Email Address** (`email`, `email_address`, `mail_address`)
- **Phone Number** (`phone`, `telephone`, `mobile`, `cell`)
- **Date of Birth** (`birth_date`, `date_of_birth`, `dob`, `birthday`)
- **Physical Address** (`address`, `street`, `city`, `state`, `zip`)
- **IP Address** (`ip_address`, `ip_addr`, `client_ip`)

### 🟠 Medium Risk PII
- **First Name** (`first_name`, `given_name`, `fname`)
- **Last Name** (`last_name`, `family_name`, `surname`)
- **Full Name** (`full_name`, `complete_name`, `display_name`)
- **Username** (`username`, `user_name`, `login`, `handle`)

### 🟢 Low Risk PII
- **User ID** (`user_id`, `uid`, `customer_id`, `client_id`)

## Usage

### Command-Line Analysis

```bash
# Analyze all APIs in database
python scripts/pii_analysis.py

# Analyze specific API
python scripts/pii_analysis.py --api-id your-api-id

# Generate JSON report only
python scripts/pii_analysis.py --output-format json

# Custom output file
python scripts/pii_analysis.py --output-file custom_report.json
```

### Programmatic Usage

```python
from core.pii_detector import PIIDetector

# Initialize detector
detector = PIIDetector()

# Analyze endpoint
result = detector.analyze_endpoint_pii(
    api_id="your-api-id",
    api_title="Your API",
    endpoint_path="/users/{id}",
    http_method="GET",
    parameters=[...],
    request_body_schema={...},
    response_schemas={...}
)

# Check results
print(f"PII Found: {result.total_pii_found}")
print(f"Compliance Score: {result.compliance_score}%")
print(f"Critical PII: {len(result.critical_pii)}")
```

### Integration with Schema Monitoring

```python
from core.pii_monitor import PIIMonitor

# Initialize monitor
monitor = PIIMonitor(config)

# Analyze PII changes
pii_changes = monitor.analyze_pii_changes(
    api_id="your-api-id",
    api_title="Your API",
    old_version_id="old-version",
    new_version_id="new-version",
    old_endpoints=[...],
    new_endpoints=[...]
)

# Check for alerts
if monitor.should_alert_pii_changes(pii_changes):
    slack_message = monitor.create_pii_slack_message(pii_changes)
    # Send to Slack...
```

## Reports & Output

### Console Report Example

```
🔍 PII DETECTION ANALYSIS REPORT
================================================================================

📊 OVERALL SUMMARY
   Total Endpoints Analyzed: 25
   Endpoints with PII: 18
   PII Exposure Rate: 72.0%
   Average Compliance Score: 65.3%

🔍 PII BREAKDOWN
   🔴 Critical: 3
   🟡 High: 12
   🟠 Medium: 8
   🟢 Low: 5
   📊 Total: 28

⚠️  RISK ASSESSMENT: HIGH - Significant privacy risks detected

💡 COMPLIANCE RECOMMENDATIONS
   1. 🔴 URGENT: Address all critical PII exposures immediately
   2. Implement comprehensive data protection impact assessment (DPIA)
   3. 🟡 Implement enhanced security controls for high-risk PII
   4. Consider data pseudonymization or anonymization techniques
```

### JSON Report Structure

```json
{
  "analysis_timestamp": "2025-01-20T23:26:00",
  "overall_summary": {
    "summary": {
      "total_endpoints_analyzed": 25,
      "endpoints_with_pii": 18,
      "pii_exposure_rate": 72.0,
      "average_compliance_score": 65.3
    },
    "pii_breakdown": {
      "critical": 3,
      "high": 12,
      "medium": 8,
      "low": 5,
      "total": 28
    },
    "risk_assessment": "HIGH - Significant privacy risks detected",
    "compliance_recommendations": [...]
  },
  "detailed_results": [
    {
      "api_id": "api-123",
      "endpoint_path": "/users/{id}",
      "http_method": "GET",
      "total_pii_found": 5,
      "compliance_score": 75.0,
      "critical_pii": [...],
      "high_pii": [...],
      "recommendations": [...]
    }
  ]
}
```

### Slack Notification Example

```
🔴 PII Monitoring Alert - CRITICAL

API Information
📊 User Management API
ID: api-12345678

PII Changes
🆕 New PII: 3
🗑️ Removed PII: 0
📊 Compliance Change: -25.0%

🔴 New Critical PII
• POST /users: ssn (social_security_number)
• POST /users: credit_card (credit_card_number)

⚡ Urgent Actions Required
• 🔴 URGENT: Review all new critical PII exposures immediately
• Implement data encryption for all critical PII fields
• Conduct security audit of affected endpoints
```

## Compliance Scoring

### Scoring Algorithm

The compliance score is calculated using a penalty-based system:

- **Critical PII**: -25 points per instance
- **High Risk PII**: -15 points per instance
- **Medium Risk PII**: -10 points per instance
- **Low Risk PII**: -5 points per instance

Starting from 100%, the final score is: `max(0, 100 - total_penalties)`

### Score Interpretation

- **90-100%**: ✅ Excellent - Minimal privacy concerns
- **75-89%**: 🟡 Good - Some privacy considerations
- **50-74%**: 🟠 Needs Work - Moderate privacy risks
- **0-49%**: 🔴 Critical - Immediate action required

## Security Recommendations

### Critical PII (SSN, Credit Cards, etc.)
- Implement PCI DSS compliance for payment data
- Use tokenization instead of storing raw values
- Encrypt all data at rest and in transit
- Implement strict access controls and audit logging
- Never log sensitive data in application logs

### High Risk PII (Email, Phone, Address)
- Implement proper input validation and sanitization
- Use hashing for lookups where possible
- Provide opt-out mechanisms for communications
- Follow regional privacy laws (GDPR, CCPA)
- Implement data retention and deletion policies

### General Recommendations
- Conduct regular privacy impact assessments
- Implement privacy by design principles
- Provide privacy training for development teams
- Establish data breach response procedures
- Ensure compliance with applicable regulations

## CI/CD Integration

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    stages {
        stage('PII Analysis') {
            steps {
                script {
                    def exitCode = sh(
                        script: 'python scripts/pii_analysis.py',
                        returnStatus: true
                    )
                    
                    if (exitCode == 2) {
                        error "Critical PII detected - Build failed"
                    } else if (exitCode == 1) {
                        unstable "PII analysis encountered errors"
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'pii_analysis_report.json'
                }
            }
        }
    }
}
```

### Exit Codes

- **0**: Success - No critical issues
- **1**: Error - Analysis failed or encountered problems
- **2**: Critical PII - Critical PII detected, build should fail

## Testing

### Running Tests

```bash
# Run all PII detection tests
python -m pytest tests/test_pii_detector.py -v

# Run with coverage
python -m pytest tests/test_pii_detector.py --cov=core.pii_detector

# Run specific test class
python -m pytest tests/test_pii_detector.py::TestPIIDetector -v
```

### Test Coverage

The test suite includes:
- **Pattern Matching Tests**: Verify PII type detection
- **Schema Analysis Tests**: Test parameter and schema analysis
- **Compliance Scoring Tests**: Validate scoring algorithm
- **Report Generation Tests**: Test summary report creation
- **Dataclass Tests**: Verify data structure functionality

## Demo & Examples

### Running the Demo

```bash
# Run interactive demonstration
python demos/pii_detection_demo.py
```

The demo showcases:
- Analysis of sample APIs with realistic PII data
- Pattern matching demonstration
- Compliance scoring scenarios
- Report generation examples

### Sample Output

The demo analyzes 3 sample APIs and generates comprehensive reports showing:
- 37 PII instances detected across 4 endpoints
- 7 Critical, 16 High, 8 Medium, 6 Low risk PII
- Overall compliance score of 22.5%
- Specific security recommendations

## Configuration

### Environment Variables

```bash
# Database configuration (from existing .env)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=openapi_store
DB_USER=postgres
DB_PASSWORD=your_password

# Slack webhook for notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

### Customization

The PII detector can be customized by:
- Adding new PII patterns to `pii_patterns` dictionary
- Modifying severity mappings in `severity_mapping`
- Updating recommendations in `pii_recommendations`
- Adjusting compliance scoring penalties

## Best Practices

### Development Workflow
1. **Regular Analysis**: Run PII analysis on all API changes
2. **Pre-deployment Checks**: Include PII detection in CI/CD pipelines
3. **Compliance Reviews**: Regular audits of PII exposure
4. **Team Training**: Educate developers on privacy risks

### Privacy by Design
1. **Data Minimization**: Only collect necessary PII
2. **Purpose Limitation**: Use PII only for stated purposes
3. **Storage Limitation**: Implement data retention policies
4. **Security**: Encrypt and protect all PII data
5. **Transparency**: Provide clear privacy policies

### Incident Response
1. **Detection**: Automated alerts for new critical PII
2. **Assessment**: Evaluate privacy impact of changes
3. **Mitigation**: Implement security controls immediately
4. **Documentation**: Record all privacy-related decisions
5. **Monitoring**: Continuous monitoring of PII exposure

## Troubleshooting

### Common Issues

**Issue**: PII not detected in expected fields
- **Solution**: Check pattern matching rules, add custom patterns if needed

**Issue**: False positives in PII detection
- **Solution**: Refine patterns or adjust confidence thresholds

**Issue**: Database connection errors
- **Solution**: Verify database configuration in .env file

**Issue**: Slack notifications not working
- **Solution**: Check SLACK_WEBHOOK_URL configuration

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

### Planned Features
- **Machine Learning**: AI-powered PII detection for better accuracy
- **Custom Rules**: User-defined PII patterns and classifications
- **Data Flow Mapping**: Track PII flow across API endpoints
- **Compliance Templates**: Pre-built templates for GDPR, CCPA, etc.
- **Integration APIs**: REST APIs for external tool integration

### Contributing

To contribute to the PII detection system:
1. Add new PII patterns to the detector
2. Implement additional compliance frameworks
3. Enhance reporting capabilities
4. Add integration with more notification systems
5. Improve test coverage and documentation

## Support

For questions or issues with the PII detection system:
1. Check this documentation first
2. Review the demo and test files for examples
3. Check the project's issue tracker
4. Consult the existing memories for implementation details

---

**Remember**: PII detection is a critical security feature. Always validate results and implement appropriate security measures for any detected PII.
