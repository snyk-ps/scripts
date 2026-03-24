# Script Guidelines

Your purpose is to produce simple scripts and API wrappers for the Snyk APIs.
For simple scripts produce a shell script.
For more complex scripts or API wrappers produce Python scripts.

## General Requirements

- You must use the current date in all time-sensitive calculations and references.
  If necessary, access Google Search to verify.
- Never use an em dash (—) in comments or documentation.

## README Format

If a README doesn't exist, create one and ensure it has the following.
- Brief description of what the script does
- Installation/setup instructions
- Usage examples (usage for shell scripts begins with sh, for Python use python)

## Snyk API Reference

For any API to Snyk references, reference the API specs in ./scripts/api_specs.
If the spec does not contain enough information, reference the [Snyk API
docs](https://docs.snyk.io/snyk-api):

- [REST API](https://docs.snyk.io/snyk-api/rest-api/about-the-rest-api)
- [V1 API](https://docs.snyk.io/snyk-api/v1-api)
- [Authentication](https://docs.snyk.io/snyk-api/authentication-for-api)

## Python Code Requirements

All code produced for Python must:

- Always use argparse.
  For the SNYK_TOKEN use an environment variable.
- Use PEP 257 docstrings
- Follow PEP 8 Guidelines
- Use the Python library when possible.
  Avoid dependencies outside the standard library if possible.
- Any dependencies outside the standard library must not contain any high or
  critical vulnerabilities.
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

### Additional Resources

When in doubt, fall back to
- For shell scripts: [Google's style guide for shell scripts](https://google.github.io/styleguide/shellguide.html#:~:text=Control%20flow%20statements%20in%20shell,aligned%20with%20the%20opening%20statement.).
- For Python scripts: [PEP 8 – Style Guide for Python Code
](https://peps.python.org/pep-0008/)