/**
 * Step 1: Trigger a Snyk SCA scan using the Snyk CLI (snyk monitor).
 *
 * This is the "merge" event trigger from the reference diagram: on a GitHub
 * push/merge event, run `snyk monitor` against the feature branch so any
 * violations are captured. Step 3 re-monitors main after ignores are copied.
 *
 * `snyk monitor` has no REST/v1 API equivalent, so this step always shells
 * out to the installed Snyk CLI. Keep the CLI invocation in a small,
 * reusable function so it can be lifted into a Lambda handler or similar.
 */

import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { getRequiredEnv } from "./lib/snykClient";

const execFileAsync = promisify(execFile);

export interface TriggerScaScanOptions {
  /** Local path to the checked out repository/branch to scan. */
  projectDirectory: string;
  /** Snyk org ID to monitor into. */
  orgId: string;
  /** Project name to record in Snyk, for example "my-repo:feature/my-branch". */
  projectName: string;
}

export interface TriggerScaScanResult {
  stdout: string;
  stderr: string;
}

export async function triggerScaScan(
  options: TriggerScaScanOptions,
): Promise<TriggerScaScanResult> {
  const token = getRequiredEnv("SNYK_TOKEN");

  try {
    const { stdout, stderr } = await execFileAsync(
      "snyk",
      [
        "monitor",
        `--org=${options.orgId}`,
        `--project-name=${options.projectName}`,
      ],
      {
        cwd: options.projectDirectory,
        env: {
          ...process.env,
          SNYK_TOKEN: token,
        },
      },
    );
    return { stdout, stderr };
  } catch (error) {
    const err = error as { stdout?: string; stderr?: string; message: string };
    throw new Error(
      `snyk monitor failed for ${options.projectName}: ${err.stderr ?? err.message}`,
    );
  }
}

async function main(): Promise<void> {
  const result = await triggerScaScan({
    projectDirectory: getRequiredEnv("PROJECT_DIRECTORY"),
    orgId: getRequiredEnv("SNYK_ORG_ID"),
    projectName: getRequiredEnv("SNYK_PROJECT_NAME"),
  });
  console.log(result.stdout.trim());
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
