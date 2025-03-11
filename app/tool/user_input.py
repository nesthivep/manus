from typing import Optional, List
from app.tool.base import BaseTool, ToolResult
from app.logger import logger

class UserInput(BaseTool):
    name: str = "user_input"
    description: str = "Request input from the user during execution. Use this when you need additional information or clarification to proceed with a task."
    parameters: dict = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The question or prompt to show the user",
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of choices to present to the user",
            }
        },
        "required": ["prompt"]
    }

    async def execute(self, prompt: str, options: Optional[List[str]] = None) -> ToolResult:
        """Request input from the user during execution."""
        logger.info(f"\n[User Input Required] {prompt}")
        
        if options:
            for i, option in enumerate(options):
                logger.info(f"  {i+1}. {option}")
            logger.info("Enter the number of your choice or type a different response:")
        
        user_response = input("➤ ")
        
        # Handle numeric option selection
        if options and user_response.isdigit():
            idx = int(user_response) - 1
            if 0 <= idx < len(options):
                user_response = options[idx]
        
        return ToolResult(output=f"User responded: {user_response}") 