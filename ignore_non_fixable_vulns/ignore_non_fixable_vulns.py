#!/usr/bin/env python3
"""
Create Snyk project ignores for vulnerabilities that currently have no fix.

Uses the V1 API ignore flag ``disregardIfFixable``. Discovers projects via the
REST API (org scope or group → orgs), tracks work in a CSV, and supports resume.

Author: Torsten Cannell, torsten.cannell@snyk.io
Revision History:
- 2026-05-05: Initial version (stdlib HTTP client).
- 2026-05-05: Resolve org/project from SNYK_* env when CLI args omitted (VS Code envFile).
- 2026-05-05: Omit expires in V1 ignore POST unless --expires set (422 on empty).
- 2026-05-06: Group/org discovery, REST project listing, CSV state + resume.
- 2026-05-06: Fix REST pagination (links.next as {\"href\": ...} JSON:API).
- 2026-05-06: REST Accept application/vnd.api+json, Link header + starting_after fallback.
- 2026-05-06: Merge V1 /org/.../dependencies project discovery; JSON:API included; Link regex.
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_API_BASE = "https://api.snyk.io/v1"
DEFAULT_REST_BASE = "https://api.snyk.io/rest"
DEFAULT_REST_VERSION = "2024-10-15"
DEFAULT_REASON = "No fix available"
DEFAULT_STATE_CSV = "ignore_non_fixable_progress.csv"

CSV_COLUMNS = ("group_id", "org_id", "project_id", "issue_id", "status")
STATUS_PENDING = "PENDING"
STATUS_IGNORED = "IGNORED"


def build_headers(token: str, *, send_json: bool) -> dict[str, str]:
    """Return HTTP headers for Snyk API requests."""
    h: dict[str, str] = {
        "Authorization": f"token {token}",
        "Accept": "application/json",
    }
    if send_json:
        h["Content-Type"] = "application/json"
    return h


def request_json(
    method: str,
    url: str,
    token: str,
    body: dict[str, Any] | None = None,
) -> Any:
    """Perform an HTTP request with optional JSON body and parse JSON response."""
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers=build_headers(token, send_json=body is not None),
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        try:
            parsed = json.loads(detail)
            if isinstance(parsed, dict):
                msg = parsed.get("message") or parsed.get("error") or parsed
            else:
                msg = parsed
        except json.JSONDecodeError:
            msg = detail or str(exc)
        raise RuntimeError(f"HTTP {exc.code}: {msg}") from exc


REST_PROJECTS_PAGE_LIMIT = 100


def request_rest_get(url: str, token: str) -> tuple[Any, str | None]:
    """
    GET a Snyk REST (JSON:API) URL.

    Uses ``Accept: application/vnd.api+json`` as required for REST contracts.
    Returns the parsed JSON body and the raw HTTP ``Link`` header (if any).
    """
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.api+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            link_hdr = resp.headers.get("Link")
            return (json.loads(raw) if raw else None, link_hdr)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        try:
            parsed = json.loads(detail)
            if isinstance(parsed, dict):
                msg = parsed.get("message") or parsed.get("error") or parsed
            else:
                msg = parsed
        except json.JSONDecodeError:
            msg = detail or str(exc)
        raise RuntimeError(f"HTTP {exc.code}: {msg}") from exc


def parse_http_link_header_next(link_header: str | None) -> str | None:
    """Extract URL for ``rel=next`` from an RFC 5988 ``Link`` header."""
    if not link_header or not link_header.strip():
        return None
    m = re.search(
        r"<([^>]+)>\s*;\s*rel\s*=\s*(?:\"next\"|'next'|next)\b",
        link_header,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    for chunk in link_header.split(","):
        chunk = chunk.strip()
        if "rel=" not in chunk.lower():
            continue
        if "next" not in chunk.lower():
            continue
        lt = chunk.find("<")
        gt = chunk.find(">", lt + 1)
        if lt >= 0 and gt > lt:
            return chunk[lt + 1 : gt].strip()
    return None


def encode_project_starting_after_cursor(last_project_id: str) -> str:
    """Build Snyk cursor token for ``starting_after`` (matches API examples)."""
    payload = json.dumps({"id": last_project_id})
    b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return f"v1.{b64}"


# V1 dependency listing: broad language list so every ecosystem contributes projects.
DEP_FILTERS_ALL_LANGUAGES = [
    "cpp",
    "dockerfile",
    "dotnet",
    "elixir",
    "golang",
    "helm",
    "java",
    "javascript",
    "kubernetes",
    "linux",
    "php",
    "python",
    "ruby",
    "scala",
    "swift-objective-c",
    "terraform",
]


def list_org_projects_from_dependencies_v1(
    api_base: str,
    org_id: str,
    token: str,
) -> list[str]:
    """
    Enumerate project IDs by paging through ``POST /org/{{orgId}}/dependencies``.

    Each dependency row lists ``projects`` that use it; the union covers the org
    even when REST ``/orgs/.../projects`` returns an incomplete list.
    """
    found: set[str] = set()
    page = 1
    per_page = 100
    max_pages = 10000
    use_full_filters = False

    while page <= max_pages:
        qs = urllib.parse.urlencode({"page": page, "perPage": per_page})
        url = f"{api_base.rstrip('/')}/org/{org_id}/dependencies?{qs}"
        if use_full_filters:
            body: dict[str, Any] = {
                "filters": {
                    "depStatus": "any",
                    "languages": list(DEP_FILTERS_ALL_LANGUAGES),
                }
            }
        else:
            body = {"filters": {"depStatus": "any"}}
        try:
            data = request_json("POST", url, token, body)
        except RuntimeError:
            if not use_full_filters:
                use_full_filters = True
                continue
            raise
        rows = data.get("results") if isinstance(data, dict) else None
        if not isinstance(rows, list) or not rows:
            break
        for row in rows:
            if not isinstance(row, dict):
                continue
            for proj in row.get("projects") or []:
                if isinstance(proj, dict) and proj.get("id"):
                    found.add(str(proj["id"]))
        if len(rows) < per_page:
            break
        page += 1

    return sorted(found)


def fetch_aggregated_issues(
    api_base: str,
    org_id: str,
    project_id: str,
    token: str,
) -> list[dict[str, Any]]:
    """Return current aggregated issues for a project (POST body)."""
    url = f"{api_base}/org/{org_id}/project/{project_id}/aggregated-issues"
    body: dict[str, Any] = {
        "includeDescription": False,
        "includeIntroducedThrough": False,
        "filters": {
            "ignored": False,
            "types": ["vuln"],
        },
    }
    data = request_json("POST", url, token, body)
    if not data or "issues" not in data:
        return []
    return data["issues"]


def should_ignore_issue(
    issue: dict[str, Any],
    *,
    require_not_partially_fixable: bool,
) -> bool:
    """Return True if this issue qualifies as non-fixable for this workflow."""
    fix_info = issue.get("fixInfo")
    if not isinstance(fix_info, dict):
        return False
    if fix_info.get("isFixable") is True:
        return False
    if require_not_partially_fixable and fix_info.get("isPartiallyFixable") is True:
        return False
    return True


def add_ignore(
    api_base: str,
    org_id: str,
    project_id: str,
    issue_id: str,
    token: str,
    *,
    reason: str,
    reason_type: str,
    disregard_if_fixable: bool,
    ignore_path: str,
    expires: str | None = None,
) -> Any:
    """POST a new ignore rule for one issue."""
    url = f"{api_base}/org/{org_id}/project/{project_id}/ignore/{issue_id}"
    payload: dict[str, Any] = {
        "ignorePath": ignore_path,
        "reason": reason,
        "reasonType": reason_type,
        "disregardIfFixable": disregard_if_fixable,
    }
    if expires is not None and expires.strip():
        payload["expires"] = expires.strip()
    return request_json("POST", url, token, payload)


def fetch_group_orgs_v1(
    api_base: str,
    group_id: str,
    token: str,
) -> list[dict[str, Any]]:
    """Return all organizations in a group (V1, paginated)."""
    all_orgs: list[dict[str, Any]] = []
    page = 1
    while True:
        qs = urllib.parse.urlencode({"page": page, "perPage": 100})
        url = f"{api_base}/group/{group_id}/orgs?{qs}"
        data = request_json("GET", url, token, None)
        orgs = data.get("orgs") if isinstance(data, dict) else None
        if not orgs:
            break
        all_orgs.extend(orgs)
        if len(orgs) < 100:
            break
        page += 1
    return all_orgs


def normalize_rest_next_url(raw: Any, rest_base: str) -> str | None:
    """
    Resolve JSON:API LinkProperty for pagination.

    Snyk REST returns ``links.next`` as either a URL string or an object
    ``{\"href\": \"...\"}``. Treating non-strings as absent broke pagination
    after the first page (often showing only one project).
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        href = raw.strip()
    elif isinstance(raw, dict):
        h = raw.get("href")
        if not isinstance(h, str):
            return None
        href = h.strip()
    else:
        return None
    if not href:
        return None
    if href.startswith(("http://", "https://")):
        return href
    base = rest_base.rstrip("/") + "/"
    return urllib.parse.urljoin(base, href)


def list_org_projects_rest(
    rest_base: str,
    rest_version: str,
    org_id: str,
    token: str,
) -> list[str]:
    """List all project IDs for an org via REST API (paginated)."""
    found: set[str] = set()
    qs = urllib.parse.urlencode(
        {"version": rest_version, "limit": str(REST_PROJECTS_PAGE_LIMIT)}
    )
    url: str | None = f"{rest_base.rstrip('/')}/orgs/{org_id}/projects?{qs}"
    seen_fallback_cursors: set[str] = set()
    pages = 0
    max_pages = 5000

    while url and pages < max_pages:
        pages += 1
        try:
            data, link_hdr = request_rest_get(url, token)
        except RuntimeError:
            if pages > 1 and "starting_after" in url:
                break
            raise
        batch = data.get("data") if isinstance(data, dict) else None
        if not isinstance(batch, list):
            batch = []

        for item in batch:
            if isinstance(item, dict) and item.get("id"):
                found.add(str(item["id"]))

        included = data.get("included") if isinstance(data, dict) else None
        if isinstance(included, list):
            for item in included:
                if not isinstance(item, dict):
                    continue
                if item.get("type") != "project":
                    continue
                iid = item.get("id")
                if iid:
                    found.add(str(iid))

        links_obj = data.get("links") if isinstance(data.get("links"), dict) else {}
        next_url = normalize_rest_next_url(links_obj.get("next"), rest_base)
        if not next_url:
            next_url = parse_http_link_header_next(link_hdr)

        if (
            not next_url
            and len(batch) >= REST_PROJECTS_PAGE_LIMIT
            and batch
        ):
            last_id = batch[-1].get("id") if isinstance(batch[-1], dict) else None
            if isinstance(last_id, str):
                cursor = encode_project_starting_after_cursor(last_id)
                if cursor not in seen_fallback_cursors:
                    seen_fallback_cursors.add(cursor)
                    fq = urllib.parse.urlencode(
                        {
                            "version": rest_version,
                            "limit": str(REST_PROJECTS_PAGE_LIMIT),
                            "starting_after": cursor,
                        }
                    )
                    next_url = (
                        f"{rest_base.rstrip('/')}/orgs/{org_id}/projects?{fq}"
                    )

        url = next_url

    return sorted(found)


def list_org_project_ids_for_org(
    api_base: str,
    rest_base: str,
    rest_version: str,
    org_id: str,
    token: str,
    *,
    discover_projects: str,
) -> list[str]:
    """Union project IDs from REST listing and/or V1 dependency graph."""
    merged: set[str] = set()
    if discover_projects in ("rest", "both"):
        merged.update(list_org_projects_rest(rest_base, rest_version, org_id, token))
    if discover_projects in ("dependencies", "both"):
        merged.update(list_org_projects_from_dependencies_v1(api_base, org_id, token))
    return sorted(merged)


def row_key(row: dict[str, str]) -> tuple[str, str, str]:
    """Stable tuple for de-duplication."""
    return (row["org_id"], row["project_id"], row["issue_id"])


def load_state_csv(path: Path) -> list[dict[str, str]]:
    """Load CSV rows; validate columns."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    rows: list[dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != list(CSV_COLUMNS):
        raise ValueError(
            f"CSV header must be exactly: {', '.join(CSV_COLUMNS)} "
            f"(got {reader.fieldnames})"
        )
    for raw in reader:
        rows.append({k: (raw.get(k) or "").strip() for k in CSV_COLUMNS})
    return rows


def save_state_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Atomically write CSV (temp file + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        for row in sorted(rows, key=lambda r: row_key(r)):
            writer.writerow({k: row[k] for k in CSV_COLUMNS})
    tmp.replace(path)


def merge_pending_rows(
    existing: list[dict[str, str]],
    new_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Insert new PENDING rows; never downgrade IGNORED."""
    by_key: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in existing:
        by_key[row_key(row)] = dict(row)

    for row in new_rows:
        key = row_key(row)
        if key not in by_key:
            by_key[key] = dict(row)
            continue
        cur = by_key[key]
        if cur.get("status") == STATUS_IGNORED:
            continue
        if cur.get("status") == STATUS_PENDING:
            if not cur.get("group_id") and row.get("group_id"):
                cur["group_id"] = row["group_id"]
    return list(by_key.values())


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Discover non-fixable vulns across Snyk org(s) or group(s), record "
            "them in a CSV, create ignores with disregardIfFixable, and resume "
            "from the CSV if interrupted."
        )
    )
    parser.add_argument(
        "--group-id",
        action="append",
        default=[],
        metavar="UUID",
        help="Snyk Group ID (repeatable). Fetches orgs via V1 /group/{id}/orgs.",
    )
    parser.add_argument(
        "--org-id",
        action="append",
        default=[],
        metavar="UUID",
        help="Snyk Organization ID (repeatable). Combined with --group-id results.",
    )
    parser.add_argument(
        "--project-id",
        action="append",
        dest="project_filter",
        default=None,
        metavar="UUID",
        help=(
            "If set, only consider these project IDs per org (intersect with "
            "REST listing). Repeatable."
        ),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Skip discovery; only process PENDING rows in the state CSV "
            "(use after an interrupted run)."
        ),
    )
    parser.add_argument(
        "--state-csv",
        "-s",
        default=DEFAULT_STATE_CSV,
        metavar="PATH",
        help=(
            "CSV path for queue/resume (default: %(default)s in the current "
            "working directory)."
        ),
    )
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("SNYK_API_BASE_URL", DEFAULT_API_BASE),
        help="V1 API base URL (ignores + aggregated issues).",
    )
    parser.add_argument(
        "--rest-api-url",
        default=os.environ.get("SNYK_REST_API_URL", DEFAULT_REST_BASE),
        help="REST API base URL (list projects). EU: https://api.eu.snyk.io/rest",
    )
    parser.add_argument(
        "--rest-version",
        default=os.environ.get("SNYK_REST_VERSION", DEFAULT_REST_VERSION),
        help="REST API version query param for /orgs/.../projects.",
    )
    parser.add_argument(
        "--discover-projects",
        choices=("rest", "dependencies", "both"),
        default="both",
        help=(
            "How to enumerate projects: REST /orgs/.../projects, V1 "
            "/org/.../dependencies (union of projects per dependency), or "
            "both merged (default)."
        ),
    )
    parser.add_argument(
        "--reason",
        default=DEFAULT_REASON,
        help="Ignore reason text stored in Snyk (default: %(default)s).",
    )
    parser.add_argument(
        "--reason-type",
        choices=("temporary-ignore", "not-vulnerable", "wont-fix"),
        default="temporary-ignore",
        help="Snyk ignore classification (default: %(default)s).",
    )
    parser.add_argument(
        "--ignore-path",
        default="*",
        help="Scope of the ignore (default: %(default)s = all paths).",
    )
    parser.add_argument(
        "--no-disregard-if-fixable",
        action="store_true",
        help="Set disregardIfFixable to false (not recommended).",
    )
    parser.add_argument(
        "--expires",
        default=None,
        metavar="ISO8601",
        help="Optional calendar expiry (ISO 8601). Omitted by default.",
    )
    parser.add_argument(
        "--include-partially-fixable",
        action="store_true",
        help="Include issues where isPartiallyFixable is true.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Do not call ignore API or mark rows IGNORED. Discovery still writes "
            "PENDING rows to the state CSV."
        ),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress on stdout.",
    )
    return parser.parse_args()


def env_extend_ids(cli_list: list[str], env_single: str, env_plural: str) -> list[str]:
    """Append UUIDs from comma-separated env vars."""
    out = list(cli_list)
    for key in (env_single, env_plural):
        raw = os.environ.get(key, "").strip()
        if raw:
            out.extend(p.strip() for p in raw.split(",") if p.strip())
    return out


def build_org_to_group(
    api_base: str,
    group_ids: list[str],
    org_ids: list[str],
    token: str,
) -> dict[str, str]:
    """
    Map org_id -> group_id (empty string when org was listed only via --org-id).

    Orgs from multiple groups: first group wins for that org id.
    """
    org_to_group: dict[str, str] = {}
    for gid in group_ids:
        for org in fetch_group_orgs_v1(api_base, gid, token):
            oid = org.get("id")
            if not oid:
                continue
            if oid not in org_to_group:
                org_to_group[oid] = gid
    for oid in org_ids:
        if oid not in org_to_group:
            org_to_group[oid] = ""
    return org_to_group


def discover_rows(
    *,
    api_base: str,
    rest_base: str,
    rest_version: str,
    org_to_group: dict[str, str],
    project_filter: set[str] | None,
    token: str,
    require_not_partial: bool,
    quiet: bool,
    discover_projects: str,
) -> list[dict[str, str]]:
    """Scan projects and issues; return new PENDING rows."""
    new_rows: list[dict[str, str]] = []
    for org_id, gid in sorted(org_to_group.items(), key=lambda x: x[0]):
        try:
            proj_ids = list_org_project_ids_for_org(
                api_base,
                rest_base,
                rest_version,
                org_id,
                token,
                discover_projects=discover_projects,
            )
        except RuntimeError as exc:
            print(f"[{org_id}] Failed to list projects: {exc}", file=sys.stderr)
            raise
        if project_filter is not None:
            proj_ids = [p for p in proj_ids if p in project_filter]
        if not proj_ids and not quiet:
            print(f"Org {org_id}: no projects (after filter).")
            continue
        if not quiet:
            print(f"Org {org_id}: scanning {len(proj_ids)} project(s).")

        for project_id in proj_ids:
            try:
                issues = fetch_aggregated_issues(api_base, org_id, project_id, token)
            except RuntimeError as exc:
                print(
                    f"[{org_id}/{project_id}] Failed to list issues: {exc}",
                    file=sys.stderr,
                )
                raise
            for issue in issues:
                if not should_ignore_issue(
                    issue,
                    require_not_partially_fixable=require_not_partial,
                ):
                    continue
                iid = issue.get("id")
                if not iid:
                    continue
                new_rows.append(
                    {
                        "group_id": gid,
                        "org_id": org_id,
                        "project_id": project_id,
                        "issue_id": str(iid),
                        "status": STATUS_PENDING,
                    }
                )
    return new_rows


def main() -> int:
    """Entry point."""
    args = parse_args()
    token = os.environ.get("SNYK_TOKEN", "").strip()
    if not token:
        print("Error: SNYK_TOKEN environment variable is not set.", file=sys.stderr)
        return 1

    group_ids = env_extend_ids(args.group_id, "SNYK_GROUP_ID", "SNYK_GROUP_IDS")
    org_ids = env_extend_ids(args.org_id, "SNYK_ORG_ID", "SNYK_ORG_IDS")

    state_path = Path(args.state_csv).expanduser()
    api_base = args.api_base_url.rstrip("/")
    rest_base = args.rest_api_url.rstrip("/")
    disregard = not args.no_disregard_if_fixable
    require_not_partial = not args.include_partially_fixable

    project_filter: set[str] | None = None
    if args.project_filter:
        project_filter = {p.strip() for p in args.project_filter if p.strip()}

    rows: list[dict[str, str]] = []
    if state_path.is_file():
        try:
            rows = load_state_csv(state_path)
        except ValueError as exc:
            print(f"Error reading state CSV: {exc}", file=sys.stderr)
            return 1

    if args.resume:
        if not rows:
            print(
                "Error: --resume requires an existing state CSV with rows.",
                file=sys.stderr,
            )
            return 1
        if not args.quiet:
            print(f"Resume mode: loaded {len(rows)} row(s) from {state_path}")
    else:
        if not group_ids and not org_ids:
            print(
                "Error: provide --group-id and/or --org-id for discovery, or use "
                "--resume with an existing state CSV.",
                file=sys.stderr,
            )
            return 1
        org_to_group = build_org_to_group(api_base, group_ids, org_ids, token)
        if not org_to_group:
            print("Error: no organizations to scan.", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"Discovering across {len(org_to_group)} org(s).")

        discovered = discover_rows(
            api_base=api_base,
            rest_base=rest_base,
            rest_version=args.rest_version,
            org_to_group=org_to_group,
            project_filter=project_filter,
            token=token,
            require_not_partial=require_not_partial,
            quiet=args.quiet,
            discover_projects=args.discover_projects,
        )
        rows = merge_pending_rows(rows, discovered)
        save_state_csv(state_path, rows)
        if not args.quiet:
            print(
                f"State CSV updated: {state_path} "
                f"({len(discovered)} candidate issue row(s) from discovery)."
            )

    pending = [r for r in rows if r.get("status") == STATUS_PENDING]
    if not args.quiet:
        print(f"PENDING rows to process: {len(pending)}")

    created = 0
    skipped_existing = 0

    for row in pending:
        org_id = row["org_id"]
        project_id = row["project_id"]
        issue_id = row["issue_id"]

        if args.dry_run:
            if not args.quiet:
                print(f"  [dry-run] would ignore {issue_id} ({org_id}/{project_id})")
            created += 1
            continue

        try:
            add_ignore(
                api_base,
                org_id,
                project_id,
                issue_id,
                token,
                reason=args.reason,
                reason_type=args.reason_type,
                disregard_if_fixable=disregard,
                expires=args.expires,
                ignore_path=args.ignore_path,
            )
            row["status"] = STATUS_IGNORED
            created += 1
            save_state_csv(state_path, rows)
            if not args.quiet:
                print(f"  ignored {issue_id}")
        except RuntimeError as exc:
            err_text = str(exc).lower()
            if (
                "already" in err_text
                or "409" in err_text
                or "duplicate" in err_text
            ):
                row["status"] = STATUS_IGNORED
                skipped_existing += 1
                save_state_csv(state_path, rows)
                if not args.quiet:
                    print(f"  skip {issue_id} (already ignored): {exc}", file=sys.stderr)
            else:
                print(f"  Error ignoring {issue_id}: {exc}", file=sys.stderr)
                return 1

    if not args.quiet:
        print(
            f"Done. Ignores applied: {created}; "
            f"marked existing/conflict as IGNORED: {skipped_existing}. "
            f"State file: {state_path}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
