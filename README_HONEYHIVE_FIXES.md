# HoneyHive Integration Fixes

This document explains the changes made to fix the asyncio-related issues in the OpenManus codebase when integrating with HoneyHive.

## Problems Fixed

1. **asyncio.run() in running event loop**:
   ```
   Error evaluating tool selection: asyncio.run() cannot be called from a running event loop
   ```

2. **Evaluator decorator for async functions**:
   ```
   Error during evaluation: please use @aevaluator instead of @evaluator for this function
   ```

3. **Browser cleanup in destructor**:
   ```
   RuntimeError: Cannot run the event loop while another loop is running
   ```

These errors occur when mixing synchronous and asynchronous code, especially when trying to run async operations from within an already running event loop.

## Changes Made

1. **Made evaluator functions async with proper decorator**:
   - Changed all evaluator functions to be async functions
   - Used `@aevaluator()` instead of `@evaluator()` for async evaluator functions
   - Replaced `asyncio.run(llm_evaluator.ask(...))` with `await llm_evaluator.ask(...)`

2. **Made agent function async**:
   - Changed `agent_function_to_evaluate` to be async
   - Replaced `asyncio.run(run_agent_with_tracing(query))` with `await run_agent_with_tracing(query)`

3. **Updated experiment runner**:
   - Modified the `run_experiment` function to create a new event loop in a separate thread
   - Used `honeyhive.async_api.evaluate` instead of the synchronous version

4. **Updated batch evaluation function**:
   - Made `run_honeyhive_evaluations` async
   - Used `honeyhive.async_api.evaluate` instead of the synchronous version

5. **Fixed BrowserUseTool cleanup**:
   - Removed `asyncio.run()` and `loop.run_until_complete()` from the `__del__` method
   - Added a warning log message to indicate that cleanup should be called explicitly

## Sample Usage

A sample experiment script (`sample_experiment.py`) has been created to demonstrate how to use the fixed code. This script follows the HoneyHive documentation and uses the async API properly.

Key points:
- Use `async def` for functions that need to be evaluated
- Use `@aevaluator()` for async evaluator functions
- Use `await async_evaluate()` instead of `evaluate()`
- Use `asyncio.run()` only at the top level (not inside an already running event loop)
- Explicitly call cleanup methods for resources like browser tools

## Environment Setup

Make sure to set the following environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `HONEYHIVE_API_KEY`: Your HoneyHive API key
- `HONEYHIVE_PROJECT`: Your HoneyHive project name
- `HONEYHIVE_SERVER_URL`: (Optional) Your HoneyHive server URL for self-hosted deployments

## Running the Sample

```bash
python sample_experiment.py
```

This will run a sample experiment with the provided dataset and evaluator. 