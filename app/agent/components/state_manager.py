from enum import Enum
from contextlib import asynccontextmanager
from typing import Optional
from loguru import logger

class AgentState(Enum):
    """Enumeration of possible agent states."""
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"
    PAUSED = "paused"

class StateManager:
    """Manages agent state transitions and state-related operations.
    
    Provides a clean interface for state management with safety checks
    and logging of state transitions.
    """
    
    def __init__(self):
        self._state = AgentState.IDLE
        self._previous_state: Optional[AgentState] = None
    
    @property
    def state(self) -> AgentState:
        """Get the current agent state."""
        return self._state
    
    @state.setter
    def state(self, new_state: AgentState):
        """Set the agent state with validation and logging."""
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")
        
        if new_state != self._state:
            logger.debug(f"State transition: {self._state.value} -> {new_state.value}")
            self._previous_state = self._state
            self._state = new_state
    
    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for temporary state transitions.
        
        Args:
            new_state: The state to transition to during the context.
            
        Yields:
            None: Allows execution within the new state.
            
        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")
        
        previous_state = self._state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR
            raise e
        finally:
            self.state = previous_state
    
    def can_transition_to(self, target_state: AgentState) -> bool:
        """Check if transitioning to the target state is valid.
        
        Args:
            target_state: The state to check transition possibility.
            
        Returns:
            bool: True if the transition is valid, False otherwise.
        """
        # Define valid state transitions
        valid_transitions = {
            AgentState.IDLE: [AgentState.RUNNING],
            AgentState.RUNNING: [AgentState.FINISHED, AgentState.PAUSED, AgentState.ERROR],
            AgentState.PAUSED: [AgentState.RUNNING, AgentState.FINISHED],
            AgentState.ERROR: [AgentState.IDLE],
            AgentState.FINISHED: [AgentState.IDLE]
        }
        
        return target_state in valid_transitions.get(self._state, [])
    
    def reset(self):
        """Reset the state manager to initial state."""
        self._state = AgentState.IDLE
        self._previous_state = None