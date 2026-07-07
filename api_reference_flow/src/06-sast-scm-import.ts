/**
 * Step 6: SAST SCM import via API.
 *
 * Runs only when step 5 found no existing target. Uses the Snyk v1
 * integrations import endpoint:
 *   POST /org/{orgId}/integrations/{integrationId}/import
 *
 * This example targets the GitHub / GitHub Enterprise import request shape.
 * Swap the body shape if your SCM is a different provider (see the
 * *ImportRequest schemas in .cursor/rules/api_specs/snyk/v1-api-spec.yaml).
 */

import { callSnykV1, getRequiredEnv } from "./lib/snykClient";
import { parseRepoUrl } from "./lib/repoUrl";

export interface SastScmImportOptions {
  orgId: string;
  integrationId: string;
  repoOwner: string;
  repoName: string;
  branch: string;
}

export interface SastScmImportResult {
  /** Location header returned by Snyk pointing at the import job status. */
  importJobLocation?: string;
}

export async function sastScmImport(
  options: SastScmImportOptions,
): Promise<SastScmImportResult> {
  await callSnykV1(
    `/org/${options.orgId}/integrations/${options.integrationId}/import`,
    {
      method: "POST",
      body: {
        target: {
          owner: options.repoOwner,
          name: options.repoName,
          branch: options.branch,
        },
      },
    },
  );

  // The v1 import endpoint returns 201 with a Location header for polling
  // job status rather than a JSON body; callSnykV1 does not currently
  // surface response headers. When integrating into a Lambda or similar
  // handler, read the Location header directly from the fetch Response if
  // job polling is needed.
  return {};
}

async function main(): Promise<void> {
  const { owner, name } = parseRepoUrl(getRequiredEnv("REPO_URL"));
  await sastScmImport({
    orgId: getRequiredEnv("SNYK_ORG_ID"),
    integrationId: getRequiredEnv("SNYK_INTEGRATION_ID"),
    repoOwner: owner,
    repoName: name,
    branch: process.env.SCM_BRANCH ?? "main",
  });
  console.log(`SAST SCM import triggered for ${owner}/${name}.`);
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
