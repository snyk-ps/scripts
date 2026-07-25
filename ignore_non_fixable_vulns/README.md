# ignore_non_fixable_vulns

Creates **project-level ignores** in Snyk for open-source **vulnerabilities** that are **not fixable** in the current project snapshot (`fixInfo.isFixable` is false). Ignores use **`disregardIfFixable: true`** (default) so they stop applying when a fix becomes available.

The tool **discovers all projects** in one or more **organizations** (directly or via a **Group**), scans aggregated issues per project (V1), records work in a **CSV**, and creates ignores. If the run stops mid-way, **`--resume`** continues from the CSV without rediscovering everything.

**Author:** Torsten Cannell, torsten.cannell@snyk.io

## Prerequisites

- Python 3.11+
- Snyk API token (`SNYK_TOKEN`) with access to the group/orgs/projects
- **REST API** for listing projects (`View Projects`), **V1 API** for aggregated issues and ignores (Enterprise)

## APIs used

| Purpose | API |
|--------|-----|
| List orgs in a group | V1 `GET /group/{groupId}/orgs` |
| List projects in an org | REST `GET /orgs/{org_id}/projects` |
| List issues | V1 `POST .../aggregated-issues` |
| Create ignore | V1 `POST .../ignore/{issueId}` |

Set **`SNYK_API_BASE_URL`** or **`--api-base-url`** for non-US tenants (host only, no path suffix).  
The script appends **`/v1`** or **`/rest`** as needed (e.g. `https://api.eu.snyk.io` or `api.eu.snyk.io`).

Project listing paginates using **`links.next`** (string or `{ "href": "..." }`), the HTTP **`Link`** header (`rel="next"`), and—only when a full page has no next link—a **`starting_after`** cursor derived from the last project id. REST calls use **`Accept: application/vnd.api+json`**. Default **`--rest-version`** is **`2024-10-15`**.

## Setup

No pip packages (stdlib only).

```sh
export SNYK_TOKEN="your-token"
# Optional, for EU or other regions:
# export SNYK_API_BASE_URL="https://api.eu.snyk.io"
```

Optional env aliases for IDs (comma-separated where noted):

- `SNYK_GROUP_ID` / `SNYK_GROUP_IDS`
- `SNYK_ORG_ID` / `SNYK_ORG_IDS`

## State CSV

Default path: **`ignore_non_fixable_progress.csv`** in the **current working directory** (override with **`--state-csv`** / **`-s`**).

Columns:

| Column | Description |
|--------|-------------|
| `group_id` | Group UUID when the org came from `--group-id`; empty if org was only from `--org-id` |
| `org_id` | Organization UUID |
| `project_id` | Project UUID |
| `issue_id` | Snyk issue ID |
| `status` | **`PENDING`** (not yet ignored) or **`IGNORED`** (ignore created or treated as already present) |

After each successful ignore (or “already ignored” response), the row is updated and the file is rewritten so you can **`--resume`** safely.

## Usage

**Discover + dry-run** (writes/updates the CSV with `PENDING`, does not call the ignore API):

```sh
python ignore_non_fixable_vulns.py --org-id "<ORG_UUID>" --dry-run
```

**Discover + create ignores** for all projects in that org:

```sh
python ignore_non_fixable_vulns.py --org-id "<ORG_UUID>"
```

**Group** (all orgs in the group, all their projects):

```sh
python ignore_non_fixable_vulns.py --group-id "<GROUP_UUID>"
```

**Resume** after interruption (uses existing CSV only):

```sh
python ignore_non_fixable_vulns.py --resume
```

Custom CSV path:

```sh
python ignore_non_fixable_vulns.py -s /path/to/state.csv --org-id "<ORG_UUID>"
python ignore_non_fixable_vulns.py --resume -s /path/to/state.csv
```

**Limit to specific projects** (intersect with REST results):

```sh
python ignore_non_fixable_vulns.py --org-id "<ORG_UUID>" \
  --project-id "<PROJ_A>" --project-id "<PROJ_B>"
```

**Reason text** (default: `No fix available`):

```sh
python ignore_non_fixable_vulns.py --org-id "<ORG_UUID>" --reason "No fix available"
```

## GitHub Actions

A sample scheduled workflow lives at [`.github/workflows/ignore-non-fixable-vulns.yml`](.github/workflows/ignore-non-fixable-vulns.yml). It runs on manual dispatch (optional schedule), discovers non-fixable issues, creates ignores, and persists progress between runs via a workflow artifact.

The workflow defines two run steps — **org** (enabled by default) and **group** (commented out). Comment out the step you do not need; only one should be active.

### Repository configuration

Set repository **secrets** and **variables** as needed. Unset or empty repository variables are ignored; the script uses its built-in defaults (GitHub Actions passes unset vars as empty strings).

| Name | Type | Required | Purpose |
|------|------|----------|---------|
| `SNYK_TOKEN` | Secret | Yes | Snyk API token with access to the group/orgs/projects |
| `SNYK_ORG_ID` | Variable | Yes* | Organization UUID (org step; also merged from env by the script) |
| `SNYK_ORG_IDS` | Variable | No | Comma-separated org UUIDs |
| `SNYK_GROUP_ID` | Variable | Yes† | Group UUID (group step; also merged from env by the script) |
| `SNYK_GROUP_IDS` | Variable | No | Comma-separated group UUIDs |
| `SNYK_API_BASE_URL` | Variable | No | API host (e.g. `https://api.eu.snyk.io`); default US |
| `SNYK_REST_VERSION` | Variable | No | REST version query param; default `2024-10-15` |

\* Required when using the **org** step (default).

† Required when using the **group** step (comment in org step, uncomment group step).

### How the workflow runs

1. **Restore** the previous run's `ignore_non_fixable_progress.csv` artifact (if any).
2. **Resume** if the CSV exists (`--resume`); otherwise **discover** using the active step (org or group). Additional org/group IDs from `SNYK_ORG_IDS` / `SNYK_GROUP_IDS` are read from the environment automatically.
3. **Create ignores** for each `PENDING` row (same as a local run without `--dry-run`).
4. **Upload** the updated CSV as artifact `snyk-ignore-progress` (90-day retention) so the next run can continue where it left off.

The CSV is gitignored locally and in CI; only the artifact carries state across runs.

### Triggers and safety

- **Schedule:** uncomment `cron: "0 7 * * *"` in the workflow for daily 07:00 UTC (adjust as needed).
- **Manual:** **Actions → Snyk ignore non-fixable vulns → Run workflow**.
- **Concurrency:** one run at a time (`cancel-in-progress: false`) so two jobs do not write the same CSV artifact concurrently.
- **Timeout:** 360 minutes; increase for very large groups or narrow scope with `--project-id` in the workflow.

### Customizing the workflow

Common edits:

- **Group instead of org** — comment out the org step, uncomment the group step, set `SNYK_GROUP_ID` (and optionally `SNYK_GROUP_IDS`).
- **Dry-run gate** — add `--dry-run` to the `python` command to validate discovery before enabling live ignores.
- **Fresh discovery** — delete the `snyk-ignore-progress` artifact in the Actions UI to force a full re-scan.

## Notes

- Issues without `fixInfo` are skipped.
- **`--expires`** is optional; omit it and rely on **`disregardIfFixable`** unless you need a calendar end date.
- For VS Code/Cursor debugging, set `SNYK_TOKEN` in `data/.env` and pass **`--org-id`** / **`--group-id`** on the command line (see repo `.vscode/launch.json`).
