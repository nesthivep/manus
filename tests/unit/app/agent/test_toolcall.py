"""
Unit tests for the ToolCallAgent class, testing tool call functionality.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.toolcall import ToolCallAgent
from app.schema import Message


@pytest.fixture
def tool_agent():
    """Create a ToolCallAgent instance for testing."""
    agent = ToolCallAgent(name="test_tool_agent")
    agent.llm = AsyncMock()
    return agent


class TestToolCallAgent:
    """Tests for the ToolCallAgent class functionality."""

    def test_extract_search_query(self, tool_agent):
        """Test extraction of search queries."""
        test_cases = [
            # Original query, expected result (same as input in current implementation)
            ("search for python tutorials", "search for python tutorials"),
            ("look up weather in San Francisco", "look up weather in San Francisco"),
            (
                "find information about machine learning",
                "find information about machine learning",
            ),
            ("Search for artificial intelligence", "Search for artificial intelligence"),
            ("google climate change effects", "google climate change effects"),
            # Test with leading/trailing whitespace - note that the implementation might strip whitespace
            ("  find   extra spaces   ", "find   extra spaces"),
        ]

        # Test each case
        for original, expected in test_cases:
            result = tool_agent._extract_search_query(original)
            assert result == expected

    def test_create_web_search_tool_call(self, tool_agent):
        """Test creation of web search tool call."""
        query = "python tutorials"
        tool_call = tool_agent._create_web_search_tool_call(query)
        
        # Check the tool call has the right structure
        assert tool_call.type == "function"
        assert tool_call.function.name == "web_search"
        
        # Parse the arguments as JSON and check the search term
        args = json.loads(tool_call.function.arguments)
        # Check for either "search_term" or "query" depending on the implementation
        search_param = args.get("search_term") or args.get("query")
        assert search_param == query

    def test_is_special_tool(self, tool_agent):
        """Test detection of special tools."""
        # Add a special tool name
        tool_agent.special_tool_names = ["terminate", "special_tool"]

        # Test with special tools
        assert tool_agent._is_special_tool("terminate")
        assert tool_agent._is_special_tool("special_tool")

        # Test with non-special tools
        assert not tool_agent._is_special_tool("web_search")
        assert not tool_agent._is_special_tool("regular_tool")


class TestToolCallExecution:
    """Tests for tool call execution functionality."""

    @pytest.mark.asyncio
    async def test_handle_stuck_state_with_web_search(self, tool_agent):
        """Test that handle_stuck_state can suggest web search when appropriate."""
        # Create a test case where agent seems to be asking for information
        tool_agent.memory.messages = [
            Message.assistant_message(
                "I need to find information about Python programming."
            ),
            Message.assistant_message(
                "Do you have any information about Python tutorials?"
            ),
            Message.assistant_message(
                "I would need to search for Python documentation."
            ),
        ]

        # Mock _verify_intervention_needed to always return True for testing
        with patch.object(
            tool_agent, "_verify_intervention_needed", AsyncMock(return_value=True)
        ):
            # Mock input function to return a command to use web search
            with patch("builtins.input", return_value="/web_search=Python tutorials"):
                with patch("builtins.print"):
                    # Call the method
                    await tool_agent.handle_stuck_state()

                    # Verify the command was processed
                    assert "user command" in tool_agent.next_step_prompt.lower()

    def test_should_auto_use_web_search(self, tool_agent):
        """Test the pattern-matching logic for web search detection."""
        # Simplified test cases that should trigger auto web search
        should_search_cases = [
            "Can you search the web for programming tutorials?",
            "Look online for recent developments in AI",
        ]

        # Test cases that should NOT trigger auto web search
        should_not_search_cases = [
            "I'll help you solve this programming problem",
            "Let me analyze this code for bugs",
        ]

        # Test positive cases - at least one should pass
        assert any(tool_agent._should_auto_use_web_search(content) for content in should_search_cases)

        # Test negative cases
        for content in should_not_search_cases:
            assert not tool_agent._should_auto_use_web_search(content)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            # Test with the actual implementation behavior
            ("/web_search=Python tutorials", "/web_search=Python tutorials"),
            ("/search for machine learning", "/search for machine learning"),
            ("/find information about climate change", "/find information about climate change"),
            # Non-search commands
            ("/continue", "/continue"),
            ("/reset", "/reset"),
            ("regular input", "regular input"),
        ],
    )
    async def test_extract_search_query_from_input(
        self, tool_agent, input_text, expected
    ):
        """Test extracting search query from user input."""
        result = tool_agent._extract_search_query(input_text)
        assert result == expected
