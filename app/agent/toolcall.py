import json
from typing import Any, List, Literal

from pydantic import Field

from app.agent.react import ReActAgent
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import AgentState, Message, ToolCall
from app.tool import CreateChatCompletion, Terminate, ToolCollection
from app.llm import get_tool_calls


TOOL_CALL_REQUIRED = "Tool calls required but none provided"


class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate()
    )
    tool_choices: Literal["none", "auto", "required"] = "auto"
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)

    max_steps: int = 30

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        # Get response with tool options
        response = await self.llm.ask_tool(
            messages=self.messages,
            system_msgs=[Message.system_message(self.system_prompt)]
            if self.system_prompt
            else None,
            tools=self.available_tools.to_params(),
            tool_choice=self.tool_choices,
        )
        
        # Use helper function to extract tool calls safely
        extracted_tool_calls = get_tool_calls(response)
        self.tool_calls = extracted_tool_calls

        # Log response info
        logger.info(f"✨ {self.name}'s thoughts: {response.content if hasattr(response, 'content') else ''}")
        logger.info(
            f"🛠️ {self.name} selected {len(extracted_tool_calls)} tools to use"
        )
        if extracted_tool_calls:
            logger.info(
                f"🧰 Tools being prepared: {[call.function.name for call in extracted_tool_calls]}"
            )

        try:
            # Handle different tool_choices modes
            if self.tool_choices == "none":
                if extracted_tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                response_content = response.content if hasattr(response, 'content') else ''
                if response_content:
                    self.memory.add_message(Message.assistant_message(response_content))
                    return True
                return False

            # Create and add assistant message
            response_content = response.content if hasattr(response, 'content') else ''
            assistant_msg = (
                Message.from_tool_calls(
                    content=response_content, tool_calls=self.tool_calls
                )
                if self.tool_calls
                else Message.assistant_message(response_content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == "required" and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == "auto" and not self.tool_calls:
                response_content = response.content if hasattr(response, 'content') else ''
                return bool(response_content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results"""
        if not self.tool_calls:
            if self.tool_choices == "required":
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            result = await self.execute_tool(command)
            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            try:
                # Try to convert the result to a proper JSON structure if it's not already
                if isinstance(result, str):
                    # Check if it's already JSON
                    try:
                        # Just test if it's valid JSON, but don't modify the string
                        json.loads(result)
                        json_result = result  # It's already valid JSON
                    except json.JSONDecodeError:
                        # Not JSON, convert to a JSON-compatible format
                        # Remove any special characters that might interfere with JSON
                        result_cleaned = result.replace('\\', '\\\\').replace('"', '\\"')
                        json_result = json.dumps({"result": result_cleaned})
                        logger.info(f"🧩 Converted string result to JSON for tool response")
                else:
                    # If it's a dict or list, convert to JSON string
                    json_result = json.dumps(result)
                    logger.info(f"🧩 Converted non-string result to JSON string for tool response")
                
                tool_msg = Message.tool_message(
                    content=json_result, 
                    tool_call_id=command.id, 
                    name=command.function.name
                )
            except Exception as e:
                # In case of any error in JSON conversion, use the original result as a string
                logger.warning(f"⚠️ Error converting tool result to JSON: {e}")
                tool_msg = Message.tool_message(
                    content=str(result),
                    tool_call_id=command.id,
                    name=command.function.name
                )
            
            self.memory.add_message(tool_msg)
            results.append(result)

        return "\n\n".join(results)

    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments
            try:
                # First try to parse as JSON
                if command.function.arguments and command.function.arguments.strip():
                    args = json.loads(command.function.arguments)
                else:
                    args = {}
            except json.JSONDecodeError:
                # If not valid JSON, use as string
                logger.warning(f"🚨 Tool '{name}' received non-JSON arguments: {command.function.arguments[:50]}...")
                # Try to convert to a dict if possible
                if isinstance(command.function.arguments, str):
                    args = {"raw_input": command.function.arguments}
                else:
                    args = {"raw_input": str(command.function.arguments)}

            # Execute the tool
            logger.info(f"🔧 Activating tool: '{name}'...")
            result = await self.available_tools.execute(name=name, tool_input=args)

            # Format result for display
            observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )

            # Handle special tools like `finish`
            await self._handle_special_tool(name=name, result=result)

            return observation
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]
