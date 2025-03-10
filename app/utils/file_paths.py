"""
Utility functions for handling file paths consistently across the application.
"""

import os
from pathlib import Path


def get_home_directory() -> str:
    """
    Get the user's home directory.
    
    Returns:
        str: The path to the user's home directory
    """
    return str(Path.home())


def get_workspace_directory() -> str:
    """
    Get the current workspace directory.
    
    Returns:
        str: The path to the current workspace directory
    """
    return os.getcwd()


def to_absolute_path(file_path: str) -> str:
    """
    Convert a relative path to an absolute path.
    
    Args:
        file_path (str): The relative or absolute path to convert
        
    Returns:
        str: The absolute path
    """
    if os.path.isabs(file_path):
        return file_path
    return os.path.abspath(os.path.join(get_workspace_directory(), file_path))


def to_file_url(file_path: str) -> str:
    """
    Convert a file path to a file:// URL.
    
    Args:
        file_path (str): The file path to convert
        
    Returns:
        str: The file:// URL
    """
    # Ensure it's an absolute path
    abs_path = to_absolute_path(file_path)
    # Convert to file URL format
    return f"file://{abs_path}"


def create_directory_if_not_exists(directory_path: str) -> None:
    """
    Create a directory if it doesn't exist.
    
    Args:
        directory_path (str): The path to the directory to create
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def is_valid_file_path(file_path: str) -> bool:
    """
    Check if a file path is valid.
    
    Args:
        file_path (str): The file path to check
        
    Returns:
        bool: True if the file path is valid, False otherwise
    """
    try:
        # This will raise an error if the path is invalid
        Path(file_path)
        return True
    except (TypeError, ValueError):
        return False 