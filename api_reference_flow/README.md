# API reference flow

Reference TypeScript modules implementing each step of the post-merge SCA
waiver flow and SAST SCM import flow. Each file is a plain function plus a
small CLI wrapper so the function body can be lifted directly into your own
Lambda handlers or other automation.

## What each step does

| File | Step | What it does |
|---|---|---|
| `src/01-trigger-sca-scan.ts` | 1 | Runs `snyk monitor` via the Snyk CLI to trigger an SCA scan on the feature branch |
| `src/02-copy-ignores-feature-to-main.ts` | 2 | Copies ignores from the feature branch's project to the `main` target reference's project via the Snyk v1 ignores API |
| `src/03-remonitor-main-branch.ts` | 3 | Re-runs `snyk monitor` on main so the snapshot reflects the newly applied ignores |
| `src/04-cron-trigger-sast-scm-scan.ts` | 4 | Entry point for a scheduler (cron/EventBridge); chains steps 5 and 6 |
| `src/05-check-existing-scm-scan.ts` | 5 | Checks the Snyk REST targets API for an existing SCM import of the repo |
| `src/06-sast-scm-import.ts` | 6 | Imports the repo for SAST SCM scanning via the Snyk v1 integrations import API, if step 5 found none |

## Prerequisites

- Node.js 18 or later (for built-in `fetch`)
- The [Snyk CLI](https://docs.snyk.io/snyk-cli/install-the-snyk-cli) installed and on `PATH` for steps 1 and 3
- A Snyk API token with access to the relevant org(s). See
  [Authentication](https://docs.snyk.io/snyk-api/authentication-for-api)

## Setup

From this directory:

```sh
npm install
cp .env.example .env
# fill in .env with real values, then export the variables you need, e.g.
export $(grep -v '^#' .env | xargs)
```

## Usage

Each step can be run independently. Examples:

```sh
# Step 1: trigger an SCA scan on the feature branch
npm run trigger-sca-scan

# Step 2: copy ignores from feature to main
npm run copy-ignores

# Step 3: re-monitor main with ignores applied
npm run remonitor-main-branch

# Step 4: scheduled entry point (checks for an existing SCM scan, imports if needed)
npm run cron-trigger-sast-scm-scan

# Step 5 and 6 individually
npm run check-existing-scm-scan
npm run sast-scm-import
```

Type-check without emitting output:

```sh
npm run build
```

## Notes

- These are reference implementations, not production Lambda handlers. They
  are meant to be read, adapted, and refactored into your own deployment
  targets.
- `SNYK_TOKEN` is read from the environment only and is never logged.
- Step 6 assumes a GitHub / GitHub Enterprise import request shape. Adjust
  the request body in `src/06-sast-scm-import.ts` if your SCM integration is
  a different provider (see the `*ImportRequest` schemas in
  `.cursor/rules/api_specs/snyk/v1-api-spec.yaml`).

## Author

samuel.dahlberg@snyk.io
