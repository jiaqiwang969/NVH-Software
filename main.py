# main.py

import os
from dotenv import load_dotenv, find_dotenv
from controller.app_controller import AppController

def main():
    # 1) 自动查找并加载 .env 文件 (与 main.py 同级)
    dotenv_path = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path)
        print(f"Loaded .env from: {dotenv_path}")
    else:
        print("[警告] 未找到 .env 文件；若需要 AI 接口请自行检查！")

    # 2) 例如也可在此查看 env 变量 (调试)
    print("OPENAI_API_KEY =", os.environ.get("OPENAI_API_KEY"))
    print("ANTHROPIC_API_KEY =", os.environ.get("ANTHROPIC_API_KEY"))

    # 3) 之后初始化 AppController 并启动
    app = AppController()
    app.run()

if __name__ == "__main__":
    main()
