from abc import ABC, abstractmethod
import json
import re
from typing import Optional, Union, Dict, Any

from pydantic import Field

from app.agent.base import BaseAgent
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Memory, Message, ToolCall


class ReActAgent(BaseAgent, ABC):
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> Union[str, Dict[str, Any]]:
        """Execute decided actions"""

    async def step(self) -> Union[str, Dict[str, Any]]:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            # Check the last message to see if it's a question that needs user input
            if self.memory.messages and len(self.memory.messages) > 0:
                last_message = self.memory.messages[-1]
                if last_message.role == "assistant" and last_message.content:
                    if self._is_asking_question(last_message.content):
                        logger.info(f"🔄 Detected question in assistant response, converting to ask_user call: {last_message.content}")
                        # Create a user input request
                        return {
                            "observation": f"❓ FOLLOW-UP: {last_message.content}\n\nPlease reply directly to this message with your response:",
                            "success": True,
                            "requires_user_response": True
                        }
            
            return "Thinking complete - no action needed"
        
        return await self.act()
        
    def _is_asking_question(self, text: str) -> bool:
        """
        Detects if the given text is asking a question or requesting input from the user.
        
        Args:
            text: The text to analyze
            
        Returns:
            bool: True if the text appears to be asking for user input
        """
        # Check for question marks
        if "?" in text:
            return True
            
        # Common question patterns
        question_patterns = [
            r"(?i)would you like",
            r"(?i)do you want",
            r"(?i)can you",
            r"(?i)could you",
            r"(?i)please provide",
            r"(?i)please let me know",
            r"(?i)please specify",
            r"(?i)tell me",
            r"(?i)what.*(?:would|should|can|could)",
            r"(?i)how.*(?:would|should|can|could)",
            r"(?i)which.*(?:option|choice)",
            r"(?i)let me know",
            r"(?i)if you have",
            r"(?i)if you would like",
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, text):
                return True
                
        return False
