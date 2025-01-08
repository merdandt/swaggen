import requests
import re
import json
import os
import copy
import click
from swaggen.utils.swagger_config_singleton import ConfigSingleton

def fetch_and_parse_openapi(url):
    click.echo(f"Fetching OpenAPI data from {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        openapi_json = response.json()
        if openapi_json:
            # Now you can work with the openapi_json variable
            if "info" in openapi_json and "title" in openapi_json["info"]:
              click.echo(f"OpenAPI Title: {openapi_json['info']['title']}")
            return openapi_json
        else:
            click.echo("OpenAPI data is empty.")
    except requests.exceptions.RequestException as e:
        click.echo(f"Error fetching OpenAPI data: {e}")
        return None

# Hardcoded for now because we have extra tags that must not be included in client app.
def delete_tags_from_path(openapi_json):
    swagger_config = ConfigSingleton()

    cleaned_openapi_json = openapi_json.copy()
    tags4remove = [
      'PYGG',
      'USER_CHAT',
      'USER_FEEDBACK',
      'USER_TRANSPORT_AIRLINES',
      'USER_AYDYM',
      'USER_BELET',
      'USER_GTS',
      'USER_HAKIMLIK_UTILITY',
      'USER_HAKIMLIK_WATER',
      'USER_KABELTV',
      'USER_SERVICES',
      'USER_PYGG',
      'USER_TRANSPORT_RAILWAYS',
      'USER_TELECOM',
      'USER_TMCELL',
      'USER_SETTINGS',
      'USER_STATE',
      'USER_WALLET',
    ]


    # Delete from `tags` whose name starts with `CLIENT_` or matches any from `tags4remove`
    tags_to_delete = [
        tag for tag in openapi_json['tags'] if tag['name'].startswith('CLIENT_') or any(tag['name'] == item for item in tags4remove)
    ]

    for tag in tags_to_delete:
        cleaned_openapi_json['tags'].remove(tag)

    # Delete `path` from ```paths``` if the [tag] key does not exist in ```tags```
    paths_to_delete = []

    for path, methods in list(cleaned_openapi_json['paths'].items()):
        for method, operation in methods.items():
            # Check if 'tags' key is present in the operation
            if 'tags' in operation:
                # If none of the operation's tags are in cleaned_openapi_json['tags'], mark this path for deletion
                # (i.e., if every tag is not found in cleaned_openapi_json['tags'], we remove the path)
                if not any(tag in [t['name'] for t in cleaned_openapi_json['tags']] for tag in operation['tags']):
                    paths_to_delete.append(path)
                    break  # Stop checking further methods for this path once we decide to delete
            else:
                # If an operation has no 'tags', maybe you also want to delete the path
                # (Uncomment if that matches your logic)
                # paths_to_delete.append(path)
                # break
                pass    

    # Now delete all the gathered paths
    for path in paths_to_delete:
        if path in cleaned_openapi_json['paths']:  # Double-check key still exists
            del cleaned_openapi_json['paths'][path] 

    # Print the number of tags
    click.echo(f"Number of tags: {len(openapi_json['tags'])}")
    # Convert JSON to list and set the tags
    tags_list = [tag['name'] for tag in openapi_json['tags']]
    swagger_config.set_tags(tags_list)
    # Print the length of the ```paths``` objects
    click.echo(f"Number of paths: {len(openapi_json['paths'])}")
    # Print the length of the ```schema```s
    click.echo(f"Number of schemas: {len(openapi_json['components']['schemas'])}")
    
    return cleaned_openapi_json


# Function for retrieving the paths of the Tag
def get_paths_by_tag(openapi_data: dict, tag_to_find: str) -> dict:
    """
    Given an OpenAPI specification (as a dict) and a tag,
    return a dictionary of all paths that have at least one operation
    containing that tag. The returned dictionary will map each matched
    path to its full path definition (i.e., all methods and their details).
    """
    paths = openapi_data.get("paths", {})
    matched_paths = {}

    for path, methods in paths.items():
        for method, operation in methods.items():
            tags = operation.get("tags", [])
            if tag_to_find in tags:
                # If we find the tag, include this entire path object
                # (with all its methods) and then stop checking this path.
                matched_paths[path] = methods
                break

    # Return the dictionary directly (rather than, for example, matched_paths.items()).
    return matched_paths


# Helper function for finding exception tags
def has_error_key(data):
    """
    Recursively searches 'data' (which could be dict, list, or primitive)
    to find if there is any key named 'error'.
    Returns True if found, otherwise False.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            # If we directly encounter the key 'error', return True immediately
            if key == "error":
                return True
            # Otherwise, keep traversing
            if has_error_key(value):
                return True
    elif isinstance(data, list):
        # If it's a list, traverse each element
        for element in data:
            if has_error_key(element):
                return True
    # If data is neither dict nor list (e.g. int or string), do nothing special
    return False


# Find and replace all the references in the PATHS
def expand_paths_references(paths_data, openapi_spec):
    """
    Recursively expand all references in `paths_data` using the OpenAPI spec.
    Handles multiple nested references.
    Also tags the expanded schema dict with "schema_name" to record its origin.
    Detects cyclical references to avoid infinite loops.
    """

    # We'll create a deep copy to avoid mutating the original.
    expanded = copy.deepcopy(paths_data)

    # Access the schemas section from the openapi_spec
    schemas = openapi_spec.get("components", {}).get("schemas", {})

    def load_schema_from_ref(ref_value):
        """
        Given something like "#/components/schemas/MySchema" or "#components/schemas/MySchema",
        returns the actual dict definition for that schema from 'schemas',
        plus a "schema_name" key indicating which schema we loaded.
        """
        # Look for 'components/schemas/' substring
        if 'components/schemas/' in ref_value:
            schema_name = ref_value.split('components/schemas/')[-1]
            # Retrieve the actual schema, then add our 'schema_name'
            loaded = copy.deepcopy(schemas.get(schema_name, {}))
            loaded["schema_name"] = schema_name
            return loaded
        return {}

    # We'll keep a set to track references currently being expanded
    # to prevent infinite loops in case of cycles.
    currently_expanding = set()

    def expand(obj):
        """
        Recursively walk through 'obj':
         - If we see { "$ref": "..."} referencing a schema, we load & expand it
           and tag it with "schema_name".
         - If there's a chain of references (schema references another schema),
           we expand those as well.
         - If there's a cycle, we'll insert { "$ref_cycle_detected": ... } to avoid infinite loops.
        """
        if isinstance(obj, dict):
            # If the entire dict itself is a $ref
            if '$ref' in obj and isinstance(obj['$ref'], str) and 'components/schemas/' in obj['$ref']:
                ref_value = obj['$ref']

                # Detect cycles
                if ref_value in currently_expanding:
                    # Cycle detected! Return something safe or empty
                    return {"$ref_cycle_detected": ref_value}

                currently_expanding.add(ref_value)

                # Load the actual schema
                loaded_schema = load_schema_from_ref(ref_value)
                # Expand that schema (it might contain further references)
                result = expand(loaded_schema)

                currently_expanding.remove(ref_value)
                return result

            # Otherwise, keep traversing the dict to expand nested objects
            expanded_dict = {}
            for k, v in obj.items():
                expanded_dict[k] = expand(v)
            return expanded_dict

        elif isinstance(obj, list):
            # Expand each element of the list
            return [expand(item) for item in obj]

        else:
            # If it's neither dict nor list, just return it as is
            return obj

    return expand(expanded)


# Revoming the Query params from the paths
def remove_query_params_and_request_body(paths_data):
    """
    Takes an OpenAPI paths dictionary and returns a new version where
    'parameters' and 'requestBody' are removed from each operation.
    """
    # Make a deep copy so the original data remains unmodified
    cleaned_paths = copy.deepcopy(paths_data)

    for path, methods in cleaned_paths.items():
        for http_method, operation_data in methods.items():
            # Remove 'parameters' if it exists
            if 'parameters' in operation_data:
                del operation_data['parameters']

            # Remove 'requestBody' if it exists
            if 'requestBody' in operation_data:
                del operation_data['requestBody']

    return cleaned_paths

def remove_responses_empty_methods_keep_queries(paths_data):
    """
    Takes an OpenAPI paths dictionary and returns a new version where:
    - 'responses' are removed from each operation.
    - HTTP methods without 'parameters' or 'requestBody' are removed.

    Args:
        paths_data (dict): The OpenAPI paths dictionary.

    Returns:
        dict: A new paths dictionary with 'responses' removed and empty methods excluded.
    """
    # Make a deep copy to ensure the original data remains unmodified
    cleaned_paths = copy.deepcopy(paths_data)

    paths_to_delete = []  # To keep track of paths that may become empty

    for path, methods in cleaned_paths.items():
        methods_to_delete = []  # To keep track of methods to remove within this path

        for http_method, operation_data in methods.items():
            # Remove 'responses' if it exists
            if 'responses' in operation_data:
                del operation_data['responses']

            # Check if both 'parameters' and 'requestBody' are absent
            has_parameters = 'parameters' in operation_data and bool(operation_data['parameters'])
            has_request_body = 'requestBody' in operation_data and bool(operation_data['requestBody'])

            if not has_parameters and not has_request_body:
                methods_to_delete.append(http_method)

        # Remove the identified methods
        for method in methods_to_delete:
            del methods[method]

        # If after deletion, the path has no methods left, mark it for deletion
        if not methods:
            paths_to_delete.append(path)

    # Optionally, remove paths that have no methods left
    for path in paths_to_delete:
        del cleaned_paths[path]

    return cleaned_paths