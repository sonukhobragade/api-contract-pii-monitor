# Jenkins Setup Guide for Nightly Schema Monitoring

## 🎯 Overview
This guide explains how to set up Jenkins to run nightly schema monitoring that will:
- Fetch fresh schemas from your APIs every night
- Compare with existing database versions
- Detect and report schema changes
- Update database with new versions
- Generate detailed reports
- Send notifications for breaking changes

## 📋 Prerequisites

### 1. Jenkins Server Requirements
- Jenkins 2.400+ with Pipeline plugin
- Python 3.8+ installed on Jenkins agents
- Network access to your database and API endpoints
- Email/Slack configuration for notifications

### 2. Required Jenkins Plugins
```bash
# Install these plugins in Jenkins
- Pipeline
- HTML Publisher
- Email Extension
- Slack Notification (optional)
- Build Timeout
- Timestamper
```

## 🔧 Setup Steps

### Step 1: Create Jenkins Job

1. **Create New Pipeline Job**
   ```
   Jenkins Dashboard → New Item → Pipeline → Enter name: "Nightly-Schema-Monitor"
   ```

2. **Configure Pipeline**
   - **Definition**: Pipeline script from SCM
   - **SCM**: Git
   - **Repository URL**: Your repository URL
   - **Script Path**: `jenkins/Jenkinsfile`

### Step 2: Environment Configuration

1. **Add Environment Variables in Jenkins**
   ```
   Manage Jenkins → Configure System → Global Properties → Environment Variables
   ```
   
   Add these variables:
   ```
   DEFAULT_RECIPIENTS=your-team@company.com
   SLACK_CHANNEL=#api-monitoring
   ```

2. **Add Credentials**
   ```
   Manage Jenkins → Manage Credentials → Add Credentials
   ```
   
   Add:
   - Database credentials (if needed)
   - API tokens (if needed)
   - Email server credentials
   - Slack token (if using Slack)

### Step 3: Configure .env File

Ensure your `.env` file is properly configured in the repository:
```env
# Database Configuration
HOST=localhost
PORT=5432
USERNAME=postgres
PASSWORD=your_password
DB_NAME=openapi_store

# API Endpoints
QA_ENDPOINT=https://your-qa-server.com
AUTHORIZATION_TOKEN=Bearer your_token_here
OPENAPI_SPEC_PRIMARY=https://your-api-gateway.com/openapi.json
OPENAPI_SPEC_SECONDARY=https://your-modular-api.com/openapi.json
```

### Step 4: Test the Setup

1. **Manual Test Run**
   ```bash
   # On your local machine or Jenkins agent
   cd /path/to/project
   python scripts/nightly_schema_monitor.py
   ```

2. **Jenkins Test Build**
   - Go to your Jenkins job
   - Click "Build Now"
   - Check console output and reports

## 📊 Understanding the Reports

### Exit Codes
- **0**: Success - No breaking changes
- **1**: Unstable - Breaking changes or warnings detected
- **2**: Failure - Critical errors occurred

### Report Files Generated
```
reports/
├── nightly_schema_report_YYYYMMDD_HHMMSS.json    # Detailed JSON report
├── nightly_schema_report_YYYYMMDD_HHMMSS.html    # HTML report for viewing
├── jenkins_exit_code.txt                         # Exit code for Jenkins
└── jenkins_build_summary.txt                     # Build description
```

### HTML Report Sections
1. **Summary**: Overview of monitoring results
2. **API Details**: Per-API change analysis
3. **Validation Results**: Schema validation success rates
4. **Recommendations**: Actionable next steps

## 🚨 Alert Configuration

### Email Notifications
The pipeline sends emails for:
- **UNSTABLE builds**: Schema changes detected
- **FAILED builds**: Critical errors occurred

Email includes:
- Summary of changes
- Build status and URL
- HTML report attachment

### Slack Notifications
Configure Slack for real-time alerts:
```groovy
slackSend(
    channel: '#api-monitoring',
    color: 'warning',
    message: "⚠️ Schema changes detected in nightly monitoring"
)
```

## 📈 Monitoring Dashboard

### Jenkins Build History
- **Green**: No changes detected
- **Yellow**: Schema changes found (review needed)
- **Red**: Critical errors (immediate attention)

### Build Trends
Monitor these metrics over time:
- Number of APIs with changes
- Breaking vs non-breaking changes
- Schema validation success rates
- Error frequency

## 🔄 Workflow Integration

### Daily Process
```
2:00 AM → Jenkins triggers nightly job
2:01 AM → Fetch fresh schemas from APIs
2:02 AM → Compare with database versions
2:03 AM → Detect and analyze changes
2:04 AM → Update database if changes found
2:05 AM → Generate reports
2:06 AM → Send notifications if needed
2:07 AM → Archive reports and artifacts
```

### Team Workflow
1. **No Changes**: Team receives no notifications
2. **Non-Breaking Changes**: Team reviews reports during daily standup
3. **Breaking Changes**: Immediate Slack/email alerts sent
4. **Critical Errors**: On-call engineer notified

## 🛠 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check database connectivity
   python -c "from core.config import config; print(config.get_connection_string())"
   ```

2. **API Endpoint Unreachable**
   ```bash
   # Test API endpoints
   curl -H "Authorization: Bearer your_token" https://your-api.com/openapi.json
   ```

3. **Schema Parsing Errors**
   ```bash
   # Test schema parsing manually
   python scripts/parse_multiple_apis.py
   ```

### Debug Mode
Run with verbose logging:
```bash
python scripts/nightly_schema_monitor.py --debug
```

## 📋 Maintenance

### Weekly Tasks
- Review accumulated reports
- Update API endpoint configurations
- Check database storage usage
- Validate notification channels

### Monthly Tasks
- Archive old reports
- Update dependencies
- Review monitoring effectiveness
- Optimize detection rules

## 🎯 Success Metrics

Track these KPIs:
- **Detection Rate**: % of actual changes caught
- **False Positive Rate**: % of non-issues flagged
- **Response Time**: Time from detection to team action
- **Database Health**: Storage and performance metrics

## 📞 Support

### Log Locations
- Jenkins console: `${BUILD_URL}/console`
- HTML reports: `${BUILD_URL}/Schema_Monitoring_Report/`
- JSON reports: Build artifacts

### Emergency Contacts
- Database issues: DBA team
- API issues: API team
- Jenkins issues: DevOps team
- Schema questions: Architecture team

---

This setup provides a complete nightly monitoring solution that will automatically detect schema changes and keep your team informed about API evolution!
