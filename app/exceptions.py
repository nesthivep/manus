class OpenManusError(Exception):
    """Base exception class for OpenManus."""
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class ToolError(OpenManusError):
    """Raised when a tool encounters an error."""
    def __init__(self, message, tool_name=None):
        self.tool_name = tool_name
        super().__init__(f"Tool error{f' in {tool_name}' if tool_name else ''}: {message}")

class ConfigError(OpenManusError):
    """Raised when there is a configuration error."""
    def __init__(self, message):
        super().__init__(f"Configuration error: {message}")

class LLMError(OpenManusError):
    """Raised when there is an error with the LLM service."""
    def __init__(self, message, model=None):
        self.model = model
        super().__init__(f"LLM error{f' with model {model}' if model else ''}: {message}")

class FlowError(OpenManusError):
    """Raised when there is an error in the flow execution."""
    def __init__(self, message, flow_name=None):
        self.flow_name = flow_name
        super().__init__(f"Flow error{f' in {flow_name}' if flow_name else ''}: {message}")

class ValidationError(OpenManusError):
    """Raised when there is a validation error."""
    def __init__(self, message):
        super().__init__(f"Validation error: {message}")

class ResourceError(OpenManusError):
    """Raised when there is a resource access or availability error."""
    def __init__(self, message, resource=None):
        self.resource = resource
        super().__init__(f"Resource error{f' for {resource}' if resource else ''}: {message}")
