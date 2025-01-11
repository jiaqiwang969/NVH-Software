# prompt_utils.py
import json
import os
from tkinter import messagebox

DEFAULT_PROMPT_DATA = {
    "system_prompt": (
        "你是NVH软件的AI助理，负责为“用户自定义信号”功能生成可执行的Python脚本。\n"
        "1) 代码仅包含信号合成、计算或特征提取相关的逻辑，必须是纯Python；\n"
        "2) result 必须和输入同维度...\n"
    ),
    "examples": []
}

def load_prompt_config(json_path="prompt_config.json"):
    """
    读取 prompt_config.json 文件:
    1) 如果文件不存在 => 创建一个默认配置文件 => 返回默认数据
    2) 如果文件存在，但读取失败 => 覆盖写入默认数据 => 返回默认数据
    3) 否则返回文件中的数据(并确保有 system_prompt / examples字段)
    """
    if not os.path.exists(json_path):
        # 文件不存在 => 写入默认
        save_prompt_config(json_path, DEFAULT_PROMPT_DATA)
        return DEFAULT_PROMPT_DATA.copy()

    # 如果存在, 就尝试读取
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 确保至少包含这两个字段
        if "system_prompt" not in data:
            data["system_prompt"] = DEFAULT_PROMPT_DATA["system_prompt"]
        if "examples" not in data:
            data["examples"] = []
        return data
    except Exception as e:
        messagebox.showerror(
            "错误",
            f"读取 {json_path} 时发生异常: {e}\n即将重置为默认配置。"
        )
        save_prompt_config(json_path, DEFAULT_PROMPT_DATA)
        return DEFAULT_PROMPT_DATA.copy()

def save_prompt_config(json_path, data):
    """
    将 data 写入指定的 JSON 文件；若写入出错，会弹框报错。
    data 的格式应当包含 "system_prompt" 和 "examples" 两个字段
    """
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        messagebox.showerror("错误", f"保存到 {json_path} 时发生异常: {e}")
