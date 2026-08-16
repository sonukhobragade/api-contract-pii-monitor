# API Change Notification Format

This document describes the format and structure of API change notifications sent by the Schema Monitor.

## Overview

The Schema Monitor sends notifications when changes are detected in API schemas. These notifications are sent to Slack and are also included in Jenkins reports. The notifications include detailed information about the changes, including:

- Summary of changes across all APIs
- API-by-API breakdown of changes
- Detailed information about endpoint, parameter, response, and component changes
- Breaking vs non-breaking change indicators
- Endpoint coverage statistics

## Notification Format

### Header Section

```
✅ True Zero-Insertion Schema Monitor Report

📅 Timestamp: 2025-08-11T14:09:03.131588
📊 Status: BREAKING CHANGES DETECTED
📋 APIs Monitored: 2
🔄 APIs Changed: 1
✅ APIs Unchanged: 1
📈 Total Changes: 6
⚠️ Breaking Changes: 1
❌ Errors: 0
```

### Change Summary Section

```
📊 CHANGE SUMMARY (1 API affected)
⚠️ 1 BREAKING CHANGE DETECTED

📊 Total Changes: 6
⚠️ Breaking Changes: 1

📍 Change Breakdown:
   🔗 Endpoints: ✅ Changed (1)
   📋 Parameters: ❌ No Changes (0)
   📤 Responses: ✅ Changed (1)
   🧩 Components: ✅ Changed (4)
```

### Detailed Changes Section

#### Endpoint Changes

```
🔗 ENDPOINT CHANGES:
   ➕ ADDED: POST /orders
      └─ New endpoint added to API
```

#### Response Changes

```
📤 RESPONSE CHANGES:
   📌 API: Billing API (URI: Newly Added)
   ➕ NEW RESPONSE: Newly Added Component
      └─ Purpose: Response added: default for POST /orders
```

#### Component Changes

```
🧩 SCHEMA COMPONENTS:
   📌 API: Billing API (URI: Newly Added)
   ➕ NEW SCHEMA: OrderResponse
      └─ Purpose: Component added: schemas/OrderResponse
      └─ Optional fields: 3 additional fields
```

### Endpoint Coverage Section

```
📍 Endpoint Coverage Showcase:
   📊 Orders API: 84 endpoints (ID: 11111111...)
   📊 Billing API: 36 endpoints (ID: 22222222...)
   🔢 TOTAL ENDPOINTS: 120
```

### Efficiency Metrics Section

```
🔒 Efficiency Metrics:
   • Database Operations Avoided: 1
   • Hash Comparisons: 2
   • Strategy: Zero DB operations until changes confirmed
```

## Special Handling for Newly Added Elements

The notification system has been enhanced to provide clear and professional reporting for newly added API elements:

### Newly Added APIs

- When a new API is detected, its ID is displayed as "Newly Added" instead of "unknown-id"
- Example: `📌 API: Billing API (URI: Newly Added)`

### Newly Added Endpoints

- New endpoints are clearly marked with the ➕ emoji and "ADDED" label
- The description explicitly states "New endpoint added to API"
- Example: 
  ```
  ➕ ADDED: POST /orders
     └─ New endpoint added to API
  ```

### Newly Added Responses

- New responses are clearly marked with the ➕ emoji and "NEW RESPONSE" label
- If the component name is not available, "Newly Added Component" is used instead of "N/A"
- Example:
  ```
  ➕ NEW RESPONSE: Newly Added Component
     └─ Purpose: Response added: default for POST /orders
  ```

### Newly Added Components

- New components are clearly marked with the ➕ emoji and "NEW SCHEMA" label
- The description provides context about the purpose of the component
- Details about required and optional fields are included
- Example:
  ```
  ➕ NEW SCHEMA: OrderResponse
     └─ Purpose: Component added: schemas/OrderResponse
     └─ Optional fields: 3 additional fields
  ```

## Testing

A test script is available to verify the notification format and send test notifications to Slack:

```bash
# Test the notification format
python tests/test_new_element_formatting.py

# Send a test notification to Slack
python tests/test_new_element_formatting.py --send-to-slack
```

## Benefits of the Enhanced Format

- ✅ Clear visibility into exactly what changed
- ✅ Professional presentation for stakeholders
- ✅ No ambiguous placeholders like "unknown-id" or "N/A"
- ✅ Breaking vs non-breaking change classification
- ✅ Detailed information about newly added elements
- ✅ Comprehensive Jenkins artifacts for CI/CD integration
