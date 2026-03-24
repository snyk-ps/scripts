#!/usr/bin/env python3
"""
Snyk GitHub App propagator (V1 API).

Clones the GitHub App configuration from a source organization to all other
organizations in a Snyk Group. This targets the GitHub App product flow, not
the legacy GitHub OAuth integration. The V1 API exposes it via org
integrations and the clone endpoint.

Author: Torsten Cannell, torsten.cannell@snyk.io
Revision History:
- 2026-03-24: Initial version using V1 API clone endpoint.
- 2026-03-24: Resolve GitHub App via integration type github-cloud-app (not github).
"""

import argparse
import os
import sys
import requests

# API Constants
API_V1_BASE = "https://api.snyk.io/v1"
# V1 integration type for Snyk GitHub Cloud App (GitHub.com). Legacy OAuth uses type "github".
DEFAULT_GITHUB_APP_TYPE = "github-cloud-app"

def get_headers(api_token):
    """Return standard headers for Snyk V1 API."""
    return {
        "Authorization": f"token {api_token}",
        "Content-Type": "application/json",
    }


def get_github_app_integration_id(org_id, integration_type, api_token):
    """
    Find the V1 integration ID for the Snyk GitHub App on a given organization.

    Uses GET /org/{{orgId}}/integrations/{{type}}. Type github-cloud-app is the
    GitHub Cloud App; type github is the separate legacy GitHub OAuth integration.

    Args:
        org_id (str): Organization UUID.
        integration_type (str): V1 type, e.g. github-cloud-app or github-server-app.
        api_token (str): Snyk API token.

    Returns:
        str: Integration ID if found, else None.
    """
    url = f"{API_V1_BASE}/org/{org_id}/integrations/{integration_type}"
    response = requests.get(url, headers=get_headers(api_token))
    if response.status_code == 404:
        print(
            f"Error: No integration of type {integration_type!r} in org {org_id}. "
            "Configure the GitHub App in this org first."
        )
        return None
    response.raise_for_status()
    data = response.json()
    integration_id = data.get("id")
    if not integration_id:
        print(f"Error: Unexpected response for {integration_type} in org {org_id}")
        return None
    return integration_id


def list_group_orgs(group_id, api_token):
    """
    List all organizations in a Snyk Group using V1 API.

    Args:
        group_id (str): Group UUID.
        api_token (str): Snyk API token.

    Returns:
        list: List of organization objects containing 'id' and 'name'.
    """
    url = f"{API_V1_BASE}/group/{group_id}/orgs"
    response = requests.get(url, headers=get_headers(api_token))
    response.raise_for_status()
    
    # V1 Group Orgs returns a wrapper object with an 'orgs' list
    return response.json().get("orgs", [])


def clone_integration(src_org, src_integ, dest_org, api_token):
    """
    Clone an integration from source org to destination org.

    Args:
        src_org (str): Source Organization UUID.
        src_integ (str): Source Integration UUID.
        dest_org (str): Destination Organization UUID.
        api_token (str): Snyk API token.
    """
    url = f"{API_V1_BASE}/org/{src_org}/integrations/{src_integ}/clone"
    payload = {"destinationOrgPublicId": dest_org}
    
    response = requests.post(url, headers=get_headers(api_token), json=payload)
    
    if response.status_code == 200:
        print(f"Successfully cloned to Org: {dest_org}")
    else:
        print(f"Failed to clone to {dest_org}: {response.status_code} {response.text}")


def main():
    """Main execution logic."""
    parser = argparse.ArgumentParser(
        description=(
            "Clone GitHub App setup from one org to all other orgs in a Group."
        )
    )
    parser.add_argument(
        "--group-id", required=True, help="The Snyk Group ID"
    )
    parser.add_argument(
        "--source-org-id", required=True, help="The Source (Template) Org ID"
    )
    parser.add_argument(
        "--integration-type",
        default=DEFAULT_GITHUB_APP_TYPE,
        choices=("github-cloud-app", "github-server-app"),
        help=(
            "V1 integration type for the Snyk GitHub App to clone "
            "(github.com vs GitHub Enterprise Server App)"
        ),
    )
    args = parser.parse_args()

    api_token = os.getenv("SNYK_TOKEN")
    if not api_token:
        print("Error: SNYK_TOKEN environment variable not set.")
        sys.exit(1)

    # 1. GitHub App integration ID (not legacy type "github")
    integ_id = get_github_app_integration_id(
        args.source_org_id, args.integration_type, api_token
    )
    if not integ_id:
        sys.exit(1)

    # 2. Get all Orgs in the group
    print(f"Fetching organizations for Group {args.group_id}...")
    orgs = list_group_orgs(args.group_id, api_token)
    print(f"Found {len(orgs)} organizations.")

    # 3. Propagate/Clone
    for org in orgs:
        target_id = org["id"]
        if target_id == args.source_org_id:
            continue
        
        print(f"Cloning GitHub App to {org['name']} ({target_id})...")
        clone_integration(args.source_org_id, integ_id, target_id, api_token)


if __name__ == "__main__":
    main()