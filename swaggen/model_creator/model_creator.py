import click
import os
import re

# Points to: packages/core/lib/src/models/{folder_name}
MODELS_FOLDER_PATH = "packages/core/lib/src/models/{folder_name}"

# If you have a different root folder, adjust this accordingly.
# This is the folder containing `models.dart` file at the "models" root level.
MODELS_ROOT_FOLDER = "packages/core/lib/src/models"

def create_dart_files(dart_classes_string: str, folder_name: str) -> None:
    """
    Parse the 'dart_classes_string' to find sections of the form:
        <some_name.dart>
        ...Dart code...
        </some_name.dart>

    Create a 'folder_name' directory (if not exists) and
    write each snippet to 'some_name.dart' inside that folder.

    Then generate or update:
        1) A barrel file named <folder_name>.dart in that folder.
        2) A root-level models.dart file that exports each folder's barrel file.
    """
    click.echo(f"Creating Dart models for: {folder_name}")
    folder_path = MODELS_FOLDER_PATH.format(folder_name=folder_name)

    # 1. Make sure the target folder exists
    os.makedirs(folder_path, exist_ok=True)

    # 2. Find each <filename.dart>...</filename.dart> block
    pattern = re.compile(r"<([^>]+)\.dart>(.*?)</\1\.dart>", re.DOTALL)
    matches = pattern.findall(dart_classes_string)

    # 3. Remove all ``` and ```dart annotations
    matches = [(filename, code.replace("```dart", "").replace("```", "")) 
               for filename, code in matches]

    written_files = []

    # 4. For each match, write the content to file
    for filename, dart_code in matches:
        file_path = os.path.join(folder_path, f"{filename}.dart")

        # Clean up leading/trailing whitespace
        dart_code = dart_code.strip()

        # Write to the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(dart_code)

        click.echo(f"Created: {file_path}")
        written_files.append(filename + ".dart")

    if not matches:
        click.echo("No <...>.dart blocks found in the input string.")
    else:
        # 5. Create/Update the folder-level barrel file
        create_barrel_file(folder_name, written_files)

        # 6. Add an export for this folder’s barrel file to root `models.dart`
        update_models_export_file(folder_name)

def create_barrel_file(folder_name: str, generated_files: list[str]) -> None:
    """
    Create or update a barrel file named <folder_name>.dart in the folder.
    It exports all the .dart files in the folder, excluding itself.
    """
    folder_path = MODELS_FOLDER_PATH.format(folder_name=folder_name)
    barrel_filename = f"{folder_name}.dart"
    barrel_path = os.path.join(folder_path, barrel_filename)

    # List all Dart files in that directory, excluding the barrel file itself
    all_dart_files = [
        f for f in os.listdir(folder_path)
        if f.endswith(".dart") and f != barrel_filename
    ]

    with open(barrel_path, "w", encoding="utf-8") as barrel_file:
        for dart_file in all_dart_files:
            barrel_file.write(f"export '{dart_file}';\n")

    click.echo(f"Barrel file created/updated: {barrel_path}")

def update_models_export_file(folder_name: str) -> None:
    """
    Ensure that the root-level `models.dart` file exports 
    the barrel file for the newly added folder.

    - If `models.dart` doesn’t exist yet, create it.
    - If `models.dart` already exists, make sure it exports `<folder_name>/<folder_name>.dart`.
    """
    # Path to the root-level models.dart
    models_file_path = os.path.join(MODELS_ROOT_FOLDER, "models.dart")
    export_line = f"export '{folder_name}/{folder_name}.dart';\n"

    # 1. If it doesn’t exist, just create it with this single line.
    if not os.path.exists(models_file_path):
        with open(models_file_path, "w", encoding="utf-8") as f:
            f.write(export_line)
        click.echo(f"Created root models.dart with export for {folder_name}.")
        return

    # 2. If it does exist, read it in, then re-write only if needed
    with open(models_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Check if we already have an export for this folder
    if any(export_line.strip() == line.strip() for line in lines):
        click.echo(f"Root models.dart already contains export for {folder_name}.")
        return

    # Otherwise, append it to the end and write it back
    lines.append(export_line)
    with open(models_file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    click.echo(f"Added export line for '{folder_name}' to root models.dart.")
