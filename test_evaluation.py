#!/usr/bin/env python3
"""
Test script for the OpenManus evaluation system.
This script demonstrates how to use the various evaluation functions.
"""

import asyncio
import logging
import json
from pprint import pprint
import os

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try importing the evaluation modules
try:
    from app.evaluation import (
        evaluate_agent,
        run_individual_evaluations,
        run_honeyhive_evaluations
    )
    from app.honeyhive_tracer import init_honeyhive
    MODULES_AVAILABLE = True
except ImportError:
    logger.warning("Could not import all required modules. Some tests will be skipped.")
    MODULES_AVAILABLE = False

# Test queries
TEST_QUERIES = [
    "What is the capital of France?",
    "Write a Python function to calculate the Fibonacci sequence",
    "How do I set up a basic React application?",
    "Explain the difference between REST and GraphQL",
    "Find the largest file in the current directory"
]

async def test_individual_evaluation():
    """Test individual evaluation on a single query."""
    logger.info("Testing individual evaluation...")
    if not MODULES_AVAILABLE:
        logger.warning("Skipping test_individual_evaluation due to missing modules.")
        return

    try:
        # Initialize HoneyHive tracer
        init_honeyhive()
        
        # Evaluate a single query
        query = TEST_QUERIES[0]
        logger.info(f"Evaluating query: {query}")
        
        result = await evaluate_agent(query)
        
        # Print results
        logger.info(f"Evaluation results for: {query}")
        logger.info(f"Overall score: {result['overall_score']:.2f}")
        
        for metric, data in result.items():
            if metric != "overall_score":
                logger.info(f"{metric.replace('_', ' ').title()}: {data['score']:.2f}")
                
        logger.info("Individual evaluation test complete.")
        return result
    except Exception as e:
        logger.error(f"Error in test_individual_evaluation: {e}")
        logger.exception("Exception details:")
        return None

async def test_batch_evaluation():
    """Test batch evaluation on multiple queries."""
    logger.info("Testing batch evaluation...")
    if not MODULES_AVAILABLE:
        logger.warning("Skipping test_batch_evaluation due to missing modules.")
        return

    try:
        # Take a subset of test queries
        test_dataset = TEST_QUERIES[:2]
        
        # Run batch evaluation
        results = await run_individual_evaluations(test_dataset)
        
        # Print summary
        logger.info("Batch evaluation results summary:")
        for item in results:
            query = item["query"]
            score = item["result"]["overall_score"]
            logger.info(f"Query: {query[:30]}... - Score: {score:.2f}")
            
        logger.info("Batch evaluation test complete.")
        return results
    except Exception as e:
        logger.error(f"Error in test_batch_evaluation: {e}")
        logger.exception("Exception details:")
        return None

def test_honeyhive_evaluation():
    """Test HoneyHive evaluation."""
    logger.info("Testing HoneyHive evaluation...")
    if not MODULES_AVAILABLE:
        logger.warning("Skipping test_honeyhive_evaluation due to missing modules.")
        return

    try:
        # Take a subset of test queries
        test_dataset = TEST_QUERIES[:1]
        
        # Run HoneyHive evaluation
        run_honeyhive_evaluations(test_dataset)
        
        logger.info("HoneyHive evaluation test initiated successfully.")
        logger.info("Check the HoneyHive dashboard for results.")
        
        return True
    except Exception as e:
        logger.error(f"Error in test_honeyhive_evaluation: {e}")
        logger.exception("Exception details:")
        return False

async def run_all_tests():
    """Run all evaluation tests."""
    logger.info("Running all evaluation tests...")
    
    # Test 1: Individual Evaluation
    individual_result = await test_individual_evaluation()
    
    # Test 2: Batch Evaluation
    batch_results = await test_batch_evaluation()
    
    # Test 3: HoneyHive Evaluation
    honeyhive_result = test_honeyhive_evaluation()
    
    # Save results to file for inspection
    if individual_result or batch_results:
        results = {
            "individual_evaluation": individual_result,
            "batch_evaluation": batch_results,
            "honeyhive_evaluation": bool(honeyhive_result)
        }
        
        with open("evaluation_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("Test results saved to evaluation_test_results.json")
    
    logger.info("All evaluation tests completed.")

if __name__ == "__main__":
    logger.info("Starting evaluation tests...")
    asyncio.run(run_all_tests())
    logger.info("Evaluation tests completed.") 