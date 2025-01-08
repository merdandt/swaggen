import json
import os
import click
from openai import OpenAI
from swaggen.utils.swagger_config_singleton import ConfigSingleton
from swaggen.gen_ai.model_gen_prompts import MODEL_GEN_SYSTEM_PROMPT, MODEL_GEN_USER_PROMPT
from swaggen.gen_ai.dto_gen_prompts import DTO_SYSTEM_PROMPT, DTO_USER_PROMPT

class GenerativeAITaskHandler:
    _instance = None

    # Hardcoded base URL
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GenerativeAITaskHandler, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.api_key = os.getenv("GEMINI_API_KEY")  # Get API key from environment variable
            cls._instance._initialize_client()
        return cls._instance

    def _initialize_client(self):
        """
        Initializes the AI client if API key is provided.
        """
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.BASE_URL  # Use the hardcoded base URL
            )
        else:
            raise ValueError("API key must be set in the GEMINI_API_KEY environment variable.")

    def generate_models(self, paths, model_name="gemini-1.5-flash", temperature=0):
        """
        Generate models based on the provided paths and current_models using the AI client.

        Args:
            paths (list): A list of file paths to process.
            current_models (list): A list of current models in JSON format.
            model_name (str): The name of the model to use.
            temperature (float): The temperature to control randomness in the output.

        Returns:
            str: The generated classes or models.
        """
        swagger_config = ConfigSingleton()
        system_prompt = self._format_model_system_prompt(swagger_config.get_current_models())
        user_prompt = self._format_model_user_prompt(paths)
        
        click.echo(f'Generating Models classes for tag - {len(paths)} paths')
        try:
            completion = self.client.chat.completions.create(
                model=model_name,
                temperature=temperature,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            generated_classes = completion.choices[0].message.content
            swagger_config.update_current_models(generated_classes)

            return generated_classes
        except Exception as e:
            click.echo(f"Error generating models: {e}")
            raise RuntimeError(f"Error generating models: {e}")
        
    def generate_DTOs(self, paths, model_name="gemini-1.5-flash", temperature=0):
        """
        Generate DTOs based on the provided paths and current_models using the AI client.
        Args:
            paths (list): A list of file paths to process.
            current_models (list): A list of current models in JSON format.
            model_name (str): The name of the model to use.
            temperature (float): The temperature to control randomness in the output.
        Returns:
            str: The generated DTOs.
        """
        swagger_config = ConfigSingleton()
        system_prompt = self._format_dto_system_prompt(swagger_config.get_current_models())
        user_prompt = self._format_dto_user_prompt(paths)

        click.echo(f'Generating DTOs for tag - {len(paths)} paths')
        try:
            completion = self.client.chat.completions.create(
                model=model_name,
                temperature=temperature,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            generated_classes = completion.choices[0].message.content
            swagger_config.update_current_models(generated_classes)

            return generated_classes
        except Exception as e:
            click.echo(f"Error generating DTOs: {e}")
            raise RuntimeError(f"Error generating models: {e}")


    def _format_model_system_prompt(self, current_models):
        return MODEL_GEN_SYSTEM_PROMPT.format(current_models=json.dumps(current_models))

    def _format_model_user_prompt(self, paths):
        return MODEL_GEN_USER_PROMPT.format(paths=json.dumps(paths))
    
    def _format_dto_system_prompt(self, current_models):
        return DTO_SYSTEM_PROMPT.format(current_models=json.dumps(current_models))
    
    def _format_dto_user_prompt(self, paths):
        return DTO_USER_PROMPT.format(paths=json.dumps(paths))

    def _update_current_models(self, generated_classes, current_models):
        """
        Updates the current models with the generated classes.

        Args:
            generated_classes (str): The generated classes as a string.
            current_models (list): The current models list to be updated.

        Returns:
            None
        """
        try:
            new_models = json.loads(generated_classes)
            if isinstance(new_models, list):
                current_models.extend(new_models)
            else:
                raise ValueError("Generated classes must be a list of models.")
        except json.JSONDecodeError:
            raise ValueError("Failed to parse generated classes as JSON.")
