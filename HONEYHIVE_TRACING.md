# HoneyHive Tracing Integration

This document explains how the HoneyHive tracing is integrated into the OpenManus codebase.

## Overview

HoneyHive is used for tracing and evaluation in OpenManus to:

1. Track agent executions and their performance
2. Evaluate tool selection and execution
3. Compare different agent strategies
4. Monitor agent behavior over time

## Initialization

HoneyHive tracing is initialized using the `init_honeyhive()` function from `app/honeyhive_tracer.py`:

```python
from app.honeyhive_tracer import init_honeyhive

# Initialize HoneyHive tracer
init_honeyhive()
```

This function sets up the HoneyHive tracer with the correct project and API key. The initialization happens in `main.py` when the application starts.

## Tracing Functions

The OpenManus codebase uses several decorators for tracing:

1. `@trace` - For synchronous functions
2. `@atrace` - For async functions
3. `@pydantic_compatible_trace` - For synchronous functions that return Pydantic models
4. `@pydantic_compatible_atrace` - For async functions that return Pydantic models

Example:

```python
from app.honeyhive_tracer import pydantic_compatible_atrace

@pydantic_compatible_atrace
async def my_function(arg1, arg2):
    # Function implementation
    return result
```

## Evaluation

For evaluation, we use:

1. Synchronous evaluator functions for HoneyHive experiments
2. Async evaluator functions for internal evaluations

The synchronous evaluator functions are designed to work with HoneyHive's `evaluate` function, while the async evaluator functions are used for internal evaluations.

Example:

```python
from honeyhive import evaluate

# Run an experiment
evaluate(
    function=my_function_to_evaluate,
    dataset=my_dataset,
    evaluators=[my_evaluator1, my_evaluator2],
    name="My Experiment"
)
```

## Best Practices

1. **Always initialize before use**: Call `init_honeyhive()` before using any HoneyHive features
2. **Use proper decorators**: Use `@trace` for sync functions and `@atrace` for async functions
3. **Be consistent**: Use the same decorators throughout your codebase
4. **Don't hardcode values**: Use the tracer initialization function instead of hardcoding project IDs and API keys

## Troubleshooting

If you encounter issues with HoneyHive tracing:

1. Check that `init_honeyhive()` is called before using any HoneyHive features
2. Verify that the decorators are applied correctly
3. Check the logs for any error messages
4. Ensure that the HoneyHive package is installed

For more information, refer to the [HoneyHive documentation](https://docs.honeyhive.ai/). 