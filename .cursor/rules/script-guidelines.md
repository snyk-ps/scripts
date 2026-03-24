# Script Guidelines

Your purpose is to produce simple scripts and API wrappers for the Snyk APIs.
For simple scripts produce a shell script.
For more complex scripts or API wrappers produce Python scripts.

## General Requirements

- You must use the current date in **UTC** for all time-sensitive calculations and references. If necessary, access Google Search to verify.
  If necessary, access Google Search to verify.
- Never use an em dash (—) in comments or documentation.

## README Format

If a README doesn't exist, create one and ensure it has the following.
- Brief description of what the script does
- Installation/setup instructions
- Usage examples (usage for shell scripts begins with sh, for Python use python)

## Root README: Current Scripts table

Whenever you add a new script or tool directory at the repository root (alongside existing tools like `check_token`), you must update the root `README.md`:

- Add a row to the **Current Scripts** table under `## Current Scripts`.
- **Script Name:** link the directory name to that folder (for example `[my_tool](my_tool)`).
- **Description:** one short line consistent with existing rows (what it does, main inputs such as API or token if helpful).
- **Owner:** email of the maintainer. Use the **Author** line from the tool README or script header; if none exists, use the contributor Snyk email.
- Keep table rows **sorted alphabetically** by directory name.

Do not list non-tool folders such as `.cursor` in this table. Shared reference data stays documented elsewhere if needed.

## API specs (Cursor context)

Store OpenAPI and similar machine-readable specs under **`.cursor/rules/api_specs/`** when you integrate with third-party systems (Snyk, GitHub, or anything else you call over HTTP). Use subfolders or clear filenames (for example `snyk/rest-spec.json`, `github/openapi.yaml`) so it stays obvious which integration each file belongs to. These files are **context for Cursor** when generating or editing integration code; the application does not need to load them at runtime unless you deliberately ship them.

## Snyk API Reference

When referencing Snyk APIs in this project, consult the Snyk specs under `.cursor/rules/api_specs/snyk/` first (for example `rest-spec.json` and `v1-api-spec.yaml`). If the spec does not contain enough information, reference the [Snyk API
docs](https://docs.snyk.io/snyk-api):

- [REST API](https://docs.snyk.io/snyk-api/rest-api/about-the-rest-api)
- [V1 API](https://docs.snyk.io/snyk-api/v1-api)
- [Authentication](https://docs.snyk.io/snyk-api/authentication-for-api)


## Python Code Requirements

Target **Python 3.11+**.

All code produced for Python must:

- Always use argparse.
- For `SNYK_TOKEN` or any other secrets, use an environment variable. Never commit secrets. Do not log the token or credentials.
- Use PEP 257 docstrings on modules and public functions and methods.
- Follow PEP 8 Guidelines.
- Use the Python standard library when possible.
  Avoid dependencies outside the standard library if possible.
- Any dependency outside the standard library must not introduce high or critical issues. **Use Snyk** to verify new or updated dependencies before merging.
- Always add non-standard-library dependencies to the requirements file with **pinned versions** (for example `package==1.2.3`).
- Always produce a requirements file.

## Shell Script Requirements

All shell scripts must:

- Always start script with a shebang line to specify the interpreter, such as
  `#!/bin/bash` or `#!/usr/bin/env bash` for portability across non-Linux
  systems.

### Error Handling

Use `set -e`, `set -u`, and `set -o pipefail` (known as "strict mode") to make
scripts more robust by exiting on errors, uninitialized variables, and pipeline
failures:

- `set -e`: Exit immediately if any command returns a non-zero exit status.
- `set -u`: Terminate the script if an uninitialized variable is used.
- `set -o pipefail`: Ensure that a pipeline command fails if any command within
  the pipe fails, not just the last one.

### Quoting

Always double-quote variables and command substitutions (e.g., `"$var"` or
`"$(command)"`) to prevent issues with word splitting and pathname expansion
when dealing with spaces or special characters in filenames or input.

### Best Practices

- Use Built-ins: Prefer shell built-in commands (like `printf` over `echo`)
- Modularity & Functions: Break down complex scripts into reusable functions to
  improve readability and manage variable scope using the `local` keyword.
- Commenting: Include a comment block at the beginning of the script with its
  purpose, author (Full Name, Email), and revision
  history. Source full name and email from git.
  Use comments to explain non-obvious or complex sections of code.

### Naming Conventions

- User-defined variables: Use lowercase letters and underscores (snake_case)
  (e.g., `user_name`).
- Constants/Environment variables: Use all uppercase letters with underscores
  (e.g., `MAX_RETRIES`, `PATH`).
- Functions: Use lowercase letters and underscores to separate words
  (e.g., `process_data()`).

### Formatting

- Indentation: Consistently use spaces for indentation, 4 spaces
  per level, and avoid using tabs.
- Line Length: Aim for a maximum line length of 80 characters for readability
  in standard terminal windows.

# Additional Resources

When in doubt, fall back to
- For shell scripts: [Google's style guide for shell scripts](https://google.github.io/styleguide/shellguide.html#:~:text=Control%20flow%20statements%20in%20shell,aligned%20with%20the%20opening%20statement.).
- For Python scripts: [PEP 8 – Style Guide for Python Code
](https://peps.python.org/pep-0008/)