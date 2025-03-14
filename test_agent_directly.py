import asyncio
import json
from app.agent.manus import Manus
from app.logger import logger

async def test_agent():
    """Test the agent directly without going through the API."""
    prompt = "List the files in the current directory"
    
    print(f"Testing agent with prompt: '{prompt}'")
    
    agent = Manus()
    try:
        logger.warning("Processing your request...")
        result = await agent.run(prompt)
        logger.info("Request processing completed.")
        
        print("\n=== Agent Result ===")
        print(json.dumps(result, indent=2))
        
        # Check for thought and action fields
        for i, step in enumerate(result):
            print(f"\nStep {i+1}:")
            for field in ["step", "thought", "action", "command", "error", "url", "termination_reason"]:
                if field in step and step[field] is not None:
                    if field in ["thought", "action"]:
                        # Truncate long thought/action content for display
                        content = step[field]
                        if content and len(content) > 100:
                            content = content[:97] + "..."
                        print(f"  {field}: {content}")
                    else:
                        print(f"  {field}: {step[field]}")
    except Exception as e:
        print(f"Exception: {str(e)}")

if __name__ == "__main__":
    print("Testing the agent directly...")
    asyncio.run(test_agent())