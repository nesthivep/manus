from typing import Dict, List, Optional, Union

from pydantic import Field

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Message


class ConversationFlow(BaseFlow):
    """A flow that manages multi-turn conversations between agents."""

    llm: LLM = Field(default_factory=lambda: LLM())
    conversation_history: List[Message] = Field(default_factory=list)
    max_turns: int = Field(default=10)
    current_turn: int = Field(default=0)
    active_agent_key: Optional[str] = None

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        super().__init__(agents, **data)
        self.active_agent_key = self.primary_agent_key

    def switch_active_agent(self, agent_key: str) -> None:
        """Switch the currently active agent."""
        if agent_key not in self.agents:
            raise ValueError(f"Agent with key {agent_key} not found")
        self.active_agent_key = agent_key

    def get_active_agent(self) -> Optional[BaseAgent]:
        """Get the currently active agent."""
        return self.agents.get(self.active_agent_key)

    def add_to_history(self, message: Message) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append(message)
        # Also update the active agent's memory
        active_agent = self.get_active_agent()
        if active_agent:
            active_agent.memory.add_message(message)

    async def execute(self, input_text: str) -> str:
        """Execute the conversation flow with the given input."""
        try:
            if not self.primary_agent:
                raise ValueError("No primary agent available")

            # Add initial user input to history
            self.add_to_history(Message.user_message(input_text))

            result = ""
            while self.current_turn < self.max_turns:
                self.current_turn += 1
                active_agent = self.get_active_agent()
                
                if not active_agent:
                    logger.error("No active agent available")
                    break

                # Prepare context for the agent
                context = self._prepare_context()
                
                # Execute turn with active agent
                try:
                    turn_result = await active_agent.run(context)
                    self.add_to_history(Message.assistant_message(turn_result))
                    result += f"Turn {self.current_turn}: {turn_result}\n"

                    # Check if conversation should end
                    if active_agent.state == AgentState.FINISHED:
                        break

                except Exception as e:
                    logger.error(f"Error in conversation turn: {str(e)}")
                    result += f"Error in turn {self.current_turn}: {str(e)}\n"
                    break

            return result.strip()

        except Exception as e:
            logger.error(f"Error in ConversationFlow: {str(e)}")
            return f"Execution failed: {str(e)}"

    def _prepare_context(self) -> str:
        """Prepare context for the active agent's next turn."""
        context = "Current conversation history:\n"
        for msg in self.conversation_history[-5:]:  # Show last 5 messages for context
            prefix = "User" if msg.role == "user" else "Assistant"
            context += f"{prefix}: {msg.content}\n"
        
        context += "\nPlease provide your response to continue the conversation."
        return context