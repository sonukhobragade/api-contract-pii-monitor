# API Release Tracking and Schema Change Detection Features

## Overview
I've enhanced the APIPostgres application with comprehensive release tracking and schema change detection capabilities. This allows you to:

- Track API versions and releases
- Detect schema changes between versions
- Monitor breaking changes
- Batch process large APIs to prevent database locks
- Get detailed logging during API parsing

## New Database Tables

### 1. Enhanced `apis` Table
Added new columns:
- `release_tag` - Version tag for the API release (e.g., "v1.2.0-20250720")
- `schema_hash` - SHA256 hash of the entire schema for change detection
- `is_latest` - Boolean flag indicating if this is the latest version
- `status` - API status: 'active', 'deprecated', or 'archived'

### 2. `schema_changes` Table
Tracks all schema changes:
- `api_id` - Reference to the API
- `endpoint_id` - Reference to specific endpoint (if applicable)
- `change_type` - Type of change (api_added, endpoint_updated, request_schema_changed, etc.)
- `old_value` - Previous value (JSON)
- `new_value` - New value (JSON)
- `release_tag` - Release where the change was detected
- `change_description` - Human-readable description
- `detected_at` - Timestamp of detection

### 3. `api_releases` Table
Tracks API releases:
- `api_id` - Reference to the API
- `release_tag` - Release identifier
- `release_notes` - Description of the release
- `schema_hash` - Hash of the schema for this release
- `endpoint_count` - Number of endpoints in this release
- `breaking_changes` - Boolean indicating if breaking changes exist

## New Features

### 1. Release Tracking
- Automatic generation of release tags based on version and date
- Schema hashing to detect identical APIs
- Marking previous versions as non-latest when new versions are added

### 2. Schema Change Detection
- Detects changes in request/response schemas
- Tracks parameter modifications
- Identifies breaking vs non-breaking changes
- Records all changes with timestamps and descriptions

### 3. Batching and Performance
- Processes components in batches of 50 to prevent database locks
- Commits every 10 endpoints during path parsing
- Detailed logging to track progress
- Prevents hanging on large API schemas

### 4. Enhanced Logging
- Detailed progress tracking during API parsing
- Shows API title, version, and description
- Tracks component and endpoint processing
- Reports batch processing status
- Shows schema hash and release information

## New Query Methods

### `get_api_releases(api_id=None)`
Get all releases for an API or all APIs with change statistics.

### `get_schema_changes(api_id=None, release_tag=None, change_type=None)`
Query schema changes with filtering options.

### `get_latest_apis()`
Get all latest API versions with their release information.

### `get_api_change_summary(api_id)`
Get a comprehensive summary of changes for a specific API.

## Usage Examples

### Track API Changes
```python
querier = OpenAPIQuerier(connection_string)

# Get all releases for a specific API
releases = querier.get_api_releases(api_id="your-api-id")

# Get schema changes for a release
changes = querier.get_schema_changes(release_tag="v1.2.0-20250720")

# Get breaking changes only
breaking_changes = querier.get_schema_changes(
    change_type="request_schema_changed"
)
```

### Monitor Latest APIs
```python
# Get all active latest APIs
latest_apis = querier.get_latest_apis()
for api in latest_apis:
    print(f"API: {api['title']} v{api['version']}")
    print(f"Release: {api['release_tag']}")
    print(f"Breaking Changes: {api['breaking_changes']}")
```

### Detect Changes
When you run the same API schema again, the system will:
1. Calculate the schema hash
2. Compare with existing versions
3. Skip processing if identical
4. Create new version if different
5. Record all detected changes

## Benefits

1. **Change Tracking**: Know exactly what changed between API versions
2. **Breaking Change Detection**: Identify changes that might break clients
3. **Performance**: Batching prevents database locks on large APIs
4. **Audit Trail**: Complete history of all API changes
5. **Release Management**: Track API releases with proper versioning
6. **Duplicate Prevention**: Avoid storing identical schemas multiple times

## Files Updated

1. `ApiPostgres.py` - Main application with new features
2. `update_schema_for_releases.py` - Schema migration script
3. `fix_constraint.py` - Constraint fix for component types

## Running the Enhanced System

1. First, update your existing database schema:
   ```bash
   python update_schema_for_releases.py
   ```

2. Run the enhanced API parser:
   ```bash
   python ApiPostgres.py
   ```

The system will now provide detailed logging and track all changes automatically!
