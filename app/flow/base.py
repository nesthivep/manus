from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Union
from datetime import datetime

from pydantic import BaseModel, Field

from app.agent.base import BaseAgent
from app.logger import logger


class FlowType(str, Enum):
    PLANNING = "planning"
    CONVERSATION = "conversation"


class FlowState(str, Enum):
    """Flow execution states"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseFlow(BaseModel, ABC):
    """Base class for execution flows supporting multiple agents"""

    agents: Dict[str, BaseAgent]
    tools: Optional[List] = None
    primary_agent_key: Optional[str] = None
    
    # Flow lifecycle management
    state: FlowState = Field(default=FlowState.INITIALIZED)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_metrics: Dict = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self, agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]], **data
    ):
        # Handle different ways of providing agents
        if isinstance(agents, BaseAgent):
            agents_dict = {"default": agents}
        elif isinstance(agents, list):
            agents_dict = {f"agent_{i}": agent for i, agent in enumerate(agents)}
        else:
            agents_dict = agents

        # If primary agent not specified, use first agent
        primary_key = data.get("primary_agent_key")
        if not primary_key and agents_dict:
            primary_key = next(iter(agents_dict))
            data["primary_agent_key"] = primary_key

        # Set the agents dictionary
        data["agents"] = agents_dict

        # Initialize using BaseModel's init
        super().__init__(**data)

    @property
    def primary_agent(self) -> Optional[BaseAgent]:
        """Get the primary agent for the flow"""
        return self.agents.get(self.primary_agent_key)

    def get_agent(self, key: str) -> Optional[BaseAgent]:
        """Get a specific agent by key"""
        return self.agents.get(key)

    def add_agent(self, key: str, agent: BaseAgent) -> None:
        """Add a new agent to the flow"""
        self.agents[key] = agent

    def update_metrics(self, metric_name: str, value: Union[int, float, str]) -> None:
        """Update flow execution metrics"""
        self.execution_metrics[metric_name] = value
        logger.debug(f"Updated metric {metric_name}: {value}")

    def set_state(self, new_state: FlowState, error_msg: Optional[str] = None) -> None:
        """Update flow state with logging"""
        old_state = self.state
        self.state = new_state
        
        if new_state == FlowState.RUNNING and not self.start_time:
            self.start_time = datetime.now()
        elif new_state in [FlowState.COMPLETED, FlowState.FAILED]:
            self.end_time = datetime.now()
            
        if error_msg:
            self.error_message = error_msg
            
        logger.info(f"Flow state changed: {old_state} -> {new_state}")
        if error_msg:
            logger.error(f"Flow error: {error_msg}")

    @abstractmethod
    async def execute(self, input_text: str) -> str:
        """Execute the flow with given input"""

    def get_execution_summary(self) -> str:
        """Get a summary of the flow execution"""
        duration = None
        if self.start_time:
            end = self.end_time or datetime.now()
            duration = (end - self.start_time).total_seconds()

        summary = f"Flow Status:\n"
        summary += f"State: {self.state}\n"
        summary += f"Duration: {duration:.2f}s\n" if duration else "Not started\n"
        
        if self.error_message:
            summary += f"Error: {self.error_message}\n"
            
        if self.execution_metrics:
            summary += "\nMetrics:\n"
            for metric, value in self.execution_metrics.items():
                summary += f"{metric}: {value}\n"
                
        return summary
