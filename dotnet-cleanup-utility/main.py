from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import json
import os
import argparse

# Load variables from .env if the file exists, but do not override system environment variables
load_dotenv(override=False)

# Get environment variables (prioritizing system environment variables)
org_id = os.getenv('SNYK_ORG_ID')
api_token = os.getenv('SNYK_API_TOKEN')

# Check if variables are set, raise an error if missing
if not org_id or not api_token:
    raise EnvironmentError("Missing required environment variables: SNYK_ORG_ID and/or SNYK_API_TOKEN")

base_url_v1 = 'https://api.snyk.io/v1'
base_url_rest = 'https://api.snyk.io/rest'
project_last_tested_delta_minutes = int(os.getenv('PROJECT_LAST_TESTED_DELTA_MINUTES', '1'))
# project_id = os.getenv('PROJECT_ID')

def get_org_project_ids(org_id, api_token):
      # Ensure all required environment variables are set
    if not all([org_id, api_token]):
        raise ValueError("Missing one or more required function parameters: ORG_ID, API_TOKEN")

    # Construct the URL
    url = f'{base_url_rest}/orgs/{org_id}/projects?version=2024-05-01'

    # Set headers
    headers = {
        'Accept': 'application/vnd.api+json',
        'Authorization': api_token
    }

    try:
        # Make the DELETE request
        response = requests.request("GET", url, headers=headers)

        # Handle specific HTTP response codes
        if response.status_code == 200:
            print(f"Project for org ID: '{org_id}' successfully received.")
        elif response.status_code == 404:
            print(f"Error: Org ID: {org_id} Projects not found.")
        elif response.status_code == 401:
            print("Error: Unauthorized. Check your API token.")
        elif response.status_code == 403:
            print("Error: Unauthorized. Check your API token.")
        else:
            print(f"Unexpected response: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")
    
    project_ids = []

    if response.status_code == 200:
        # Extract project IDs from response and store them in project_ids array
        project_ids = [project['id'] for project in response.json().get('data', [])]

        # Loop through the collected project IDs and process them
        for project_id in project_ids:
            print(f"Found Project ID : {project_id}")            

    return project_ids
    
def get_project_details(org_id, project_id, api_token):
    # Ensure all required parameters are set
    if not all([org_id, project_id, api_token]):
        raise ValueError("Missing one or more required function parameters: ORG_ID, PROJECT_ID, API_TOKEN")
    
    # Define base URLs
    base_url_rest = "https://api.snyk.io/rest"
    base_url_v1 = "https://api.snyk.io/v1"
    
    # Construct URLs for both requests
    url_rest = f"{base_url_rest}/orgs/{org_id}/projects/{project_id}?version=2024-05-01"
    url_v1 = f"{base_url_v1}/org/{org_id}/project/{project_id}"
    
    # Set headers
    headers_rest = {
        'Accept': 'application/vnd.api+json',
        'Authorization': api_token
    }

    headers_v1 = {
    'Content-Type': 'application/json',
    'Authorization': 'token ' + api_token 
    }
    
    try:
        # Make the first GET request
        response_rest = requests.get(url_rest, headers=headers_rest)
        response_rest.raise_for_status()
        data_rest = response_rest.json().get("data", {})
        
        # Make the second GET request
        response_v1 = requests.get(url_v1, headers=headers_v1)
        response_v1.raise_for_status()
        data_v1 = response_v1.json()        

        project_name = data_v1.get("name", data_rest.get("attributes", {}).get("name"))
        project_id =  data_v1.get("id", data_rest.get("id"))
        project_created_date =  data_v1.get("created", data_rest.get("attributes", {}).get("created"))
        project_last_tested_date = data_v1.get("lastTestedDate")
        project_runtime = data_rest.get("attributes", {}).get("target_runtime")

        print(f"Project : {project_name} runtime : {project_runtime} details successfully retrieved.")

        # Merge relevant fields
        merged_data = {
            "name": project_name,
            "id": project_id,
            "created_date": project_created_date,
            "last_tested_date": project_last_tested_date,
            "runtime":project_runtime
        }
        
        return merged_data
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while retrieving Project ID : {project_id} order Org ID : {org_id}: {e}")
        return None

def delete_project(org_id, project_id, api_token):
    # Ensure all required environment variables are set
    if not all([org_id, project_id, api_token]):
        raise ValueError("Missing one or more required environment variables: ORG_ID, PROJECT_ID, API_TOKEN")

    # Construct the URL
    url = f'https://api.snyk.io/rest/orgs/{org_id}/projects/{project_id}?version=2024-05-01'

    # Set headers
    headers = {
        'Accept': 'application/vnd.api+json',
        'Authorization': api_token
    }

    try:
        # Make the DELETE request
        response = requests.request("DELETE", url, headers=headers)

        # Log response status and details
        # print(f"Response Status Code: {response.status_code}")
        # print(f"Response Reason: {response.reason}")
        # print(f"Response Text: {response.text}")

        # Handle specific HTTP response codes
        if response.status_code == 204:
            print(f"Project ID : {project_id} order Org ID : {org_id} successfully deleted.")
        elif response.status_code == 404:
            print("Error: Project not found.")
        elif response.status_code == 401:
            print("Error: Unauthorized. Check your API token.")
        elif response.status_code == 500:
            print("Error: Serverside Error.")
        else:
            print(f"Unexpected response: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the request: {e}")
    
    if(response.status_code == 204):
        return True
    else:
        return False

def create_project_keep_deletion_lists(project_json):
    project_name_map = defaultdict(list)
    
    # Step 1: Group projects by details.name
    for item in project_json:
        project_name = item["details"]["name"]
        project_name_map[project_name].append(item)
    
    # Step 2: Sort each list by details.tested (most recent first)
    for project_name in project_name_map:
        project_name_map[project_name].sort(key=lambda x: x["details"]["last_tested_date"], reverse=True)
    
    projects_to_keep = []    
    
    # Step 3: Keep the most recent project from each group
    for project_name, projects in project_name_map.items():
        if projects:
            projects_to_keep.append(projects.pop(0))
    
    # Step 4: Handle projects created from the same .csproj file
    delete_candidates = []
    for project_name, projects in project_name_map.items():
        delete_candidates.extend(projects)
    
    final_delete_list = []
    for project in delete_candidates:

        project_tested_time = parse_iso_datetime(project["details"]["last_tested_date"])
        
        # Check if any project in the keep list was tested within one minute of this project
        if not any(
            abs(parse_iso_datetime(keep_project["details"]["last_tested_date"]) - project_tested_time) <= timedelta(minutes=project_last_tested_delta_minutes)
            for keep_project in projects_to_keep
        ):
            final_delete_list.append(project)
        else:
            projects_to_keep.append(project)  # Retain due to proximity
    
    return {"keep": projects_to_keep, "delete": final_delete_list}

def get_ignores_for_project_v1(org_id, project_id, api_token):

    # Ensure all required environment variables are set
    if not all([org_id, project_id, api_token]):
        raise ValueError("Missing one or more required environment variables: ORG_ID, PROJECT_ID, API_TOKEN")

    url = f"{base_url_v1}/org/{org_id}/project/{project_id}/ignores"
        
    ignored_issues = []
            
    headers = {
            "Authorization": f"token {api_token}"
        }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response = response.json()
    
    if response is not None and response != {}:
        keys = list(response.keys())

        for key in keys:
            subobjects = response[key]

            for subobj in subobjects:
                path = list(subobj.keys())[0]
                settings = subobj[path]
                reason = settings["reason"]
                reason_type = settings["reasonType"]
                expires = settings.get("expires", "")
                disregard = settings["disregardIfFixable"]

                ignore_obj = {
                    "project-id": project_id,
                    "key": key,
                    "path": path,
                    "reason": reason,
                    "expires": expires,
                    "type": reason_type,
                    "disregard": disregard
                }

                ignored_issues.append(ignore_obj)
        
    return ignored_issues

def get_issues_for_project(org_id, project_id, api_token, ignored):

    # Ensure all required environment variables are set
    if not all([org_id, project_id, api_token]):
        raise ValueError("Missing one or more required environment variables: ORG_ID, PROJECT_ID, API_TOKEN")
                            
    url = f"{base_url_rest}/orgs/{org_id}/issues?scan_item.id={project_id}&scan_item.type=project&ignored={ignored}&version=2024-10-15"

    headers = {
    'Content-Type': 'application/json',
    "Authorization": f"token {api_token}"
    }
    
    payload = {}    

    response = requests.request("GET", url, headers=headers, data=payload)
    response.raise_for_status()
    response = response.json()

    
    issues_to_keep = []
    if response is not None and response != {}:
        if response['data'] is not None:
            for issue in response['data']:
                
                id = issue['id']
                attributes = issue['attributes']
                key = attributes['key']
                ignored = attributes['ignored']

                issue_obj = {
                    "project-id": project_id,
                    "id": id,
                    "key": key,
                    "ignored": ignored
                }

                issues_to_keep.append(issue_obj)            

    return issues_to_keep


def migrate_ignores_for_project(issues_in_project_to_keep, ignores_to_migrate, project, org_id, project_id, api_token, dry_run):
        # Ensure all required environment variables are set
    if not all([project, org_id, project_id, api_token]):
        raise ValueError("Missing one or more required environment variables: PROJECT_NAME, ORG_ID, PROJECT_ID, API_TOKEN")
    
    # Check if the project_name exists in ignored_issues_to_migrate
    if project["details"]["name"] in ignores_to_migrate and project["details"]["name"] in issues_in_project_to_keep:
        # Iterate through the issues for this project
        for ignore in ignores_to_migrate[project["details"]["name"]]:            
            # Iterate through the issues for the project being kept
            for issue_to_keep in issues_in_project_to_keep[project["details"]["name"]]:                
                    # If the key of the existing ignore from a project do delte matches the 
                    # the key for an issue within the project to keep then we are considering
                    # the issue matching and will proceed with the ignore
                    if ignore['key'] == issue_to_keep['key']:
                        # To avoid trying to create duplicate ignores
                        # we are checking to see if there is already an ignore on the 
                        # newer project issue and if there is then we do not proceed
                        if not issue_to_keep['ignored']:

                            #Gather the relevant information needed and create the request.
                            issue_id = issue_to_keep['key']
                            reason = ignore.get("reason", "No reason provided")
                            type = ignore.get("type", "temporary-ignore")
                            disregard = ignore.get("disregard", False)
                            expires = ignore.get("expires")
                                                        
                            url = f"https://snyk.io/api/v1/org/{org_id}/project/{project_id}/ignore/{issue_id}"
                            headers = {"Authorization": f"token {api_token}", "Content-Type": "application/json"}
                            
                            payload = {}

                            if len(expires) == 0:
                                payload= json.dumps({"reason": reason,"reasonType":type,"disregardIfFixable":disregard})
                            else:                                                         
                                payload= json.dumps({"reason": reason,"reasonType":type,"disregardIfFixable":disregard,"expires":expires})

                            print(f'Migrating Ignore for Issue : {issue_to_keep["key"]} under Project : {project["details"]["name"]} - runtime : {project["details"]["runtime"]}  : ID { project_id }.')

                            if not dry_run:
                                response = requests.request("POST", url, headers=headers, data=payload)
                                response.raise_for_status()
                                
                                data = response.json()

                                print(f'Ignore for Issue : {issue_to_keep["key"]} under Project : {project["details"]["name"]} - runtime : {project["details"]["runtime"]}  : ID { project_id } migrated successfully.')

    else:
        print(f'No issues found to migrate for project : {project["details"]["name"]} - runtime : {project["details"]["runtime"]}  : ID { project_id }.')

# This function is used to parse ISO datetime strings and ensure compatibility with the format expected by Python's datetime module.
# This is specifically for supporting various versions of Python's datetime parsing, especially for handling the 'Z' suffix in ISO strings.
def parse_iso_datetime(iso_string):
    """Ensures compatibility by replacing 'Z' with '+00:00' if present."""
    if iso_string.endswith("Z"):
        iso_string = iso_string.replace("Z", "+00:00")
    return datetime.fromisoformat(iso_string)

# This function converts common string representations of boolean values to Python's boolean type.
def str_to_bool(value):
    """Convert common string representations to boolean."""
    if isinstance(value, bool):
        return value
    if value.lower() in {"true", "1", "yes", "y"}:
        return True
    elif value.lower() in {"false", "0", "no", "n"}:
        return False
    else:
        raise argparse.ArgumentTypeError(f"Invalid boolean value: '{value}'")    

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="A script that accepts a command-line argument.")
    parser.add_argument("--dry-run", type=str_to_bool, default=True, help="By default this utility is run in Dry Run which will only print the ignores to be added and will NOt delete and projects.")
    
    args = parser.parse_args()
    dry_run = args.dry_run

    print(f"Dry Run is Set to : {dry_run}")

    # Call the function to get all project IDs
    project_ids = get_org_project_ids(org_id, api_token)  
    
    # Initialize a dictionary to store project details by project ID
    project_details_list = []
    project_deletion_list = []

    # Loop through the collected project IDs and fetch details for each
    for project_id in project_ids:        
        project_details_list.append({
            'id': project_id,
            'details': get_project_details(org_id, project_id, api_token)
        })

    # Print or use the structured list
    # print(project_details_list) 
    keep_delete_dict = create_project_keep_deletion_lists(project_details_list)
    project_deletion_list = keep_delete_dict["delete"]
    project_keep_list = keep_delete_dict["keep"]

    for project in project_keep_list:
        print(f'Keeping - Project Name: {project["details"]["name"]} - runtime : {project["details"]["runtime"]} - Created At: {project["details"]["created_date"]} - ID: {project["id"]}')

    # Loop through the list of projects that will be deleted and retrieve all the ignores
    # unfortunately the ignores don't come with the issue id, so we will have to match off the key
    ignores_to_migrate = defaultdict(list)
    for project in project_deletion_list:
        ignores_to_migrate[project["details"]["name"]] = get_ignores_for_project_v1(org_id, project['id'], api_token)

    # Retrieve all the issues per project that are not ignored so that we can add ignores to them if appropriate. 
    issues_in_project_to_keep = defaultdict(list)
    for project in project_keep_list:
        issues_in_project_to_keep[project["details"]["name"]] = get_issues_for_project(org_id, project['id'], api_token, ignored='false')

    for project in project_keep_list:        
        migrate_ignores_for_project(issues_in_project_to_keep, ignores_to_migrate, project, org_id, project['id'], api_token, dry_run)
    
    # Loop through the collected project details and delete projects 
    for project in project_deletion_list:        
        print(f'Deleting - Project Name: {project["details"]["name"]} - runtime : {project["details"]["runtime"]} - Created At: {project["details"]["created_date"]} - ID: {project["id"]}')
        if not dry_run:
            delete_project(org_id, project['id'], api_token)
