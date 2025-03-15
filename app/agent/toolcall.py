import json
from typing import Any, List, Optional, Union

from pydantic import Field

from app.agent.react import ReActAgent
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.tool import CreateChatCompletion, Terminate, ToolCollection


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
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        try:
            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=[Message.system_message(self.system_prompt)]
                if self.system_prompt
                else None,
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        self.tool_calls = response.tool_calls

        # Log response info
        logger.info(f"✨ {self.name}'s thoughts: {response.content}")
        logger.info(
            f"🛠️ {self.name} selected {len(response.tool_calls) if response.tool_calls else 0} tools to use"
        )
        
        # Handle empty content responses
        if not response.content and len(self.messages) > 1:
            # Check if we just executed any tools
            for i in range(min(5, len(self.messages))):
                if i < len(self.messages) and self.messages[-(i+1)].role == "tool":
                    # Found a recent tool message, we should synthesize a response
                    try:
                        # Identify which tools were used
                        recent_tools = []
                        for j in range(min(5, len(self.messages))):
                            if j < len(self.messages) and self.messages[-(j+1)].role == "tool":
                                if hasattr(self.messages[-(j+1)], 'name') and self.messages[-(j+1)].name:
                                    recent_tools.append(self.messages[-(j+1)].name)
                        
                        # Create a generic synthesis prompt based on tool types
                        synthesis_prompt = "Based on the information provided by the tools"
                        if recent_tools:
                            synthesis_prompt += f" ({', '.join(recent_tools)})"
                        synthesis_prompt += ", please synthesize a comprehensive response to address the user's request. Be specific and detailed."
                        
                        synthesis_msg = Message.user_message(synthesis_prompt)
                        
                        # Add the synthesis request and get a new response
                        synthesis_response = await self.llm.ask(
                            messages=self.messages + [synthesis_msg],
                            system_msgs=[Message.system_message(self.system_prompt)] if self.system_prompt else None,
                        )
                        
                        # Update with the synthesis response
                        if synthesis_response and hasattr(synthesis_response, 'content') and synthesis_response.content:
                            logger.info(f"🔄 Synthesizing tool results: {synthesis_response.content[:100]}...")
                            # Update the original response with synthesized content
                            response.content = synthesis_response.content
                            # Create a proper assistant message with the synthesized content
                            assistant_msg = Message.assistant_message(content=synthesis_response.content)
                            self.memory.add_message(assistant_msg)
                    except Exception as e:
                        logger.error(f"🚨 Error synthesizing tool results: {e}")
                        # Provide a fallback response if synthesis fails
                        tool_names = "results" if not recent_tools else f"{', '.join(recent_tools)} results"
                        fallback_msg = f"I've gathered {tool_names}, but I'm having trouble synthesizing a complete response. Please let me know if you'd like specific details from what I found."
                        response.content = fallback_msg
                        self.memory.add_message(Message.assistant_message(content=fallback_msg))
                    
                    # We've handled the synthesis, so break out of the loop
                    break
        if response.tool_calls:
            logger.info(
                f"🧰 Tools being prepared: {[call.function.name for call in response.tool_calls]}"
            )

        try:
            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if response.tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if response.content:
                    self.memory.add_message(Message.assistant_message(response.content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(
                    content=response.content, tool_calls=self.tool_calls
                )
                if self.tool_calls
                else Message.assistant_message(response.content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, try to identify and use appropriate tools if none selected
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                if self._should_auto_use_web_search(response.content):
                    logger.info("🔍 No tools selected but request seems like a web search. Auto-selecting web_search tool.")
                    # Auto-create a web search tool call
                    search_query = self._extract_search_query(response.content)
                    self.tool_calls = [self._create_web_search_tool_call(search_query)]
                    # Update the assistant message with our synthetic tool call
                    assistant_msg = Message.from_tool_calls(content=response.content, tool_calls=self.tool_calls)
                    self.memory.messages[-1] = assistant_msg
                    return True
                    
                # Otherwise continue with just content if it exists
                # If response content is empty but we've been using tools, this should still count as a valid step
                if not response.content and len(self.messages) > 1:
                    # Check for any recent tool messages (up to 5 messages back)
                    has_recent_tool = False
                    for i in range(min(5, len(self.messages))):
                        if i < len(self.messages) and self.messages[-(i+1)].role == "tool":
                            has_recent_tool = True
                            break
                    
                    if has_recent_tool:
                        # We've used tools but got empty response, still count as valid step
                        return True
                return bool(response.content)

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
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        results = []
        for command in self.tool_calls:
            result = await self.execute_tool(command)

            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result, tool_call_id=command.id, name=command.function.name
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
            args = json.loads(command.function.arguments or "{}")

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
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
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
        
    def _should_auto_use_web_search(self, content: str) -> bool:
        """Check if content indicates a web search request
        
        Args:
            content: The assistant's response content
            
        Returns:
            bool: True if the content suggests a web search should be performed
        """
        if not content:
            return False
            
        # Normalize content for easier pattern matching
        normalized = content.lower()
        
        # Common patterns suggesting web search
        web_search_patterns = [
            "search", "find", "look up", "browse", "internet", "web", 
            "get information", "research", "discover", "google", 
            "latest", "news", "current", "information about"
        ]
        
        # Check for question prompts that often need search
        question_indicators = [
            "what is", "how to", "where can", "who is", "when did", 
            "why does", "which", "tell me about", "i need information", 
            "can you find", "help me learn", "i'd like to know"
        ]
        
        # Count matches in content
        web_matches = sum(1 for pattern in web_search_patterns if pattern in normalized)
        question_matches = sum(1 for pattern in question_indicators if pattern in normalized)
        
        # If content has multiple indicators of needing web search
        return web_matches >= 1 or question_matches >= 1
    
    def _extract_search_query(self, content: str) -> str:
        """Extract or formulate a search query from the assistant's response
        
        Args:
            content: The assistant's response content
            
        Returns:
            str: Extracted or formulated search query
        """
        # Get the original user message for context
        user_message = ""
        for msg in reversed(self.memory.messages):
            if msg.role == "user":
                user_message = msg.content or ""
                break
        
        if not user_message:
            # If we somehow don't have user message, use assistant content
            return content.strip()
            
        # Clean up the query
        query = user_message.strip()
        
        # Remove common prefixes that confuse search engines
        prefixes = [
            "please ", "can you ", "i need ", "i want ", "help me ", 
            "find ", "search for ", "look up ", "tell me about ", 
            "what is ", "how to ", "where can i find "
        ]
        
        for prefix in prefixes:
            if query.lower().startswith(prefix):
                query = query[len(prefix):]
                break
                
        # Limit query length
        if len(query) > 200:
            query = query[:200]
            
        return query.strip()
        
    def _create_web_search_tool_call(self, query: str) -> ToolCall:
        """Create a web search tool call
        
        Args:
            query: The search query to use
            
        Returns:
            ToolCall: A properly formatted web search tool call
        """
        from app.schema import Function, ToolCall
        import uuid
        import json
        
        # Default to 10 results if not specified
        num_results = 10
        
        # Extract number from query if specified
        num_indicator_phrases = ["top ", "first ", " results", " links"]
        for phrase in num_indicator_phrases:
            if phrase in query.lower():
                # Try to extract a number
                try:
                    import re
                    numbers = re.findall(r'\d+', query)
                    if numbers:
                        potential_num = int(numbers[0])
                        if 1 <= potential_num <= 50:  # Reasonable range
                            num_results = potential_num
                except:
                    pass  # Keep default if extraction fails
        
        # Create function arguments
        args = {"query": query, "num_results": num_results}
        
        # Create the tool call
        return ToolCall(
            id=str(uuid.uuid4()),
            type="function",
            function=Function(
                name="web_search",
                arguments=json.dumps(args)
            )
        )

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]
