# GitHub App propagator

Propagates the **Snyk GitHub App** (GitHub Cloud App or GitHub Server App) from a source organization to every other organization in a Snyk Group. That is different from the legacy **GitHub** integration in Snyk, which is OAuth-based and uses V1 integration type `github`.

## Which API endpoints

- **Resolve the GitHub App integration ID:** `GET /v1/org/{orgId}/integrations/github-cloud-app` (GitHub.com) or `GET /v1/org/{orgId}/integrations/github-server-app` (GitHub Enterprise Server). Response shape includes `id` (see [Integrations (v1)](https://docs.snyk.io/snyk-api/reference/integrations-v1)).
- **Clone to another org in the same group:** `POST /v1/org/{sourceOrgId}/integrations/{integrationId}/clone` with body `{"destinationOrgPublicId": "<dest org uuid>"}`. There is no separate clone URL for the app; you must pass the **GitHub App** integration UUID from the step above, not the UUID for type `github`.

Using `GET /v1/org/{orgId}/integrations` and reading the `github` key clones the **wrong** integration (legacy OAuth) if that integration still exists.

## Prerequisites

- Python 3
- A Snyk API token with permission to list group orgs, read the GitHub App entry on the source org, and clone it to target orgs. Set it as `SNYK_TOKEN` (see [Authentication](https://docs.snyk.io/snyk-api/authentication-for-api)).

## Setup

From this directory:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Export your token, then run the script with your Group ID and the organization ID whose GitHub App setup should be used as the template:

```sh
export SNYK_TOKEN="your-token"
python propagate.py --group-id "<group-uuid>" --source-org-id "<source-org-uuid>"
```

GitHub Enterprise Server App as the template:

```sh
python propagate.py --group-id "<group-uuid>" --source-org-id "<source-org-uuid>" \
  --integration-type github-server-app
```

The script skips the source org when iterating; all other orgs in the group are targets.

