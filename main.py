import asyncio

from app.agent.manus import Manus
from app.logger import logger


async def read_multiline_input():
    """
    读取用户的多行输入，直到用户输入'---'结束或'exit'退出

    Returns:
        str: 用户输入的多行文本，如果用户输入'exit'则返回'exit'
    """
    lines = []
    logger.info("请输入您的指令 (可以输入多行，输入'---'结束，或输入'exit'退出):")
    print("> ", end="", flush=True)  # 显示提示符
    
    while True:
        try:
            line = input()
            if line.strip() == "---":
                break
            if line.strip().lower() == "exit":
                return "exit"
            lines.append(line)
            print("> ", end="", flush=True)  # 继续显示提示符
        except EOFError:  # 处理 Ctrl+D
            logger.info("检测到EOF，结束输入")
            break
    
    return "\n".join(lines)


async def main():
    agent = Manus()
    
    # 显示欢迎信息和使用说明
    print("\n====================================================")
    print("欢迎使用 OpenManus AI 助手!")
    print("本程序支持多行输入，请按以下方式使用：")
    print("1. 输入您的问题或指令 (可以跨多行)")
    print("2. 输入 '---' 结束输入并提交处理")
    print("3. 输入 'exit' 或按 Ctrl+C 退出程序")
    print("====================================================\n")
    
    while True:
        try:
            prompt = await read_multiline_input()
            if prompt.lower() == "exit":
                logger.info("Goodbye!")
                break
            
            if not prompt.strip():
                logger.warning("输入为空，请重新输入")
                continue
                
            logger.warning("正在处理您的请求...")
            await agent.run(prompt)
            print("\n--------------------")
            print("请输入新的指令，或输入 'exit' 退出")
            print("--------------------\n")
        except KeyboardInterrupt:
            logger.warning("检测到中断，正在退出...")
            break


if __name__ == "__main__":
    asyncio.run(main())
