#!/usr/bin/env python3
"""
Simple test script to verify that the HoneyHive experiment functionality works correctly.
"""
import asyncio
import logging
from app.evaluation import run_honeyhive_evaluations

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Run a simple test of the HoneyHive experiment system."""
    print("Testing HoneyHive experiment system...")
    
    # Define a small test dataset
    test_queries = [
        "What is the capital of France?",
        "Write a Python function to calculate the Fibonacci sequence",
        "Explain the concept of quantum computing"
    ]
    
    try:
        # Run HoneyHive batch evaluation
        print(f"Running HoneyHive batch evaluation on {len(test_queries)} queries...")
        run_honeyhive_evaluations(test_queries)
        
        print("\nSuccess! The HoneyHive experiment system is working correctly.")
        print("Check the HoneyHive dashboard to view the experiment results.")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nThe HoneyHive experiment system encountered an error.")

if __name__ == "__main__":
    asyncio.run(main()) 