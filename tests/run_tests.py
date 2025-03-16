"""
Simple test runner that doesn't require pytest to be installed.
This provides a way to verify the functionality without external dependencies.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch


# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the classes to test
from app.agent.base import BaseAgent
from app.schema import Memory, Message


class MockTestAgent(BaseAgent):
    """Mock implementation of BaseAgent for testing purposes."""

    name: str = "mock_agent"

    async def think(self) -> bool:
        return True

    async def act(self) -> str:
        return "Test action"

    async def observe(self, result: str) -> None:
        pass

    async def step(self) -> str:
        return "Mock step executed"


class TestBasicFunctionality(unittest.TestCase):
    """Basic tests to verify core functionality works."""

    def setUp(self):
        """Set up test agent."""
        self.agent = MockTestAgent(name="test_agent")
        self.agent.llm = AsyncMock()

    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        self.assertEqual(self.agent.name, "test_agent")
        self.assertEqual(self.agent.state, "IDLE")
        self.assertIsNotNone(self.agent.memory)
        self.assertEqual(len(self.agent.memory.messages), 0)

    def test_memory_operations(self):
        """Test basic memory operations."""
        # Add a message
        self.agent.memory.add_message(Message.user_message("Test message"))
        self.assertEqual(len(self.agent.memory.messages), 1)
        self.assertEqual(self.agent.memory.messages[0].content, "Test message")
        self.assertEqual(self.agent.memory.messages[0].role, "user")


# Helper function to run async tests
def run_async_test(coroutine):
    """Run an async test coroutine."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


# Async test cases
async def test_parameter_handling():
    """Test parameter extraction from user input."""
    agent = MockTestAgent(name="test_agent")
    agent.llm = AsyncMock()
    
    # Mock _verify_intervention_needed to return True
    with patch.object(agent, "_verify_intervention_needed", AsyncMock(return_value=True)):
        # Mock input function to return a parameter
        with patch("builtins.input", return_value="/topic=machine learning"):
            with patch("builtins.print"):  # Suppress print output
                # Call the method
                await agent.handle_stuck_state()
                
                # Check that system message about parameter was added
                system_msg_found = False
                for msg in agent.memory.messages:
                    if (msg.role == "system" and 
                        "User provided parameter: topic=machine learning" in msg.content):
                        system_msg_found = True
                        break
                
                assert system_msg_found, "System parameter message not found in memory"
                
                # Check that user message with parameter was added
                user_msg_found = False
                for msg in agent.memory.messages:
                    if (msg.role == "user" and 
                        "I'm interested in topic: machine learning" in msg.content):
                        user_msg_found = True
                        break
                
                assert user_msg_found, "User parameter message not found in memory"


async def test_verify_intervention_needed_deeply_stuck():
    """Test LLM verification when deeply stuck."""
    agent = MockTestAgent(name="test_agent")
    
    # Mock LLM to return "YES" for intervention
    agent.llm = AsyncMock()
    agent.llm.ask.return_value = MagicMock(content="YES, user intervention is needed.")

    # Call with deeply_stuck=True
    result = await agent._verify_intervention_needed(
        [Message.assistant_message("Repetitive message")], deeply_stuck=True
    )

    # Should recommend intervention
    assert result is True


async def test_verify_intervention_not_needed():
    """Test LLM verification when not deeply stuck."""
    agent = MockTestAgent(name="test_agent")
    
    # Mock LLM to return "NO" for intervention
    agent.llm = AsyncMock()
    agent.llm.ask.return_value = MagicMock(content="NO, the agent can proceed.")

    # Call with deeply_stuck=False
    result = await agent._verify_intervention_needed(
        [Message.assistant_message("Normal message")], deeply_stuck=False
    )

    # Should not recommend intervention
    assert result is False


async def test_handle_stuck_state_with_intervention_needed():
    """Test handle_stuck_state with intervention needed."""
    agent = MockTestAgent(name="test_agent")
    agent.llm = AsyncMock()
    
    # Mock _verify_intervention_needed to return True
    with patch.object(agent, "_verify_intervention_needed", AsyncMock(return_value=True)):
        # Mock input function to return a command
        with patch("builtins.input", return_value="/continue"):
            with patch("builtins.print"):  # Suppress print output
                # Call the method
                await agent.handle_stuck_state()

                # Verify next_step_prompt is set
                assert agent.next_step_prompt is not None
                assert agent.next_step_prompt != ""


def run_tests():
    """Run all tests."""
    # Run regular unittest suite
    unittest.main(argv=["first-arg-is-ignored"], exit=False)

    # Run all async tests manually
    print("\nRunning async tests:")
    
    run_async_test(test_parameter_handling())
    print("✓ test_parameter_handling")
    
    run_async_test(test_verify_intervention_needed_deeply_stuck())
    print("✓ test_verify_intervention_needed_deeply_stuck")
    
    run_async_test(test_verify_intervention_not_needed())
    print("✓ test_verify_intervention_not_needed")
    
    run_async_test(test_handle_stuck_state_with_intervention_needed())
    print("✓ test_handle_stuck_state_with_intervention_needed")

    print("\nAll tests completed!")


if __name__ == "__main__":
    run_tests()
