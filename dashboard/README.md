# 🔒 PII Security Dashboard

Interactive Streamlit dashboard for visualizing and analyzing PII (Personally Identifiable Information) security findings across your APIs.

## 🚀 Features

### 📊 **Interactive Visualizations**
- **PII Severity Distribution** - Bar chart showing Critical, High, Medium, Low PII counts
- **Compliance Score Gauge** - Visual gauge showing overall compliance percentage
- **API Breakdown** - Stacked bar chart showing PII distribution across APIs
- **PII Types Analysis** - Pie chart showing distribution of PII types (SSN, Email, Phone, etc.)

### 📈 **Real-time Metrics**
- Total endpoints analyzed
- Endpoints with PII exposure
- Average compliance score
- Total PII instances found
- Processing time and speed

### 🔍 **Detailed Findings**
- **Critical PII Endpoints** - Expandable sections with detailed PII information
- **High PII Summary** - Table view of high-risk endpoints
- **Field-level Details** - Specific PII fields and their locations

### 📤 **Export Options**
- **JSON Export** - Download complete analysis results
- **CSV Export** - Download detailed results as spreadsheet
- **Slack Integration** - Send reports directly to Slack

## 🎯 **Dashboard Sections**

### 1. **Summary Metrics**
Quick overview of key security metrics with color-coded risk levels.

### 2. **Risk Assessment Alerts**
- 🚨 **Critical Risk** - Immediate action required
- ⚠️ **High Risk** - Action recommended
- ✅ **Low Risk** - Good compliance

### 3. **Interactive Charts**
- **Severity Distribution** - Visual breakdown of PII by risk level
- **Compliance Gauge** - Real-time compliance score with color zones
- **API Comparison** - Side-by-side comparison of APIs

### 4. **Detailed Analysis**
- **Critical PII Details** - Expandable sections for each critical endpoint
- **Field Information** - Specific PII fields, paths, and contexts
- **Compliance Scores** - Individual endpoint compliance ratings

## 🚀 **How to Launch**

### **Option 1: Using the Launcher Script**
```bash
# Activate virtual environment
source venv/bin/activate

# Run the dashboard
python run_dashboard.py
```

### **Option 2: Direct Streamlit Command**
```bash
# Activate virtual environment
source venv/bin/activate

# Run streamlit directly
streamlit run dashboard/pii_security_dashboard.py
```

### **Option 3: Custom Port**
```bash
streamlit run dashboard/pii_security_dashboard.py --server.port 8502
```

## 🌐 **Access the Dashboard**

Once launched, the dashboard will be available at:
- **Local:** http://localhost:8501
- **Network:** http://your-ip:8501

## 📱 **Dashboard Controls**

### **Sidebar Options**
- **🔄 Refresh Analysis** - Re-run PII analysis and update dashboard
- **📊 Real-time Updates** - Dashboard updates automatically

### **Export Functions**
- **📄 Export to JSON** - Download complete analysis data
- **📊 Export to CSV** - Download results as spreadsheet
- **📱 Send to Slack** - Send report to configured Slack channel

## 🎨 **Visual Design**

### **Color Coding**
- 🔴 **Critical** - Red (#d32f2f)
- 🟡 **High** - Orange (#ff9800)
- 🟠 **Medium** - Yellow (#ffc107)
- 🟢 **Low** - Green (#4caf50)

### **Risk Alerts**
- **Critical Alert Box** - Red background with warning icon
- **High Alert Box** - Orange background with caution icon
- **Success Messages** - Green with checkmark icons

## 📊 **Data Sources**

The dashboard connects to:
- **Database:** PostgreSQL with OpenAPI schemas
- **Analysis Engine:** FastPIIAnalyzer for real-time scanning
- **Slack Integration:** SlackPIIManager for notifications

## 🔧 **Configuration**

The dashboard uses the same configuration as the main application:
- **Database settings** from `core/config.py`
- **Slack settings** from environment variables
- **Analysis parameters** from FastPIIAnalyzer

## 📈 **Performance**

- **Real-time Analysis** - Runs PII analysis on-demand
- **Fast Processing** - Processes 1000+ endpoints per second
- **Interactive Charts** - Smooth zoom, pan, and hover interactions
- **Responsive Design** - Works on desktop and mobile

## 🛠️ **Troubleshooting**

### **Dashboard Won't Load**
1. Check if virtual environment is activated
2. Verify all dependencies are installed: `pip install streamlit plotly pandas numpy`
3. Check if port 8501 is available

### **No Data Displayed**
1. Verify database connection in `core/config.py`
2. Check if APIs are available in the database
3. Try refreshing the analysis

### **Charts Not Rendering**
1. Check browser console for JavaScript errors
2. Verify Plotly is installed: `pip install plotly`
3. Try clearing browser cache

## 📚 **Integration**

The dashboard integrates with:
- **FastPIIAnalyzer** - For PII detection and analysis
- **SlackPIIManager** - For Slack notifications
- **Database** - For OpenAPI schema storage
- **Export Functions** - For data sharing

## 🎯 **Use Cases**

1. **Security Audits** - Comprehensive PII risk assessment
2. **Compliance Monitoring** - Track compliance scores over time
3. **API Development** - Identify PII issues during development
4. **Incident Response** - Quick assessment of PII exposure
5. **Stakeholder Reporting** - Visual reports for management

---

**🔒 Secure your APIs with real-time PII monitoring!**
