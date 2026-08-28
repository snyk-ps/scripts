# monitor_fetch_issues

Run `snyk monitor`, parse the project ID from CLI output, and fetch issues for
that project via the Snyk V1 `aggregated-issues` API using `curl`.

## Prerequisites

- [Snyk CLI](https://docs.snyk.io/developer-tools/snyk-cli/install-or-update-the-snyk-cli)
- `curl`
- `jq`
- Snyk API token with access to the target org/project

## Setup

```bash
export SNYK_TOKEN="your-snyk-api-token"
export SNYK_ORG="your-org-id-or-slug"   # optional if set in snyk config
```

## Usage

From this directory:

```bash
sh ./monitor-fetch-issues.sh
```

Monitor a specific path and write issues to a file:

```bash
sh ./monitor-fetch-issues.sh --org <ORG_ID> --output issues.json /path/to/project
```

Monitor all projects in a directory (for example a monorepo):

```bash
sh ./monitor-fetch-issues.sh data/juice-shop --all-projects
```

Pass additional flags to `snyk monitor` after `--`:

```bash
sh ./monitor-fetch-issues.sh --output issues.json -- --project-name=my-app --file=package.json
```

## What it does

1. Runs `snyk monitor --json` (the script adds `--json` automatically).
2. Parses the **project UUID from the monitor `uri` field** (not the top-level
   `id`, which is not the project ID in `--all-projects` output).
3. Resolves the organization slug to a UUID when needed.
4. Calls `POST /org/{org_id}/project/{project_id}/aggregated-issues` with
   `types: ["vuln"]` by default (open-source vulnerabilities, not licenses).
5. Prints a JSON summary to stdout, or writes it to `--output`.

## Output

For a single monitored project, the payload includes:

| Field | Description |
| --- | --- |
| `org_id` | Organization ID used for the API call |
| `project_id` | Project UUID parsed from the monitor `uri` |
| `project_name` | Project name from `snyk monitor` |
| `issue_type` | Issue type filter applied (`package_vulnerability` by default) |
| `issue_count` | Number of issues returned |
| `data` | V1 aggregated issue objects |

With `--all-projects`, the payload wraps multiple projects:

| Field | Description |
| --- | --- |
| `project_count` | Number of monitored projects |
| `total_issue_count` | Sum of issues across all projects |
| `projects` | Array of per-project payloads (same shape as above) |

## Environment variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `SNYK_TOKEN` | Yes | — | Snyk API token |
| `SNYK_ORG` | No | — | Organization ID or slug |
| `SNYK_ISSUE_TYPE` | No | `package_vulnerability` | Issue type filter |
| `SNYK_V1_API_URL` | No | `https://api.snyk.io/v1` | V1 API base URL |

## Issue type filter

By default the script requests **open-source vulnerability** issues only
(`types: ["vuln"]`). License issues are excluded unless you override the filter:

```bash
# License issues only
sh ./monitor-fetch-issues.sh --issue-type license data/juice-shop --all-projects

# All issue types
sh ./monitor-fetch-issues.sh --all-issue-types data/juice-shop --all-projects
```

## Errors

- Exits if `SNYK_TOKEN` is missing.
- Exits if `snyk monitor` fails or returns no parseable project ID.
- Exits if org cannot be resolved from `--org`, monitor output, or `snyk config get org`.
