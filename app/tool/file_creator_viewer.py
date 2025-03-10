"""
Tool that combines file creation and browser viewing capabilities.
"""

from app.tool.base import BaseTool
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.utils.file_paths import to_file_url


class FileCreatorViewer(BaseTool):
    """Tool that combines file saving and browser viewing in one operation."""

    name: str = "file_creator_viewer"
    description: str = """
Create and view files in a single operation. This tool combines file saving and browser viewing
to streamline development and testing workflows.

Use this tool when you want to:
1. Create or update a file
2. Immediately view it in a browser (especially useful for HTML, CSS, JS, etc.)
3. Iterate quickly on a file and see the changes

The tool will first save the file to the specified location and then open it in a browser.
"""
    parameters: dict = {
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
            "auto_view": {
                "type": "boolean",
                "description": "Whether to automatically open the file in a browser. Default is True.",
                "default": True,
            },
        },
        "required": ["content", "file_path"],
    }

    async def execute(
        self, content: str, file_path: str, mode: str = "w", auto_view: bool = True
    ) -> str:
        """
        Create a file and optionally view it in a browser.

        Args:
            content (str): The content to save to the file.
            file_path (str): The path where the file should be saved.
            mode (str, optional): The file opening mode. Default is 'w' for write.
            auto_view (bool, optional): Whether to automatically open the file in a browser. Default is True.

        Returns:
            str: A message indicating the result of the operation.
        """
        # First, save the file
        file_saver = FileSaver()
        save_result = await file_saver.execute(content, file_path, mode)

        # If saving was successful and auto_view is enabled, open in browser
        if "successfully saved" in save_result and auto_view:
            browser_tool = BrowserUseTool()
            # Only certain file types should be viewed in a browser
            viewable_extensions = [
                ".html", ".htm", ".svg", ".xhtml", ".xml", ".pdf",
                ".md", ".txt", ".json", ".css", ".js"
            ]
            
            # Check if the file has a viewable extension
            file_extension = file_path.lower().split(".")[-1]
            if f".{file_extension}" in viewable_extensions:
                file_url = to_file_url(file_path)
                browser_result = await browser_tool.execute(action="navigate", url=file_url)
                return f"{save_result}. {browser_result}"
            else:
                return f"{save_result}. File type is not typically viewed in a browser, so skipping browser view."
        
        return save_result 