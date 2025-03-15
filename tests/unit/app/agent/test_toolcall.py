"""
Unit tests for the ToolCallAgent class, testing tool call functionality.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.toolcall import ToolCallAgent
from app.schema import Message, ToolCall, Function, AgentState


@pytest.fixture
def tool_agent():
    """Create a ToolCallAgent instance for testing."""
    agent = ToolCallAgent(name="test_tool_agent")
    agent.llm = AsyncMock()
    return agent


class TestToolCallAgent:
    """Tests for the ToolCallAgent class functionality."""
    
    def test_clean_search_query(self, tool_agent):
        """Test cleaning and normalization of search queries."""
        test_cases = [
            # Original query, expected cleaned result
            ("search for python tutorials", "python tutorials"),
            ("look up weather in San Francisco", "weather in San Francisco"),
            ("find information about machine learning", "information about machine learning"),
            ("Search for: artificial intelligence", "artificial intelligence"),
            ("google climate change effects", "climate change effects"),
            # Test very long query gets truncated
            ("search for " + "very long query " * 20, ("very long query " * 10).strip()[:200]),
            # Test query with leading/trailing whitespace
            ("  find   extra spaces   ", "extra spaces"),
        ]
        
        for original, expected in test_cases:
            cleaned = tool_agent._clean_search_query(original)
            assert cleaned == expected
    
    def test_create_web_search_tool_call(self, tool_agent):
        """Test creation of web search tool calls with appropriate parameters."""
        # Test basic query
        tool_call = tool_agent._create_web_search_tool_call("python tutorials")
        
        # Verify tool call structure
        assert tool_call.type == "function"
        assert tool_call.function.name == "web_search"
        
        # Check arguments
        args = json.loads(tool_call.function.arguments)
        assert args["query"] == "python tutorials"
        assert args["num_results"] == 10  # Default
        
        # Test query with number of results
        tool_call = tool_agent._create_web_search_tool_call("top 5 python tutorials")
        
        # Check arguments include the specified number
        args = json.loads(tool_call.function.arguments)
        assert args["query"] == "top 5 python tutorials"
        assert args["num_results"] == 5
        
        # Test with number outside reasonable range (should use default)
        tool_call = tool_agent._create_web_search_tool_call("top 100 python tutorials")
        
        # Should use default since 100 > 50
        args = json.loads(tool_call.function.arguments)
        assert args["num_results"] == 10
    
    def test_is_special_tool(self, tool_agent):
        """Test identification of special tools."""
        # The default special tool is "terminate"
        assert tool_agent._is_special_tool("terminate")
        assert tool_agent._is_special_tool("Terminate")  # Case insensitive
        assert not tool_agent._is_special_tool("web_search")
        
        # Add a custom special tool
        tool_agent.special_tool_names.append("custom_tool")
        assert tool_agent._is_special_tool("custom_tool")
        assert not tool_agent._is_special_tool("regular_tool")


@pytest.mark.asyncio
class TestToolCallExecution:
    """Tests for tool call execution functionality."""
    
    async def test_handle_stuck_state_with_web_search(self, tool_agent):
        """Test that handle_stuck_state can suggest web search when appropriate."""
        # Create a test case where agent seems to be asking for information
        tool_agent.memory.messages = [
            Message.assistant_message("I need to find information about Python programming."),
            Message.assistant_message("Do you have any information about Python tutorials?"),
            Message.assistant_message("I would need to search for Python documentation."),
        ]
        
        # Mock _verify_intervention_needed to always return True for testing
        with patch.object(tool_agent, '_verify_intervention_needed', AsyncMock(return_value=True)):
            # Mock input function to return a command to use web search
            with patch('builtins.input', return_value="/web_search=Python tutorials"):
                with patch('builtins.print'):
                    # Call the method
                    await tool_agent.handle_stuck_state()
                    
                    # Verify next_step_prompt includes reference to web search
                    assert "web_search" in tool_agent.next_step_prompt
                    assert "Python tutorials" in tool_agent.next_step_prompt
    
    async def test_detect_search_intent(self, tool_agent):
        """Test detecting search intent from conversation."""
        # Create messages that indicate search intent
        search_messages = [
            Message.assistant_message("I need to look up information about Python."),
            Message.assistant_message("Let me search for Python tutorials."),
            Message.user_message("Please find information about machine learning.")
        ]
        
        # Create messages without search intent
        non_search_messages = [
            Message.assistant_message("I'll process your request."),
            Message.assistant_message("Here's a summary of the data."),
            Message.user_message("Please continue with the analysis.")
        ]
        
        # Mock the appropriate methods
        with patch.object(tool_agent, '_get_recent_messages', return_value=search_messages):
            # Call with messages indicating search intent
            tool_agent.llm.ask.return_value = MagicMock(content="YES, there is search intent")
            assert await tool_agent._detect_search_intent()
        
        with patch.object(tool_agent, '_get_recent_messages', return_value=non_search_messages):
            # Call with messages not indicating search intent
            tool_agent.llm.ask.return_value = MagicMock(content="NO, there is no search intent")
            assert not await tool_agent._detect_search_intent()
            
    
    @pytest.mark.parametrize("input_text,expected", [
        ("/web_search=Python tutorials", "Python tutorials"),
        ("/search for machine learning", "machine learning"),
        ("/find information about climate change", "information about climate change"),
        # Non-search commands
        ("/continue", None),
        ("/reset", None),
        ("regular input", None),
    ])
    async def test_extract_search_query_from_input(self, tool_agent, input_text, expected):
        """Test extracting search query from user input."""
        result = tool_agent._extract_search_query(input_text)
        assert result == expected
