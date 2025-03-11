import asyncio

from app.agent.manus import Manus
from app.logger import logger


async def main():
    agent = Manus()
    while True:
        try:
            prompt = input("Enter your prompt (or 'exit'/'quit'/'q' to quit): ")
            prompt_lower = prompt.lower()
            if prompt_lower in ["exit", "quit", "q"]:
                logger.info("Goodbye!")
                break
            if not prompt.strip():
                logger.warning("Skipping empty prompt.")
                continue
            logger.warning("Processing your request...")
            await agent.run(prompt)
        except KeyboardInterrupt:
            logger.warning("Goodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())
