from typing import Dict, List, Union

from app.agent.base import BaseAgent
from app.flow.base import BaseFlow, FlowType
from app.flow.planning import PlanningFlow
from app.flow.conversation import ConversationFlow
from app.exceptions import FlowError


class FlowFactory:
    """Factory for creating different types of flows with support for multiple agents"""

    @staticmethod
    def create_flow(
        flow_type: FlowType,
        agents: Union[BaseAgent, List[BaseAgent], Dict[str, BaseAgent]],
        **kwargs,
    ) -> BaseFlow:
        # 验证输入参数
        if not isinstance(flow_type, FlowType):
            raise FlowError(f"Invalid flow type: {flow_type}")
        
        if not agents:
            raise FlowError("No agents provided")

        # 支持的流程类型映射
        flows = {
            FlowType.PLANNING: PlanningFlow,
            FlowType.CONVERSATION: ConversationFlow,
        }

        flow_class = flows.get(flow_type)
        if not flow_class:
            raise FlowError(f"Unsupported flow type: {flow_type}")

        try:
            return flow_class(agents, **kwargs)
        except Exception as e:
            raise FlowError(f"Failed to create flow: {str(e)}", flow_type.value)
