"""
Unit tests for the BaseAgent class, specifically testing the stuck state detection
and intervention functionality.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.base import BaseAgent
from app.llm import LLM
from app.schema import AgentState, Memory, Message


class TestAgent(BaseAgent):
    """Test implementation of BaseAgent for testing purposes."""
    
    name = "test_agent"
    
    async def think(self) -> bool:
        return True
        
    async def act(self) -> str:
        return "Test action"
        
    async def observe(self, result: str) -> None:
        pass
        
    async def step(self) -> str:
        """Implement required step method"""
        return "Test step executed"


@pytest.fixture
def test_agent():
    """Create a test agent instance for testing."""
    agent = TestAgent(name="test_agent")
    agent.llm = AsyncMock(spec=LLM)
    return agent


class TestStuckStateDetection:
    """Tests for stuck state detection functionality."""
    
    def test_is_stuck_with_no_repetition(self, test_agent):
        """Test is_stuck returns False when no repetition."""
        # Add different messages
        test_agent.memory.messages = [
            Message.assistant_message("Message 1"),
            Message.assistant_message("Message 2"),
            Message.assistant_message("Message 3"),
        ]
        
        assert not test_agent.is_stuck()
    
    def test_is_stuck_with_repetition(self, test_agent):
        """Test is_stuck returns True when repetitive content detected."""
        # Add similar messages
        test_agent.memory.messages = [
            Message.assistant_message("I need more information about that."),
            Message.assistant_message("I still need more information about that."),
            Message.assistant_message("Could you provide more information about that?"),
        ]
        
        assert test_agent.is_stuck()
    
    def test_deeply_stuck_detection(self, test_agent):
        """Test _is_deeply_stuck returns True with high repetition."""
        # Setting up mock for deeply stuck detection
        with patch.object(test_agent, 'is_stuck') as mock_is_stuck:
            # Create a side effect that counts calls
            call_count = 0
            def side_effect():
                nonlocal call_count
                call_count += 1
                # Return True after 3 calls
                return call_count >= 3
            
            mock_is_stuck.side_effect = side_effect
            
            # First calls should be False
            assert not test_agent._is_deeply_stuck()
            assert not test_agent._is_deeply_stuck()
            
            # Third call should be True
            assert test_agent._is_deeply_stuck()


@pytest.mark.asyncio
class TestStuckStateHandling:
    """Tests for stuck state handling and intervention."""
    
    async def test_verify_intervention_needed_deeply_stuck(self, test_agent):
        """Test LLM verification when deeply stuck."""
        # Mock LLM to return "YES" for intervention
        test_agent.llm.ask.return_value = MagicMock(content="YES, user intervention is needed.")
        
        # Call with deeply_stuck=True
        result = await test_agent._verify_intervention_needed(
            [Message.assistant_message("Repetitive message")], 
            deeply_stuck=True
        )
        
        # Should recommend intervention
        assert result is True
        # LLM should have been called
        assert test_agent.llm.ask.called
    
    async def test_verify_intervention_not_needed(self, test_agent):
        """Test LLM verification when not truly stuck."""
        # Mock LLM to return "NO" for intervention
        test_agent.llm.ask.return_value = MagicMock(content="NO, the agent can proceed.")
        
        # Call with deeply_stuck=False
        result = await test_agent._verify_intervention_needed(
            [Message.assistant_message("Some message")], 
            deeply_stuck=False
        )
        
        # Should not recommend intervention
        assert result is False
        # LLM should have been called
        assert test_agent.llm.ask.called
    
    async def test_handle_stuck_state_with_intervention_needed(self, test_agent):
        """Test handle_stuck_state when intervention is needed."""
        # Mock _verify_intervention_needed to return True
        with patch.object(test_agent, '_verify_intervention_needed', AsyncMock(return_value=True)):
            # Mock input function to return a command
            with patch('builtins.input', return_value="/continue"):
                with patch('builtins.print') as mock_print:
                    # Call the method
                    await test_agent.handle_stuck_state()
                    
                    # Check that the right messages were printed
                    assert any("agent requires your guidance" in str(call) for call in mock_print.call_args_list)
                    # Check that next_step_prompt was updated
                    assert "default values" in test_agent.next_step_prompt
    
    async def test_handle_stuck_state_no_intervention_needed(self, test_agent):
        """Test handle_stuck_state when intervention is not needed."""
        # Mock _verify_intervention_needed to return False
        with patch.object(test_agent, '_verify_intervention_needed', AsyncMock(return_value=False)):
            # Call the method
            await test_agent.handle_stuck_state()
            
            # Check that next_step_prompt contains guidance but didn't request intervention
            assert test_agent.next_step_prompt is not None
            assert "different approach" in test_agent.next_step_prompt
    
    async def test_special_command_handling(self, test_agent):
        """Test handling of special commands."""
        # Test cases for different command types
        test_cases = [
            # Command, expected phrase in next_step_prompt
            ("/continue", "default values"),
            ("/reset", "fresh approach"),
            ("/num_results=5", "num_results=5"),
            ("regular input", "user's message")
        ]
        
        # Mock _verify_intervention_needed to return True
        with patch.object(test_agent, '_verify_intervention_needed', AsyncMock(return_value=True)):
            for command, expected in test_cases:
                # Reset next_step_prompt
                test_agent.next_step_prompt = ""
                
                # Mock input function to return the command
                with patch('builtins.input', return_value=command):
                    with patch('builtins.print'):
                        # Call the method
                        await test_agent.handle_stuck_state()
                        
                        # Check that next_step_prompt was updated appropriately
                        assert expected in test_agent.next_step_prompt


@pytest.mark.asyncio
class TestAgentRunIntegration:
    """Tests for the full agent run loop with stuck detection."""
    
    async def test_run_with_stuck_detection(self, test_agent):
        """Test that run method properly calls stuck detection and handling."""
        # Set up the agent for testing
        test_agent.state = AgentState.IDLE
        
        # Mock step method to return something predictable
        test_agent.step = AsyncMock(return_value="Step result")
        
        # Make is_stuck return True on second call
        original_is_stuck = test_agent.is_stuck
        call_count = 0
        def mock_is_stuck():
            nonlocal call_count
            call_count += 1
            return call_count == 2
        test_agent.is_stuck = mock_is_stuck
        
        # Mock handle_stuck_state
        test_agent.handle_stuck_state = AsyncMock()
        
        # Run the agent
        result = await test_agent.run("Test request")
        
        # Verify handle_stuck_state was called
        test_agent.handle_stuck_state.assert_called_once()
        
        # Restore original is_stuck
        test_agent.is_stuck = original_is_stuck
        
        # Verify agent executed steps
        assert "Step" in result
