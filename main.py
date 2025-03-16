import asyncio

from app.agent.manus import Manus
from app.input_handler import get_user_input, is_break_command
from app.logger import logger


async def main():
    agent = Manus()
    try:
        # Get initial prompt with our special input handler
        prompt = get_user_input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        # If it's a break command, we don't need to process it initially
        # as there's no conversation to break out of yet
        if is_break_command(prompt):
            logger.warning(
                "Break command provided at start. No ongoing conversation to affect."
            )

        logger.warning("Processing your request...")
        result = await agent.run(prompt)
        logger.info("Request processing completed.")

        # If we got a result, display it
        if result:
            print("\nFinal result:\n" + result)
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")


if __name__ == "__main__":
    asyncio.run(main())
