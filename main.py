# main.py

import os
from dotenv import load_dotenv, find_dotenv
from controller.app_controller import AppController

def main():
    # 1) 自动查找并加载 .env 文件 (与 main.py 同级)
    dotenv_path = find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path)
    # 不打印 API 密钥，避免泄露

    # 2) 之后初始化 AppController 并启动
    app = AppController()
    app.run()

if __name__ == "__main__":
    main()
