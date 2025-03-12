#!/usr/bin/env python3

"""
Test script for HoneyHive experiments with OpenManus agent.

This script runs a simple query through the OpenManus agent and creates a HoneyHive experiment
to evaluate the agent's performance.
"""

import asyncio
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the evaluation module
try:
    from app.evaluation import run_agent_with_experiment, init_honeyhive
except ImportError:
    logger.error("Failed to import evaluation module. Make sure you're in the correct directory.")
    sys.exit(1)

async def test_honeyhive_experiment():
    """Run a test query and create a HoneyHive experiment."""
    # Initialize HoneyHive
    if not init_honeyhive():
        logger.error("Failed to initialize HoneyHive. Check your API key.")
        return False
    
    # Test query
    test_query = "What is the capital of France?"
    
    try:
        logger.info(f"Running test query: {test_query}")
        response = await run_agent_with_experiment(test_query)
        
        logger.info(f"Agent response: {response}")
        logger.info("HoneyHive experiment created successfully!")
        return True
    except Exception as e:
        logger.error(f"Error running HoneyHive experiment: {e}")
        return False

def main():
    """Main function to run the test."""
    logger.info("Testing HoneyHive experiment integration with OpenManus agent...")
    
    try:
        success = asyncio.run(test_honeyhive_experiment())
        
        if success:
            logger.info("Test completed successfully!")
            sys.exit(0)
        else:
            logger.error("Test failed.")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 