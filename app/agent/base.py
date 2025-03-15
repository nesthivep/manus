from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.schema import ROLE_TYPE, AgentState, Memory, Message


class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:
            self.state = previous_state  # Revert to previous state

    def update_memory(
        self,
        role: ROLE_TYPE,  # type: ignore
        content: str,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        msg_factory = message_map[role]
        msg = msg_factory(content, **kwargs) if role == "tool" else msg_factory(content)
        self.memory.add_message(msg)

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop asynchronously.

        Args:
            request: Optional initial user request to process.

        Returns:
            A string summarizing the execution results.

        Raises:
            RuntimeError: If the agent is not in IDLE state at start.
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            # Process special commands before adding to memory
            if self._is_special_command(request):
                return self._process_special_command(request)
                
            self.update_memory("user", request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")
                step_result = await self.step()

                # Check for stuck state
                if self.is_stuck():
                    await self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

            if self.current_step >= self.max_steps:
                self.current_step = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

        return "\n".join(results) if results else "No steps executed"

    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """

    async def handle_stuck_state(self):
        """Handle stuck state by first verifying with LLM if intervention is needed,
        then pausing execution and requesting user input if necessary"""
        # Check if we're already in a deeply stuck state (3+ repetitions)
        deeply_stuck = self._is_deeply_stuck()
        
        # Extract recent conversation and the last assistant message to analyze and show
        last_messages = []
        last_assistant_message = ""
        if self.memory and self.memory.messages:
            # Get last 4-6 messages for context
            last_messages = self.memory.messages[-6:]
            
            # Find the last assistant message
            for msg in reversed(self.memory.messages):
                if msg.role == "assistant" and msg.content:
                    last_assistant_message = msg.content
                    break
                    
        # Verify with LLM if intervention is truly needed
        intervention_needed = await self._verify_intervention_needed(last_messages, deeply_stuck)
        
        # If not stuck according to LLM verification, add a subtle prompt and continue
        if not intervention_needed:
            logger.info("LLM determined user intervention is not needed despite repetition detected.")
            if deeply_stuck:
                self.next_step_prompt = "Consider a different approach to solve this problem. Be direct and don't repeat questions."
            else:
                self.next_step_prompt = "Try to be more direct and specific in your responses."
            return
        
        # If we reach here, intervention is needed
        
        # Print the stuck state notification
        if deeply_stuck:
            logger.warning("Agent is deeply stuck in a loop and cannot proceed. Pausing for user intervention.")
        else:
            logger.warning("Agent is stuck and requires guidance to proceed. Pausing for input.")
        
        # Show the last message from the agent
        if last_assistant_message:
            print("\nLast message from agent:\n")
            print(last_assistant_message)
            # Simple prompt for freeform response
            print("\nThe agent is waiting for your response.")
        
        # Get user input
        user_input = input("\nYour response: ").strip()
        
        # Process the user's input
        if user_input.startswith('/'):
            # Handle special commands
            if user_input == '/continue':
                self.update_memory("system", "User instructed to proceed with default values.")
                self.next_step_prompt = "Proceed with reasonable default values without asking for further clarification."
                logger.info("User selected to continue with default values")
            elif user_input == '/reset':
                # Clear the memory except for the initial request
                initial_request = ""
                for msg in self.memory.messages:
                    if msg.role == "user":
                        initial_request = msg.content
                        break
                        
                # Reset the agent state
                self.memory.messages = []
                self.current_step = 0
                
                # Re-add the initial request if found
                if initial_request:
                    self.update_memory("user", initial_request)
                    
                logger.info("User selected to reset the conversation")
                self.next_step_prompt = "Starting with a fresh approach based on the initial request."
            elif '=' in user_input[1:]:
                # Handle parameter setting
                param, value = user_input[1:].split('=', 1)
                param = param.strip()
                value = value.strip()
                
                # Add as both system message (to guide agent) and user message (to make it clear this is user input)
                self.update_memory("system", f"User provided parameter: {param}={value}")
                self.update_memory("user", f"I'm interested in {param}: {value}")
                
                # More explicit next_step_prompt that ensures agent uses the parameter
                self.next_step_prompt = f"The user has specified {param}='{value}'. Use this information directly without asking about it again. Proceed with providing relevant content about {value}."
                logger.info(f"User provided parameter: {param}={value}")
            else:
                # Unknown command
                print(f"Unknown command: {user_input}")
                # Use as normal input
                self.update_memory("user", user_input)
                self.next_step_prompt = f"Respond to the user's message: {user_input}"
        else:
            # Regular user input
            self.update_memory("user", user_input)
            self.next_step_prompt = f"Respond to the user's message: {user_input}"
            logger.info("User provided direct input")
            
        # Mark that we've broken out of the loop
        self._reset_stuck_detection()
        
    async def _verify_intervention_needed(self, recent_messages, deeply_stuck):
        """Verify with LLM if user intervention is truly needed.
        
        Args:
            recent_messages: List of recent messages for context
            deeply_stuck: Whether agent is in a deeply stuck state
            
        Returns:
            bool: True if intervention is needed, False if agent can proceed
        """
        try:
            # If deeply stuck (3+ repetitions), we're more likely to need intervention
            if deeply_stuck:
                intervention_threshold = 0.6  # Lower threshold when deeply stuck
            else:
                intervention_threshold = 0.8  # Higher threshold for mild repetition
            
            # Format messages for LLM context
            messages_text = ""
            for i, msg in enumerate(recent_messages):
                role = msg.role.upper()
                content = msg.content if msg.content else "[No content]"
                messages_text += f"{role}: {content}\n\n"
                
            # Create a system message for LLM to analyze the conversation
            system_message = Message.system_message(
                "You are an expert conversation analyzer that can detect when an AI agent is truly stuck " +
                "and cannot proceed without user intervention. Analyze the following conversation and " +
                "determine if user intervention is necessary. Only answer YES if the agent is clearly " +
                "asking the same questions repeatedly, is in a logical loop, or cannot proceed without " +
                "specific information that it has already requested multiple times. Answer NO if the agent " +
                "can reasonably continue on its own by making an assumption or taking a different approach."
            )
            
            # Create a user message with the conversation to analyze
            prompt_text = (
                f"Analyze this conversation and determine if user intervention is necessary to proceed:\n\n"
                f"{messages_text}\n\n"
                f"The system has detected {'a deep ' if deeply_stuck else 'a possible'} repetition pattern. "
                f"Is user intervention truly necessary? Answer only YES or NO."
            )
            user_message = Message.user_message(prompt_text)
            
            # Call LLM for analysis
            response = await self.llm.ask(
                messages=[user_message],
                system_msgs=[system_message],
            )
            
            # Handle both object responses with content attribute and direct string responses
            response_text = response.content.strip().lower() if hasattr(response, 'content') else str(response).strip().lower()
            logger.info(f"LLM intervention analysis: {response_text}")
            
            # Check if LLM thinks intervention is needed
            if "yes" in response_text[:10]:
                return True
            elif "no" in response_text[:10]:
                return False
            else:
                # If unclear, use the deeply_stuck status as fallback
                return deeply_stuck
            
        except Exception as e:
            logger.warning(f"Failed to verify intervention need: {e}")
            # Default to cautious approach - if exception, use deeply_stuck status
            return deeply_stuck

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )
        
        # Enhanced detection: Check for repetitive questions
        question_pattern = self._get_question_pattern(last_message.content)
        if question_pattern:
            question_count = sum(
                1
                for msg in reversed(self.memory.messages[:-1])
                if msg.role == "assistant" and self._get_question_pattern(msg.content) == question_pattern
            )
            # If asking the same type of question repeatedly
            if question_count >= self.duplicate_threshold:
                return True

        return duplicate_count >= self.duplicate_threshold

    def _is_special_command(self, request: str) -> bool:
        """Check if user input contains a special command to handle loop breaking
        
        Args:
            request: The user input to check
            
        Returns:
            bool: True if it's a special command
        """
        return request.strip().startswith('/break')
    
    def _process_special_command(self, request: str) -> str:
        """Process a special command from the user to break out of loops
        
        Args:
            request: The user input containing a special command
            
        Returns:
            str: Result message after processing the command
        """
        parts = request.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "Please provide a command after /break. Examples: '/break continue', '/break num_results=5', '/break start_over'"
        
        command = parts[1].lower()
        
        # Handle continue command - use reasonable defaults
        if command == 'continue' or command == 'proceed':
            self.update_memory("system", "User instructed to proceed with default values.")
            result = "Proceeding with default values. Agent has been instructed to continue."
            self._reset_stuck_detection()
            return result
            
        # Handle start_over command - clear memory and start fresh
        if command == 'start_over' or command == 'reset':
            # Get the initial user request if possible
            initial_request = ""
            for msg in self.memory.messages:
                if msg.role == "user":
                    initial_request = msg.content or ""
                    break
                    
            # Clear memory and reset
            self.memory.messages = []
            self.current_step = 0
            
            if initial_request:
                self.update_memory("user", initial_request)
                
            return "Agent memory has been reset. Starting over with a fresh approach."
            
        # Handle parameter setting with param=value syntax
        if '=' in command:
            param, value = command.split('=', 1)
            param = param.strip()
            value = value.strip()
            
            # Add this as a system message to guide the agent
            self.update_memory("system", f"User provided parameter: {param}={value}")
            self._reset_stuck_detection()
            return f"Set {param} to {value}. Agent has been instructed to continue with this parameter."
            
        # Unknown command
        return f"Unknown command: {command}. Available commands: continue, start_over, or param=value"
    
    def _get_question_pattern(self, content: str) -> str:
        """Extract a question pattern to identify repetitive questions
        
        Args:
            content: The message content to analyze
            
        Returns:
            str: A simplified pattern of the question, or empty string if no question found
        """
        import re
        
        if not content:
            return ""
            
        # Find question sentences (ending with ? or asking for input)
        questions = re.findall(r'[^.!?]*\?', content)
        
        # Also look for implicit questions/requests like "Please specify" or "Could you tell me"
        implicit_patterns = [
            r'(?:please|kindly|can you|could you)\s+(?:provide|specify|tell|let me know|indicate|select)',
            r'(?:what|how|which|when|where|who|why)\s+(?:would|do|is|are|should)',
            r'(?:need|require|waiting for)\s+(?:your|more|additional)\s+(?:input|response|choice|selection)',
        ]
        
        for pattern in implicit_patterns:
            implicit_q = re.findall(pattern, content.lower())
            if implicit_q:
                questions.extend(implicit_q)
                
        if not questions:
            return ""
            
        # Take the first/primary question and create a simplified pattern
        # Remove specific values, keep structure
        question = questions[0]
        # Replace numbers with NUM
        pattern = re.sub(r'\d+', 'NUM', question)
        # Replace specific terms with generic placeholders
        pattern = re.sub(r'"[^"]+"', 'VALUE', pattern)
        
        return pattern.strip()
    
    def _is_deeply_stuck(self) -> bool:
        """Check if the agent is in a deeply stuck state (multiple loops detected)
        
        Returns:
            bool: True if deeply stuck
        """
        if len(self.memory.messages) < 4:
            return False
            
        # Get recent assistant messages
        assistant_msgs = [msg for msg in self.memory.messages if msg.role == "assistant"][-5:]
        
        if len(assistant_msgs) < 3:
            return False
            
        # Check for highly similar content or question patterns
        questions = [self._get_question_pattern(msg.content) for msg in assistant_msgs]
        questions = [q for q in questions if q]  # Filter out empty patterns
        
        if not questions or len(questions) < 3:
            return False
            
        # If we have 3+ repeated question patterns, we're deeply stuck
        unique_patterns = len(set(questions))
        return unique_patterns <= 2 and len(questions) >= 3
    
    def _reset_stuck_detection(self):
        """Reset the stuck detection mechanism after receiving user intervention"""
        # Add a system message to break repetition pattern
        self.update_memory("system", "Loop broken by user command.")
        
        # Modify next_step_prompt to discourage loops
        self.next_step_prompt = "Process user command and proceed without asking the same questions again." 
    
    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value
