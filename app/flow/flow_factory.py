from typing import Dict, List, Union
from enum import Enum

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow, FlowType
from app.flow.planning import PlanningFlow
from app.flow.dual_system_planning import DualSystemPlanningFlow


class FlowFactory:
    """Factory for creating different types of flows with support for multiple agents"""

    PLANNING = "planning"
    CONVERSATION = "conversation"
    DUAL_SYSTEM = "dual_system" 

    @classmethod
    def create_flow(
        cls,
        flow_type: FlowType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **kwargs,
    ) -> BaseFlow:
        """Create a new flow of specified type with given agents."""
        
        if flow_type == FlowType.PLANNING:
            return PlanningFlow(agents=agents, **kwargs)
        elif flow_type == FlowType.CONVERSATION:
            return ConversationFlow(agents=agents, **kwargs)
        elif flow_type == FlowType.DUAL_SYSTEM:  # Handle the new flow type
            return DualSystemPlanningFlow(agents=agents, **kwargs)
        else:
            raise ValueError(f"Unknown flow type: {flow_type}")
