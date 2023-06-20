from itertools import count
import argparse
import json
import requests
import tableauserverclient as TSC
from tableauserverclient import Pager


def viz_portal_call(server: TSC.Server, payload: dict) -> dict:
    """
    Make a call to the VizPortal API.
    Leverage REST Auth token for authentication.
    This is not officially supported by Tableau.
    """
    endpoint = payload.get("method")
    url = f"{server.server_address}/vizportal/api/web/v1/{endpoint}"
    headers = {
        "cache-control": "no-cache",
        "accept": "application/json, text/plain, */*",
        "x-xsrf-token": "",
        "content-type": "application/json;charset=UTF-8",
    }
    headers["cookie"] = f"workgroup_session_id={server.auth_token}; XSRF-TOKEN="

    response = requests.post(
        url, headers=headers, data=json.dumps(payload), verify=False
    )
    if response.status_code != 200:
        raise Exception(f"Response: {response.text}")

    return response.json()


def get_project_vpc_data(server: TSC.Server) -> dict:
    """Get all projects from the VizPortal API"""
    project_payload = {
        "method": "getProjects",
        "params": {
            "order": [{"field": "name", "ascending": True}],
            "page": {"startIndex": 0, "maxItems": 600},
        },
    }
    vpc_projects = viz_portal_call(server, project_payload)
    result = vpc_projects["result"]
    return result["projects"], result["users"]


def lookup_user_by_id(vpc_users: list[dict], user_id: str) -> dict:
    """Lookup a user from the VizPortal API result by its ID"""
    return next((user for user in vpc_users if user["id"] == str(user_id)), None)


def lookup_project_by_id(items: list[TSC.ProjectItem], item_id: str) -> TSC.ProjectItem:
    """Lookup a project from the REST API result by its ID"""
    return next((item for item in items if item.id == item_id), None)


def lookup_parent_project(vpc_projects: list[dict], parent_id: str) -> dict:
    """Lookup a project from the VizPortal API result by its ID"""
    return next(
        (project for project in vpc_projects if project["id"] == str(parent_id)), None
    )


def get_rest_projects_and_populate_permissions(
    server: TSC.Server,
) -> list[TSC.ProjectItem]:
    """Get all projects from the REST API and populate the permissions"""
    rest_projects = list(Pager(server.projects))
    for project in rest_projects:
        server.projects.populate_permissions(project)
    return rest_projects


def get_project_level_and_root(vpc_projects: list[dict], vpc_project: dict) -> str:
    """Determine the project level and root project ID"""
    if vpc_project["topLevelProject"]:
        return 0, vpc_project["luid"]

    for project_level in count(1):
        parent_project = lookup_parent_project(vpc_projects, vpc_project["parentProjectId"])
        if parent_project["topLevelProject"]:
            return project_level, parent_project["luid"]
        vpc_project = parent_project


def main():
    # CLI arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("--pat-name", "-n", required=True, help="The name of the Personal Access Token")
    parser.add_argument("--pat-value", "-v", required=True, help="The value of the Personal Access Token")
    parser.add_argument("--server", "-s", required=True, help="The Tableau Server URL")
    parser.add_argument("--site", "-t", help="The site ID", default="")

    args = parser.parse_args()

    server = TSC.Server(args.server, use_server_version=True)
    server.add_http_options({"verify": False})
                        
    tableau_auth = TSC.PersonalAccessTokenAuth(
        token_name=args.pat_name, personal_access_token=args.pat_value, site_id=args.site
    )

    site_name = args.site
    
    with server.auth.sign_in(tableau_auth):
        # Get all projects from the REST API
        rest_projects = get_rest_projects_and_populate_permissions(server)

        # Get all projects from the VizPortal API
        vpc_projects, vpc_users = get_project_vpc_data(server)

        # Merge the VPC data with the REST API data
        # We need to do this because the REST API does not provide the owner name
        # or the project level/root project ID
        for vpc_project in vpc_projects:
            # Set the site name
            vpc_project["siteName"] = site_name

            # Lookup the REST API project object
            rest_project = lookup_project_by_id(rest_projects, vpc_project["luid"])
            if rest_project is None:
                raise Exception(f"Project with luid {vpc_project['luid']} not found")

            # Set the project content permissions
            vpc_project["contentPermissions"] = rest_project.content_permissions

            # Lookup the owner metadata
            project_owner = lookup_user_by_id(vpc_users, vpc_project["ownerId"])
            vpc_project["ownerName"] = project_owner["displayName"]
            vpc_project["ownerDSID"] = project_owner["username"]

            # Determine the project level and root project ID
            project_level, root_project_luid = get_project_level_and_root(
                vpc_projects, vpc_project
            )
            vpc_project["projectLevel"] = project_level
            vpc_project["rootProjectId"] = root_project_luid

        # After we process all the Projects, we can append the parent project
        # This is done in a separate loop because the parent project may not
        # be in the list yet
        for vpc_project in vpc_projects:
            # Check if the project has a parent project
            parent_project_id = vpc_project.get("parentProjectId")

            # If the project has a parent project, append it
            if parent_project_id:
                vpc_project["parentProject"] = lookup_parent_project(
                    vpc_projects, parent_project_id
                )

    # Write the results to a JSON file
    with open("output/projects.json", "w") as f:
        json.dump(vpc_projects, f, indent=4)


if __name__ == "__main__":
    main()
