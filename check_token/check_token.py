import os
import argparse
import json
from github import Github, Auth, GithubException

class ApiClient:
    """
    A client to interact with the GitHub API using the PyGithub library.
    """

    def __init__(self, github_token):
        """
        Initializes the ApiClient with a GitHub Personal Access Token.
        """
        if not github_token:
            raise ValueError("GitHub token cannot be empty.")
        self.github = Github(auth=Auth.Token(github_token))

    def check_org_permissions(self, org_name):
        """
        Performs two permission checks on a single GitHub organization.

        1. Lists all repositories in the organization.
        2. Retrieves the contents of the first repository in that list.

        Args:
            org_name (str): The name of the GitHub organization.

        Returns:
            dict: A dictionary with the results for the two checks.
        """
        results = {
            "org_name": org_name,
            "repo_list_check": {"result": "fail", "message": {}},
            "repo_contents_check": {"repo_name": "N/A", "result": "fail", "message": {}}
        }

        try:
            organization = self.github.get_organization(org_name)

            # Check 1: List Repositories
            repos = organization.get_repos()
            
            results["repo_list_check"]["result"] = "success"
            results["repo_list_check"]["message"] = f"Successfully listed {repos.totalCount} repositories."

            # Check 2: Get Repository Contents
            if repos.totalCount > 0:
                first_repo = repos[0]  
                
                results["repo_contents_check"]["repo_name"] = first_repo.name
                try:
                    # Attempt to get contents, which validates 'repo' scope.
                    first_repo.get_contents("/")
                    results["repo_contents_check"]["result"] = "success"
                    results["repo_contents_check"]["message"] = "Successfully retrieved repository contents."
                except GithubException as e:
                    results["repo_contents_check"]["message"] = {"error": f"Failed to get contents: {e.data['message']}"}
            else:
                results["repo_contents_check"]["message"] = {"error": "No repositories found to check contents."}

        except GithubException as e:
            results["repo_list_check"]["message"] = {"error": f"Failed to list repos: {e.data['message']}"}
        except Exception as e:
            results["repo_list_check"]["message"] = {"error": str(e)}

        return results

def main():
    """
    Main function to parse arguments and run the checks.
    """
    parser = argparse.ArgumentParser(description="Check GitHub permissions for organizations.")
    parser.add_argument(
        "orgs",
        type=str,
        help="A comma-separated list of GitHub organization names."
    )
    
    args = parser.parse_args()
    org_names = [org.strip() for org in args.orgs.split(',')]

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is not set.")
        exit(1)

    try:
        client = ApiClient(github_token)
        all_results = []

        for org in org_names:
            print(f"Checking permissions for organization: {org}...")
            result = client.check_org_permissions(org)
            all_results.append(result)

        final_output = {"orgs": all_results}
        print("\n--- Final Results ---")
        print(json.dumps(final_output, indent=2))
        
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()