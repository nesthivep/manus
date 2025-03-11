import asyncio

from app.agent.manus import Manus
from app.logger import logger

# Import the evaluation module for HoneyHive experiments
try:
    from app.evaluation import run_agent_with_experiment, init_honeyhive
    HONEYHIVE_AVAILABLE = True
    # Initialize HoneyHive at startup
    init_honeyhive()
except ImportError:
    logger.warning("HoneyHive evaluation module not available")
    HONEYHIVE_AVAILABLE = False


async def main():
    agent = Manus()
    while True:
        try:
            prompt = input("Enter your prompt (or 'exit'/'quit' to quit): ")
            prompt_lower = prompt.lower()
            if prompt_lower in ["exit", "quit"]:
                logger.info("Goodbye!")
                break
            if not prompt.strip():
                logger.warning("Skipping empty prompt.")
                continue
            
            logger.warning("Processing your request...")
            
            # Run the agent with HoneyHive experiment if available
            if HONEYHIVE_AVAILABLE:
                try:
                    # This will run the agent and create a HoneyHive experiment
                    response = await run_agent_with_experiment(prompt)
                    logger.info("HoneyHive experiment created for this query")
                except Exception as e:
                    logger.error(f"Error running agent with HoneyHive experiment: {e}")
                    # Fallback to regular agent run
                    logger.warning("Falling back to regular agent run without HoneyHive experiment")
                    response = await agent.run(prompt)
            else:
                # Regular agent run without HoneyHive
                response = await agent.run(prompt)
                
        except KeyboardInterrupt:
            logger.warning("Goodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
