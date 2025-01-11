# view/dialogs.py
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox, scrolledtext
from model.data_models import SensorSettings
import pyaudio
import wave
import os

import threading
import aisuite as ai

import traceback
from openai import OpenAI  # 新API
import json
from .prompt_utils import load_prompt_config, save_prompt_config, DEFAULT_PROMPT_DATA

import datetime  # 确保导入 datetime
import time
from pydub import AudioSegment  # 如果需要使用 pydub


class UserDefineDialog(tk.Toplevel):
    """
    左侧：用户自定义信号(通道选择 + code_text + 导入/导出脚本 + 频谱/时域分析按钮 + “确定”按钮)
    右侧：AI Agent (System prompt, 聊天记录, 录音, 对比模式, 以及“导入/导出聊天记录”按钮)

    1) 没有单独的“最终脚本可编辑”区域；AI 生成的脚本直接写入左侧 code_text。
    2) 新增“导入聊天记录”/“导出聊天记录”按钮，可以保存/载入 chat_history_1/2。
    3) “完成(脚本)”按钮改成“应用AI脚本”，将对比模式中选定的脚本写到左侧 code_text。
    4) 窗口保持打开，可并行做频谱/时域等测试，不退出。
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.controller = parent.controller  # 保持原接口
        self.title("用户自定义信号 + AI Agent (合并窗口)")

        # 录音相关
        self.is_recording = False
        self.frames = []
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100

        # AI相关
        self.ai_client = ai.Client()        
        self.openai_client = OpenAI()       # Whisper 用

        self.model_list = [
            # GPT-4o 系列
            "openai:gpt-4o",  # 最新高智能旗舰模型
            "openai:gpt-4o-mini",  # 适合快速任务的小模型
            "openai:gpt-4o-2024-11-20",  # 高智能模型的特定快照版本
            "openai:gpt-4o-mini-2024-07-18",  # 小模型的特定快照版本
            "openai:gpt-4o-realtime-preview",  # 实时模型
            "openai:gpt-4o-mini-realtime-preview",  # 实时小模型
            "openai:gpt-4o-audio-preview",  # 音频支持模型

            # GPT-4 Turbo 和 GPT-3.5 Turbo 系列
            "openai:gpt-4-turbo",  # GPT-4 的更快版本
            "openai:gpt-4-turbo-preview",  # GPT-4 Turbo 的预览版本
            "openai:gpt-3.5-turbo",  # GPT-3.5 的快速版本
            "openai:gpt-3.5-turbo-0125",  # GPT-3.5 Turbo 的最新快照

            # o1 和 o1-mini 系列
            "openai:o1",  # 强化学习的复杂推理模型
            "openai:o1-mini",  # 快速的强化学习推理模型
            "openai:o1-preview",  # o1 的预览模型

            # Whisper 系列
            "openai:whisper-1",  # 通用语音识别模型

            # DALL·E 系列
            "openai:dall-e-3",  # 最新的图像生成模型
            "openai:dall-e-2",  # 之前版本的图像生成模型

            # TTS (Text to Speech)
            "openai:tts-1",  # 实时文本转语音模型
            "openai:tts-1-hd",  # 高质量文本转语音模型

            # Embeddings (嵌入向量模型)
            "openai:text-embedding-3-large",  # 最强嵌入向量模型
            "openai:text-embedding-3-small",  # 性能优化的小嵌入向量模型

            # Moderation (内容审核模型)
            "openai:omni-moderation-latest",  # 最新多模态审核模型
            "openai:text-moderation-latest",  # 文本审核模型
        ]

        self.use_compare_mode = tk.BooleanVar(value=False)
        self.model_var_1 = tk.StringVar(value=self.model_list[0])
        self.model_var_2 = tk.StringVar(value=self.model_list[1] if len(self.model_list) > 1 else "")
        self.final_model_choice_var = tk.StringVar(value="model1")

        # 分别存储模型1/2的对话上下文
        self.chat_history_1 = []
        self.chat_history_2 = []

        # 读取并合并 prompt (system_prompt + examples)
        self.merged_prompt = self.load_and_merge_prompt("prompt_config.json")

        self._create_widgets()

    def _create_widgets(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧：用户自定义信号
        self.left_frame = tk.Frame(main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._create_left_user_define()

        # 右侧：AI agent
        self.right_frame = tk.Frame(main_frame)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self._create_right_ai_agent()


    # -------------------------------------------------------------------------
    # 左侧：用户自定义信号区
    # -------------------------------------------------------------------------
    def _create_left_user_define(self):
        tk.Label(self.left_frame, text="请选择要使用的通道(可多选):").pack(anchor=tk.W, padx=5, pady=5)

        channel_frame = tk.Frame(self.left_frame)
        channel_frame.pack(fill=tk.X, padx=10, pady=5)
        scrollbar = tk.Scrollbar(channel_frame, orient=tk.VERTICAL)
        self.channel_listbox = tk.Listbox(
            channel_frame, selectmode=tk.MULTIPLE,
            yscrollcommand=scrollbar.set, height=8, width=40
        )
        scrollbar.config(command=self.channel_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.channel_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 将可用通道插入
        for ch_name in self.controller.view.channel_options:
            self.channel_listbox.insert(tk.END, ch_name)

        # 脚本编辑区
        tk.Label(self.left_frame, text="在此处编写或粘贴Python脚本(确保最终result=...)："
                 ).pack(anchor=tk.W, padx=5, pady=5)
        self.code_text = scrolledtext.ScrolledText(self.left_frame, width=60, height=12)
        self.code_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        example_code = (
            "# 示例:\n"
            "# import numpy as np\n"
            "# # ch0, ch1, ..., t -> result\n"
            "# result = ch0 + ch1\n"
        )
        self.code_text.insert("1.0", example_code)

        btn_frame = tk.Frame(self.left_frame)
        btn_frame.pack(anchor=tk.CENTER, pady=5)
        tk.Button(btn_frame, text="导入脚本", command=self.import_code).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="导出脚本", command=self.export_code).pack(side=tk.LEFT, padx=5)

        tk.Label(self.left_frame, text="新信号名称:").pack(anchor=tk.W, padx=5, pady=5)
        self.new_signal_name_var = tk.StringVar(value="Custom1")
        tk.Entry(self.left_frame, textvariable=self.new_signal_name_var, width=30
                ).pack(anchor=tk.W, padx=5, pady=5)

        # 底部按钮：确定 + 取消
        action_frame = tk.Frame(self.left_frame)
        action_frame.pack(pady=10)

        tk.Button(action_frame, text="确定(创建信号)", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="取消", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def import_code(self):
        path = filedialog.askopenfilename(
            title="导入Python代码",
            filetypes=[("Python 文件","*.py"),("文本文件","*.txt"),("所有文件","*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding='utf-8') as f:
                content = f.read()
            self.code_text.delete("1.0", tk.END)
            self.code_text.insert("1.0", content)
        except Exception as e:
            messagebox.showerror("错误", f"导入脚本失败:{e}")

    def export_code(self):
        path = filedialog.asksaveasfilename(
            title="导出Python代码",
            defaultextension=".py",
            filetypes=[("Python 文件","*.py"),("文本文件","*.txt"),("所有文件","*.*")]
        )
        if not path:
            return
        try:
            code_str = self.code_text.get("1.0", tk.END)
            with open(path, "w", encoding='utf-8') as f:
                f.write(code_str)
            messagebox.showinfo("成功","脚本已成功导出!")
        except Exception as e:
            messagebox.showerror("错误", f"导出脚本失败:{e}")

    def on_ok(self):
        """创建/测试自定义信号，但不关闭窗口"""
        code_str = self.code_text.get("1.0", tk.END).strip()
        if not code_str:
            messagebox.showwarning("警告", "脚本不能为空!")
            return

        indices = self.channel_listbox.curselection()
        if not indices:
            messagebox.showwarning("警告","请至少选择一个通道!")
            return
        selected_channels = [self.channel_listbox.get(i) for i in indices]

        new_name = self.new_signal_name_var.get().strip()
        if not new_name:
            messagebox.showwarning("警告","请输入新信号名称!")
            return

        try:
            self.controller.create_user_defined_signal(code_str, selected_channels, new_name)
        except Exception as e:
            messagebox.showerror("错误",f"脚本执行出错:{e}")


    # -------------------------------------------------------------------------
    # 右侧：AI Agent 区
    # -------------------------------------------------------------------------
    def _create_right_ai_agent(self):
        top_frame = tk.Frame(self.right_frame)
        top_frame.pack(fill=tk.X, pady=5)

        compare_check = tk.Checkbutton(
            top_frame, text="对比模式",
            variable=self.use_compare_mode,
            command=self.on_toggle_compare
        )
        compare_check.pack(side=tk.LEFT, padx=5)

        tk.Label(top_frame, text="模型1:").pack(side=tk.LEFT)
        self.model_combo_1 = ttk.Combobox(
            top_frame, values=self.model_list,
            textvariable=self.model_var_1, state="readonly", width=22
        )
        self.model_combo_1.pack(side=tk.LEFT, padx=5)

        self.model2_label = tk.Label(top_frame, text="模型2:")
        self.model2_label.pack(side=tk.LEFT)
        self.model_combo_2 = ttk.Combobox(
            top_frame, values=self.model_list,
            textvariable=self.model_var_2, state="readonly", width=22
        )
        self.model_combo_2.pack(side=tk.LEFT, padx=5)
        if not self.use_compare_mode.get():
            self.model2_label.config(state=tk.DISABLED)
            self.model_combo_2.config(state=tk.DISABLED)

        # 编辑Prompt库按钮
        prompt_editor_btn = tk.Button(top_frame, text="编辑Prompt库", command=self.on_open_prompt_editor)
        prompt_editor_btn.pack(side=tk.LEFT, padx=15)

        # 这里改成 "Merged Prompt(可编辑)"，只显示合并后的内容
        mp_frame = tk.LabelFrame(self.right_frame, text="Merged Prompt(可编辑)")
        mp_frame.pack(fill=tk.X, padx=5, pady=5)
        self.merged_prompt_text = scrolledtext.ScrolledText(mp_frame, width=50, height=8)
        self.merged_prompt_text.pack(fill=tk.X, padx=5, pady=5)

        # 把合并后的Prompt放进 merged_prompt_text
        self.merged_prompt_text.insert("1.0", self.merged_prompt)

        # 聊天区
        chat_frame = tk.LabelFrame(self.right_frame, text="聊天记录")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_box_1 = scrolledtext.ScrolledText(chat_frame, width=40, height=15)
        self.chat_box_1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.chat_box_1.insert(tk.END, "== 模型1 对话 ==\n")

        self.chat_box_2 = scrolledtext.ScrolledText(chat_frame, width=40, height=15)
        self.chat_box_2.insert(tk.END, "== 模型2 对话 ==\n")
        if self.use_compare_mode.get():
            self.chat_box_2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 下方按钮区：录音、用户输入、导入/导出聊天记录
        bottom_frame = tk.Frame(self.right_frame)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        self.record_button = tk.Button(bottom_frame, text="开始录音", command=self.on_record_toggle)
        self.record_button.pack(side=tk.LEFT, padx=5)

        tk.Button(bottom_frame, text="导入聊天记录", command=self.import_chat_history).pack(side=tk.LEFT, padx=5)
        tk.Button(bottom_frame, text="导出聊天记录", command=self.export_chat_history).pack(side=tk.LEFT, padx=5)

        tk.Label(self.right_frame, text="用户提问:").pack(anchor=tk.W)
        self.user_entry = scrolledtext.ScrolledText(self.right_frame, width=60, height=4)
        self.user_entry.pack(fill=tk.X, padx=5, pady=5)

        # 发送/重置/对比模式选择/应用AI脚本
        btn_frame = tk.Frame(self.right_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        self.send_button = tk.Button(btn_frame, text="发送", command=self.on_send)
        self.send_button.pack(side=tk.LEFT, padx=5)

        reset_btn = tk.Button(btn_frame, text="重置对话", command=self.on_reset)
        reset_btn.pack(side=tk.LEFT, padx=5)

        self.model_choice_frame = tk.Frame(btn_frame)
        tk.Label(self.model_choice_frame, text="选用最终脚本:").pack(side=tk.LEFT)
        rb1 = tk.Radiobutton(self.model_choice_frame, text="模型1",
                            variable=self.final_model_choice_var, value="model1",
                            command=self.on_final_model_choice_changed)
        rb2 = tk.Radiobutton(self.model_choice_frame, text="模型2",
                            variable=self.final_model_choice_var, value="model2",
                            command=self.on_final_model_choice_changed)
        rb1.pack(side=tk.LEFT)
        rb2.pack(side=tk.LEFT)
        if self.use_compare_mode.get():
            self.model_choice_frame.pack(side=tk.LEFT, padx=20)

        finish_btn = tk.Button(btn_frame, text="应用AI脚本", command=self.on_finish)
        finish_btn.pack(side=tk.RIGHT, padx=5)

        # 最终脚本可编辑区域
        tk.Label(self.right_frame, text="最终脚本(可编辑):").pack(anchor=tk.W, padx=5, pady=5)
        big_font = ("Consolas", 12)
        self.ai_output_text = scrolledtext.ScrolledText(self.right_frame, width=60, height=8)
        self.ai_output_text.configure(font=big_font)
        self.ai_output_text.pack(fill=tk.BOTH, padx=5, pady=5)

    def on_open_prompt_editor(self):
        """
        打开 PromptEditorDialog 来编辑 prompt_config.json
        """
        editor = PromptEditorDialog(self, json_path="prompt_config.json")
        editor.grab_set()
        self.wait_window(editor)

        # 重新加载合并
        self.merged_prompt = self.load_and_merge_prompt("prompt_config.json")
        self.merged_prompt_text.delete("1.0", tk.END)
        self.merged_prompt_text.insert("1.0", self.merged_prompt)

    # ------------------- 聊天记录的导入/导出 -------------------
    def import_chat_history(self):
        """
        从JSON文件中读 chat_history_1/2，并显示到 chat_box_1/chat_box_2
        """
        filepath = filedialog.askopenfilename(
            title="导入聊天记录",
            filetypes=[("JSON文件","*.json"),("所有文件","*.*")]
        )
        if not filepath:
            return
        try:
            with open(filepath,"r",encoding="utf-8") as f:
                data = json.load(f)

            self.chat_history_1 = data.get("chat_history_1", [])
            self.chat_history_2 = data.get("chat_history_2", [])
            is_compare = data.get("use_compare_mode", False)
            self.use_compare_mode.set(is_compare)

            # 重绘
            self.chat_box_1.delete("1.0",tk.END)
            self.chat_box_1.insert(tk.END,"== 模型1 对话 ==\n")
            for msg in self.chat_history_1:
                role = "User" if msg["role"] == "user" else (
                    "System" if msg["role"] == "system" else "Assistant"
                )
                self.chat_box_1.insert(tk.END, f"[{role}]: {msg['content']}\n")

            self.chat_box_2.delete("1.0",tk.END)
            self.chat_box_2.insert(tk.END,"== 模型2 对话 ==\n")
            for msg in self.chat_history_2:
                role = "User" if msg["role"] == "user" else (
                    "System" if msg["role"] == "system" else "Assistant"
                )
                self.chat_box_2.insert(tk.END, f"[{role}]: {msg['content']}\n")

            self.on_toggle_compare()  # 根据 is_compare 来显示/隐藏 chat_box_2
            messagebox.showinfo("提示",f"已成功导入聊天记录: {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("错误", f"导入聊天记录失败: {e}")

    def export_chat_history(self):
        """
        将当前 chat_history_1 / chat_history_2 导出到JSON文件。
        """
        filepath = filedialog.asksaveasfilename(
            title="导出聊天记录",
            defaultextension=".json",
            filetypes=[("JSON文件","*.json"),("所有文件","*.*")]
        )
        if not filepath:
            return
        try:
            data = {
                "chat_history_1": self.chat_history_1,
                "chat_history_2": self.chat_history_2,
                "use_compare_mode": self.use_compare_mode.get(),
            }
            with open(filepath,"w",encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("提示",f"已成功导出聊天记录到: {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("错误", f"导出聊天记录失败:{e}")

    # ------------------- AI对话相关 -------------------
    def on_toggle_compare(self):
        if self.use_compare_mode.get():
            self.model2_label.config(state=tk.NORMAL)
            self.model_combo_2.config(state="readonly")
            self.chat_box_2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
            self.model_choice_frame.pack(side=tk.LEFT, padx=20)
        else:
            self.model2_label.config(state=tk.DISABLED)
            self.model_combo_2.config(state=tk.DISABLED)
            self.chat_box_2.pack_forget()
            self.model_choice_frame.pack_forget()


    def on_send(self):
        """
        发送：把 merged_prompt_text 的内容视为最终 prompt
        """
        user_msg = self.user_entry.get("1.0", tk.END).strip()
        if not user_msg:
            messagebox.showinfo("提示","请先输入提问")
            return

        # 从 merged_prompt_text 读取合并后的内容
        merged_prompt_final = self.merged_prompt_text.get("1.0", tk.END).strip()

        self.send_button.config(text="正在处理...", state=tk.DISABLED)
        self.update_idletasks()

        # history_1
        self.chat_history_1.append({"role":"system","content": merged_prompt_final})
        self.chat_history_1.append({"role":"user","content": user_msg})
        # 在 chat_box_1 显示
        self.chat_box_1.insert(tk.END,f"[User]: {user_msg}\n")

        # history_2
        if self.use_compare_mode.get():
            self.chat_history_2.append({"role":"system","content": merged_prompt_final})
            self.chat_history_2.append({"role":"user","content": user_msg})
            self.chat_box_2.insert(tk.END,f"[User]: {user_msg}\n")

        self.user_entry.delete("1.0", tk.END)

        threading.Thread(target=self._send_in_background).start()



    def _send_in_background(self):
        # 先处理模型1
        model_name1 = self.model_var_1.get().strip()
        resp_1 = self.query_llm(model_name1, self.chat_history_1)
        self.after(0, lambda: self._on_ai_done(1, model_name1, resp_1))

        # 如果对比模式，处理模型2
        if self.use_compare_mode.get():
            model_name2 = self.model_var_2.get().strip()
            resp_2 = self.query_llm(model_name2, self.chat_history_2)
            self.after(0, lambda: self._on_ai_done(2, model_name2, resp_2))

    def _on_ai_done(self, which_model, model_name, text):
        if which_model == 1:
            self.chat_history_1.append({"role":"assistant","content":text})
            self.chat_box_1.insert(tk.END,f"[{model_name}]:\n{text}\n\n")
        else:
            self.chat_history_2.append({"role":"assistant","content":text})
            self.chat_box_2.insert(tk.END,f"[{model_name}]:\n{text}\n\n")

        # 如果不是对比模式，就直接把生成的脚本更新到 self.ai_output_text
        if not self.use_compare_mode.get():
            self.ai_output_text.delete("1.0", tk.END)
            self.ai_output_text.insert("1.0", text)
            self.send_button.config(text="发送", state=tk.NORMAL)
        else:
            # 在对比模式下，需要等模型1/2都完成后，才可更新
            done1 = any(msg["role"] == "assistant" for msg in self.chat_history_1)
            done2 = any(msg["role"] == "assistant" for msg in self.chat_history_2)

            if done1 and done2:  # 两个模型都完成
                chosen = self.final_model_choice_var.get()
                if chosen == "model1":
                    code = self.get_last_assistant_text(self.chat_history_1)
                else:
                    code = self.get_last_assistant_text(self.chat_history_2)

                self.ai_output_text.delete("1.0", tk.END)
                self.ai_output_text.insert("1.0", code)

                self.send_button.config(text="发送", state=tk.NORMAL)

    def on_reset(self):
        self.chat_history_1.clear()
        self.chat_history_2.clear()
        self.chat_box_1.delete("1.0", tk.END)
        self.chat_box_1.insert(tk.END, "== 模型1 对话 ==\n")
        self.chat_box_2.delete("1.0", tk.END)
        self.chat_box_2.insert(tk.END, "== 模型2 对话 ==\n")
        self.ai_output_text.delete("1.0", tk.END)

    def on_final_model_choice_changed(self):
        """
        在对比模式下，用户切换单选时，如果想立即更新左边AI脚本也可以，
        不过这里仅更新 self.ai_output_text，真正应用还在 on_finish。
        """
        chosen = self.final_model_choice_var.get()
        if chosen == "model1":
            code = self.get_last_assistant_text(self.chat_history_1)
        else:
            code = self.get_last_assistant_text(self.chat_history_2)

        self.ai_output_text.delete("1.0", tk.END)
        if code:
            self.ai_output_text.insert("1.0", code)

    def on_finish(self):
        """
        “应用AI脚本”按钮：将当前选定模型的assistant输出，写到左侧 code_text。
        """
        chosen = self.final_model_choice_var.get()
        if chosen == "model1":
            code = self.get_last_assistant_text(self.chat_history_1)
        else:
            code = self.get_last_assistant_text(self.chat_history_2)

        if code:
            self.code_text.delete("1.0", tk.END)
            self.code_text.insert("1.0", code)
            messagebox.showinfo("提示","已将AI脚本写入左侧编辑区，可继续编辑/测试/分析。")
        else:
            messagebox.showinfo("提示","未找到可用的AI脚本(可能对话为空)")

    @staticmethod
    def get_last_assistant_text(chat_hist):
        """
        获取对话中最后一条assistant的内容
        """
        for msg in reversed(chat_hist):
            if msg["role"] == "assistant":
                return msg["content"]
        return None

    def query_llm(self, model_name, chat_history):
        """
        调用 aisuite / openai
        """
        try:
            resp = self.ai_client.chat.completions.create(
                model=model_name,
                messages=chat_history,
                temperature=0.7
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"# AI 出错: {e}\n"

    # -------------------------------------------------------------------------
    # 录音相关
    # -------------------------------------------------------------------------
    def on_record_toggle(self):
        if not self.is_recording:
            self.is_recording = True
            self.record_button.config(text="停止录音")
            self.frames = []
            threading.Thread(target=self._record_loop, daemon=True).start()
        else:
            self.is_recording = False
            self.record_button.config(text="开始录音")
            threading.Thread(target=self._process_recorded_audio, daemon=True).start()

    def _record_loop(self):
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            stream = p.open(
                format=self.FORMAT, 
                channels=self.CHANNELS,
                rate=self.RATE, 
                input=True, 
                frames_per_buffer=self.CHUNK
            )
            while self.is_recording:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                self.frames.append(data)

            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("录音错误", str(e)))

    def _process_recorded_audio(self):
        if not self.frames:
            return
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_filename = f"audio_{timestamp}.wav"
        try:
            import wave, pyaudio
            p = pyaudio.PyAudio()
            wf = wave.open(wav_filename,'wb')
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(p.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            p.terminate()
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", f"写WAV失败:{e}"))
            return

        # Whisper
        try:
            with open(wav_filename, "rb") as f:
                trans = self.openai_client.audio.transcriptions.create(
                    model="whisper-1", file=f
                )
            text = trans.text
            self.after(0, lambda: self._append_transcription(text))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("错误", f"OpenAI Audio失败:{e}"))
        finally:
            if os.path.exists(wav_filename):
                os.remove(wav_filename)
            self.frames.clear()

    def _append_transcription(self, text):
        """
        录音转写后的文本，追加到用户输入框
        """
        cur = self.user_entry.get("1.0", tk.END).strip()
        new_text = (cur + "\n" + text).strip()
        self.user_entry.delete("1.0", tk.END)
        self.user_entry.insert("1.0", new_text)

    # -------------------------------------------------------------------------
    # 合并system_prompt 与 examples
    # -------------------------------------------------------------------------
    def load_and_merge_prompt(self, config_path):
        """
        读取 prompt_config.json 后，将 system_prompt 与 examples 进行合并。
        """
        data = load_prompt_config(config_path)
        system_prompt = data.get("system_prompt", "")
        examples = data.get("examples", [])

        merged = system_prompt + "\n\nExamples:\n"
        for ex in examples:
            exid = ex.get("example_id", "?")
            sample = ex.get("sample_prompt", "")
            possible_output = ex.get("possible_output", [])
            code_block = "\n".join(possible_output)

            merged += f"{exid}.\nInput: {sample}\nOutput:\n{code_block}\n\n"
        return merged




class PromptEditorDialog(tk.Toplevel):
    """
    用于编辑 prompt_config.json，包含:
      - system_prompt
      - examples (多个示例)
    
    操作原则:
      1) 用户在示例列表中选中某一示例 -> 右侧显示其信息
      2) 用户可编辑右侧的内容 -> 点击"保存当前示例修改" 只保存到 self.prompt_data 内存
      3) system_prompt 大文本框也可随时编辑, 不需要立即保存
      4) "保存到JSON文件" -> 把目前内存中的所有修改(包括 system_prompt+examples)写回 prompt_config.json
    """

    def __init__(self, parent, json_path="prompt_config.json"):
        super().__init__(parent)
        self.title("Prompt 编辑器")
        self.json_path = json_path

        # 读取 prompt_config.json
        self.prompt_data = load_prompt_config(self.json_path)
        if "examples" not in self.prompt_data:
            self.prompt_data["examples"] = []

        self.current_example_index = None  # 当前选中的示例索引 (int或None)
        self.is_example_dirty = False      # 标记右侧示例编辑区是否有改动(未保存)

        self._create_widgets()
        self._fill_data()

    def _create_widgets(self):
        # 顶部: system_prompt
        sp_frame = tk.LabelFrame(self, text="System Prompt (可编辑)")
        sp_frame.pack(fill=tk.X, padx=5, pady=5)

        self.system_prompt_text = scrolledtext.ScrolledText(sp_frame, width=80, height=6)
        self.system_prompt_text.pack(fill=tk.X, padx=5, pady=5)

        # 中部: examples
        mid_frame = tk.Frame(self)
        mid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧列表
        left_frame = tk.Frame(mid_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, expand=False)

        tk.Label(left_frame, text="示例列表:").pack(anchor=tk.W)
        self.examples_listbox = tk.Listbox(left_frame, height=14, width=35)
        self.examples_listbox.pack(fill=tk.BOTH, expand=True)
        self.examples_listbox.bind("<<ListboxSelect>>", self.on_select_example)

        btns_frame = tk.Frame(left_frame)
        btns_frame.pack(fill=tk.X, pady=5)
        tk.Button(btns_frame, text="新增示例", command=self.on_add_example).pack(side=tk.LEFT, padx=5)
        tk.Button(btns_frame, text="删除示例", command=self.on_delete_example).pack(side=tk.LEFT, padx=5)

        # 右侧详细编辑
        right_frame = tk.Frame(mid_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        rrow = 0
        tk.Label(right_frame, text="example_id:").grid(row=rrow, column=0, sticky=tk.E, padx=5, pady=3)
        self.id_var = tk.StringVar()
        self.id_entry = tk.Entry(right_frame, textvariable=self.id_var)
        self.id_entry.grid(row=rrow, column=1, sticky=tk.W)
        rrow += 1

        tk.Label(right_frame, text="description:").grid(row=rrow, column=0, sticky=tk.E, padx=5, pady=3)
        self.desc_var = tk.StringVar()
        self.desc_entry = tk.Entry(right_frame, textvariable=self.desc_var, width=50)
        self.desc_entry.grid(row=rrow, column=1, sticky=tk.W)
        rrow += 1

        tk.Label(right_frame, text="sample_prompt:").grid(row=rrow, column=0, sticky=tk.NE, padx=5, pady=3)
        self.sample_prompt_text = scrolledtext.ScrolledText(right_frame, width=60, height=4)
        self.sample_prompt_text.grid(row=rrow, column=1, sticky=tk.W)
        rrow += 1

        tk.Label(right_frame, text="possible_output: (多行代码)").grid(row=rrow, column=0, sticky=tk.NE, padx=5, pady=3)
        self.possible_output_text = scrolledtext.ScrolledText(right_frame, width=60, height=8)
        self.possible_output_text.grid(row=rrow, column=1, sticky=tk.W)
        rrow += 1

        save_ex_btn = tk.Button(right_frame, text="保存当前示例修改", command=self.on_save_example_changes)
        save_ex_btn.grid(row=rrow, column=1, sticky=tk.E, pady=5)

        # 底部: "保存到JSON文件" 按钮
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill=tk.X, pady=5)
        tk.Button(bottom_frame, text="保存到JSON文件", command=self.on_save_json).pack(side=tk.RIGHT, padx=5)

        # 右侧编辑区焦点变化 -> 标记 is_example_dirty
        for widget in [self.id_entry, self.desc_entry, self.sample_prompt_text, self.possible_output_text]:
            widget.bind("<Key>", lambda e: self._mark_example_dirty())

    def _fill_data(self):
        # system_prompt
        cur_sp = self.prompt_data.get("system_prompt", "")
        self.system_prompt_text.insert("1.0", cur_sp)

        # 填充示例列表
        self.refresh_listbox()

        # 选中第一个(如存在)
        if self.prompt_data["examples"]:
            self.examples_listbox.select_set(0)
            self.on_select_example(None)

    def refresh_listbox(self):
        self.examples_listbox.delete(0, tk.END)
        examples = self.prompt_data.get("examples", [])
        for i, ex in enumerate(examples):
            exid = ex.get("example_id", "?")
            desc = ex.get("description", "")
            label_str = f"ID={exid} | {desc}"
            self.examples_listbox.insert(tk.END, label_str)

    def on_select_example(self, event):
        idxs = self.examples_listbox.curselection()
        if not idxs:
            return

        # 如果有正在编辑的示例尚未保存 -> 提示
        if self.is_example_dirty and (self.current_example_index is not None):
            confirm = messagebox.askyesnocancel("提示", "当前示例有未保存改动，是否先保存？")
            if confirm is None:  # 用户取消
                # 取消选中的变化，回到原先选项
                self.examples_listbox.selection_clear(0, tk.END)
                self.examples_listbox.select_set(self.current_example_index)
                return
            elif confirm is True:
                # 先保存当前示例
                self.on_save_example_changes()
            else:
                # 不保存，直接丢弃当前改动
                self.is_example_dirty = False

        idx = idxs[0]
        self.load_example_data(idx)
        self.current_example_index = idx
        self.is_example_dirty = False  # 加载后，未改动

    def load_example_data(self, idx):
        ex = self.prompt_data["examples"][idx]

        self.id_var.set(str(ex.get("example_id", "")))
        self.desc_var.set(ex.get("description", ""))

        self.sample_prompt_text.delete("1.0", tk.END)
        self.sample_prompt_text.insert("1.0", ex.get("sample_prompt", ""))

        code_lines = ex.get("possible_output", [])
        joined = "\n".join(code_lines)
        self.possible_output_text.delete("1.0", tk.END)
        self.possible_output_text.insert("1.0", joined)

    def on_add_example(self):
        new_ex = {
            "example_id": 999,
            "description": "新示例",
            "sample_prompt": "这里是sample_prompt",
            "possible_output": [
                "import numpy as np",
                "result = ch0 + ch1"
            ]
        }
        self.prompt_data["examples"].append(new_ex)
        self.refresh_listbox()

        new_idx = len(self.prompt_data["examples"]) - 1
        self.examples_listbox.select_set(new_idx)
        self.on_select_example(None)

    def on_delete_example(self):
        idxs = self.examples_listbox.curselection()
        if not idxs:
            return
        idx = idxs[0]

        confirm = messagebox.askyesno("确认", "确定要删除该示例吗？")
        if not confirm:
            return

        del self.prompt_data["examples"][idx]
        self.clear_example_fields()
        self.refresh_listbox()
        self.current_example_index = None
        self.is_example_dirty = False

    def clear_example_fields(self):
        self.id_var.set("")
        self.desc_var.set("")
        self.sample_prompt_text.delete("1.0", tk.END)
        self.possible_output_text.delete("1.0", tk.END)

    def on_save_example_changes(self):
        """
        将当前右侧编辑区内容写回 self.prompt_data["examples"][self.current_example_index]
        """
        if self.current_example_index is None or self.current_example_index >= len(self.prompt_data["examples"]):
            messagebox.showinfo("提示", "未选择任何示例，无法保存")
            return

        examples = self.prompt_data["examples"]
        ex = examples[self.current_example_index]

        # example_id
        try:
            ex_id = int(self.id_var.get())
        except ValueError:
            ex_id = self.id_var.get()

        ex["example_id"] = ex_id
        ex["description"] = self.desc_var.get()
        ex["sample_prompt"] = self.sample_prompt_text.get("1.0", tk.END).rstrip("\n")

        code_str = self.possible_output_text.get("1.0", tk.END).rstrip("\n")
        lines = code_str.split("\n")
        ex["possible_output"] = lines

        # 更新列表显示
        self.refresh_listbox()
        self.examples_listbox.select_set(self.current_example_index)

        self.is_example_dirty = False
        messagebox.showinfo("提示", "当前示例修改已保存(暂存内存)，如需落盘请点'保存到JSON文件'")

    def on_save_json(self):
        """
        将所有修改(含system_prompt+examples)写回 JSON 文件
        """
        # 先保存当前示例(若有改动)
        if self.is_example_dirty and (self.current_example_index is not None):
            self.on_save_example_changes()

        # 同步 system_prompt
        new_sp = self.system_prompt_text.get("1.0", tk.END).rstrip("\n")
        self.prompt_data["system_prompt"] = new_sp

        # 真正写盘
        try:
            save_prompt_config(self.json_path, self.prompt_data)
            messagebox.showinfo("提示", f"JSON 文件已成功保存: {os.path.abspath(self.json_path)}")
        except Exception as e:
            messagebox.showerror("错误", f"保存 JSON 文件时发生异常: {e}")

    def _mark_example_dirty(self):
        """
        当右侧编辑区内容被修改时，标记 is_example_dirty
        """
        self.is_example_dirty = True










class SensorSettingsDialog(tk.Toplevel):
    def __init__(self, num_channels, output_folder):
        super().__init__()
        self.title("设置传感器参数")
        self.num_channels = num_channels
        self.output_folder = output_folder
        self.settings = None
        self.create_widgets()

    def create_widgets(self):
        # 默认值
        default_sensitivities = {
                '加速度': 1,          # g/g
                '电涡流': 8,          # V/mm
                '力环': 0.2,          # V/N
                '脉动压力传感器': {'a': 1, 'b': 0},  # 需要输入 a 和 b
                '扭矩传感器': 0.02,   # V/Nm
                '力台传感器': 0.00667,# V/N
                '空载信号': 1,        # 灵敏度为 1
                '力锤': 1             # V/N
                }
        default_units = {
                '加速度': 'g',
                '电涡流': 'mm',
                '力环': 'N',
                '脉动压力传感器': 'pa',
                '扭矩传感器': 'Nm',
                '力台传感器': 'N',
                '空载信号': 'V',
                '力锤': 'N'
                }
        sensor_types = ['加速度', '电涡流', '力环', '脉动压力传感器', '扭矩传感器', '力台传感器', '空载信号', '力锤']

        self.sensor_type_vars = []
        self.sensitivity_vars = []
        self.name_vars = []
        self.a_vars = []
        self.b_vars = []

        self.ref_channel_var = tk.IntVar(value=-1)  # 默认不选中任何参考通道

        # 添加表头
        tk.Label(self, text="通道").grid(row=0, column=0)
        tk.Label(self, text="传感器类型").grid(row=0, column=1)
        tk.Label(self, text="灵敏度 (V/单位)").grid(row=0, column=2)
        tk.Label(self, text="通道名称").grid(row=0, column=3)
        tk.Label(self, text="参数 a").grid(row=0, column=4)
        tk.Label(self, text="参数 b").grid(row=0, column=5)
        tk.Label(self, text="参考信号").grid(row=0, column=6)

        for i in range(self.num_channels):
            sensor_type_var = tk.StringVar(value='加速度')
            sensitivity_var = tk.StringVar()
            name_var = tk.StringVar(value='加速度{}'.format(i+1))
            a_var = tk.StringVar(value='')
            b_var = tk.StringVar(value='')

            def set_defaults(i=i):
                sensor_type = self.sensor_type_vars[i].get()
                default_sensitivity = default_sensitivities.get(sensor_type, 1)
                if sensor_type == '脉动压力传感器':
                    self.sensitivity_vars[i].set('')
                    self.a_vars[i].set(str(default_sensitivity.get('a', 1)))
                    self.b_vars[i].set(str(default_sensitivity.get('b', 0)))
                else:
                    if isinstance(default_sensitivity, dict):
                        self.sensitivity_vars[i].set('')
                    else:
                        self.sensitivity_vars[i].set(str(default_sensitivity))
                    self.a_vars[i].set('')
                    self.b_vars[i].set('')
                self.name_vars[i].set('{}{}'.format(sensor_type, i+1))

            sensor_type_var.trace('w', lambda *args, i=i: set_defaults(i))

            self.sensor_type_vars.append(sensor_type_var)
            self.sensitivity_vars.append(sensitivity_var)
            self.name_vars.append(name_var)
            self.a_vars.append(a_var)
            self.b_vars.append(b_var)
            set_defaults(i)

            # 创建控件
            tk.Label(self, text="通道 {}".format(i+1)).grid(row=i+1, column=0)
            tk.OptionMenu(self, sensor_type_var, *sensor_types).grid(row=i+1, column=1)
            tk.Entry(self, textvariable=sensitivity_var).grid(row=i+1, column=2)
            tk.Entry(self, textvariable=name_var).grid(row=i+1, column=3)
            tk.Entry(self, textvariable=a_var).grid(row=i+1, column=4)
            tk.Entry(self, textvariable=b_var).grid(row=i+1, column=5)
            tk.Radiobutton(self, variable=self.ref_channel_var, value=i).grid(row=i+1, column=6)

        # 添加按钮
        button_frame = tk.Frame(self)
        button_frame.grid(row=self.num_channels+1, column=0, columnspan=7, pady=10)
        tk.Button(button_frame, text="导入参数", command=self.import_parameters).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="导出参数", command=self.export_parameters).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="确定", command=self.on_ok).pack(side=tk.LEFT, padx=5)

    def import_parameters(self):
        import json
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(title="导入参数", filetypes=[("JSON 文件", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                if len(settings_data) != self.num_channels:
                    messagebox.showwarning("警告", "导入的参数数量与当前通道数量不匹配！")
                    return
                for i, setting in enumerate(settings_data):
                    self.sensor_type_vars[i].set(setting['sensor_type'])
                    self.sensitivity_vars[i].set(setting.get('sensitivity', ''))
                    self.name_vars[i].set(setting['name'])
                    self.a_vars[i].set(str(setting.get('a', '')))
                    self.b_vars[i].set(str(setting.get('b', '')))
                    if setting.get('is_reference', False):
                        self.ref_channel_var.set(i)
            except Exception as e:
                messagebox.showerror("错误", f"导入参数时发生错误：{e}")

    def export_parameters(self):
        import json
        from tkinter import filedialog
        settings = []
        for i in range(self.num_channels):
            sensor_type = self.sensor_type_vars[i].get()
            sensitivity = self.sensitivity_vars[i].get()
            name = self.name_vars[i].get()
            a = self.a_vars[i].get()
            b = self.b_vars[i].get()
            is_reference = (i == self.ref_channel_var.get())
            setting = {
                    'sensor_type': sensor_type,
                    'sensitivity': sensitivity,
                    'name': name,
                    'a': a,
                    'b': b,
                    'is_reference': is_reference
                    }
            settings.append(setting)
        file_path = filedialog.asksaveasfilename(title="导出参数", defaultextension=".json",
                                                 filetypes=[("JSON 文件", "*.json")])
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("成功", "参数已成功导出！")
            except Exception as e:
                messagebox.showerror("错误", f"导出参数时发生错误：{e}")

    def on_ok(self):
        settings = []
        default_units = {
                '加速度': 'g',
                '电涡流': 'mm',
                '力环': 'N',
                '脉动压力传感器': 'pa',
                '扭矩传感器': 'Nm',
                '力台传感器': 'N',
                '空载信号': 'V',
                '力锤': 'N'
                }
        for i in range(self.num_channels):
            sensor_type = self.sensor_type_vars[i].get()
            sensitivity = self.sensitivity_vars[i].get()
            name = self.name_vars[i].get()
            unit = default_units[sensor_type]
            is_reference = (i == self.ref_channel_var.get())
            if sensor_type == '脉动压力传感器':
                a = self.a_vars[i].get()
                b = self.b_vars[i].get()
                try:
                    a = float(a)
                    b = float(b)
                except ValueError:
                    messagebox.showwarning("警告", "参数 a 和 b 必须是数字！")
                    return
                settings.append(SensorSettings(sensor_type, None, unit, name, a, b, is_reference))
            else:
                if sensitivity == '':
                    messagebox.showwarning("警告", "灵敏度不能为空！")
                    return
                try:
                    sensitivity = float(sensitivity)
                except ValueError:
                    messagebox.showwarning("警告", "灵敏度必须是数字！")
                    return
                settings.append(SensorSettings(sensor_type, sensitivity, unit, name, None, None, is_reference))
        self.settings = settings
        self.destroy()

