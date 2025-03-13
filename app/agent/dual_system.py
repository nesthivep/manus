"""
DualSystemAgent implements 'Thinking Fast and Slow' concepts for problem solving.
Based on Kahneman's dual-process theory with System 1 (fast) and System 2 (slow) thinking.
"""

from typing import Dict, List, Optional, Union
import re
from pydantic import Field, model_validator

from app.agent.manus import Manus
from app.llm import LLM
from app.logger import logger
from app.schema import Message, AgentState
from app.utils.cognitive_bias import CognitiveBiasMitigation


class DualSystemAgent(Manus):
    """
    Agent implementing the dual-system thinking principles from 'Thinking Fast and Slow'.
    Chooses between fast (intuitive) and slow (deliberate) thinking based on problem complexity.
    """
    
    name: str = "DualSystemAgent"
    description: str = "An agent that implements fast and slow thinking systems for optimal problem solving"
    
    # Configuration for the two thinking systems
    system1_llm: Optional[LLM] = Field(default=None)  # Fast thinking LLM (smaller, faster)
    system2_llm: Optional[LLM] = Field(default=None)  # Slow thinking LLM (larger, more capable)
    
    # Cognitive bias mitigation system
    bias_mitigation: CognitiveBiasMitigation = Field(default_factory=CognitiveBiasMitigation)
    
    # Threshold for determining which system to use (0-1 scale, higher means more likely to use System 2)
    complexity_threshold: float = 0.6
    
    # Override system prompts for fast and slow thinking
    system1_prompt: Optional[str] = Field(
        default="You are an efficient assistant that provides quick, intuitive responses based on pattern recognition. "
                "Focus on giving direct answers without extensive analysis when possible."
    )
    system2_prompt: Optional[str] = Field(
        default="You are a thorough, analytical assistant that carefully considers problems step-by-step. "
                "Break down complex issues methodically, consider multiple perspectives, "
                "and provide well-reasoned responses with appropriate caution about certainty."
    )
    
    @model_validator(mode="after")
    def initialize_llms(self) -> "DualSystemAgent":
        """Initialize the LLMs for both thinking systems if not provided."""
        # Fast thinking system (system1) uses a smaller, faster model
        if self.system1_llm is None:
            self.system1_llm = LLM(config_name="system1")  # Use the system1 configuration from config.toml
        
        # Slow thinking system (system2) uses a more comprehensive model
        if self.system2_llm is None:
            self.system2_llm = LLM(config_name="system2")  # Use the system2 configuration from config.toml
        
        return self
    
    async def analyze_problem_complexity(self, input_text: str) -> float:
        """
        Determine the complexity of a problem to decide which thinking system to use.
        Returns a score between 0 and 1, where higher values indicate more complex problems.
        """
        # Initialize complexity metrics
        complexity_score = 0.0
        
        # 1. Length-based complexity (longer queries tend to be more complex)
        word_count = len(input_text.split())
        if word_count > 100:
            complexity_score += 0.3
        elif word_count > 50:
            complexity_score += 0.2
        elif word_count > 20:
            complexity_score += 0.1
        
        # 2. Keyword-based complexity detection
        complexity_indicators = [
            "analyze", "compare", "evaluate", "synthesize", "design", 
            "create", "develop", "implement", "solve", "optimize",
            "why", "how", "implications", "consequences", "trade-offs"
        ]
        
        matched_indicators = sum(1 for indicator in complexity_indicators 
                               if indicator.lower() in input_text.lower())
        complexity_score += min(0.3, matched_indicators * 0.05)
        
        # 3. Question complexity (multiple questions indicate complexity)
        question_count = input_text.count('?')
        complexity_score += min(0.2, question_count * 0.1)
        
        # 4. Detect requests for step-by-step thinking
        if any(phrase in input_text.lower() for phrase in 
               ["step by step", "detailed analysis", "thorough explanation", 
                "systematic approach", "comprehensive review"]):
            complexity_score += 0.2
        
        logger.info(f"Problem complexity analysis: score={complexity_score:.2f}")
        return min(1.0, complexity_score)
    
    async def run(self, input_text: str) -> str:
        """Execute the appropriate thinking system based on problem complexity."""
        if not input_text.strip():
            return "I need some input to work with. Please provide a question or task."
        
        # Analyze problem complexity
        complexity = await self.analyze_problem_complexity(input_text)
        
        # Choose thinking system based on complexity
        if complexity < self.complexity_threshold:
            logger.info(f"Using System 1 (fast thinking) for problem with complexity {complexity:.2f}")
            response = await self.fast_thinking(input_text)
        else:
            logger.info(f"Using System 2 (slow thinking) for problem with complexity {complexity:.2f}")
            response = await self.slow_thinking(input_text)
        
        return response
    
    async def fast_thinking(self, input_text: str) -> str:
        """
        Fast, intuitive thinking approach (System 1).
        Uses pattern matching and heuristics for quicker responses.
        """
        # Set up the system message for fast thinking
        system_message = Message.system_message(self.system1_prompt)
        
        # Create user message with instruction to respond quickly and intuitively
        user_message = Message.user_message(
            f"Provide a quick, intuitive response to this question/task:\n\n{input_text}"
        )
        
        # Get response using the faster/smaller model
        response = await self.system1_llm.ask(
            messages=[user_message],
            system_msgs=[system_message]
        )
        
        # Add a note about the thinking system used
        response_with_note = (
            f"{response}\n\n"
            f"_Note: I used fast thinking (System 1) for this response since the query appeared "
            f"straightforward. If you need a more detailed analysis, please let me know._"
        )
        
        return response_with_note
    
    async def slow_thinking(self, input_text: str) -> str:
        """
        Slow, deliberate thinking approach (System 2).
        Uses step-by-step analysis for complex problems.
        """
        # First, create a structured approach to the problem
        structure_system_msg = Message.system_message(self.system2_prompt)
        
        structure_user_msg = Message.user_message(
            f"I need a well-structured approach to this problem. Please help me break it down:\n\n{input_text}\n\n"
            f"1. First, outline the key aspects of this problem that need to be addressed\n"
            f"2. Then, define a step-by-step approach to solve it"
        )
        
        # Get the structured approach using system2 LLM
        plan_response = await self.system2_llm.ask(
            messages=[structure_user_msg],
            system_msgs=[structure_system_msg]
        )
        
        # Check for cognitive biases in the planned approach
        detected_biases = self.bias_mitigation.check_for_biases(plan_response)
        
        # If biases detected, get mitigation prompts
        if detected_biases:
            mitigation_prompts = self.bias_mitigation.get_mitigation_prompts(detected_biases)
            
            # Construct a bias mitigation message
            mitigation_text = "Before proceeding, please consider these perspective shifts:\n" + \
                              "\n".join(f"- {prompt}" for prompt in mitigation_prompts)
            
            # Add the mitigation prompt to the conversation
            mitigation_msg = Message.user_message(mitigation_text)
            
            # Get a bias-mitigated plan
            plan_response = await self.system2_llm.ask(
                messages=[structure_user_msg, Message.assistant_message(plan_response), mitigation_msg],
                system_msgs=[structure_system_msg]
            )
        
        # Now execute the plan using system2 LLM
        execute_user_msg = Message.user_message(
            f"Based on this structured approach:\n\n{plan_response}\n\n"
            f"Please provide a comprehensive solution to the original problem:\n\n{input_text}"
        )
        
        final_response = await self.system2_llm.ask(
            messages=[execute_user_msg],
            system_msgs=[structure_system_msg]
        )
        
        # Add a note about the thinking system used
        response_with_note = (
            f"{final_response}\n\n"
            f"_Note: I used slow thinking (System 2) for this response since the query required "
            f"careful analysis. I broke down the problem methodically before providing my answer._"
        )
        
        return response_with_note 