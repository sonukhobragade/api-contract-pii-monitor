# Simple PII Dashboard - Modular Version

A clean, modular PII security dashboard with proper component separation.

## 🏗️ Architecture

```
simple_dashboard/
├── components/           # Reusable UI components
│   ├── data_loader.py   # Data loading and filtering
│   ├── schema_utils.py  # Schema generation and PII highlighting
│   └── ui_components.py # UI display components
├── pages/               # Page components
│   ├── overview_page.py # Overview page logic
│   └── analysis_page.py # Analysis page logic
├── utils/               # Utility functions (future use)
├── main.py             # Main dashboard orchestrator
└── README.md           # This file
```

## 🚀 Features

### 📊 Overview Page
- **Overall Summary** - Total endpoints, PII counts, risk score
- **API Breakdown** - Grouped by API with expandable sections
- **PII Endpoints List** - All endpoints with PII details

### 🔍 Analysis Page
- **Risk Level Filtering** - Filter by Critical/High/Medium/Low risk
- **Endpoint Selection** - Choose from filtered endpoints
- **Schema Display** - Simple JSON schemas with PII highlighting
- **PII Details** - Field-level PII information

## 🎯 Components

### Data Loader (`components/data_loader.py`)
- `load_sample_data()` - Load sample PII analysis data
- `filter_endpoints_by_risk()` - Filter endpoints by risk level
- `calculate_overall_metrics()` - Calculate summary metrics
- `group_endpoints_by_api()` - Group endpoints by API

### Schema Utils (`components/schema_utils.py`)
- `generate_simple_json_schema()` - Convert complex OpenAPI to simple JSON
- `highlight_pii_in_simple_json()` - Add PII highlighting to schemas
- `get_schema_from_database()` - Fetch schemas from database

### UI Components (`components/ui_components.py`)
- `display_metrics_row()` - Display metrics in columns
- `display_api_breakdown()` - Show API grouping
- `create_endpoint_selector()` - Create endpoint dropdown
- `display_schema_tabs()` - Show request/response schemas

## 🚀 Usage

### Run the Dashboard
```bash
# From project root
python run_modular_dashboard.py
```

### Access the Dashboard
- **URL**: http://localhost:8503
- **Port**: 8503 (different from original dashboard)

## 🔧 Benefits

1. **Modular Design** - Clean separation of concerns
2. **Reusable Components** - Easy to maintain and extend
3. **Scalable Architecture** - Easy to add new pages/features
4. **Better Organization** - Clear file structure
5. **Maintainable Code** - Each component has a single responsibility

## 🎨 UI Features

- **Risk-based Filtering** - Filter endpoints by PII risk level
- **Visual Indicators** - 🔴🟡🟠✅ for different risk levels
- **Expandable Sections** - Collapsible API breakdowns
- **Schema Highlighting** - PII fields highlighted in JSON
- **Responsive Layout** - Works on different screen sizes

## 🔄 Navigation

- **Sidebar Navigation** - Switch between Overview and Analysis
- **Risk Level Filter** - Filter endpoints by risk in Analysis page
- **Endpoint Selection** - Choose specific endpoints for detailed view

## 📈 Metrics Display

- **Total Endpoints** - Count of all analyzed endpoints
- **Critical PII** - Number of critical PII fields
- **High PII** - Number of high-risk PII fields
- **Risk Score** - Weighted risk calculation
- **API Breakdown** - Per-API statistics
