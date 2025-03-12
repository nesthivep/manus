# HoneyHive Experiments with OpenManus

This document explains how to use HoneyHive experiments to evaluate the OpenManus agent's performance.

## Overview

HoneyHive is an AI Observability and Evaluation Platform that helps you trace, evaluate, and monitor your AI applications. OpenManus integrates with HoneyHive to automatically evaluate each agent run and track performance metrics.

The evaluation framework assesses the agent's performance across five key dimensions:

1. **Tool Selection**: How well the agent selects appropriate tools for the task
2. **Tool Execution**: How effectively the agent uses the selected tools
3. **Reasoning Process**: The quality of the agent's reasoning and decision-making
4. **Task Completion**: Whether the agent successfully completes the user's task
5. **Efficiency**: How efficiently the agent solves the problem

## Setup

### 1. Install HoneyHive

First, ensure you have the HoneyHive SDK installed:

```bash
pip install honeyhive
```

### 2. Set up your HoneyHive API Key

You need to set your HoneyHive API key as an environment variable:

```bash
export HH_API_KEY=your_honeyhive_api_key
```

You can get your API key from the HoneyHive dashboard after creating an account at [honeyhive.ai](https://honeyhive.ai).

## Running Experiments

### Automatic Experiments

With the integration in place, HoneyHive experiments run automatically whenever you use the OpenManus agent. Simply run the main script:

```bash
python main.py
```

Each query you enter will:
1. Run the agent to process your query
2. Collect trace information about the agent's execution
3. Create a HoneyHive experiment to evaluate the agent's performance
4. Log the evaluation results

### Manual Testing

You can also run a test experiment to verify that HoneyHive integration is working correctly:

```bash
./test_honeyhive_experiment.py
```

This script runs a simple query through the agent and creates a HoneyHive experiment.

## Viewing Results

You can view the results of your experiments in the HoneyHive dashboard:

1. Log in to your HoneyHive account
2. Navigate to the "Experiments" section
3. Find your experiment (named "OpenManus Agent Run - [query]...")
4. Click on the experiment to view detailed evaluation results

The dashboard provides insights into:
- Overall performance scores
- Detailed evaluations for each dimension
- Trace information for each agent run
- Comparisons between different runs

## How It Works

### Evaluation Process

1. **Agent Execution**: The agent processes the user query and generates a response
2. **Trace Collection**: The system collects detailed information about the agent's execution, including:
   - Tool calls and parameters
   - Tool results
   - Reasoning steps
   - Execution time
3. **Evaluation**: Five evaluators assess different aspects of the agent's performance
4. **Experiment Creation**: A HoneyHive experiment is created with the trace information and evaluation results
5. **Result Logging**: The evaluation results are logged and available in the HoneyHive dashboard

### Evaluators

The evaluation framework uses five evaluators:

1. **Tool Selection Evaluator**: Assesses if the agent selected the most appropriate tools for the task
2. **Tool Execution Evaluator**: Evaluates if the tools were executed correctly with proper parameters
3. **Reasoning Process Evaluator**: Analyzes the agent's reasoning process and decision-making
4. **Task Completion Evaluator**: Determines if the agent successfully completed the user's task
5. **Efficiency Evaluator**: Measures the efficiency of the agent's approach to solving the task

Each evaluator uses an LLM (GPT-4o) to assess the agent's performance and provide a score between 0.0 and 1.0, along with a detailed explanation.

### Tracing Implementation

OpenManus uses HoneyHive's tracing capabilities to track the execution of various components:

1. **Agent Methods**: Key methods in the agent classes are traced using the `@pydantic_compatible_atrace` decorator:
   - `BaseAgent.run()`: Traces the main agent execution loop
   - `ReActAgent.step()`: Traces each step in the ReAct loop
   - `ToolCallAgent.think()`: Traces the thinking process
   - `ToolCallAgent.act()`: Traces the action execution
   - `ToolCallAgent.execute_tool()`: Traces individual tool executions

2. **Tool Execution**: Tool calls are traced using the `@pydantic_compatible_atrace` decorator:
   - `BaseTool.__call__()`: Traces each tool call

3. **LLM Interactions**: LLM calls are traced using the `@pydantic_compatible_atrace` decorator:
   - `LLM.ask()`: Traces regular LLM interactions
   - `LLM.ask_tool()`: Traces tool-based LLM interactions

This comprehensive tracing ensures that all aspects of the agent's execution are captured and available for evaluation.

## Troubleshooting

### Common Issues

1. **HoneyHive API Key Not Found**
   - Make sure you've set the `HH_API_KEY` environment variable
   - Check that the API key is valid and has the necessary permissions

2. **Experiment Creation Fails**
   - Check your internet connection
   - Verify that your HoneyHive account is active
   - Look for error messages in the logs

3. **Evaluations Not Showing in Dashboard**
   - Allow some time for the experiments to process
   - Check that the experiments were created successfully
   - Verify that you're looking at the correct project in the dashboard

### Logs

Check the logs for detailed information about experiment creation and evaluation:

```bash
tail -f honeyhive.log
```

## References

- [HoneyHive Documentation](https://docs.honeyhive.ai/)
- [HoneyHive Evaluation Quickstart](https://docs.honeyhive.ai/evaluation/quickstart)
- [OpenManus Documentation](https://github.com/yourusername/OpenManus) 