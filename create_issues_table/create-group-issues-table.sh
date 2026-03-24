#!/usr/bin/env bash

################################################################################
# Purpose: Fetch issues from Snyk REST API by Group ID and create a CSV table.
# Author: Torsten Cannell, torsten.cannell@snyk.io
# Usage: sh ./create-group-issues-table.sh <group_id> [output_file]
#
# Output CSVs under this directory are gitignored (see repo .gitignore); do not commit them.
#
# Revision History:
# 2026-03-24: Initial version
################################################################################

# Strict mode for robust error handling
set -e
set -u
set -o pipefail

# Constants
readonly BASE_URL="${SNYK_API_URL:-https://api.snyk.io/rest}"
readonly API_VERSION="${API_VERSION:-2024-10-15}"

# Global user-defined variables from environment/arguments
group_id="${1:-}"
output_file="${2:-group-issues-table.csv}"
snyk_token="${SNYK_TOKEN:-}"

validate_inputs() {
    if [[ -z "$group_id" ]]; then
        printf "Error: group_id is required\n" >&2
        printf "Usage: %s <group_id> [output_file]\n" "$0" >&2
        exit 1
    fi

    if [[ -z "$snyk_token" ]]; then
        printf "Error: SNYK_TOKEN environment variable is not set\n" >&2
        exit 1
    fi
}

fetch_group_issues() {
    local current_url
    local page_count
    local response
    local next_page

    # Endpoint as per Snyk REST spec for Group Issues
    current_url="${BASE_URL}/groups/${group_id}/issues"
    current_url="${current_url}?version=${API_VERSION}&limit=100"
    current_url="${current_url}&effective_severity_level=high,critical"
    
    page_count=0

    # Create CSV header including Group ID and Organization ID
    printf "group_id,org_id,project_id,issue_id,created_at,severity\n" > "$output_file"

    printf "Fetching issues for group: %s\n" "$group_id"

    while [[ -n "$current_url" ]]; do
        page_count=$((page_count + 1))
        printf "Fetching page %d...\n" "$page_count"
        
        # Fetch data using token auth
        response=$(curl -s -L \
            -H "Authorization: token $snyk_token" \
            "$current_url")
        
        # Check for API-level errors
        if printf "%s" "$response" | jq -e '.errors' > /dev/null 2>&1; then
            local err_msg
            err_msg=$(printf "%s" "$response" | \
                jq -r '.errors[0].detail // "Unknown Error"')
            printf "Error in API response: %s\n" "$err_msg" >&2
            exit 1
        fi
        
        # Extract issues and append to CSV
        # Maps Group ID as first column and Org ID from relationships
        printf "%s" "$response" | jq -r --arg group "$group_id" '.data[]? | 
            [
                $group,
                .relationships.organization.data.id // "N/A",
                .relationships.scan_item.data.id // "N/A",
                .attributes.key,
                .attributes.created_at,
                .attributes.effective_severity_level // "N/A"
            ] | @csv' >> "$output_file"
        
        # Determine next page URL from JSON:API links object
        next_page=$(printf "%s" "$response" | jq -r '.links.next // empty')
        
        if [[ -n "$next_page" ]]; then
            if [[ "$next_page" == http* ]]; then
                current_url="$next_page"
            else
                current_url="https://api.snyk.io${next_page}"
            fi
        else
            current_url=""
        fi
    done

    printf "✓ Group issues table created: %s\n" "$output_file"
    printf "  Total pages processed: %d\n" "$page_count"
    printf "  Total issues: %d\n" "$(($(wc -l < "$output_file") - 1))"
}

main() {
    validate_inputs
    fetch_group_issues
}

main "$@"