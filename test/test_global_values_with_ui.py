#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_global_values_with_ui.py

演示:
1) GlobalValues 多级键管理(文件/通道/参数)
2) Tkinter 界面，交互式地增/改/查 全局参数
3) 在“用户自定义函数”中读写 GlobalValues 示例

可直接运行: python test_global_values_with_ui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

class GlobalValues:
    """
    利用多级键 (file_name, channel_name, param_key) 管理自定义参数。
    file_name=None => "__GLOBAL__"
    channel_name=None => "__ALL__"
    """
    def __init__(self):
        self._values = {}

    def set_value(self, file_name: str, channel_name: str, param_key: str, value):
        fkey = file_name if file_name else "__GLOBAL__"
        ckey = channel_name if channel_name else "__ALL__"
        self._values[(fkey, ckey, param_key)] = value

    def get_value(self, file_name: str, channel_name: str, param_key: str, default=None):
        fkey = file_name if file_name else "__GLOBAL__"
        ckey = channel_name if channel_name else "__ALL__"
        return self._values.get((fkey, ckey, param_key), default)

    def list_all_params(self):
        """ 返回所有存储条目的可读列表(字符串). """
        lines = []
        for (fkey, ckey, pkey), val in self._values.items():
            lines.append(f"({fkey}, {ckey}, {pkey}) => {val}")
        return lines

# ---------------- 用户自定义函数示例 ----------------
def user_defined_function(global_values: GlobalValues):
    """
    一个模拟“用户自定义脚本”或函数的示例，在其中读取/写入 GlobalValues.
    这里示范: 如果 "FileA, ch0" 下有 param_key="freq_to_remove" 则执行一些逻辑.
    """
    # 假设我们想获取 (FileA, ch0, "freq_to_remove")
    freq_list = global_values.get_value("FileA", "ch0", "freq_to_remove", default=[])
    # 做点演示:
    if freq_list:
        return f"【用户自定义函数】从(FileA,ch0)读到 freq_to_remove={freq_list}, 将进行去频计算..."
    else:
        return "【用户自定义函数】(FileA,ch0) 未定义 freq_to_remove, 无操作."


class TestGlobalValuesUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GlobalValues 测试示例")

        # 初始化 GlobalValues
        self.gv = GlobalValues()

        # 模拟有两个文件, 各有 2 通道
        self.file_options = ["<Global>", "FileA", "FileB"]
        self.channel_options = ["<All>", "ch0", "ch1"]

        # 建立 UI 控件
        self._create_widgets()

    def _create_widgets(self):
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # 1) 文件选择
        tk.Label(top_frame, text="File:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.file_var = tk.StringVar(value="<Global>")  # 默认全局
        file_combo = ttk.Combobox(top_frame, textvariable=self.file_var, values=self.file_options, width=12)
        file_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 2) 通道选择
        tk.Label(top_frame, text="Channel:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        self.ch_var = tk.StringVar(value="<All>")
        ch_combo = ttk.Combobox(top_frame, textvariable=self.ch_var, values=self.channel_options, width=8)
        ch_combo.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        # 3) 参数名
        tk.Label(top_frame, text="ParamKey:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.param_key_var = tk.StringVar(value="freq_to_remove")
        tk.Entry(top_frame, textvariable=self.param_key_var, width=15).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # 4) 参数值
        tk.Label(top_frame, text="ParamValue:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.E)
        self.param_value_var = tk.StringVar(value="50, 120")
        tk.Entry(top_frame, textvariable=self.param_value_var, width=15).grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        # 5) 按钮
        btn_frame = tk.Frame(top_frame)
        btn_frame.grid(row=0, column=4, rowspan=2, padx=20, pady=5)

        tk.Button(btn_frame, text="Set Param", command=self.on_set_param, width=10).pack(pady=5)
        tk.Button(btn_frame, text="Get Param", command=self.on_get_param, width=10).pack(pady=5)
        tk.Button(btn_frame, text="List All", command=self.on_list_all, width=10).pack(pady=5)

        # 结果显示
        self.result_box = scrolledtext.ScrolledText(self, width=80, height=12, font=("Consolas", 10))
        self.result_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 增加一个“运行用户自定义函数”示例
        userfunc_btn = tk.Button(self, text="Run User-Defined Function", command=self.on_run_user_function)
        userfunc_btn.pack(pady=5)

    def on_set_param(self):
        """将用户输入的 ParamKey, ParamValue 写入 GlobalValues."""
        file_name = None if self.file_var.get() == "<Global>" else self.file_var.get()
        ch_name = None if self.ch_var.get() == "<All>" else self.ch_var.get()
        pkey = self.param_key_var.get().strip()
        pval_str = self.param_value_var.get().strip()

        if not pkey:
            messagebox.showwarning("警告", "请先输入 ParamKey")
            return

        # 这里简单处理: 如果用户输入形如 "50, 120", 则解析为 [50.0, 120.0] 向量
        # 如果只是"100", 则float(100.0) 或 int(100)
        # 也可更复杂的解析
        value_final = pval_str
        if "," in pval_str:
            # 尝试解析成 float list
            try:
                parts = pval_str.split(",")
                value_final = [float(x.strip()) for x in parts]
            except ValueError:
                pass
        else:
            # 尝试解析单个数
            try:
                val_num = float(pval_str)
                value_final = val_num
            except ValueError:
                # 就保留原字符串
                pass

        self.gv.set_value(file_name, ch_name, pkey, value_final)
        self._append_text(f"[Set] (file={file_name}, ch={ch_name}, pkey={pkey}) => {value_final}\n")

    def on_get_param(self):
        """从 GlobalValues 读取 ParamKey, 并显示."""
        file_name = None if self.file_var.get() == "<Global>" else self.file_var.get()
        ch_name = None if self.ch_var.get() == "<All>" else self.ch_var.get()
        pkey = self.param_key_var.get().strip()
        if not pkey:
            messagebox.showwarning("警告", "请先输入 ParamKey")
            return

        val = self.gv.get_value(file_name, ch_name, pkey, default="(None)")
        self._append_text(f"[Get] (file={file_name}, ch={ch_name}, pkey={pkey}) => {val}\n")

    def on_list_all(self):
        """列出当前所有参数."""
        lines = self.gv.list_all_params()
        self._append_text("=== List All GlobalValues ===\n")
        for line in lines:
            self._append_text("  " + line + "\n")
        self._append_text("=== End ===\n")

    def on_run_user_function(self):
        """示例：调用 user_defined_function(gv) 并显示结果."""
        result_str = user_defined_function(self.gv)
        self._append_text(f"{result_str}\n")

    def _append_text(self, text):
        self.result_box.insert(tk.END, text)
        self.result_box.see(tk.END)

def main():
    app = TestGlobalValuesUI()
    app.mainloop()

if __name__ == "__main__":
    main()
