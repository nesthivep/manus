# HoneyHive Integration

This document explains the changes made to fix the HoneyHive experiment integration in the OpenManus codebase.

## Issues Fixed

1. **Stuck "Working on evals..." message**:
   - The experiment was getting stuck because of issues with the async/sync function handling
   - The evaluator functions were not properly defined for HoneyHive

2. **Asyncio-related issues**:
   - `asyncio.run()` was being called from within an already running event loop
   - Async evaluator functions were using the wrong decorator

## Changes Made

1. **Simplified the experiment structure**:
   - Created synchronous wrapper functions for async code
   - Used synchronous evaluator functions instead of async ones for HoneyHive
   - Properly handled event loops in separate threads

2. **Environment variable integration**:
   - Added support for getting API keys and project names from environment variables
   - Created a setup script to easily set these variables

3. **Improved error handling**:
   - Added more detailed error logging
   - Added fallbacks for missing environment variables

## How to Use

1. **Set up environment variables**:
   ```bash
   # Edit the API key in the script first
   source setup_honeyhive.sh
   ```

2. **Run a test experiment**:
   ```bash
   python test_honeyhive_experiment.py
   ```

3. **Use in your code**:
   ```python
   from app.evaluation import run_honeyhive_evaluations
   
   # Define your dataset
   dataset = [
       "What is the capital of France?",
       "Write a Python function to calculate the Fibonacci sequence",
       "Explain the concept of quantum computing"
   ]
   
   # Run the experiment
   run_honeyhive_evaluations(dataset)
   ```

## HoneyHive Experiment Structure

The HoneyHive experiment structure follows the official documentation:

1. **Function to evaluate**: A synchronous function that takes inputs and ground_truths parameters
2. **Dataset**: A list of dictionaries with inputs and ground_truths fields
3. **Evaluators**: Synchronous functions that compute metrics on the outputs

Example:

```python
def function_to_evaluate(inputs, ground_truths):
    # Process inputs
    return result

def sample_evaluator(outputs, inputs, ground_truths):
    # Evaluate outputs
    return score

evaluate(
    function=function_to_evaluate,
    dataset=dataset,
    evaluators=[sample_evaluator],
    name="My Experiment",
    hh_project="my-project",
    hh_api_key="my-api-key"
)
```

## Troubleshooting

If you encounter issues:

1. **Check environment variables**: Make sure HONEYHIVE_API_KEY and HONEYHIVE_PROJECT are set
2. **Check HoneyHive installation**: Run `pip install honeyhive` to ensure it's installed
3. **Check logs**: Look for detailed error messages in the logs

For more information, refer to the [HoneyHive documentation](https://docs.honeyhive.ai/). 