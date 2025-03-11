from typing import Dict, List, Literal, Optional, Union
import time
import asyncio
from collections import deque

from openai import (
    APIError,
    AsyncAzureOpenAI,
    AsyncOpenAI,
    AuthenticationError,
    OpenAIError,
    RateLimitError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
    wait_fixed,
    wait_chain,
)

from app.config import LLMSettings, config
from app.logger import logger  # Assuming a logger is set up in your app
from app.schema import Message

# Custom retry strategy for rate limit errors
def rate_limit_retry_strategy():
    """Creates a retry strategy that's more lenient with rate limit errors"""
    return retry(
        # First use exponential backoff, then fixed longer waits for rate limits
        wait=wait_chain(
            # Standard exponential backoff for first 3 attempts
            *[wait_random_exponential(min=1, max=10) for _ in range(3)],
            # Longer fixed waits for subsequent attempts
            *[wait_fixed(delay) for delay in [15, 30, 45, 60, 90, 120]]
        ),
        # Allow up to 10 attempts (instead of 6)
        stop=stop_after_attempt(10),
        # Only retry on rate limit errors and API errors
        retry=retry_if_exception_type((RateLimitError, APIError)),
        # Log retries
        before_sleep=lambda retry_state: logger.warning(
            f"Rate limit hit - retrying in {retry_state.next_action.sleep} seconds... "
            f"(Attempt {retry_state.attempt_number} of {10})"
        ),
    )


class TokenRateLimiter:
    """
    Manages token rate limits to prevent exceeding the 20k tokens per minute limit.
    Uses a sliding window approach to track token usage over time.
    """
    def __init__(self, tokens_per_minute=20000, window_size=60):
        self.tokens_per_minute = tokens_per_minute
        self.window_size = window_size  # window size in seconds
        self.usage_history = deque()  # stores (timestamp, token_count) tuples
        self.lock = asyncio.Lock()  # to make operations thread-safe

    async def add_tokens(self, token_count):
        """Record token usage"""
        async with self.lock:
            current_time = time.time()
            self.usage_history.append((current_time, token_count))
            self._clean_old_entries(current_time)

    async def wait_if_needed(self, token_count):
        """Wait if adding this many tokens would exceed the rate limit"""
        current_time = time.time()
        
        while True:
            async with self.lock:
                self._clean_old_entries(current_time)
                current_usage = sum(count for _, count in self.usage_history)
                
                # If adding these tokens would exceed our limit
                if current_usage + token_count > self.tokens_per_minute:
                    # Calculate how long we need to wait
                    if len(self.usage_history) > 0:
                        oldest_time = self.usage_history[0][0]
                        # How long until oldest entry drops out of window
                        wait_time = oldest_time + self.window_size - current_time
                        if wait_time > 0:
                            logger.warning(f"Token rate limit approaching - waiting {wait_time:.2f} seconds. " 
                                          f"Current usage: {current_usage}/{self.tokens_per_minute} tokens per minute")
                            break  # Exit the lock before sleeping
                    else:
                        wait_time = 0  # Should not happen, but just in case
                        break
                else:
                    return  # No need to wait
            
            # Wait outside the lock to allow other operations
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                current_time = time.time()  # Update time for next check
            else:
                return

    def _clean_old_entries(self, current_time):
        """Remove entries older than the window size"""
        cutoff_time = current_time - self.window_size
        while self.usage_history and self.usage_history[0][0] < cutoff_time:
            self.usage_history.popleft()

    def estimate_tokens(self, messages):
        """
        Estimate token count for a list of messages.
        This is a simple approximation - more accurate would be to use tiktoken.
        """
        total_tokens = 0
        for message in messages:
            # Count content tokens (4 chars ~= 1 token as a rough estimate)
            if isinstance(message, dict):
                if "content" in message and message["content"]:
                    if isinstance(message["content"], str):
                        total_tokens += len(message["content"]) // 4
                    elif isinstance(message["content"], list):
                        for content_item in message["content"]:
                            if isinstance(content_item, dict) and "text" in content_item:
                                total_tokens += len(content_item["text"]) // 4
            elif hasattr(message, "content") and message.content:
                total_tokens += len(message.content) // 4
                
        # Add a buffer for message formatting overhead
        return max(1, int(total_tokens * 1.2))


class LLM:
    _instances: Dict[str, "LLM"] = {}
    _token_limiter = TokenRateLimiter()  # Shared token limiter for all instances

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
            
            if self.api_type == "anthropic":
                try:
                    import anthropic
                    ANTHROPIC_AVAILABLE = True
                    self.client_type = "anthropic"
                    self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
                except ImportError:
                    ANTHROPIC_AVAILABLE = False
                    raise ImportError(
                        "The Anthropic package is not installed. "
                        "Please install it with: pip install anthropic"
                    )
            elif self.api_type == "azure":
                self.client_type = "openai"
                self.client = AsyncAzureOpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    api_version=self.api_version,
                )
            else:
                self.client_type = "openai"
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

    @rate_limit_retry_strategy()
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
            # Format system and user messages
            if system_msgs:
                system_msgs = self.format_messages(system_msgs)
                formatted_messages = system_msgs + self.format_messages(messages)
            else:
                formatted_messages = self.format_messages(messages)

            # Estimate tokens and respect rate limits
            estimated_tokens = self._token_limiter.estimate_tokens(formatted_messages)
            await self._token_limiter.wait_if_needed(estimated_tokens)
            
            try:
                if self.client_type == "anthropic":
                    # Handle Anthropic API - implement actual logic here
                    if not stream:
                        # Non-streaming Anthropic request
                        response = await self.client.messages.create(
                            model=self.model,
                            messages=formatted_messages,
                            max_tokens=self.max_tokens,
                            temperature=temperature or self.temperature,
                        )
                        result = response.content[0].text
                    else:
                        # Streaming Anthropic request
                        stream_response = await self.client.messages.create(
                            model=self.model,
                            messages=formatted_messages,
                            max_tokens=self.max_tokens,
                            temperature=temperature or self.temperature,
                            stream=True,
                        )
                        
                        collected_messages = []
                        async for chunk in stream_response:
                            if chunk.type == "content_block_delta":
                                chunk_message = chunk.delta.text
                                collected_messages.append(chunk_message)
                                print(chunk_message, end="", flush=True)
                        
                        print()  # Newline after streaming
                        result = "".join(collected_messages).strip()
                        if not result:
                            raise ValueError("Empty response from streaming Anthropic LLM")
                else:
                    # Original OpenAI implementation
                    if not stream:
                        # Non-streaming request
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=formatted_messages,
                            max_tokens=self.max_tokens,
                            temperature=temperature or self.temperature,
                            stream=False,
                        )
                        if not response.choices or not response.choices[0].message.content:
                            raise ValueError("Empty or invalid response from LLM")
                        result = response.choices[0].message.content
                    else:
                        # Streaming request
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=formatted_messages,
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
                        result = "".join(collected_messages).strip()
                        if not result:
                            raise ValueError("Empty response from streaming LLM")
                
                # Record token usage after successful API call
                await self._token_limiter.add_tokens(estimated_tokens)
                return result
                
            except Exception as e:
                # If there's an error, still try to record token usage
                # but don't block on it if it fails
                try:
                    await self._token_limiter.add_tokens(estimated_tokens)
                except:
                    pass
                raise e

        except ValueError as ve:
            logger.error(f"Validation error: {ve}")
            raise
        except OpenAIError as oe:
            logger.error(f"OpenAI API error: {oe}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in ask: {e}")
            raise

    @rate_limit_retry_strategy()
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
            if tool_choice not in ["none", "auto", "required"]:
                raise ValueError(f"Invalid tool_choice: {tool_choice}")

            # Format messages
            if system_msgs:
                system_msgs = self.format_messages(system_msgs)
                formatted_messages = system_msgs + self.format_messages(messages)
            else:
                formatted_messages = self.format_messages(messages)
                
            # Estimate tokens and respect rate limits
            estimated_tokens = self._token_limiter.estimate_tokens(formatted_messages)
            await self._token_limiter.wait_if_needed(estimated_tokens)

            # Validate tools if provided
            if tools:
                for tool in tools:
                    if not isinstance(tool, dict) or "type" not in tool:
                        raise ValueError("Each tool must be a dict with 'type' field")

            # Set up the completion request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
                tools=tools,
                tool_choice=tool_choice,
                timeout=timeout,
                **kwargs,
            )

            # Check if response is valid
            if not response.choices or not response.choices[0].message:
                print(response)
                raise ValueError("Invalid or empty response from LLM")

            # Record token usage after successful API call
            await self._token_limiter.add_tokens(estimated_tokens)

            return response.choices[0].message

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
