import os
import click
from swaggen.utils.swagger_json_utils import has_error_key
from swaggen.utils.swagger_config_singleton import ConfigSingleton

def generate_error_types_enum(openapi_json):
    """
    Gathers all schema names within openapi_json['components']['schemas']
    for which there's an 'error' key anywhere in the schema definition.

    - Stores those schema names in the global list GLOBAL_ERROR_TYPES.
    - Constructs a Dart enum named 'ExceptionTypes' with these entries.
    - Returns the enum string for immediate use if needed.
    """
    click.echo('Generating ExceptionTypes enum...')
    swagger_config = ConfigSingleton()
    # Validate the input structure
    if openapi_json and "components" in openapi_json and "schemas" in openapi_json["components"]:
        # Look through each schema's data
        for schema_name, schema_data in openapi_json["components"]["schemas"].items():
            # Use our helper function to find 'error' key in any sub-node
            if has_error_key(schema_data):
                swagger_config.append_to_error_types(schema_name)


    # Build Dart enum definition
    enum_string = """
    // ignore_for_file: constant_identifier_names\n

    enum ExceptionTypes {\n"""
    for error_type in swagger_config.get_error_types():
        enum_string += f"  {error_type},\n"
    enum_string += """OTHER\n}\n"""

    with open('packages/core/lib/src/exceptions/exception_types.dart', 'w') as f:
        f.write(enum_string)            
    click.echo(f'{len(swagger_config.get_error_types())} error types generated.')   
