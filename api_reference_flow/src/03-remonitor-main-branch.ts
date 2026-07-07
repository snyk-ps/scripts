/**
 * Step 3: Trigger snyk monitor with the newly applied ignores on main.
 *
 * Runs after step 2 copies ignores onto the main branch project, so the
 * next monitored snapshot for main reflects the applied ignores (this is
 * what turns an "unapplied waiver" into an "applied waiver" in the
 * post-merge flow).
 *
 * This reuses the same CLI invocation as step 1, kept as a separate module
 * so it maps 1:1 to the numbered step.
 */

import { getRequiredEnv } from "./lib/snykClient";
import { triggerScaScan } from "./01-trigger-sca-scan";

export interface RemonitorMainBranchOptions {
  projectDirectory: string;
  orgId: string;
  projectName: string;
}

export async function remonitorMainBranch(
  options: RemonitorMainBranchOptions,
): Promise<void> {
  const result = await triggerScaScan(options);
  console.log(result.stdout.trim());
}

async function main(): Promise<void> {
  await remonitorMainBranch({
    projectDirectory: getRequiredEnv("PROJECT_DIRECTORY"),
    orgId: getRequiredEnv("SNYK_ORG_ID"),
    projectName: getRequiredEnv("MAIN_SNYK_PROJECT_NAME"),
  });
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
