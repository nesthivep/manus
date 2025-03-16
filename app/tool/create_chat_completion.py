import re
from typing import Any, List, Optional, Type, Union, get_args, get_origin

from pydantic import BaseModel, Field

from app.input_handler import is_break_command, process_break_command
from app.logger import logger
from app.tool import BaseTool


class CreateChatCompletion(BaseTool):
    name: str = "create_chat_completion"
    description: str = (
        "Creates a structured completion with specified output formatting."
    )

    # Type mapping for JSON schema
    type_mapping: dict = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        dict: "object",
        list: "array",
    }
    response_type: Optional[Type] = None
    required: List[str] = Field(default_factory=lambda: ["response"])

    def __init__(self, response_type: Optional[Type] = str):
        """Initialize with a specific response type."""
        super().__init__()
        self.response_type = response_type
        self.parameters = self._build_parameters()

    def _build_parameters(self) -> dict:
        """Build parameters schema based on response type."""
        if self.response_type == str:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "The response text that should be delivered to the user.",
                    },
                },
                "required": self.required,
            }

        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            schema = self.response_type.model_json_schema()
            return {
                "type": "object",
                "properties": schema["properties"],
                "required": schema.get("required", self.required),
            }

        return self._create_type_schema(self.response_type)

    def _create_type_schema(self, type_hint: Type) -> dict:
        """Create a JSON schema for the given type."""
        origin = get_origin(type_hint)
        args = get_args(type_hint)

        # Handle primitive types
        if origin is None:
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": self.type_mapping.get(type_hint, "string"),
                        "description": f"Response of type {type_hint.__name__}",
                    }
                },
                "required": self.required,
            }

        # Handle List type
        if origin is list:
            item_type = args[0] if args else Any
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "array",
                        "items": self._get_type_info(item_type),
                    }
                },
                "required": self.required,
            }

        # Handle Dict type
        if origin is dict:
            value_type = args[1] if len(args) > 1 else Any
            return {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "object",
                        "additionalProperties": self._get_type_info(value_type),
                    }
                },
                "required": self.required,
            }

        # Handle Union type
        if origin is Union:
            return self._create_union_schema(args)

        return self._build_parameters()

    def _get_type_info(self, type_hint: Type) -> dict:
        """Get type information for a single type."""
        if isinstance(type_hint, type) and issubclass(type_hint, BaseModel):
            return type_hint.model_json_schema()

        return {
            "type": self.type_mapping.get(type_hint, "string"),
            "description": f"Value of type {getattr(type_hint, '__name__', 'any')}",
        }

    def _create_union_schema(self, types: tuple) -> dict:
        """Create schema for Union types."""
        return {
            "type": "object",
            "properties": {
                "response": {"anyOf": [self._get_type_info(t) for t in types]}
            },
            "required": self.required,
        }

    async def execute(self, required: list | None = None, **kwargs) -> Any:
        """Execute the chat completion with type conversion.

        Args:
            required: List of required field names or None
            **kwargs: Response data

        Returns:
            Converted response based on response_type
        """
        required = required or self.required

        # Check if this is a user-facing chat completion that needs input
        if self._is_user_prompt(**kwargs):
            # Process the input with special command handling
            return await self._handle_user_facing_completion(**kwargs)

        # Handle case when required is a list
        if isinstance(required, list) and len(required) > 0:
            if len(required) == 1:
                required_field = required[0]
                result = kwargs.get(required_field, "")
            else:
                # Return multiple fields as a dictionary
                return {field: kwargs.get(field, "") for field in required}
        else:
            required_field = "response"
            result = kwargs.get(required_field, "")

        # Type conversion logic
        if self.response_type == str:
            return result

        if isinstance(self.response_type, type) and issubclass(
            self.response_type, BaseModel
        ):
            return self.response_type(**kwargs)

        if get_origin(self.response_type) in (list, dict):
            return result  # Assuming result is already in correct format

        try:
            return self.response_type(result)
        except (ValueError, TypeError):
            return result

    def _is_user_prompt(self, **kwargs) -> bool:
        """Detect if this completion is asking the user for input.

        Args:
            **kwargs: The parameters of the chat completion

        Returns:
            bool: True if this is a user-facing prompt requiring input
        """
        response = kwargs.get("response", "")

        # Skip if not a string (shouldn't happen with normal usage)
        if not isinstance(response, str):
            return False

        # Check for common question patterns
        question_indicators = [
            r"\?$",  # Ends with question mark
            r"(?:please|kindly|can you|could you)\s+(?:provide|specify|tell|enter)",
            r"(?:what|how|which|when|where|who|why)\s+(?:would|do|is|are|should)",
            r"(?:enter|type|input|give( me)?)\s+(?:your|the|a|an)",
        ]

        for pattern in question_indicators:
            if re.search(pattern, response.lower()):
                return True

        return False

    async def _handle_user_facing_completion(self, **kwargs) -> str:
        """Handle a chat completion that is asking the user for input.

        Displays the agent's request to the user and handles any special commands.

        Args:
            **kwargs: The parameters passed to the execute method

        Returns:
            str: The user's response or the result of a command
        """
        response = kwargs.get("response", "")

        # Display the agent's question/request to the user
        print(response)

        # Get user input (allow empty input)
        user_input = input().strip()

        # If it's not a special command, return as is
        if not is_break_command(user_input):
            return user_input

        # Process break command
        success, message = process_break_command(user_input)

        # If command was successful, send back a special response
        # that the agent will recognize in its flow
        if success:
            logger.info(f"Break command processed: {message}")

            # Determine what value to return based on common patterns in the question
            if re.search(r"how many", response.lower()):
                return "10"  # Default number for quantity questions
            elif re.search(r"yes or no", response.lower()):
                return "yes"  # Default positive for confirmation
            elif re.search(r"select|choose|pick", response.lower()):
                return "1"  # Default first option for selection
            elif "continue" in user_input.lower():
                # Generic default value with explanation
                return "[DEFAULT VALUE - User selected to continue with defaults]"
            elif "=" in user_input:
                # Extract the value part from param=value format
                value = user_input.split("=", 1)[1].strip()
                return value
            else:
                # Just proceed with empty value
                return ""  # Agent will need to handle this

        # If command failed or wasn't recognized, return the error message
        print(message)  # Show error to user
        return user_input  # Return original input to let agent handle it
