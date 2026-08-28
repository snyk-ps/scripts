#!/bin/sh

################################################################################
# Purpose: Run snyk monitor, parse the project ID from CLI output, and fetch
#          issues for the monitored project via the Snyk API.
# Author: Torsten Cannell, torsten.cannell@snyk.io
# Usage: sh ./monitor-fetch-issues.sh [options] [-- snyk monitor args...]
#
# Revision History:
# 2026-08-26: Initial version
# 2026-08-27: POSIX sh compatibility; --all-projects support; jq pagination fix
# 2026-08-27: Default to package_vulnerability issues (not license)
# 2026-08-27: Parse project ID from uri; clean monitor JSON; V1 aggregated-issues
################################################################################

set -e
set -u
set -o pipefail

V1_BASE="${SNYK_V1_API_URL:-https://api.snyk.io/v1}"
DEFAULT_ISSUE_TYPE="package_vulnerability"

snyk_token="${SNYK_TOKEN:-}"
org_id="${SNYK_ORG:-}"
output_file=""
issue_type="${SNYK_ISSUE_TYPE:-$DEFAULT_ISSUE_TYPE}"

usage() {
    cat <<'EOF'
Usage: monitor-fetch-issues.sh [options] [-- snyk monitor args...]

Run snyk monitor, parse the project ID from JSON output, and fetch issues
for that project from the Snyk V1 aggregated-issues API.

Options:
  --org ORG_ID       Organization ID or slug (overrides monitor output)
  --output FILE      Write issues JSON to FILE (default: stdout)
  --issue-type TYPE  Issue type filter (default: package_vulnerability).
                     One of: package_vulnerability, license, all
  --all-issue-types  Same as --issue-type all
  -h, --help         Show this help message

Environment:
  SNYK_TOKEN         Required. Snyk API token.
  SNYK_ORG           Optional default organization ID or slug.
  SNYK_ISSUE_TYPE    Issue type filter (default: package_vulnerability)
  SNYK_V1_API_URL    V1 API base URL (default: https://api.snyk.io/v1)

Examples:
  sh ./monitor-fetch-issues.sh
  sh ./monitor-fetch-issues.sh --org <ORG_ID> /path/to/project
  sh ./monitor-fetch-issues.sh data/juice-shop --all-projects
  sh ./monitor-fetch-issues.sh --output issues.json -- --project-name=my-app

Any arguments after "--" are passed to snyk monitor (the script always adds
--json so project metadata can be parsed reliably).
EOF
}

require_command() {
    cmd=$1
    if ! command -v "$cmd" >/dev/null 2>&1; then
        printf "Error: required command not found: %s\n" "$cmd" >&2
        exit 1
    fi
}

validate_inputs() {
    if [ -z "$snyk_token" ]; then
        printf "Error: SNYK_TOKEN environment variable is not set\n" >&2
        exit 1
    fi

    require_command snyk
    require_command curl
    require_command jq
}

validate_issue_type() {
    case "$issue_type" in
        package_vulnerability|license|all)
            ;;
        *)
            printf "Error: invalid issue type: %s\n" "$issue_type" >&2
            printf "Valid values: package_vulnerability, license, all\n" >&2
            exit 1
            ;;
    esac
}

is_uuid() {
    value=$1
    printf "%s" "$value" | \
        grep -Eq '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
}

normalize_monitor_json() {
    raw=$1

    if printf "%s" "$raw" | jq -e . >/dev/null 2>&1; then
        printf "%s" "$raw"
        return 0
    fi

    cleaned=$(printf "%s" "$raw" | sed 's/^[^{[]*//')
    if [ -z "$cleaned" ]; then
        printf "Error: snyk monitor output is not valid JSON\n" >&2
        printf "Output was:\n%s\n" "$raw" >&2
        exit 1
    fi

    if ! printf "%s" "$cleaned" | jq -e . >/dev/null 2>&1; then
        printf "Error: snyk monitor output is not valid JSON\n" >&2
        printf "Output was:\n%s\n" "$raw" >&2
        exit 1
    fi

    printf "%s" "$cleaned"
}

run_snyk_monitor() {
    tmp_stdout=
    tmp_stderr=

    tmp_stdout=$(mktemp "${TMPDIR:-/tmp}/monitor-fetch-stdout.XXXXXX")
    tmp_stderr=$(mktemp "${TMPDIR:-/tmp}/monitor-fetch-stderr.XXXXXX")

    printf "Running: snyk monitor --json" >&2
    for arg in "$@"; do
        printf " %s" "$arg" >&2
    done
    printf "\n" >&2

    set +e
    snyk monitor --json "$@" >"$tmp_stdout" 2>"$tmp_stderr"
    monitor_status=$?
    set -e

    if [ -s "$tmp_stderr" ]; then
        cat "$tmp_stderr" >&2
    fi

    if [ "$monitor_status" -ne 0 ]; then
        rm -f "$tmp_stdout" "$tmp_stderr"
        printf "Error: snyk monitor failed (exit %d)\n" \
            "$monitor_status" >&2
        exit "$monitor_status"
    fi

    if [ ! -s "$tmp_stdout" ]; then
        rm -f "$tmp_stdout" "$tmp_stderr"
        printf "Error: snyk monitor produced no output\n" >&2
        exit 1
    fi

    monitor_json=$(cat "$tmp_stdout")
    rm -f "$tmp_stdout" "$tmp_stderr"

    normalize_monitor_json "$monitor_json"
}

extract_monitor_records() {
    monitor_json=$1
    tmp_records=$2

    printf "%s" "$monitor_json" | jq -c '
        def ok_record:
            (.ok // true) == true and
            ((.uri // "") | test("/project/") or (.id // "") != "");
        if type == "array" then .[] | select(ok_record)
        elif .projects? != null then .projects[] | select(ok_record)
        elif ok_record then .
        else empty
        end
    ' > "$tmp_records"
}

resolve_org_id() {
    record_org=$1
    candidate=

    if [ -n "$org_id" ]; then
        candidate=$org_id
    elif [ -n "$record_org" ] && [ "$record_org" != "null" ]; then
        candidate=$record_org
    else
        candidate=$(snyk config get org 2>/dev/null || true)
    fi

    if [ -z "$candidate" ]; then
        printf "Error: organization not found. Set SNYK_ORG, pass --org,\n" \
            >&2
        printf "or configure a default org with: snyk config set org=<ORG_ID>\n" \
            >&2
        exit 1
    fi

    if is_uuid "$candidate"; then
        printf "%s" "$candidate"
        return 0
    fi

    resolved=$(curl -sS \
        -H "Authorization: token ${snyk_token}" \
        "${V1_BASE}/orgs" | \
        jq -r --arg slug "$candidate" \
        '.orgs[]? | select(.slug == $slug or .name == $slug) | .id' | \
        head -n 1)

    if [ -z "$resolved" ] || [ "$resolved" = "null" ]; then
        printf "%s" "$candidate"
        return 0
    fi

    printf "%s" "$resolved"
}

parse_project_id() {
    record=$1

    printf "%s" "$record" | jq -r '
        if (.uri // "") | test("/project/") then
            .uri | capture(".*/project/(?<pid>[0-9a-fA-F-]+)") | .pid
        else
            .id // empty
        end
    '
}

build_aggregated_issues_body() {
    case "$issue_type" in
        package_vulnerability)
            printf '%s' \
                '{"includeDescription":false,"includeIntroducedThrough":false,"filters":{"ignored":false,"types":["vuln"]}}'
            ;;
        license)
            printf '%s' \
                '{"includeDescription":false,"includeIntroducedThrough":false,"filters":{"ignored":false,"types":["license"]}}'
            ;;
        all)
            printf '%s' \
                '{"includeDescription":false,"includeIntroducedThrough":false,"filters":{"ignored":false}}'
            ;;
    esac
}

fetch_project_issues() {
    org=$1
    project_id=$2
    project_name=$3
    request_body=
    url=
    response=

    request_body=$(build_aggregated_issues_body)
    url="${V1_BASE}/org/${org}/project/${project_id}/aggregated-issues"

    printf "Fetching aggregated issues for project %s...\n" "$project_id" >&2

    response=$(curl -sS -X POST \
        -H "Authorization: token ${snyk_token}" \
        -H "Content-Type: application/json" \
        -d "$request_body" \
        "$url")

    if printf "%s" "$response" | jq -e '.message? // .error? // .errors?' \
        >/dev/null 2>&1; then
        err_msg=$(printf "%s" "$response" | \
            jq -r '.message // .error // .errors[0].detail // .errors[0].title // "Unknown error"')
        printf "Error fetching issues: %s\n" "$err_msg" >&2
        exit 1
    fi

    printf "%s" "$response" | jq \
        --arg org "$org" \
        --arg project_id "$project_id" \
        --arg project_name "$project_name" \
        --arg issue_type "$issue_type" \
        '{
            org_id: $org,
            project_id: $project_id,
            project_name: $project_name,
            issue_type: (if $issue_type == "all" then null else $issue_type end),
            issue_count: (.issues | length),
            data: (.issues // [])
        }'
}

write_results_output() {
    results_json=$1
    project_count=$2

    if [ -n "$output_file" ]; then
        printf "%s\n" "$results_json" > "$output_file"
        total_issues=$(printf "%s" "$results_json" | \
            jq '.total_issue_count // .issue_count')
        printf "Wrote %d project(s), %d total issues to %s\n" \
            "$project_count" "$total_issues" "$output_file" >&2
    else
        printf "%s\n" "$results_json"
    fi
}

process_monitor_record() {
    record=$1
    project_id=
    project_name=
    record_org=
    resolved_org=

    project_id=$(parse_project_id "$record")
    project_name=$(printf "%s" "$record" | \
        jq -r '.projectName // .name // "unknown"')
    record_org=$(printf "%s" "$record" | jq -r '.org // empty')

    if [ -z "$project_id" ]; then
        printf "Error: could not parse project ID from monitor output:\n" \
            >&2
        printf "%s\n" "$record" >&2
        exit 1
    fi

    resolved_org=$(resolve_org_id "$record_org")

    printf "Monitored project: %s (%s)\n" "$project_name" "$project_id" >&2
    printf "Organization: %s\n" "$resolved_org" >&2

    fetch_project_issues "$resolved_org" "$project_id" "$project_name"
}

wrap_project_results() {
    projects_json=$1
    project_count=$2

    if [ "$project_count" -eq 1 ]; then
        printf "%s" "$projects_json" | jq '.[0]'
        return 0
    fi

    printf "%s" "$projects_json" | jq \
        '{
            project_count: length,
            total_issue_count: ([.[].issue_count] | add // 0),
            projects: .
        }'
}

main() {
    monitor_json=
    tmp_records=
    record=
    record_count=0
    projects_json='[]'
    results_json=

    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help)
                usage
                exit 0
                ;;
            --org)
                if [ $# -lt 2 ]; then
                    printf "Error: --org requires a value\n" >&2
                    exit 1
                fi
                org_id=$2
                shift 2
                ;;
            --output)
                if [ $# -lt 2 ]; then
                    printf "Error: --output requires a value\n" >&2
                    exit 1
                fi
                output_file=$2
                shift 2
                ;;
            --issue-type)
                if [ $# -lt 2 ]; then
                    printf "Error: --issue-type requires a value\n" >&2
                    exit 1
                fi
                issue_type=$2
                shift 2
                ;;
            --all-issue-types)
                issue_type=all
                shift
                ;;
            --)
                shift
                break
                ;;
            -*)
                printf "Error: unknown option: %s\n" "$1" >&2
                usage >&2
                exit 1
                ;;
            *)
                break
                ;;
        esac
    done

    validate_inputs
    validate_issue_type

    tmp_records=$(mktemp "${TMPDIR:-/tmp}/monitor-fetch-records.XXXXXX")
    trap 'rm -f "$tmp_records"' EXIT INT TERM

    monitor_json=$(run_snyk_monitor "$@")
    extract_monitor_records "$monitor_json" "$tmp_records"

    while IFS= read -r record; do
        if [ -z "$record" ]; then
            continue
        fi
        record_count=$((record_count + 1))
        project_issues=$(process_monitor_record "$record")
        projects_json=$(printf '%s' "$project_issues" | \
            jq -c --argjson acc "$projects_json" '$acc + [.]')
    done < "$tmp_records"

    if [ "$record_count" -eq 0 ]; then
        printf "Error: no project records found in monitor output\n" >&2
        exit 1
    fi

    results_json=$(wrap_project_results "$projects_json" "$record_count")
    write_results_output "$results_json" "$record_count"
}

main "$@"
