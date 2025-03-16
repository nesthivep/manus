"""
Input handling utilities for OpenManus.

This module provides functions to intercept and process user input,
including special commands for breaking out of stuck states.
"""

from typing import Any, Callable, Optional, Tuple

from app.logger import logger


def is_break_command(input_text: str) -> bool:
    """Check if the input is a break command.

    Args:
        input_text: The user input to check

    Returns:
        True if the input is a break command
    """
    return bool(input_text) and input_text.strip().startswith("/break")


def process_break_command(
    input_text: str, agent: Any = None, update_memory_func: Optional[Callable] = None
) -> Tuple[bool, str]:
    """Process a break command and update agent state if provided.

    Args:
        input_text: The user input containing a break command
        agent: Optional agent instance to modify
        update_memory_func: Optional function to update agent memory

    Returns:
        Tuple of (success, message)
    """
    if not is_break_command(input_text):
        return False, "Not a break command"

    parts = input_text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return (
            False,
            "Please provide a command after /break. Examples: '/break continue', '/break param=value', '/break start_over'",
        )

    command = parts[1].lower()

    # Handle continue command - use reasonable defaults
    if command == "continue" or command == "proceed":
        message = "Proceeding with default values."
        if agent:
            if hasattr(agent, "state"):
                # Reset any stuck loop detection
                if hasattr(agent, "_reset_stuck_detection"):
                    agent._reset_stuck_detection()
                # Add a system message
                if update_memory_func:
                    update_memory_func(
                        "system", "User instructed to proceed with default values."
                    )

        return True, message

    # Handle start_over command - clear memory and start fresh
    if command == "start_over" or command == "reset":
        message = "Starting over with a fresh approach."
        if agent and hasattr(agent, "memory"):
            # Store initial request
            initial_request = ""
            for msg in agent.memory.messages:
                if msg.role == "user":
                    initial_request = msg.content or ""
                    break

            # Clear memory
            agent.memory.messages = []
            if hasattr(agent, "current_step"):
                agent.current_step = 0

            # Re-add initial request if available
            if initial_request and update_memory_func:
                update_memory_func("user", initial_request)

        return True, message

    # Handle parameter setting with param=value syntax
    if "=" in command:
        param, value = command.split("=", 1)
        param = param.strip()
        value = value.strip()

        message = f"Set {param} to {value}."

        # Add as system message if agent available
        if agent and update_memory_func:
            update_memory_func("system", f"User provided parameter: {param}={value}")
            if hasattr(agent, "_reset_stuck_detection"):
                agent._reset_stuck_detection()

        return True, message

    # Unknown command
    return (
        False,
        f"Unknown command: {command}. Available commands: continue, start_over, or param=value",
    )


def get_user_input(prompt: str = "", allow_intercept: bool = True) -> str:
    """Get user input with command interception.

    This is a replacement for the built-in input() function that adds
    special command processing capabilities.

    Args:
        prompt: Optional prompt to display
        allow_intercept: Whether to intercept special commands

    Returns:
        User input or processed command result
    """
    raw_input = input(prompt)

    if not allow_intercept or not is_break_command(raw_input):
        return raw_input

    # Process the break command (no agent context here)
    success, message = process_break_command(raw_input)
    if success:
        logger.info(f"Break command processed: {message}")
        # For global input, we still return the command for further processing

    return raw_input
