# check_token

Checks GitHub organization permissions by listing repositories and retrieving repository contents.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
export GITHUB_TOKEN=<your-github-token>
python check_token.py <org-name>
```

For multiple organizations:
```bash
python check_token.py "org1,org2,org3"
```

## Output

Returns JSON with results of two permission checks:
- `repo_list_check`: Verifies ability to list organization repositories
- `repo_contents_check`: Verifies ability to read repository contents
