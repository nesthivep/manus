from typing import Dict, List, Literal, Optional, Union
import os
import json
import boto3

from openai import (
    APIError,
    AsyncAzureOpenAI,
    AsyncOpenAI,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.config import LLMSettings, config
from app.logger import logger  # Assuming a logger is set up in your app
from app.schema import Message


class LLM:
    _instances: Dict[str, "LLM"] = {}

    def __new__(
        cls, config_name: str = "default", llm_config: Optional[LLMSettings] = None
    ):
        if config_name not in cls._instances:
            instance = super().__new__(cls)
            instance.__init__(config_name, llm_config)
            cls._instances[config_name] = instance
        return cls._instances[config_name]

    def __init__(
        self, config_name: str = "default", llm_config: Optional[LLMSettings] = None
    ):
        if not hasattr(self, "client"):  # Only initialize if not already initialized
            llm_config = llm_config or config.llm
            llm_config = llm_config.get(config_name, llm_config["default"])
            self.model = llm_config.model
            self.max_tokens = llm_config.max_tokens
            self.temperature = llm_config.temperature
            self.api_type = llm_config.api_type
            self.api_key = llm_config.api_key
            self.api_version = llm_config.api_version
            self.base_url = llm_config.base_url
            
            # Initialize AWS Bedrock client if needed
            self.bedrock_client = None
            if self.api_type == "bedrock":
                try:
                    # Extract region from model ARN if present, or use aws_region_name from config
                    region = getattr(llm_config, "aws_region_name", "us-east-2")
                    if "arn:aws:bedrock:" in self.model:
                        region_match = self.model.split("arn:aws:bedrock:")[1].split(":")[0]
                        if region_match:
                            region = region_match
                    
                    # Create a boto3 client for Bedrock Runtime using default credential chain
                    self.bedrock_client = boto3.client(
                        service_name="bedrock-runtime",
                        region_name=region
                    )
                    logger.info(f"Initialized AWS Bedrock client for model: {self.model} in region: {region}")
                    
                    # Create a wrapper client that provides an OpenAI-compatible interface
                    class BedrockCompatClient:
                        def __init__(self, bedrock_client, llm_instance):
                            self.bedrock_client = bedrock_client
                            self.llm_instance = llm_instance
                            self.chat = type('ChatObject', (), {
                                'completions': self.ChatCompletions(bedrock_client, llm_instance)
                            })
                            
                        class ChatCompletions:
                            def __init__(self, bedrock_client, llm_instance):
                                self.bedrock_client = bedrock_client
                                self.llm_instance = llm_instance
                                
                            async def create(self, model, messages, temperature=None, max_tokens=None, 
                                           tools=None, tool_choice="auto", stream=False, timeout=60, **kwargs):
                                # For streaming, we don't support it with Bedrock directly
                                if stream:
                                    raise ValueError("Streaming is not supported with Bedrock client")
                                    
                                # For tool calling, use the converse method
                                if tools:
                                    logger.info(f"Using Bedrock client for tool calling with model: {model}")
                                    response_dict = self.llm_instance._direct_bedrock_converse(
                                        messages=messages,
                                        tools=tools,
                                        tool_choice=tool_choice,
                                        temperature=temperature,
                                        max_tokens=max_tokens,
                                        **kwargs
                                    )
                                    
                                    # For ask_tool method, we need to properly handle the message object
                                    message_dict = response_dict["choices"][0]["message"]
                                    
                                    # Log if tool_calls exist in the message
                                    
                                    message_obj = self.llm_instance._dict_to_message_obj(message_dict)
                                    
                                    # Ensure content is never None - empty string is better
                                    if message_obj.content is None:
                                        logger.info("BEDROCK - Content was None, setting to empty string")
                                        message_obj.content = ""
                                        
                                    # Ensure tool_calls is properly initialized if not present
                                    if not hasattr(message_obj, "tool_calls"):
                                        logger.info("BEDROCK - No tool_calls attribute, initializing empty list")
                                        message_obj.tool_calls = []
                                    
                                    return message_obj
                                # For regular completions, use the invoke method
                                else:
                                    logger.info(f"Using Bedrock client for completion with model: {model}")
                                    response_text = self.llm_instance._direct_bedrock_invoke(
                                        messages=messages,
                                        temperature=temperature,
                                        max_tokens=max_tokens,
                                        **kwargs
                                    )
                                    # Create an object with a compatible interface
                                    class SimpleResponse:
                                        def __init__(self, content):
                                            self.choices = [type('obj', (object,), {
                                                'message': type('obj', (object,), {'content': content})
                                            })]
                                            
                                    return SimpleResponse(response_text)
                    
                    # Use the compatibility wrapper instead of setting to None
                    self.client = BedrockCompatClient(self.bedrock_client, self)
                except Exception as e:
                    logger.error(f"Failed to initialize AWS Bedrock client: {str(e)}")
                    self.bedrock_client = None
                    self.client = None
            elif self.api_type == "azure":
                self.client = AsyncAzureOpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    api_version=self.api_version,
                )
            else:
                self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    @staticmethod
    def format_messages(messages: List[Union[dict, Message]]) -> List[dict]:
        """
        Format messages for LLM by converting them to OpenAI message format.

        Args:
            messages: List of messages that can be either dict or Message objects

        Returns:
            List[dict]: List of formatted messages in OpenAI format

        Raises:
            ValueError: If messages are invalid or missing required fields
            TypeError: If unsupported message types are provided

        Examples:
            >>> msgs = [
            ...     Message.system_message("You are a helpful assistant"),
            ...     {"role": "user", "content": "Hello"},
            ...     Message.user_message("How are you?")
            ... ]
            >>> formatted = LLM.format_messages(msgs)
        """
        formatted_messages = []

        for message in messages:
            if isinstance(message, dict):
                # If message is already a dict, ensure it has required fields
                if "role" not in message:
                    raise ValueError("Message dict must contain 'role' field")
                formatted_messages.append(message)
            elif isinstance(message, Message):
                # If message is a Message object, convert it to dict
                formatted_messages.append(message.to_dict())
            else:
                raise TypeError(f"Unsupported message type: {type(message)}")

        # Validate all messages have required fields
        for msg in formatted_messages:
            if msg["role"] not in ["system", "user", "assistant", "tool"]:
                raise ValueError(f"Invalid role: {msg['role']}")
            if "content" not in msg and "tool_calls" not in msg:
                raise ValueError(
                    "Message must contain either 'content' or 'tool_calls'"
                )

        return formatted_messages

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
    )
    async def ask(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        stream: bool = True,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Send a prompt to the LLM and get the response.

        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            stream (bool): Whether to stream the response
            temperature (float): Sampling temperature for the response

        Returns:
            str: The generated response

        Raises:
            ValueError: If messages are invalid or response is empty
            OpenAIError: If API call fails after retries
            Exception: For unexpected errors
        """
        try:
            # Format messages
            if system_msgs:
                system_msgs = self.format_messages(system_msgs)
                messages = system_msgs + self.format_messages(messages)
            else:
                messages = self.format_messages(messages)

            if not self.client:
                raise ValueError(f"No client available for API type: {self.api_type}")

            # For streaming requests
            if stream:
                # Bedrock doesn't support streaming through our compatibility layer
                if self.api_type == "bedrock":
                    logger.info(f"Streaming not supported for Bedrock models, using non-streaming request")
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=temperature or self.temperature,
                        stream=False,
                    )
                    if not response.choices or not response.choices[0].message.content:
                        raise ValueError("Empty or invalid response from LLM")
                    return response.choices[0].message.content
                else:
                    # Use streaming for OpenAI/Azure
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=temperature or self.temperature,
                        stream=True,
                    )

                    collected_messages = []
                    async for chunk in response:
                        chunk_message = chunk.choices[0].delta.content or ""
                        collected_messages.append(chunk_message)
                        print(chunk_message, end="", flush=True)

                    print()  # Newline after streaming
                    full_response = "".join(collected_messages).strip()
                    if not full_response:
                        raise ValueError("Empty response from streaming LLM")
                    return full_response
            else:
                # Non-streaming request - use the unified client interface
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=temperature or self.temperature,
                    stream=False,
                )
                if not response.choices or not response.choices[0].message.content:
                    raise ValueError("Empty or invalid response from LLM")
                return response.choices[0].message.content

        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise
        except OpenAIError as oe:
            logger.error(f"OpenAI API error: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ask: {e}")
            raise

    @retry(
        wait=wait_random_exponential(min=1, max=60),
        stop=stop_after_attempt(6),
    )
    async def ask_tool(
        self,
        messages: List[Union[dict, Message]],
        system_msgs: Optional[List[Union[dict, Message]]] = None,
        timeout: int = 60,
        tools: Optional[List[dict]] = None,
        tool_choice: Literal["none", "auto", "required"] = "auto",
        temperature: Optional[float] = None,
        **kwargs,
    ):
        """
        Ask LLM using functions/tools and return the response.

        Args:
            messages: List of conversation messages
            system_msgs: Optional system messages to prepend
            timeout: Request timeout in seconds
            tools: List of tools to use
            tool_choice: Tool choice strategy
            temperature: Sampling temperature for the response
            **kwargs: Additional completion arguments

        Returns:
            ChatCompletionMessage: The model's response

        Raises:
            ValueError: If tools, tool_choice, or messages are invalid
            OpenAIError: If API call fails after retries
            Exception: For unexpected errors
        """
        try:
            # Validate tool_choice
            if tool_choice not in ["none", "auto", "required"] and not isinstance(tool_choice, dict):
                raise ValueError(f"Invalid tool_choice: {tool_choice}")

            # Format messages
            if system_msgs:
                system_msgs = self.format_messages(system_msgs)
                messages = system_msgs + self.format_messages(messages)
            else:
                messages = self.format_messages(messages)

            # Validate tools if provided
            if tools:
                for tool in tools:
                    if not isinstance(tool, dict) or "type" not in tool:
                        raise ValueError("Each tool must be a dict with 'type' field")

            if not self.client:
                raise ValueError(f"No client available for API type: {self.api_type}")
                
            # Set up the completion request using the unified client interface
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                timeout=timeout,
                **kwargs,
            )

            # Check if response is valid
            if not response:
                raise ValueError("Invalid or empty response from LLM")
                
            # DEBUG: Log the response type and structure
            logger.info(f"TOOL DEBUG - Response type: {type(response)}")
            if hasattr(response, "tool_calls"):
                logger.info(f"TOOL DEBUG - Response has {len(response.tool_calls)} tool_calls")
            elif hasattr(response, "choices") and hasattr(response.choices[0].message, "tool_calls"):
                logger.info(f"TOOL DEBUG - Response has {len(response.choices[0].message.tool_calls)} tool_calls")
            else:
                logger.info("TOOL DEBUG - No tool_calls found in response")
                
            # If a direct object (Bedrock compatibility layer), log its attributes
            if not hasattr(response, "choices") and hasattr(response, "content"):
                logger.info(f"TOOL DEBUG - Response is direct object with content: {response.content[:50]}...")
                if hasattr(response, "model_dump"):
                    logger.info(f"TOOL DEBUG - Response dump: {json.dumps(response.model_dump(), default=str)[:500]}...")

            return response

        except ValueError as ve:
            logger.error(f"Validation error in ask_tool: {ve}")
            raise
        except OpenAIError as oe:
            if isinstance(oe, AuthenticationError):
                logger.error("Authentication failed. Check API key.")
            elif isinstance(oe, RateLimitError):
                logger.error("Rate limit exceeded. Consider increasing retry attempts.")
            elif isinstance(oe, APIError):
                logger.error(f"API error: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ask_tool: {e}")
            raise

    def _direct_bedrock_converse(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        tool_choice: Literal["none", "auto", "required"] = "auto",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> dict:
        """
        Direct call to Amazon Bedrock converse API for tool calling.
        
        Args:
            messages: List of conversation messages
            tools: List of tools in OpenAI format
            tool_choice: Tool choice strategy
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            dict: Response formatted to match OpenAI completion format
        """
        if not self.bedrock_client:
            raise ValueError("Bedrock client not initialized")
            
        try:
            # Extract model ID from the model string (remove ARN prefix if present)
            model_id = self.model
            if "/" in model_id:
                model_id = model_id.split("/")[-1]
            
            # Handle system messages separately
            bedrock_messages = []
            system_content = ""
            
            # Extract system messages
            for msg in messages:
                if msg.get("role", "") == "system":
                    if msg.get("content"):
                        system_content += msg.get("content", "") + "\n"
            
            # Process non-system messages
            tool_results_exist = any("tool_call_id" in msg for msg in messages)
            
            # For multi-step tool calling with tool results, we need special handling
            if tool_results_exist:
                logger.info("BEDROCK - Tool results detected in messages, restructuring conversation")
                
                # Find the last tool result and its corresponding tool_call_id
                last_tool_result = None
                tool_use_id = None
                
                for msg in messages:
                    if "tool_call_id" in msg and "name" in msg and "content" in msg:
                        last_tool_result = msg
                        tool_use_id = msg.get("tool_call_id")
                
                if last_tool_result and tool_use_id:
                    # IMPORTANT: For Bedrock, we need EXACTLY ONE toolUse followed by EXACTLY ONE matching toolResult
                    # Create a minimal conversation with:
                    # 1. ONE user question
                    # 2. ONE assistant response with ONE toolUse
                    # 3. ONE user response with ONE matching toolResult
                    
                    # Find the most relevant assistant message with a toolUse that matches our toolResult
                    matching_user_msg = None
                    matching_assistant_msg = None
                    matching_tool_use = None
                    
                    # First, find the assistant message with a matching toolUse for our tool result
                    for msg in messages:
                        if msg.get("role") == "assistant" and "tool_calls" in msg:
                            # Check OpenAI format tool calls
                            for tool_call in msg.get("tool_calls", []):
                                if tool_call.get("id") == tool_use_id:
                                    matching_assistant_msg = msg
                                    matching_tool_use = tool_call
                                    break
                    
                    # If we found a matching assistant message, find the user message that preceded it
                    if matching_assistant_msg:
                        # Find the last user message before this assistant message
                        for i, msg in enumerate(messages):
                            if msg.get("role") == "user" and i < messages.index(matching_assistant_msg):
                                matching_user_msg = msg
                    else:
                        # Fallback: Just use the first user message and most recent assistant message with any tool call
                        for msg in messages:
                            if msg.get("role") == "user" and "tool_call_id" not in msg and not matching_user_msg:
                                matching_user_msg = msg
                            if msg.get("role") == "assistant" and "tool_calls" in msg:
                                matching_assistant_msg = msg
                    
                    # Reset and build a minimal, balanced conversation
                    bedrock_messages = []
                    
                    # 1. Add ONE user message
                    if matching_user_msg:
                        content = matching_user_msg.get("content", "")
                        if isinstance(content, str) and content.strip():
                            bedrock_messages.append({
                                "role": "user",
                                "content": [{"text": content}]
                            })
                    else:
                        # If no matching user message, create a simple context message
                        bedrock_messages.append({
                            "role": "user",
                            "content": [{"text": "I need help with a task."}]
                        })
                    
                    # 2. Add ONE assistant message with EXACTLY ONE toolUse
                    if matching_assistant_msg and matching_tool_use:
                        # Create a clean assistant message with exactly one toolUse
                        tool_use_obj = {
                            "toolUse": {
                                "toolUseId": tool_use_id,
                                "name": matching_tool_use.get("function", {}).get("name", "unknown_tool"),
                                "input": json.loads(matching_tool_use.get("function", {}).get("arguments", "{}")) if isinstance(matching_tool_use.get("function", {}).get("arguments"), str) else matching_tool_use.get("function", {}).get("arguments", {})
                            }
                        }
                        
                        bedrock_messages.append({
                            "role": "assistant",
                            "content": [tool_use_obj]
                        })
                    else:
                        # Error - we must have a matching toolUse to proceed
                        logger.error("BEDROCK - No matching toolUse found for toolResult - cannot proceed with multi-step conversation")
                        raise ValueError("No matching toolUse found for toolResult in Bedrock conversation")
                    
                    # 3. Add ONE user message with EXACTLY ONE toolResult
                    try:
                        # Try to parse content as JSON
                        content = last_tool_result.get("content", "")
                        if isinstance(content, str):
                            try:
                                json_content = json.loads(content)
                                tool_result = {
                                    "toolUseId": tool_use_id,
                                    "content": [{"json": json_content}]
                                }
                            except json.JSONDecodeError:
                                # If not valid JSON, send as text
                                tool_result = {
                                    "toolUseId": tool_use_id,
                                    "content": [{"text": content}]
                                }
                        else:
                            # Handle non-string content
                            content_value = content if isinstance(content, dict) else {"result": str(content)}
                            tool_result = {
                                "toolUseId": tool_use_id,
                                "content": [{"json": content_value}]
                            }
                        
                        # Create ONE user message with ONE toolResult
                        bedrock_messages.append({
                            "role": "user",
                            "content": [{"toolResult": tool_result}]
                        })
                    except Exception as e:
                        logger.error(f"BEDROCK - Error formatting tool result: {e}")
                        # In case of error, try a more direct approach
                        tool_result = {
                            "toolUseId": tool_use_id,
                            "content": [{"text": str(content)}]
                        }
                        bedrock_messages.append({
                            "role": "user", 
                            "content": [{"toolResult": tool_result}]
                        })
                else:
                    # If we couldn't identify the specific tool use/result pattern, fall back to standard processing
                    logger.warning("BEDROCK - Tool results detected but couldn't identify matching pattern. Using standard processing.")
                    # Continue with regular message processing below...
            
            # Only process messages using the standard approach if we haven't already built a streamlined conversation
            if not tool_results_exist:
                for msg in messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    
                    # Skip system messages as they're handled separately
                    if role == "system":
                        continue
                        
                    # Convert role names to match Bedrock expectations
                    if role == "user":
                        bedrock_role = "user"
                    elif role == "assistant":
                        bedrock_role = "assistant"
                    else:
                        bedrock_role = "user"  # Default to user for unsupported roles
                        
                    # Create Bedrock content format
                    bedrock_content = []
                    if isinstance(content, str) and content.strip():
                        bedrock_content = [{"text": content}]
                    
                    # Handle tool results in messages - needed for multi-step tool calling
                    if "tool_call_id" in msg and "name" in msg and "content" in msg:
                        # This is a tool result, format it as toolResult
                        try:
                            # Try to parse content as JSON
                            if isinstance(msg["content"], str):
                                try:
                                    json_content = json.loads(msg["content"])
                                    tool_result = {
                                        "toolUseId": msg["tool_call_id"],
                                        "content": [{"json": json_content}]
                                    }
                                except json.JSONDecodeError:
                                    # If not valid JSON, send as text
                                    logger.info(f"BEDROCK - Tool result content is not valid JSON, sending as text: {msg['content'][:50]}...")
                                    tool_result = {
                                        "toolUseId": msg["tool_call_id"],
                                        "content": [{"text": msg["content"]}]
                                    }
                            else:
                                # If content is not a string (e.g., it's already a dict or list)
                                tool_result = {
                                    "toolUseId": msg["tool_call_id"],
                                    "content": [{"json": msg["content"] if isinstance(msg["content"], dict) else {"result": msg["content"]}}]
                                }
                            
                            bedrock_content = [{"toolResult": tool_result}]
                        except Exception as e:
                            logger.error(f"BEDROCK - Error processing tool result: {e}")
                            # Fallback to empty text to avoid breaking the conversation
                            tool_result = {
                                "toolUseId": msg["tool_call_id"],
                                "content": [{"text": "Error processing tool result"}]
                            }
                            bedrock_content = [{"toolResult": tool_result}]
                    
                    # Only add the message if it has content    
                    if bedrock_content:
                        bedrock_messages.append({
                            "role": bedrock_role,
                            "content": bedrock_content
                        })
                        
            # Log the final message structure
            logger.info(f"BEDROCK - Sending {len(bedrock_messages)} messages to Bedrock")
            for i, msg in enumerate(bedrock_messages):
                content_summary = []
                for content_item in msg.get("content", []):
                    if isinstance(content_item, dict):
                        content_summary.append(list(content_item.keys())[0] if content_item else "empty-dict")
                logger.info(f"BEDROCK - Message {i}: role={msg['role']}, content_types={content_summary}")
                
            # Convert OpenAI tools to Bedrock toolSpec format
            bedrock_tools = []
            tool_config = None
            if tools:
                for tool in tools:
                    # Extract function details from the OpenAI format
                    if tool.get("type") == "function" and "function" in tool:
                        function_details = tool["function"]
                        function_name = function_details.get("name", "")
                        function_description = function_details.get("description", "")
                        function_parameters = function_details.get("parameters", {})
                        
                        # Create Bedrock toolSpec
                        bedrock_tool = {
                            "toolSpec": {
                                "name": function_name,
                                "description": function_description,
                                "inputSchema": {
                                    "json": function_parameters
                                }
                            }
                        }
                        bedrock_tools.append(bedrock_tool)
            
            # Convert tool_choice to Bedrock format (if needed)
            bedrock_tool_choice = {"auto": {}}  # Default to "auto" for Bedrock
            if tool_choice == "none":
                bedrock_tool_choice = {"none": {}}
            elif tool_choice == "auto":
                # For Bedrock/Claude, use "auto" to allow model to decide
                bedrock_tool_choice = {"auto": {}}
            elif tool_choice == "required":
                # For "required" setting, use "any" in Bedrock
                bedrock_tool_choice = {"any": {}}
            elif isinstance(tool_choice, dict) and "function" in tool_choice:
                # Handle explicit tool selection
                tool_name = tool_choice["function"].get("name", "")
                bedrock_tool_choice = {
                    "tool": {
                        "name": tool_name
                    }
                }
            
            # Set up toolConfig parameter - CRITICAL: this must be included in EVERY API call
            # For multi-step tool calling, AWS documentation shows we need EXACTLY the same tools
            # in the follow-up calls as in the initial call
            tool_config = {
                "tools": bedrock_tools,
                "toolChoice": bedrock_tool_choice
            }
            logger.info(f"BEDROCK - Created toolConfig with {len(bedrock_tools)} tools")
        
            # Check if we have a multi-step tool conversation
            is_multi_step_tool_conversation = False
            has_tool_result = False
            
            for msg in bedrock_messages:
                for content_item in msg.get("content", []):
                    if isinstance(content_item, dict):
                        if "toolUse" in content_item:
                            is_multi_step_tool_conversation = True
                        if "toolResult" in content_item:
                            has_tool_result = True
                            is_multi_step_tool_conversation = True
            
            # CRITICAL: According to AWS documentation examples, we MUST include the exact same
            # toolConfig in follow-up calls as in the initial call
            if is_multi_step_tool_conversation:
                # If we have a toolResult but no tools were provided, we need to fail gracefully
                if not tools or not bedrock_tools:
                    logger.error("BEDROCK - Multi-step tool conversation detected but no tools provided")
                    raise ValueError("Multi-step tool conversation requires tools to be provided for Bedrock API")
                
                # Ensure tool_config is set even if somehow it wasn't created above
                if not tool_config:
                    tool_config = {
                        "tools": bedrock_tools,
                        "toolChoice": {"any": {}}
                    }
                
                if has_tool_result:
                    logger.info("BEDROCK - Making follow-up call with toolResult")
            
            # Ensure we ALWAYS include toolConfig for ANY api call with tools or tool results
            if (tools or has_tool_result) and not tool_config:
                # Final fallback - should never happen, but just in case
                tool_config = {
                    "tools": bedrock_tools,
                    "toolChoice": {"any": {}}
                }
            
            # Set up additional fields for the API call
            additional_fields = {}
            if system_content:
                additional_fields["system"] = system_content
            if temperature is not None:
                additional_fields["temperature"] = temperature or self.temperature
            if max_tokens is not None:
                additional_fields["max_tokens"] = max_tokens or self.max_tokens
                
            # Log whether we're including toolConfig
            if tool_config:
                logger.info(f"BEDROCK - Making API call with {len(tool_config.get('tools', []))} tools")
                # Make the Bedrock converse API call
                response = self.bedrock_client.converse(
                    modelId=model_id,
                    messages=bedrock_messages,
                    toolConfig=tool_config,  # CRITICAL: Include toolConfig in all tool-related API calls
                    additionalModelRequestFields=additional_fields
                )
            else:
                response = self.bedrock_client.converse(
                    modelId=model_id,
                    messages=bedrock_messages,
                    additionalModelRequestFields=additional_fields
                )
            
            # Convert Bedrock response to OpenAI-compatible format
            bedrock_content = response["output"]["message"].get("content", [])
            
            # Initialize variables to collect response parts
            content = ""
            tool_calls = []
            
            # Process the content which is a list in Bedrock's response
            for item in bedrock_content:
                if "text" in item:
                    content += item["text"]
                elif "toolUse" in item:
                    tool_use = item["toolUse"]
                    
                    # Ensure that 'arguments' is a string (JSON string)
                    arguments = tool_use.get("input", "{}")
                    if isinstance(arguments, dict):
                        arguments = json.dumps(arguments)
                    
                    tool_calls.append({
                        "id": tool_use.get("toolUseId", f"call_{len(tool_calls)}"),  # Use toolUseId if available
                        "type": "function",
                        "function": {
                            "name": tool_use.get("name", ""),
                            "arguments": arguments
                        }
                    })
            
            # Create OpenAI-compatible message structure
            openai_message = {
                "role": "assistant",
                # Always provide a string for content, never None
                "content": content if content else "",
            }
            
            if tool_calls:
                openai_message["tool_calls"] = tool_calls
                logger.info(f"BEDROCK - Processed response with {len(tool_calls)} tool_calls")
            
            return {
                "id": "bedrock_response",
                "choices": [
                    {
                        "finish_reason": "stop" if not tool_calls else "tool_calls",
                        "index": 0,
                        "message": openai_message
                    }
                ],
                "model": self.model,
                "usage": {
                    "completion_tokens": int(response.get("usage", {}).get("output_tokens", 0)),
                    "prompt_tokens": int(response.get("usage", {}).get("input_tokens", 0)),
                    "total_tokens": (
                        int(response.get("usage", {}).get("input_tokens", 0)) +
                        int(response.get("usage", {}).get("output_tokens", 0))
                    )
                }
            }
        except Exception as e:
            logger.error(f"Error in direct Bedrock converse API call: {str(e)}")
            raise

    def _dict_to_message_obj(self, message_dict):
        """
        Convert a message dictionary to a message object compatible with OpenAI's response format.
        This ensures consistent return types between OpenAI/Azure and direct Bedrock API calls.
        
        Args:
            message_dict: Dictionary containing message data
            
        Returns:
            object: An object with attributes matching the dictionary keys
        """
        # Handle None or unexpected types
        if message_dict is None:
            return None
        if not isinstance(message_dict, dict):
            logger.warning(f"Expected dict in _dict_to_message_obj, got {type(message_dict)}")
            return message_dict
            
        class MessageObj:
            def __init__(self, **kwargs):
                # Always initialize key attributes with sensible defaults
                self.tool_calls = []
                self.content = ""
                self.role = "assistant"
                
                for key, value in kwargs.items():
                    # Special handling for function.arguments to ensure it's a string
                    if key == 'function' and isinstance(value, dict) and 'arguments' in value:
                        args = value['arguments']
                        if isinstance(args, dict):
                            value['arguments'] = json.dumps(args)
                    setattr(self, key, value)
                    
            def __str__(self):
                return str({k: v for k, v in self.__dict__.items()})
                
            def __repr__(self):
                return self.__str__()
                
            def model_dump(self):
                """
                Mimics the Pydantic model_dump method to maintain compatibility.
                Returns a dictionary of the object's attributes.
                """
                return {k: v for k, v in self.__dict__.items()}
                
            def dict(self):
                """
                Legacy Pydantic compatibility method
                """
                return self.model_dump()
        
        # Create object with attributes matching dictionary keys
        msg_obj = MessageObj(**message_dict)
        
        # If there are tool_calls, convert each tool call dictionary to an object too
        if message_dict.get("tool_calls"):
            tool_calls_objs = []
            for tc in message_dict["tool_calls"]:
                # Convert the function part to an object if it exists
                if "function" in tc:
                    # Ensure function.arguments is a string (JSON string)
                    function_dict = tc["function"].copy()
                    if "arguments" in function_dict and isinstance(function_dict["arguments"], dict):
                        function_dict["arguments"] = json.dumps(function_dict["arguments"])
                    
                    function_obj = MessageObj(**function_dict)
                    tc_copy = tc.copy()
                    tc_copy["function"] = function_obj
                    tool_calls_objs.append(MessageObj(**tc_copy))
                else:
                    tool_calls_objs.append(MessageObj(**tc))
            
            # Replace the tool_calls list with the list of objects
            msg_obj.tool_calls = tool_calls_objs
            
        return msg_obj

    def _direct_bedrock_invoke(
        self,
        messages: List[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Direct call to Amazon Bedrock invoke API for non-tool completions.
        
        Args:
            messages: List of conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            str: The model's response text
        """
        if not self.bedrock_client:
            raise ValueError("Bedrock client not initialized")
            
        # Extract model ID from the model string (remove ARN prefix if present)
        model_id = self.model
        if "/" in model_id:
            model_id = model_id.split("/")[-1]
        
        # Prepare system and message content
        system_content = ""
        prompt = ""
        
        # Extract system messages and build prompt
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                system_content += content + "\n"
            elif role == "user":
                prompt += f"Human: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
            else:
                # For any other role, treat as user
                prompt += f"Human: {content}\n"
        
        # Add final assistant prompt
        prompt += "Assistant: "
        
        # Format the request for Claude models
        invoke_body = {
            "prompt": prompt,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature or self.temperature,
            "anthropic_version": "bedrock-2023-05-31"
        }
        
        if system_content:
            invoke_body["system"] = system_content
            
        try:
            # Make the Bedrock invoke API call
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(invoke_body)
            )
            
            # Parse and return the response
            response_body = json.loads(response.get('body').read())
            completion = response_body.get('completion', '')
            
            return completion.strip()
            
        except Exception as e:
            logger.error(f"Error in direct Bedrock invoke API call: {str(e)}")
            raise


def get_tool_calls(response):
    """
    Extract tool calls from either object-style or dictionary-style responses.
    
    Args:
        response: The response from an LLM, which could be either an object with attributes
                or a dictionary
                
    Returns:
        list: List of tool call objects/dictionaries, or empty list if none found
    """
    try:
        # Handle case when response is a dictionary (like from Bedrock)
        if isinstance(response, dict):
            # Check if it's an OpenAI-style response
            if "choices" in response and len(response["choices"]) > 0:
                message = response["choices"][0].get("message", {})
                if isinstance(message, dict) and "tool_calls" in message:
                    return message["tool_calls"]
            # Direct access to tool_calls
            if "tool_calls" in response:
                return response["tool_calls"]
            return []
            
        # Handle case when response is an object (like from OpenAI)
        if hasattr(response, "choices") and len(response.choices) > 0:
            message = response.choices[0].message
            if hasattr(message, "tool_calls"):
                return message.tool_calls
        
        # Handle case when response is already a message object
        if hasattr(response, "tool_calls"):
            return response.tool_calls
            
        # Handle case when the response has get method (like a model object)
        if hasattr(response, "get") and callable(response.get):
            tool_calls = response.get("tool_calls", [])
            if tool_calls:
                return tool_calls
            
        # If we can't find tool calls, return empty list
        return []
    except Exception as e:
        logger.error(f"Error extracting tool calls: {e}")
        return []
