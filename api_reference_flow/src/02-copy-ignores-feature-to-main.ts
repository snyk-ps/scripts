/**
 * Step 2: Copy ignores from the feature branch target reference to the
 * "main" target reference.
 *
 * Uses the Snyk v1 ignores API:
 *   GET  /org/{orgId}/project/{projectId}/ignores
 *   POST /org/{orgId}/project/{projectId}/ignore/{issueId}
 *
 * Each ignore returned for the feature-branch project is re-created on the
 * main-branch project so waivers granted during feature development are
 * promoted to main on merge.
 */

import { callSnykV1, getRequiredEnv } from "./lib/snykClient";

interface IgnoreSettings {
  reason: string;
  reasonType: string;
  expires?: string;
  ignoredBy?: unknown;
  disregardIfFixable?: boolean;
}

/** Snyk v1 "list all ignores" response: issue ID -> array of ignore settings. */
type IgnoresByIssue = Record<string, IgnoreSettings[]>;

export interface CopyIgnoresOptions {
  orgId: string;
  mainProjectId: string;
  featureProjectId: string;
}

export interface CopyIgnoresResult {
  issuesConsidered: number;
  ignoresCopied: number;
}

export async function copyIgnoresFeatureToMain(
  options: CopyIgnoresOptions,
): Promise<CopyIgnoresResult> {
  const { orgId, mainProjectId, featureProjectId } = options;

  const featureIgnores = await callSnykV1<IgnoresByIssue>(
    `/org/${orgId}/project/${featureProjectId}/ignores`,
  );

  const issueIds = Object.keys(featureIgnores);
  let ignoresCopied = 0;

  for (const issueId of issueIds) {
    for (const ignore of featureIgnores[issueId]) {
      await callSnykV1(
        `/org/${orgId}/project/${mainProjectId}/ignore/${issueId}`,
        {
          method: "POST",
          body: {
            reason: ignore.reason,
            reasonType: ignore.reasonType,
            expires: ignore.expires,
            disregardIfFixable: ignore.disregardIfFixable ?? false,
          },
        },
      );
      ignoresCopied += 1;
    }
  }

  return { issuesConsidered: issueIds.length, ignoresCopied };
}

async function main(): Promise<void> {
  const result = await copyIgnoresFeatureToMain({
    orgId: getRequiredEnv("SNYK_ORG_ID"),
    mainProjectId: getRequiredEnv("MAIN_PROJECT_ID"),
    featureProjectId: getRequiredEnv("FEATURE_PROJECT_ID"),
  });
  console.log(
    `Copied ${result.ignoresCopied} ignore(s) across ${result.issuesConsidered} issue(s).`,
  );
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
