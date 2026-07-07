# Scripts

A shared repository for Snyk Professional Services team scripts and utilities.

## Overview

This repository contains simple scripts and tools developed by the Snyk Professional Services team to support common tasks and workflows. Feel free to contribute useful scripts that may benefit the team.

## Structure

Each script/tool should be contained in its own directory with clear documentation and any dependencies specified. Use appropriate dependency files for your language:

```
scripts/
├── script_name/
│   ├── script.py (or script.js, script.sh, etc.)
│   ├── requirements.txt (Python) OR package.json (Node.js) OR go.mod (Go) OR equivalent
│   └── README.md (recommended)
```

**Dependency file examples:**
- **Python**: `requirements.txt` or `Pipfile`
- **Node.js/JavaScript**: `package.json`
- **Go**: `go.mod`
- **Shell/Bash**: document system dependencies in README

## Current Scripts

| Script Name | Description | Owner |
|---|---|---|
| [check_token](check_token) | Python utility for checking GitHub organization permissions | torsten.cannell@snyk.io |
| [create_issues_table](create_issues_table) | Shell script that exports high and critical Snyk issues for a group to CSV via the REST API | torsten.cannell@snyk.io |
| [github_app_propagator](github_app_propagator) | Python utility that clones the Snyk GitHub App integration from one org to the other orgs in a group | torsten.cannell@snyk.io |
| [api_reference_flow](api_reference_flow) | TypeScript reference modules for the Vpost-merge SCA ignore copy flow and SAST SCM import flow | samuel.dahlberg@snyk.io |

## Contributing

1. Create a new directory for your script
2. Include all necessary source files
3. Add a dependency file appropriate for your language (e.g., `requirements.txt`, `package.json`, etc.)
4. Add a `README.md` with:
   - Brief description of what the script does
   - Installation/setup instructions
   - Usage examples
5. Add a row for your tool to the **Current Scripts** table in this README (see `.cursor/rules/script-guidelines.md`)
6. Ensure your script has clear comments and is easy for others to understand

## Requirements

- Appropriate runtime for your language (Python 3.x, Go, etc.)
- See individual script dependency files for additional library dependencies
