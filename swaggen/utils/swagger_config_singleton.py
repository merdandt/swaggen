import re

class ConfigSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigSingleton, cls).__new__(cls)
            # Initialize the variables
            cls._instance.current_models = []  # A list of dictionaries
            cls._instance.error_types = []    # A list of strings
            cls._instance.tags = []          # A list of strings
        return cls._instance

    # Getters
    def get_current_models(self):
        return self.current_models

    def get_error_types(self):
        return self.error_types

    def get_tags(self):
        return self.tags

    # Setters
    def set_current_models(self, models):
        if isinstance(models, list) and all(isinstance(model, dict) for model in models):
            self.current_models = models
        else:
            raise ValueError("current_models must be a list of dictionaries")

    def set_error_types(self, errors):
        if isinstance(errors, list) and all(isinstance(error, str) for error in errors):
            self.error_types = errors
        else:
            raise ValueError("error_types must be a list of strings")

    def set_tags(self, tags):
        if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
            self.tags = tags
        else:
            raise ValueError("tags must be a list of strings")

    # Append functionality
    def append_to_current_models(self, model):
        if isinstance(model, dict):
            self.current_models.append(model)
        else:
            raise ValueError("Appended item to current_models must be a dictionary")

    def append_to_error_types(self, error):
        if isinstance(error, str):
            self.error_types.append(error)
        else:
            raise ValueError("Appended item to error_types must be a string")

    def append_to_tags(self, tag):
        if isinstance(tag, str):
            self.tags.append(tag)
        else:
            raise ValueError("Appended item to tags must be a string")

    def _parse_dart_code(self, dart_code_str: str) -> list[dict]:
       """
       Parses a string containing Dart code with @freezed classes and documentation
       that includes a Schema:<Name>. Returns a list of dictionaries where each
       dictionary has {schema_name: class_name}.
       """

       # Regex to extract the entire snippet between <something.dart> and </something.dart>
       snippet_pattern = re.compile(
           r"<(?P<filename>[\w\-_\.]+)>(?P<content>.*?)</(?P=filename)>",
           re.DOTALL
       )

       # Regex to find "Schema:SomeSchemaName"
       schema_pattern = re.compile(r"Schema\s*:\s*([A-Za-z0-9_]+)")

       # Regex to find the class name after `@freezed class XXX with`
       class_pattern = re.compile(r"@freezed\s*class\s+(\w+)\s+with")

       results = []

       # Find all snippets
       for match in snippet_pattern.finditer(dart_code_str):
           snippet_content = match.group("content")

           # Extract schema name (e.g. "UserCardListResourceSchema")
           schema_match = schema_pattern.search(snippet_content)
           if not schema_match:
               continue  # If there's no schema in the snippet, skip

           schema_name = schema_match.group(1)

           # Extract class name (e.g. "CardItem")
           class_match = class_pattern.search(snippet_content)
           if not class_match:
               continue  # If there's no @freezed class, skip

           class_name = class_match.group(1)

           # Append a dictionary like {"UserCardListResourceSchema": "CardItem"}
           results.append({schema_name: class_name})

       return results
    
    def update_current_models(self, generated_classes):
        new_scemas =  self._parse_dart_code(generated_classes)
        self.current_models.extend(new_scemas)


