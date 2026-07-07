/**
 * Step 4: Cron-based script to trigger a SAST SCM scan.
 *
 * Intended as the entry point a scheduler (cron, EventBridge, etc.) invokes
 * on a recurring basis. It chains step 5 (check for an existing SCM scan)
 * and, only if none exists, step 6 (SAST SCM import via API). This mirrors
 * the "SCM Schedule Retriever Lambda" / "SCM Import Lambda" pair from the
 * reference architecture diagram, driven by a single scheduled entry point.
 */

import { getRequiredEnv } from "./lib/snykClient";
import { parseRepoUrl } from "./lib/repoUrl";
import { checkExistingScmScan } from "./05-check-existing-scm-scan";
import { sastScmImport } from "./06-sast-scm-import";

export interface CronTriggerSastScmScanOptions {
  orgId: string;
  repoUrl: string;
  integrationId: string;
  branch: string;
}

export async function cronTriggerSastScmScan(
  options: CronTriggerSastScmScanOptions,
): Promise<void> {
  const existing = await checkExistingScmScan({
    orgId: options.orgId,
    repoUrl: options.repoUrl,
  });

  if (existing.exists) {
    console.log(
      `SCM target already exists (${existing.targetId}) for ${options.repoUrl}. Nothing to do.`,
    );
    return;
  }

  const { owner, name } = parseRepoUrl(options.repoUrl);
  await sastScmImport({
    orgId: options.orgId,
    integrationId: options.integrationId,
    repoOwner: owner,
    repoName: name,
    branch: options.branch,
  });
  console.log(`No existing SCM target found. Import triggered for ${options.repoUrl}.`);
}

async function main(): Promise<void> {
  await cronTriggerSastScmScan({
    orgId: getRequiredEnv("SNYK_ORG_ID"),
    repoUrl: getRequiredEnv("REPO_URL"),
    integrationId: getRequiredEnv("SNYK_INTEGRATION_ID"),
    branch: process.env.SCM_BRANCH ?? "main",
  });
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
