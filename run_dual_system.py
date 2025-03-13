import asyncio

from app.agent.dual_system import DualSystemAgent
from app.logger import logger


async def main():
    """Run the DualSystemAgent interactively."""
    logger.info("Starting DualSystemAgent - Thinking Fast and Slow")
    
    agent = DualSystemAgent()
    
    print("\n🧠 DualSystemAgent - Implementing 'Thinking Fast and Slow' principles")
    print("Type 'exit' or 'quit' to end the session\n")
    
    while True:
        try:
            prompt = input("Enter your prompt: ")
            prompt_lower = prompt.lower()
            
            if prompt_lower in ["exit", "quit"]:
                logger.info("Ending session")
                print("Goodbye!")
                break
                
            if not prompt.strip():
                logger.warning("Skipping empty prompt.")
                continue
                
            logger.info(f"Processing: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
            print("\nThinking...\n")
            
            result = await agent.run(prompt)
            print(f"\n{result}\n")
            
        except KeyboardInterrupt:
            logger.warning("Session interrupted")
            print("\nSession ended. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main()) 