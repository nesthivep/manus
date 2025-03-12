import os
import json
import re
from typing import Dict, List, Any, Optional, Callable
import asyncio
import logging
import multiprocessing
from functools import wraps
from openai import OpenAI

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import HoneyHive
try:
    from honeyhive import evaluator, evaluate, trace, atrace, HoneyHiveTracer
    HoneyHive_AVAILABLE = True
    
    # Initialize the HoneyHive tracer directly in evaluation module
    def init_honeyhive():
        """Initialize the HoneyHive tracer for OpenManus."""
        try:
            # Try to get API key from environment variable
            api_key = os.environ.get("HH_API_KEY")
            
            if not api_key:
                logger.error("HH_API_KEY not found in environment variables. HoneyHive experiments will not work.")
                return False
            
            HoneyHiveTracer.init(
                api_key=api_key,
                project='openmanus-trace',
                source='development',
                session_name='OpenManus Session', 
                server_url = "https://api.staging.honeyhive.ai"
            )
            logger.info("HoneyHive tracer initialized successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize HoneyHive tracer: {e}")
            return False
    
    # Create pydantic-compatible trace decorators
    def pydantic_compatible_trace(func: Callable) -> Callable:
        """A trace decorator that's compatible with Pydantic models."""
        traced_func = trace(func)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return traced_func(*args, **kwargs)
        
        return wrapper
    
    def pydantic_compatible_atrace(func: Callable) -> Callable:
        """An async trace decorator that's compatible with Pydantic models."""
        traced_func = atrace(func)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await traced_func(*args, **kwargs)
        
        return wrapper
    
except ImportError:
    logger.warning("HoneyHive not available, using mock decorators")
    HoneyHive_AVAILABLE = False
    
    # Mock decorators
    def evaluator(func):
        return func
    
    def trace(func):
        return func
    
    def atrace(func):
        return func
    
    def pydantic_compatible_trace(func):
        return func
    
    def pydantic_compatible_atrace(func):
        return func
    
    class HoneyHiveTracer:
        @staticmethod
        def init(*args, **kwargs):
            pass
    
    def init_honeyhive():
        logger.warning("HoneyHive not available, init_honeyhive is a no-op")
        return False

try:
    from app.agent.manus import Manus
    from app.logger import logger
    from app.llm import LLM
    
    # Initialize LLM for evaluations
    llm_evaluator = LLM(config_name="default")
except ImportError:
    logger.warning("OpenManus modules not available, using mock implementations")
    # Mock implementations if modules are not available
    class Manus:
        def __init__(self):
            self.memory = type('obj', (object,), {'messages': []})
            self.current_step = 0
        
        async def run(self, query):
            return f"Mock response for: {query}"
    
    llm_evaluator = None

# Initialize OpenAI client for evaluations
try:
    openai_client = OpenAI(api_key="your openai api key")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    openai_client = None

# Define evaluators for HoneyHive
@evaluator
def tool_selection_evaluator(outputs, inputs, ground_truths=None):
    """
    Evaluates if the agent selected the most appropriate tools for the task.
    """
    # Extract tool calls from the trace
    tool_calls = outputs.get("tool_calls", [])
    user_query = inputs.get("query", "")
    steps = outputs.get("steps", [])
    
    if not tool_calls:
        return {
            "score": 0.0,
            "explanation": "The agent did not use any tools to solve the task."
        }
    
    # Prepare the prompt for evaluation
    prompt = f"""
You are evaluating an AI agent's tool selection for a given task.

User Query: {user_query}

Tools Selected by the Agent:
{json.dumps(tool_calls, indent=2)}

Step-by-Step Execution:
{json.dumps(steps, indent=2)}

Evaluate the agent's tool selection based on the following criteria:
1. Appropriateness: Did the agent select tools that are relevant to the task?
2. Completeness: Did the agent select all necessary tools to complete the task?
3. Efficiency: Did the agent avoid selecting unnecessary tools?

Score the agent's tool selection on a scale from 0.0 to 1.0, where:
- 1.0: Perfect tool selection (all appropriate tools, no unnecessary ones)
- 0.5-0.9: Good tool selection with minor issues
- 0.1-0.4: Partial success with significant issues
- 0.0: Poor tool selection (inappropriate or missing critical tools)

Provide your score and a detailed explanation.
"""
    
    # Get evaluation from LLM
    try:
        if openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            evaluation_text = response.choices[0].message.content
            
            # Extract score from the evaluation text
            score_match = re.search(r'(\d+\.\d+)', evaluation_text)
            score = float(score_match.group(1)) if score_match else 0.5
            
            return {
                "tool_selection_score": score,
                "explanation": evaluation_text
            }
        else:
            return {
                "score": 0.5,
                "explanation": "OpenAI client not available for evaluation."
            }
    except Exception as e:
        logger.error(f"Error evaluating tool selection: {e}")
        return {
            "score": 0.5,
            "explanation": f"Error during evaluation: {str(e)}"
        }

@evaluator
def tool_execution_evaluator(outputs, inputs, ground_truths=None):
    """
    Evaluates if the tools were executed correctly with proper parameters.
    """
    # Extract tool calls and results from the trace
    tool_calls = outputs.get("tool_calls", [])
    tool_results = outputs.get("tool_results", [])
    user_query = inputs.get("query", "")
    steps = outputs.get("steps", [])
    
    if not tool_calls:
        return {
            "score": 0.0,
            "explanation": "The agent did not use any tools to solve the task."
        }
    
    # Prepare the prompt for evaluation
    prompt = f"""
You are evaluating an AI agent's tool execution for a given task.

User Query: {user_query}

Tool Calls:
{json.dumps(tool_calls, indent=2)}

Tool Results:
{json.dumps(tool_results, indent=2)}

Step-by-Step Execution:
{json.dumps(steps, indent=2)}

Evaluate the agent's tool execution based on the following criteria:
1. Parameter Quality: Did the agent provide appropriate parameters to the tools?
2. Error Handling: Did the agent handle errors or unexpected results appropriately?
3. Sequential Logic: Did the agent execute tools in a logical sequence?

Score the agent's tool execution on a scale from 0.0 to 1.0, where:
- 1.0: Perfect tool execution (appropriate parameters, excellent error handling)
- 0.5-0.9: Good tool execution with minor issues
- 0.1-0.4: Partial success with significant issues
- 0.0: Poor tool execution (inappropriate parameters, failed to handle errors)

Provide your score and a detailed explanation.
"""
    
    # Get evaluation from LLM
    try:
        if openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            evaluation_text = response.choices[0].message.content
            
            # Extract score from the evaluation text
            score_match = re.search(r'(\d+\.\d+)', evaluation_text)
            score = float(score_match.group(1)) if score_match else 0.5
            
            return {
                "tool_execution_score": score,
                "explanation": evaluation_text
            }
        else:
            return {
                "score": 0.5,
                "explanation": "OpenAI client not available for evaluation."
            }
    except Exception as e:
        logger.error(f"Error evaluating tool execution: {e}")
        return {
            "score": 0.5,
            "explanation": f"Error during evaluation: {str(e)}"
        }

@evaluator
def reasoning_process_evaluator(outputs, inputs, ground_truths=None):
    """
    Evaluates the agent's reasoning process and decision-making.
    """
    # Extract reasoning steps from the trace
    steps = outputs.get("steps", [])
    user_query = inputs.get("query", "")
    final_response = outputs.get("response", "")
    
    if not steps:
        return {
            "score": 0.0,
            "explanation": "No reasoning steps were recorded for evaluation."
        }
    
    # Prepare the prompt for evaluation
    prompt = f"""
You are evaluating an AI agent's reasoning process for a given task.

User Query: {user_query}

Step-by-Step Reasoning:
{json.dumps(steps, indent=2)}

Final Response:
{final_response}

Evaluate the agent's reasoning process based on the following criteria:
1. Logical Flow: Did the agent's reasoning follow a logical progression?
2. Thoroughness: Did the agent consider relevant factors and alternatives?
3. Adaptability: Did the agent adapt its approach based on new information?
4. Clarity: Was the agent's reasoning clear and easy to follow?

Score the agent's reasoning process on a scale from 0.0 to 1.0, where:
- 1.0: Excellent reasoning (logical, thorough, adaptive, and clear)
- 0.5-0.9: Good reasoning with minor issues
- 0.1-0.4: Partial success with significant issues
- 0.0: Poor reasoning (illogical, incomplete, rigid, or unclear)

Provide your score and a detailed explanation.
"""
    
    # Get evaluation from LLM
    try:
        if openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            evaluation_text = response.choices[0].message.content
            
            # Extract score from the evaluation text
            score_match = re.search(r'(\d+\.\d+)', evaluation_text)
            score = float(score_match.group(1)) if score_match else 0.5
            
            return {
                "reasoning_score": score,
                "explanation": evaluation_text
            }
        else:
            return {
                "score": 0.5,
                "explanation": "OpenAI client not available for evaluation."
            }
    except Exception as e:
        logger.error(f"Error evaluating reasoning process: {e}")
        return {
            "score": 0.5,
            "explanation": f"Error during evaluation: {str(e)}"
        }

@evaluator
def task_completion_evaluator(outputs, inputs, ground_truths=None):
    """
    Evaluates if the agent successfully completed the user's task.
    """
    # Extract relevant information from the trace
    user_query = inputs.get("query", "")
    final_response = outputs.get("response", "")
    steps = outputs.get("steps", [])
    
    if not final_response:
        return {
            "score": 0.0,
            "explanation": "The agent did not provide a final response."
        }
    
    # Prepare the prompt for evaluation
    prompt = f"""
You are evaluating an AI agent's task completion for a given user query.

User Query: {user_query}

Agent's Final Response:
{final_response}

Step-by-Step Execution:
{json.dumps(steps, indent=2)}

Evaluate the agent's task completion based on the following criteria:
1. Completeness: Did the agent fully address all aspects of the user's query?
2. Correctness: Is the information provided accurate and reliable?
3. Relevance: Is the response directly relevant to what the user asked?
4. Helpfulness: Does the response provide practical value to the user?

Score the agent's task completion on a scale from 0.0 to 1.0, where:
- 1.0: Perfect task completion (complete, correct, relevant, and helpful)
- 0.5-0.9: Good task completion with minor issues
- 0.1-0.4: Partial success with significant issues
- 0.0: Failed to complete the task (incomplete, incorrect, irrelevant, or unhelpful)

Provide your score and a detailed explanation.
"""
    
    # Get evaluation from LLM
    try:
        if openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            evaluation_text = response.choices[0].message.content
            
            # Extract score from the evaluation text
            score_match = re.search(r'(\d+\.\d+)', evaluation_text)
            score = float(score_match.group(1)) if score_match else 0.5
            
            return {
                "task_completion_score": score,
                "explanation": evaluation_text
            }
        else:
            return {
                "score": 0.5,
                "explanation": "OpenAI client not available for evaluation."
            }
    except Exception as e:
        logger.error(f"Error evaluating task completion: {e}")
        return {
            "score": 0.5,
            "explanation": f"Error during evaluation: {str(e)}"
        }

@evaluator
def efficiency_evaluator(outputs, inputs, ground_truths=None):
    """
    Evaluates the efficiency of the agent's approach to solving the task.
    """
    # Extract relevant information from the trace
    user_query = inputs.get("query", "")
    steps = outputs.get("steps", [])
    tool_calls = outputs.get("tool_calls", [])
    execution_time = outputs.get("execution_time", 0)
    
    if not steps:
        return {
            "score": 0.0,
            "explanation": "No steps were recorded for evaluation."
        }
    
    # Prepare the prompt for evaluation
    prompt = f"""
You are evaluating an AI agent's efficiency in solving a task.

User Query: {user_query}

Step-by-Step Execution:
{json.dumps(steps, indent=2)}

Number of Tool Calls: {len(tool_calls)}
Execution Time: {execution_time:.2f} seconds

Evaluate the agent's efficiency based on the following criteria:
1. Directness: Did the agent take a direct path to the solution without unnecessary detours?
2. Tool Economy: Did the agent use tools efficiently without redundant calls?
3. Step Minimization: Did the agent solve the task in a reasonable number of steps?
4. Time Efficiency: Was the execution time reasonable for the complexity of the task?

Score the agent's efficiency on a scale from 0.0 to 1.0, where:
- 1.0: Highly efficient (direct, economical, minimal steps, fast)
- 0.5-0.9: Good efficiency with minor issues
- 0.1-0.4: Inefficient with significant issues
- 0.0: Extremely inefficient (indirect, wasteful, excessive steps, slow)

Provide your score and a detailed explanation.
"""
    
    # Get evaluation from LLM
    try:
        if openai_client:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            evaluation_text = response.choices[0].message.content
            
            # Extract score from the evaluation text
            score_match = re.search(r'(\d+\.\d+)', evaluation_text)
            score = float(score_match.group(1)) if score_match else 0.5
            
            return {
                "efficency_score": score,
                "explanation": evaluation_text
            }
        else:
            return {
                "score": 0.5,
                "explanation": "OpenAI client not available for evaluation."
            }
    except Exception as e:
        logger.error(f"Error evaluating efficiency: {e}")
        return {
            "score": 0.5,
            "explanation": f"Error during evaluation: {str(e)}"
        }

# Function to run the agent and collect trace information
async def run_agent_with_tracing(query: str) -> Dict[str, Any]:
    """
    Run the Manus agent with the given query and collect trace information.
    
    Parameters:
        query: The user query to process
        
    Returns:
        Dict containing the agent's response and trace information
    """
    logger.info(f"Collecting trace information for query: {query}")
    
    try:
        # Record start time
        start_time = asyncio.get_event_loop().time()
        
        # Create a traced version of the agent run
        agent = Manus()
        final_response = await agent.run(query)
        
        # Record end time and calculate execution time
        execution_time = asyncio.get_event_loop().time() - start_time
        
        # Extract trace information
        trace_info = {
            "response": final_response,
            "step_count": agent.current_step,
            "tool_calls": [],
            "tool_results": [],
            "thinking_steps": [],
            "steps": [],
            "execution_time": execution_time
        }
        
        # For each message in the agent's memory, extract relevant information
        for i, msg in enumerate(getattr(agent.memory, "messages", [])):
            # Track step information
            if i > 0 and hasattr(msg, "role") and msg.role == "assistant":
                step_info = {
                    "step_number": len(trace_info["steps"]) + 1,
                    "content": getattr(msg, "content", ""),
                    "tool_calls": []
                }
                
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        if hasattr(tool_call, "function"):
                            step_info["tool_calls"].append({
                                "name": getattr(tool_call.function, "name", "unknown"),
                                "parameters": json.loads(getattr(tool_call.function, "arguments", "{}") or "{}")
                            })
                
                trace_info["steps"].append(step_info)
            
            # Extract tool calls
            if hasattr(msg, "role") and msg.role == "assistant" and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if hasattr(tool_call, "function"):
                        trace_info["tool_calls"].append({
                            "name": getattr(tool_call.function, "name", "unknown"),
                            "parameters": json.loads(getattr(tool_call.function, "arguments", "{}") or "{}")
                        })
            
            # Extract tool results
            if hasattr(msg, "role") and msg.role == "tool":
                trace_info["tool_results"].append(getattr(msg, "content", ""))
            
            # Extract thinking steps
            if hasattr(msg, "role") and msg.role == "assistant" and hasattr(msg, "content") and msg.content:
                trace_info["thinking_steps"].append(msg.content)
        
        # Clean up any browser tools if they exist
        if hasattr(agent, "tools"):
            for tool in getattr(agent, "tools", []):
                if hasattr(tool, "cleanup") and callable(tool.cleanup):
                    try:
                        await tool.cleanup()
                    except Exception as e:
                        logger.warning(f"Error cleaning up tool: {e}")
        
        logger.info(f"Collected trace information: {len(trace_info['tool_calls'])} tool calls, {len(trace_info['thinking_steps'])} thinking steps, {len(trace_info['steps'])} detailed steps")
        return trace_info
    except Exception as e:
        logger.error(f"Error collecting trace information: {e}")
        return {
            "response": f"Error: {str(e)}",
            "step_count": 0,
            "tool_calls": [],
            "tool_results": [],
            "thinking_steps": [],
            "steps": [],
            "execution_time": 0
        }

# Function to be evaluated by HoneyHive
def agent_function_to_evaluate(inputs, ground_truths=None):
    """
    Function to be evaluated by HoneyHive.
    This is a wrapper around the async function.
    """
    query = inputs.get("query", "")
    
    # Create a new event loop for this function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the agent and collect trace information
        trace_info = loop.run_until_complete(run_agent_with_tracing(query))
        return trace_info
    finally:
        loop.close()

# Function to create and run a HoneyHive experiment
def create_honeyhive_experiment(query, trace_info=None):
    """
    Create and run a HoneyHive experiment for a single query.
    
    Parameters:
        query: The user query
        trace_info: Optional trace information from the agent run
    """
    if not HoneyHive_AVAILABLE:
        logger.warning("HoneyHive not available, cannot create experiment")
        return False
    
    # Initialize HoneyHive
    if not init_honeyhive():
        logger.error("Failed to initialize HoneyHive, cannot create experiment")
        return False
    
    logger.info(f"Creating HoneyHive experiment for query: {query}")
    
    try:
        # Create a dataset with this query
        dataset = [{
            "inputs": {"query": query},
            "ground_truths": {}
        }]
        
        # If trace_info is provided, use a simple function that returns it
        if trace_info:
            def simple_function_to_evaluate(inputs, ground_truths=None):
                return trace_info
            
            function_to_evaluate = simple_function_to_evaluate
        else:
            # Otherwise use the standard function that runs the agent
            function_to_evaluate = agent_function_to_evaluate
        
        # Run the experiment in a separate process to avoid event loop issues
        def run_experiment_process():
            try:
                # Re-initialize HoneyHive in the new process
                init_honeyhive()
                
                # Run the experiment
                evaluate(
                    function=function_to_evaluate,
                    dataset=dataset,
                    hh_api_key="your honeyhive api key", 
                    hh_project="openmanus-trace",
                    server_url = "https://api.staging.honeyhive.ai",
                    evaluators=[
                        tool_selection_evaluator,
                        tool_execution_evaluator,
                        reasoning_process_evaluator,
                        task_completion_evaluator,
                        efficiency_evaluator
                    ],
                    name=f"OpenManus Agent Run - {query[:30]}..."
                )
                
                logger.info(f"HoneyHive experiment completed for query: {query}")
            except Exception as e:
                logger.error(f"Error running HoneyHive experiment: {e}")
        
        # Start the experiment in a separate process
        process = multiprocessing.Process(target=run_experiment_process)
        process.daemon = True
        process.start()
        
        logger.info(f"Started HoneyHive experiment process for query: {query}")
        return True
    except Exception as e:
        logger.error(f"Error creating HoneyHive experiment: {e}")
        return False

# Function to run agent and create HoneyHive experiment
async def run_agent_with_experiment(query):
    """
    Run the agent and create a HoneyHive experiment for the query.
    
    Parameters:
        query: The user query
        
    Returns:
        The agent's response
    """
    logger.info(f"Running agent with experiment for query: {query}")
    
    try:
        # Run the agent and collect trace information
        trace_info = await run_agent_with_tracing(query)
        
        # Create a HoneyHive experiment
        create_honeyhive_experiment(query, trace_info)
        
        return trace_info["response"]
    except Exception as e:
        logger.error(f"Error running agent with experiment: {e}")
        return f"Error: {str(e)}"

# Export the functions for use in other modules
__all__ = [
    'init_honeyhive',
    'trace',
    'atrace',
    'pydantic_compatible_trace',
    'pydantic_compatible_atrace',
    'create_honeyhive_experiment',
    'run_agent_with_experiment',
    'run_agent_with_tracing'
] 