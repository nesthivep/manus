# OpenManus Agent Evaluation

This document explains how the OpenManus agent is evaluated using HoneyHive.

## Overview

The OpenManus agent includes an integrated evaluation system that automatically evaluates each user query. The evaluation framework:

- Evaluates the agent's tool selection
- Assesses tool execution effectiveness
- Analyzes the agent's reasoning process
- Measures task completion success
- Evaluates efficiency

Each query is also automatically tracked as a HoneyHive experiment, allowing for comprehensive analysis and comparison of agent performance over time.

## Setup

1. Make sure you have installed all the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure that the HoneyHive API key is configured in `app/honeyhive_tracer.py`

## How It Works

When you run the OpenManus agent and enter a query:

1. The agent processes your query and generates a response
2. The evaluation system automatically evaluates the agent's performance
3. Evaluation results are displayed in the console after each interaction
4. The query is tracked as a HoneyHive experiment for later analysis

This integrated approach provides immediate feedback on the agent's performance for each query, helping you understand its strengths and weaknesses.

## Running the Agent with Evaluation

Simply run the OpenManus agent as usual:

```bash
python main.py
```

Then enter your queries. After each query is processed, you'll see the evaluation results displayed in the console.

## Evaluation Metrics

The evaluation framework uses the following metrics:

1. **Tool Selection**: Evaluates if the agent selected the most appropriate tools for the task
2. **Tool Execution**: Assesses if the tools were executed correctly with proper parameters
3. **Reasoning Process**: Analyzes the agent's reasoning process and decision-making
4. **Task Completion**: Measures if the agent successfully completed the task
5. **Efficiency**: Evaluates if the agent used the minimum necessary steps

Each metric is scored on a scale from 0.0 to 1.0, where:
- 1.0: Perfect performance
- 0.7: Good performance with minor issues
- 0.4: Partial success with significant issues
- 0.0: Poor performance or failure

## Viewing Results

### Console Output

After each query, evaluation results are displayed in the console:

```
==================================================
EVALUATION RESULTS:
Overall Score: 0.86/1.00
--------------------------------------------------
Detailed Scores:
• Tool Selection: 0.90
• Tool Execution: 0.80
• Reasoning Process: 0.90
• Task Completion: 0.90
• Efficiency: 0.80
==================================================
This query has been tracked as a HoneyHive experiment.
```

### HoneyHive Dashboard

Evaluation results are also available in the HoneyHive dashboard:

1. Visit the [HoneyHive dashboard](https://app.honeyhive.ai/)
2. Navigate to the `openmanus-trace` project
3. View the traces, experiments, and evaluation results

## HoneyHive Experiments

Each query is automatically tracked as a HoneyHive experiment, which provides several benefits:

1. **Comprehensive Tracing**: Every step of the agent's execution is traced and recorded
2. **Detailed Evaluation**: Multiple evaluators assess different aspects of the agent's performance
3. **Historical Comparison**: Compare performance across different queries and over time
4. **Experiment Analysis**: Use HoneyHive's analysis tools to identify patterns and areas for improvement

### Viewing Experiments

To view experiments in the HoneyHive dashboard:

1. Visit the [HoneyHive dashboard](https://app.honeyhive.ai/)
2. Navigate to the `openmanus-trace` project
3. Click on "Experiments" in the sidebar
4. Browse and filter experiments by name, date, or performance metrics

### Running Batch Experiments

You can also run batch experiments to evaluate the agent on multiple queries at once:

```python
from app.evaluation import run_honeyhive_evaluations

# Define a list of queries to evaluate
queries = [
    "What is the capital of France?",
    "Write a Python function to calculate the Fibonacci sequence",
    "Explain the concept of quantum computing"
]

# Run batch evaluation
run_honeyhive_evaluations(queries)
```

## Customizing Evaluations

### Adding New Evaluators

You can add new evaluators by creating functions with the `@evaluator()` decorator in `app/evaluation.py`:

```python
from honeyhive import evaluator

@evaluator()
def my_custom_evaluator(outputs, inputs, ground_truths=None):
    # Your evaluation logic here
    return {
        "score": score,
        "explanation": explanation
    }
```

Then add your new evaluator to the `evaluate_agent` function and the experiment setup in `app/evaluation.py`.

## References

- [HoneyHive Documentation](https://docs.honeyhive.ai/)
- [OpenManus Documentation](https://github.com/mannaandpoem/OpenManus) 