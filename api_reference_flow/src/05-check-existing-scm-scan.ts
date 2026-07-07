/**
 * Step 5: Check for an existing SCM scan. If it doesn't exist, the caller
 * should proceed to step 6.
 *
 * Uses the Snyk REST API to look up whether a target already exists for
 * the repository:
 *   GET /rest/orgs/{org_id}/targets?url={repoUrl}
 *
 * A "target" existing means the repo has already been imported through an
 * SCM integration (as opposed to CLI-only monitoring), so re-importing it
 * would create a duplicate.
 */

import { callSnykRest, getRequiredEnv } from "./lib/snykClient";

interface SnykTarget {
  id: string;
  attributes?: {
    displayName?: string;
    url?: string;
  };
}

interface SnykTargetsResponse {
  data: SnykTarget[];
}

export interface CheckExistingScmScanOptions {
  orgId: string;
  repoUrl: string;
}

export interface CheckExistingScmScanResult {
  exists: boolean;
  targetId?: string;
}

export async function checkExistingScmScan(
  options: CheckExistingScmScanOptions,
): Promise<CheckExistingScmScanResult> {
  const params = new URLSearchParams({ url: options.repoUrl, limit: "10" });
  const response = await callSnykRest<SnykTargetsResponse>(
    `/orgs/${options.orgId}/targets?${params.toString()}`,
  );

  const match = response.data.find(
    (target) => target.attributes?.url === options.repoUrl,
  );

  return match ? { exists: true, targetId: match.id } : { exists: false };
}

async function main(): Promise<void> {
  const result = await checkExistingScmScan({
    orgId: getRequiredEnv("SNYK_ORG_ID"),
    repoUrl: getRequiredEnv("REPO_URL"),
  });

  if (result.exists) {
    console.log(`Existing SCM target found: ${result.targetId}. Skipping import.`);
  } else {
    console.log("No existing SCM target found. Proceed to import (step 6).");
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
