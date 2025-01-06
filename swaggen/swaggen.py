import click
import os
import swaggen.utils.swagger_json_utils as sju
from swaggen.exception_creator.exception_creator import generate_error_types_enum
from swaggen.gen_ai.gen_ai_handler  import GenerativeAITaskHandler
from swaggen.model_creator.model_creator import create_dart_files

@click.group()
@click.version_option(version='0.1.0')
def cli():
    """
    Swaggen CLI - Generate Dart/Flutter code from Swagger documentation referencing OpenAPI specifications.
    """
    pass

@cli.command()
def clear():
    """
    Clear all files created by Swaggen.
    """
    click.echo('Clearing all files created by Swaggen...')
    # Clear folders at packages/core/src/model and packages/core/src/exceptions
    os.system('rm -rf packages/core/src/model/*')
    os.system('rm -rf packages/core/src/exceptions/*')
    click.echo('Done!')

@cli.command()
@click.option('--url', required=True, help='URL to Swagger documentation.')
def generate(url):
    """
    Generate Dart/Flutter code from Swagger documentation.
    """
    click.echo(f'Generating Dart/Flutter code from Swagger doc - {url}')
    json_object = sju.fetch_and_parse_openapi(url)
    if not json_object:
        click.echo('Error fetching OpenAPI data.')
        return None
    click.echo('OpenAPI data fetched successfully.')
    click.echo('Cleaning up OpenAPI data... (optional in future)')
    cleaned_openapi_json = sju.delete_tags_from_path(json_object)
    generate_error_types_enum(cleaned_openapi_json)
    click.echo("Start generating Models' code...")

    generative_ai_handler = GenerativeAITaskHandler()
    # for loop
    # Retrieving the concrete path
    one = "USER_ALEMTV"
    paths_of_one = sju.get_paths_by_tag(cleaned_openapi_json, one)
    expanded_paths_of_one =sju.expand_paths_references(paths_of_one, cleaned_openapi_json)
    cleaned_query_paths_of_one = sju.remove_query_params_and_request_body(expanded_paths_of_one)
    # generating
    dart_models_raw=generative_ai_handler.generate_models(paths=cleaned_query_paths_of_one)
    create_dart_files(dart_classes_string=dart_models_raw, folder_name=one.lower())


if __name__ == '__main__':
    cli()
