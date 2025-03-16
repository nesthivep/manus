class ToolError(Exception):
    """Raised when a tool encounters an error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message: str = message
