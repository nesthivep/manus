#!/usr/bin/env python3
"""
Example demonstrating how to use the evaluate_with_honeyhive decorator
for direct integration with HoneyHive evaluation.
"""

import asyncio
import sys
import os
import logging

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.evaluation import evaluate_with_honeyhive

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Example function that uses the decorator
@evaluate_with_honeyhive(experiment_name="example_function")
async def example_function(query):
    """
    Example function that simulates an agent's response.
    
    Parameters:
        query: The user query to process
        
    Returns:
        A dictionary containing the response and trace information
    """
    # Simulate some processing time
    await asyncio.sleep(1)
    
    # Simulate tool calls
    tool_calls = [
        {"name": "search", "arguments": {"query": query}},
        {"name": "calculator", "arguments": {"expression": "2+2"}}
    ]
    
    # Simulate tool results
    tool_results = [
        {"name": "search", "result": f"Search results for {query}"},
        {"name": "calculator", "result": "4"}
    ]
    
    # Simulate thinking steps
    thinking_steps = [
        f"I need to understand the query: {query}",
        "I should search for information",
        "I should perform a calculation"
    ]
    
    # Return a response with trace information
    return {
        "response": f"I processed your query: {query}",
        "execution_time": 1.0,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "thinking_steps": thinking_steps,
        "steps": [
            {"type": "thinking", "content": thinking_steps[0]},
            {"type": "tool_call", "content": tool_calls[0]},
            {"type": "tool_result", "content": tool_results[0]},
            {"type": "thinking", "content": thinking_steps[1]},
            {"type": "tool_call", "content": tool_calls[1]},
            {"type": "tool_result", "content": tool_results[1]},
            {"type": "thinking", "content": thinking_steps[2]}
        ]
    }

# Example function without trace information
@evaluate_with_honeyhive()
async def simple_function(query):
    """
    A simpler function that just returns a string response.
    The decorator will still work, but with less trace information.
    """
    await asyncio.sleep(0.5)
    return f"Simple response to: {query}"

async def main():
    """Run the example functions"""
    logger.info("Running example_function...")
    result1 = await example_function("How does photosynthesis work?")
    logger.info(f"Result from example_function: {result1['response']}")
    
    logger.info("\nRunning simple_function...")
    result2 = await simple_function("What is the capital of France?")
    logger.info(f"Result from simple_function: {result2}")
    
    logger.info("\nBoth functions have been evaluated with HoneyHive!")
    logger.info("Check your HoneyHive dashboard to see the results.")

if __name__ == "__main__":
    asyncio.run(main()) 