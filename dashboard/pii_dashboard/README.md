# PII Analysis Dashboard

An interactive Streamlit dashboard for visualizing Personally Identifiable Information (PII) detected in API schemas.

## Features

- **Overall Summary**: View key metrics and PII breakdown by severity
- **API-Level Analysis**: Analyze PII findings for specific APIs
- **Endpoint Analysis**: Explore PII findings at the endpoint level with filtering
- **Compliance Recommendations**: View actionable recommendations based on findings
- **Interactive Filtering**: Filter data by API, severity level, and more
- **Data Visualization**: Interactive charts and tables for data exploration

## Requirements

- Python 3.8+
- Streamlit 1.28.0+
- Plotly 5.17.0+
- Pandas 2.0.0+
- NumPy 1.24.0+

## Usage

### Running the Dashboard

You can run the dashboard using the launcher script:

```bash
python run_pii_dashboard.py
```

Or directly with Streamlit:

```bash
streamlit run dashboard/pii_dashboard/app.py
```

### Command Line Arguments

When using the launcher script, you can specify the following arguments:

- `--port`: Port to run the Streamlit dashboard on (default: 8501)
- `--file`: Path to the PII analysis report file (default: fast_pii_analysis_report.json)

Example:

```bash
python run_pii_dashboard.py --port 8502 --file custom_pii_report.json
```

### Dashboard Interface

1. **File Selection**: Specify the path to your PII analysis JSON file
2. **Overall Summary**: View key metrics and charts for all APIs
3. **API-Level Analysis**: Select an API to view detailed metrics
4. **Endpoint Analysis**: Filter and explore endpoint-level PII findings
5. **Compliance Recommendations**: View actionable recommendations

## Data Format

The dashboard expects a JSON file with the following structure:

```json
{
  "analysis_timestamp": "2025-08-09T12:42:52.854035",
  "processing_time_seconds": 0.65,
  "endpoints_per_second": 2123.6,
  "overall_summary": {
    "summary": {
      "total_endpoints_analyzed": 1387,
      "endpoints_with_pii": 599,
      "pii_exposure_rate": 43.2,
      "average_compliance_score": 85.5
    },
    "pii_breakdown": {
      "critical": 11,
      "high": 617,
      "medium": 1595,
      "low": 389,
      "total": 2612
    },
    "most_common_pii_types": [
      ["full_name", 1520],
      ["user_id", 389],
      ["physical_address", 345],
      ["email_address", 134],
      ["phone_number", 132]
    ],
    "risk_assessment": "CRITICAL - Immediate action required",
    "compliance_recommendations": [
      "🔴 URGENT: Address all critical PII exposures immediately",
      "Implement comprehensive data protection impact assessment (DPIA)",
      "Review and update privacy policies and consent mechanisms"
    ]
  },
  "api_summaries": {
    "api-id-1": {
      "title": "API Title",
      "endpoints_analyzed": 1178,
      "total_pii_found": 2250,
      "critical_pii": 11,
      "high_pii": 562,
      "medium_pii": 1337,
      "low_pii": 340,
      "avg_compliance_score": 85.6
    }
  },
  "detailed_results": [
    {
      "api_id": "api-id-1",
      "api_title": "API Title",
      "endpoint_path": "/path/to/endpoint",
      "http_method": "GET",
      "total_pii_found": 3,
      "critical_pii": [],
      "high_pii": [
        {
          "pii_type": "email_address",
          "severity": "high",
          "field_name": "email",
          "field_path": "user.email",
          "context": "response_default_resolved",
          "description": "PII detected in resolved response schema",
          "pattern_matched": "email",
          "confidence": 1.0,
          "recommendations": []
        }
      ],
      "medium_pii": [],
      "low_pii": [],
      "compliance_score": 85.0,
      "recommendations": [
        "Implement enhanced security controls for high-risk PII"
      ]
    }
  ]
}
```

## Customization

You can customize the dashboard by modifying the following files:

- `app.py`: Main Streamlit application
- `utils.py`: Utility functions for data processing and visualization

## Integration with PII Analysis

This dashboard is designed to work with the output of the `fast_pii_analysis.py` script. Run the script first to generate the PII analysis report:

```bash
python scripts/fast_pii_analysis.py --output-file pii_report.json
```

Then run the dashboard with the generated report:

```bash
python run_pii_dashboard.py --file pii_report.json
```