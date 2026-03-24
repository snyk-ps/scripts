# GitHub App propagator

Propagates the **Snyk GitHub App** setup from a source organization to every other organization in a Snyk Group. This is the GitHub App flow (installing and using the Snyk app on GitHub), not the separate legacy **GitHub integration** (OAuth-based GitHub connection).

The script uses the [V1 API](https://docs.snyk.io/snyk-api/v1-api) integration clone flow: Snyk still models the GitHub App under org integrations, so the clone endpoint is `/org/.../integrations/.../clone` and the list response key is `github`. Operationally you are copying the GitHub App configuration from your template org to the rest of the group.

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

The script skips the source org when iterating; all other orgs in the group are targets.

## API reference

For endpoint details beyond what you see in the code, see the [Snyk V1 API documentation](https://docs.snyk.io/snyk-api/v1-api) and the API specs in the parent repository under `api_specs/` if present.
