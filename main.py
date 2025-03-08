import asyncio
import argparse
from typing import Optional

from app.agent.manus import Manus
from app.flow.base import FlowType
from app.flow.flow_factory import FlowFactory
from app.logger import logger


async def run_agent(agent: Manus, prompt: str) -> Optional[str]:
    try:
        return await agent.run(prompt)
    except Exception as e:
        logger.error(f"Error running agent: {e}")
        return None

async def run_flow(agent: Manus, prompt: str) -> Optional[str]:
    try:
        flow = FlowFactory.create_flow(
            flow_type=FlowType.PLANNING,
            agents=agent,
        )
        return await flow.execute(prompt)
    except Exception as e:
        logger.error(f"Error running flow: {e}")
        return None

async def interactive_mode(mode: str = "agent"):
    agent = Manus()
    logger.info(f"Starting OpenManus in {mode} mode...")
    
    while True:
        try:
            prompt = input("Enter your prompt (or 'exit' to quit): ")
            if prompt.lower() == "exit":
                logger.info("Goodbye!")
                break
            if prompt.strip().isspace():
                logger.warning("Skipping empty prompt.")
                continue
                
            logger.info("Processing your request...")
            result = await (run_agent(agent, prompt) if mode == "agent" else run_flow(agent, prompt))
            
            if result:
                print(result)
            
        except KeyboardInterrupt:
            logger.warning("Operation interrupted by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

def main():
    parser = argparse.ArgumentParser(description="OpenManus CLI")
    parser.add_argument(
        "--mode",
        choices=["agent", "flow"],
        default="agent",
        help="Run mode: 'agent' for direct agent interaction, 'flow' for flow-based execution"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Direct prompt to process (optional, if not provided will start in interactive mode)"
    )
    
    args = parser.parse_args()
    
    if args.prompt:
        agent = Manus()
        result = asyncio.run(
            run_agent(agent, args.prompt) if args.mode == "agent" else run_flow(agent, args.prompt)
        )
        if result:
            print(result)
    else:
        asyncio.run(interactive_mode(args.mode))

if __name__ == "__main__":
    main()
