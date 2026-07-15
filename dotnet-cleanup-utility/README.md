# dotnet-cleanup-utility

Finds duplicate .NET projects in a Snyk organization (same project name, typically from a .NET framework migration), keeps the most recently tested project, migrates issue ignores from older duplicates to the keeper, and deletes the rest.

**Author:** Andrew Reifers, [andrew.reifers@snyk.io](mailto:andrew.reifers@snyk.io)

## Prerequisites

- Python 3.10+
- Snyk API token with access to the target org and projects
- **REST API** for listing/deleting projects; **V1 API** for project details, ignores, and creating ignores

## APIs used


| Purpose                   | API                                                                                             |
| ------------------------- | ----------------------------------------------------------------------------------------------- |
| List projects in an org   | REST `GET /orgs/{org_id}/projects`                                                              |
| Get project details       | REST `GET /orgs/{org_id}/projects/{project_id}` and V1 `GET /org/{org_id}/project/{project_id}` |
| List issues on a project  | REST `GET /orgs/{org_id}/issues?scan_item.id={project_id}&scan_item.type=project`               |
| List ignores on a project | V1 `GET /org/{org_id}/project/{project_id}/ignores`                                             |
| Create ignore             | V1 `POST /org/{org_id}/project/{project_id}/ignore/{issue_id}`                                  |
| Delete project            | REST `DELETE /orgs/{org_id}/projects/{project_id}`                                              |




## Setup

```sh
cd dotnet-cleanup-utility
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set required environment variables (shell or `data/.env` at the repo root when debugging from VS Code/Cursor):

```sh
export SNYK_API_TOKEN="your-token"
export SNYK_ORG_ID="your-org-uuid"
```

Optional:

- `PROJECT_LAST_TESTED_DELTA_MINUTES` — treat projects tested within this many minutes as simultaneous (default: `1`). Used when deciding whether a duplicate was tested at the same time as the keeper.



## Usage

**Dry run** (default): prints keep/delete decisions and ignore migrations; does not delete projects or POST ignores.

```sh
python main.py
```

**Execute** deletes and ignore migration:

```sh
python main.py --dry-run false
```



## Behavior

1. Lists all projects in the org.
2. Groups projects by name; keeps the most recently tested project per name.
3. If a duplicate was tested within `PROJECT_LAST_TESTED_DELTA_MINUTES` of a keeper, it is kept instead of deleted (handles same-.csproj re-imports).
4. Migrates V1 ignores from projects marked for deletion to matching issues (by issue key) on the keeper project.
5. Deletes duplicate projects (when not in dry run).



## Notes

- Always run with default dry run first and review output before `--dry-run false`.
- Ignores are matched by issue **key** between the deleted and kept projects.
- Duplicate ignores on the keeper are skipped (only non-ignored issues receive migrated ignores).

