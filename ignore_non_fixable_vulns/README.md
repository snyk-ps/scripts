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

Use **`--rest-api-url`** and **`--api-base-url`** (and EU hosts if needed):  
EU example: `https://api.eu.snyk.io/rest` and `https://api.eu.snyk.io/v1`.

Project listing paginates using **`links.next`** (string or `{ "href": "..." }`), the HTTP **`Link`** header (`rel="next"`), and—only when a full page has no next link—a **`starting_after`** cursor derived from the last project id. REST calls use **`Accept: application/vnd.api+json`**. Default **`--rest-version`** is **`2024-10-15`**.

## Setup

No pip packages (stdlib only).

```sh
export SNYK_TOKEN="your-token"
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

## Notes

- Issues without `fixInfo` are skipped.
- **`--expires`** is optional; omit it and rely on **`disregardIfFixable`** unless you need a calendar end date.
- For VS Code/Cursor debugging, set `SNYK_TOKEN` in `data/.env` and pass **`--org-id`** / **`--group-id`** on the command line (see repo `.vscode/launch.json`).
