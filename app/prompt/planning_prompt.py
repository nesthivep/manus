from typing import Dict, Optional, Any
from app.prompt.base import BasePrompt, PromptVersion

class PlanningPrompt(BasePrompt):
    """Planning场景的提示词模板
    
    实现了Planning Agent的系统提示词和下一步提示词模板，
    支持计划创建、执行和跟踪等功能
    """
    
    def __init__(self, version: PromptVersion = PromptVersion.V1, language: str = "en", parameters: Optional[Dict[str, Any]] = None):
        super().__init__(version=version, language=language, parameters=parameters or {})
    
    def get_system_prompt(self) -> str:
        template = """
        You are an expert Planning Agent tasked with solving complex problems by creating and managing structured plans.
        Your job is:
        1. Analyze requests to understand the task scope
        2. Create clear, actionable plans with the `planning` tool
        3. Execute steps using available tools as needed
        4. Track progress and adapt plans dynamically
        5. Use `finish` to conclude when the task is complete

        Available tools will vary by task but may include:
        - `planning`: Create, update, and track plans (commands: create, update, mark_step, etc.)
        - `finish`: End the task when complete

        Break tasks into logical, sequential steps. Think about dependencies and verification methods.
        """
        return self.format_prompt(template)
    
    def get_next_step_prompt(self) -> str:
        template = """
        Based on the current state, what's your next step?
        Consider:
        1. Do you need to create or refine a plan?
        2. Are you ready to execute a specific step?
        3. Have you completed the task?

        Provide reasoning, then select the appropriate tool or action.
        """
        return self.format_prompt(template)