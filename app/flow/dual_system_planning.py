"""
Implementation of a planning flow that incorporates dual-system thinking principles
from "Thinking Fast and Slow" by Daniel Kahneman.
"""

from typing import Dict, List, Optional, Union
from pydantic import Field

from app.agent.base import BaseAgent
from app.agent.dual_system import DualSystemAgent
from app.flow.planning import PlanningFlow
from app.logger import logger
from app.utils.cognitive_bias import CognitiveBiasMitigation


class DualSystemPlanningFlow(PlanningFlow):
    """
    Planning flow that implements dual-system thinking principles.
    Uses System 1 (fast) for simple steps and System 2 (slow) for complex steps.
    Includes cognitive bias detection and mitigation.
    """
    
    bias_mitigation: CognitiveBiasMitigation = Field(
        default_factory=CognitiveBiasMitigation
    )
    
    def _analyze_step_complexity(self, step_info: Dict) -> float:
        """
        Determine the complexity of a planning step to decide which thinking system to use.
        Returns a value between 0 and 1, where higher values indicate more complex steps.
        """
        if not step_info:
            return 0.0
            
        step_description = step_info.get("description", "")
        step_type = step_info.get("type", "").lower()
        
        # Initialize complexity score
        complexity_score = 0.0
        
        # 1. Type-based complexity
        if step_type in ["research", "analyze", "design", "implement", "code"]:
            complexity_score += 0.3
        elif step_type in ["verify", "test", "evaluate"]:
            complexity_score += 0.2
        
        # 2. Length-based complexity
        word_count = len(step_description.split())
        if word_count > 50:
            complexity_score += 0.2
        elif word_count > 20:
            complexity_score += 0.1
        
        # 3. Keyword-based complexity
        complexity_indicators = [
            "complex", "difficult", "challenging", "analyze", "design",
            "implement", "create", "optimize", "multiple", "consider"
        ]
        
        matched_indicators = sum(1 for indicator in complexity_indicators 
                               if indicator.lower() in step_description.lower())
        complexity_score += min(0.3, matched_indicators * 0.05)
        
        logger.info(f"Step complexity analysis: score={complexity_score:.2f}")
        return min(1.0, complexity_score)
    
    async def _execute_step(self, executor: BaseAgent, step_info: Dict) -> str:
        """
        Override to implement thinking system selection and cognitive bias mitigation.
        """
        step_description = step_info.get("description", "")
        step_type = step_info.get("type", "")
        step_id = step_info.get("id", "unknown")
        
        logger.info(f"Executing step {step_id} of type [{step_type}]")
        
        # If executor is a DualSystemAgent, handle system selection
        if isinstance(executor, DualSystemAgent):
            # Determine step complexity
            step_complexity = self._analyze_step_complexity(step_info)
            
            # Choose fast or slow thinking based on complexity
            if step_complexity < executor.complexity_threshold:
                logger.info(f"Using System 1 (fast thinking) for step {step_id} with complexity {step_complexity:.2f}")
                result = await executor.fast_thinking(step_description)
            else:
                logger.info(f"Using System 2 (slow thinking) for step {step_id} with complexity {step_complexity:.2f}")
                result = await executor.slow_thinking(step_description)
        else:
            # For non-dual-system agents, use the normal execution flow
            result = await super()._execute_step(executor, step_info)
        
        # Check for cognitive biases
        detected_biases = self.bias_mitigation.check_for_biases(result)
        
        # Apply mitigation if biases detected
        if detected_biases:
            logger.info(f"Detected potential biases in step {step_id}: {detected_biases}")
            
            # Get mitigation prompts
            mitigation_prompts = self.bias_mitigation.get_mitigation_prompts(detected_biases)
            
            if mitigation_prompts:
                # Construct a user prompt for bias mitigation
                mitigation_text = (
                    f"I need to revise my approach to this task: \"{step_description}\"\n\n"
                    f"My current solution is:\n{result}\n\n"
                    f"However, I should consider these perspective shifts:\n" + 
                    "\n".join(f"- {prompt}" for prompt in mitigation_prompts) +
                    "\n\nPlease provide an improved solution that addresses these concerns."
                )
                
                # Get improved result with bias mitigation
                if isinstance(executor, DualSystemAgent):
                    # For dual system agents, always use System 2 for bias mitigation
                    improved_result = await executor.slow_thinking(mitigation_text)
                else:
                    # For regular agents, use their standard run method
                    improved_result = await executor.run(mitigation_text)
                
                # Add a note about bias mitigation
                final_result = (
                    f"{improved_result}\n\n"
                    f"_Note: This response has been refined to address potential cognitive biases._"
                )
                
                return final_result
        
        return result 