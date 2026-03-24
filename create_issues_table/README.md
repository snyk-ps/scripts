# Create Group Issues Table

## Description

This script fetches security issues from the Snyk REST API for a specific group and generates a CSV table containing issue details across all organizations within that group. It filters for issues with high or critical severity levels and includes information about the group, organization, projects, issue identifiers, creation dates, and severity levels.

## Installation

### Prerequisites

- curl (Used for making HTTP requests to the Snyk API.)
- jq (for JSON processing)

### Setup

1. Ensure the script is executable:
   ```bash
   chmod +x create-group-issues-table.sh
   ```

2. Set your Snyk API token as an environment variable:
   ```bash
   export SNYK_TOKEN="your-snyk-api-token"
   ```

3. Optional: Set a custom API URL if not using the default Snyk cloud:
   ```bash
   export SNYK_API_URL="https://your-custom-api.url/rest"
   ```

## Usage

### Basic Usage

Fetch issues for a group and save to the default filename (group-issues-table.csv):

```bash
sh ./create-group-issues-table.sh <group_id>
```

### Custom Output File

Specify a custom output filename:

```bash
sh ./create-group-issues-table.sh <group_id> custom-issues.csv
```

### Examples

Fetch issues for group "0708d6a5-c79a-4f28-9fde-b7126a5c7252":

```bash
sh ./create-group-issues-table.sh 0708d6a5-c79a-4f28-9fde-b7126a5c7252
```

## Output

The script generates a CSV file with the following columns:

- `group_id` - Group identifier
- `org_id` - Organization identifier
- `project_id` - Project identifier
- `issue_id` - Snyk issue identifier
- `created_at` - Issue creation timestamp (ISO 8601 format)
- `severity` - Issue severity level (high or critical)

### Example Output

| group_id | org_id | project_id | issue_id | created_at | severity |
|----------|--------|--------|----------|----------|----------|
| 0708d6a5-c79a-4f28-9fde-b7126a5c7252 | 1b68fd5f-9f20-4301-8668-4ceee0a13e08 | 6bf941c7-0d60-491a-8695-b7608f6d49ee | SNYK-JS-VM2-5772823 | 2025-04-29T17:58:10.439Z | critical |
| 0708d6a5-c79a-4f28-9fde-b7126a5c7252 | 1b68fd5f-9f20-4301-8668-4ceee0a13e08 | 6bf941c7-0d60-491a-8695-b7608f6d49ee | SNYK-JS-MARSDB-480405 | 2025-04-29T17:58:10.439Z | critical |

## Error Handling

The script uses strict error handling and will exit if:
- The group ID is not provided
- The SNYK_TOKEN environment variable is not set
- The API returns an error response

All errors are reported to stderr for proper logging integration.

## Author

Torsten Cannell, torsten.cannell@snyk.io

## Last Updated

2026-03-24
