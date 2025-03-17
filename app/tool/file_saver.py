import os
from typing import Any, Dict

import aiofiles  # type: ignore

from app.config import WORKSPACE_ROOT
from app.tool.base import BaseTool


class FileSaver(BaseTool):
    name: str = "file_saver"
    description: str = """Save content to a local file at a specified path.
Use this tool when you need to save text, code, or generated content to a file on the local filesystem.
The tool accepts content and a file path, and saves the content to that location.
"""
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "(required) The content to save to the file.",
            },
            "file_path": {
                "type": "string",
                "description": "(required) The path where the file should be saved, including filename and extension.",
            },
            "mode": {
                "type": "string",
                "description": "(optional) The file opening mode. Default is 'w' for write. Use 'a' for append.",
                "enum": ["w", "a"],
                "default": "w",
            },
        },
        "required": ["content", "file_path"],
    }

    async def execute(self, **kwargs: Any) -> str:
        """
        Save content to a file at the specified path.

        Args:
            **kwargs: The keyword arguments containing content, file_path, and mode.

        Returns:
            Coroutine[Any, Any, str]: A coroutine that returns a message indicating the result of the operation.
        """
        content: str = kwargs.get("content", "")
        file_path: str = kwargs.get("file_path", "")
        mode: str = kwargs.get("mode", "w")

        try:
            # Place the generated file in the workspace directory
            if os.path.isabs(file_path):
                file_name = os.path.basename(file_path)
                full_path = os.path.join(WORKSPACE_ROOT, file_name)
            else:
                full_path = os.path.join(WORKSPACE_ROOT, file_path)

            # Ensure the directory exists
            directory = os.path.dirname(full_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # Write directly to the file
            async with aiofiles.open(full_path, mode, encoding="utf-8") as file:
                await file.write(content)

            return f"Content successfully saved to {full_path}"
        except Exception as e:
            return f"Error saving file: {str(e)}"
