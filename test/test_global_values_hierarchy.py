#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
test_global_values_hierarchy.py

演示:
  1) GlobalValues 多级键 (file, channel, param_key)
  2) 在 GUI 中设置时, File 可选 (ALL_FILES|File1|File2), Channel 可选 (ALL_CHANNELS|ch0|ch1)
  3) 提供“回退”函数 get_value_fallback(...)：优先查 (file, channel)，否则 (file, ALL_CHANNELS)，再 (ALL_FILES, channel)，最后 (ALL_FILES, ALL_CHANNELS)
  4) 用户可通过“Test Fallback”按钮来验证“如果没设置更具体的，就会用上级的值”
  5) 还示范了一个“用户自定义脚本”函数 user_defined_function(...) 根据 freq_to_remove 做一些输出，展示如何在脚本中使用本多级逻辑
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext


# ======================== GlobalValues类 ========================
class GlobalValues:
    """
    用字典存储 (file_key, channel_key, param_key) => value.

    在本示例里, file_key 可取 'ALL_FILES', 'File1', 'File2'
               channel_key 可取 'ALL_CHANNELS', 'ch0', 'ch1'
    当然您可扩展到更多文件/通道.
    """

    def __init__(self):
        self._values = {}  # dict of {(fkey, ckey, pkey): value}

    def set_value(self, fkey: str, ckey: str, param_key: str, value):
        """设置/覆盖某个多级键对应的值."""
        self._values[(fkey, ckey, param_key)] = value

    def get_value_exact(self, fkey: str, ckey: str, param_key: str, default=None):
        """仅精确匹配 (fkey, ckey, param_key), 无回退."""
        return self._values.get((fkey, ckey, param_key), default)

    def delete_value(self, fkey: str, ckey: str, param_key: str) -> bool:
        """删除条目, 返回是否成功."""
        if (fkey, ckey, param_key) in self._values:
            del self._values[(fkey, ckey, param_key)]
            return True
        return False

    def list_all_params(self):
        """列出所有 (fkey, ckey, param_key) => value."""
        lines = []
        for (f, c, p), v in self._values.items():
            lines.append(f"({f}, {c}, {p}) => {v}")
        return sorted(lines)  # 排序一下方便看


# ================ 回退函数:从最具体到最全局 ================
def get_value_fallback(gv: GlobalValues, fkey: str, ckey: str, param_key: str, default=None):
    """
    回退链: 
       1) (fkey, ckey) 
       2) (fkey, ALL_CHANNELS)
       3) (ALL_FILES, ckey)
       4) (ALL_FILES, ALL_CHANNELS)
    若都没找到, 返回 default.

    比如 fkey='File1', ckey='ch0':
      a) 先看 (File1, ch0) 
      b) 若没则看 (File1, ALL_CHANNELS)
      c) 若还没, 看 (ALL_FILES, ch0)
      d) 最后看 (ALL_FILES, ALL_CHANNELS)
    """
    # 1) 先 (fkey, ckey)
    val = gv.get_value_exact(fkey, ckey, param_key, None)
    if val is not None:
        return val
    # 2) (fkey, ALL_CHANNELS)
    val = gv.get_value_exact(fkey, "ALL_CHANNELS", param_key, None)
    if val is not None:
        return val
    # 3) (ALL_FILES, ckey)
    val = gv.get_value_exact("ALL_FILES", ckey, param_key, None)
    if val is not None:
        return val
    # 4) (ALL_FILES, ALL_CHANNELS)
    val = gv.get_value_exact("ALL_FILES", "ALL_CHANNELS", param_key, default)
    return val


# ================ 示例：模拟“用户自定义脚本”或函数 ================
def user_defined_function(gv: GlobalValues):
    """
    这里模拟: 我们要处理 File1/ch0 的 freq_to_remove.
    用 get_value_fallback(...) 看最终拿到多少 Hz, 然后做演示输出.
    """
    freq_list = get_value_fallback(gv, "File1", "ch0", "freq_to_remove", default=[])
    if freq_list:
        return f"[UserFunc] (File1,ch0) freq_to_remove={freq_list}, 准备进行去除频率计算!"
    else:
        return "[UserFunc] (File1,ch0) 没设 freq_to_remove, 不做处理."


# ======================== GUI 主界面 ========================
class TestGlobalValuesUI(tk.Tk):
    """
    一个简单的 Tkinter UI 演示:
    - File 可选: ALL_FILES, File1, File2
    - Channel 可选: ALL_CHANNELS, ch0, ch1
    - 输入 param_key + param_value => Set Param
    - Get Param: 仅精确获取 (不走回退)
    - Test Fallback: 让用户指定 file+channel, param_key, 看最终回退值
    - List All: 查看所有条目
    - Run User-Defined Func: 演示一个脚本使用 freq_to_remove
    """

    def __init__(self):
        super().__init__()
        self.title("GlobalValues Hierarchy Test")

        # 1) 初始化 GlobalValues
        self.gv = GlobalValues()

        # 2) 预定义 File, Channel 下拉可选
        self.file_options = ["ALL_FILES", "File1", "File2"]
        self.channel_options = ["ALL_CHANNELS", "ch0", "ch1"]

        self._create_widgets()

    def _create_widgets(self):
        # ---------- 上方参数输入框 ----------
        frame_top = tk.Frame(self)
        frame_top.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # File
        tk.Label(frame_top, text="File:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.file_var = tk.StringVar(value="ALL_FILES")
        file_combo = ttk.Combobox(frame_top, textvariable=self.file_var, values=self.file_options, width=12)
        file_combo.grid(row=0, column=1, sticky=tk.W)

        # Channel
        tk.Label(frame_top, text="Channel:").grid(row=0, column=2, sticky=tk.E, padx=5, pady=5)
        self.ch_var = tk.StringVar(value="ALL_CHANNELS")
        ch_combo = ttk.Combobox(frame_top, textvariable=self.ch_var, values=self.channel_options, width=12)
        ch_combo.grid(row=0, column=3, sticky=tk.W)

        # ParamKey
        tk.Label(frame_top, text="ParamKey:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.param_key_var = tk.StringVar(value="freq_to_remove")
        tk.Entry(frame_top, textvariable=self.param_key_var, width=18).grid(row=1, column=1, sticky=tk.W)

        # ParamValue
        tk.Label(frame_top, text="ParamValue:").grid(row=1, column=2, sticky=tk.E, padx=5, pady=5)
        self.param_value_var = tk.StringVar(value="50,120")
        tk.Entry(frame_top, textvariable=self.param_value_var, width=18).grid(row=1, column=3, sticky=tk.W)

        # 按钮区域
        btn_frame = tk.Frame(frame_top)
        btn_frame.grid(row=0, column=4, rowspan=2, padx=10, pady=5)

        tk.Button(btn_frame, text="Set Param", command=self.on_set_param, width=10).pack(pady=5)
        tk.Button(btn_frame, text="Get Param", command=self.on_get_param, width=10).pack(pady=5)
        tk.Button(btn_frame, text="List All", command=self.on_list_all, width=10).pack(pady=5)

        # ---------- 中间“Test Fallback” ----------
        frame_mid = tk.LabelFrame(self, text="Test Fallback (多级回退)")
        frame_mid.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(frame_mid, text="File:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.E)
        self.fb_file_var = tk.StringVar(value="File1")
        ttk.Combobox(frame_mid, textvariable=self.fb_file_var, values=self.file_options, width=12).grid(row=0, column=1)

        tk.Label(frame_mid, text="Channel:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.E)
        self.fb_ch_var = tk.StringVar(value="ch0")
        ttk.Combobox(frame_mid, textvariable=self.fb_ch_var, values=self.channel_options, width=12).grid(row=0, column=3)

        tk.Label(frame_mid, text="ParamKey:").grid(row=0, column=4, padx=5, pady=2, sticky=tk.E)
        self.fb_param_var = tk.StringVar(value="freq_to_remove")
        tk.Entry(frame_mid, textvariable=self.fb_param_var, width=18).grid(row=0, column=5)

        tk.Button(frame_mid, text="Get w/Fallback", command=self.on_test_fallback).grid(row=0, column=6, padx=8)

        # ---------- 下方文本区 ----------
        self.text_box = scrolledtext.ScrolledText(self, width=80, height=10, font=("Consolas", 9))
        self.text_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---------- 额外: 用户自定义函数按钮 ----------
        user_btn = tk.Button(self, text="Run User-Defined Func", command=self.on_run_user_func)
        user_btn.pack(pady=5)

    # ============ 回调函数 =============
    def on_set_param(self):
        """
        用户点击“Set Param”按钮: 将 ParamValue 写进 GlobalValues(fkey, ckey, param_key).
        """
        fkey = self.file_var.get()
        ckey = self.ch_var.get()
        pkey = self.param_key_var.get().strip()
        if not pkey:
            messagebox.showwarning("警告", "ParamKey 不能为空")
            return
        val_str = self.param_value_var.get().strip()

        # 简单解析: 如果含逗号, 视作 list[float]; 否则尝试转 float, 否则保持字符串
        final_val = val_str
        if "," in val_str:
            try:
                final_val = [float(x.strip()) for x in val_str.split(",")]
            except ValueError:
                pass
        else:
            try:
                final_val = float(val_str)
            except ValueError:
                pass

        self.gv.set_value(fkey, ckey, pkey, final_val)
        self._log(f"SetParam => ({fkey}, {ckey}, {pkey}) = {final_val}")

    def on_get_param(self):
        """
        用户点击“Get Param”按钮: 仅做精确匹配, 不回退.
        """
        fkey = self.file_var.get()
        ckey = self.ch_var.get()
        pkey = self.param_key_var.get().strip()
        if not pkey:
            messagebox.showwarning("警告", "ParamKey 不能为空")
            return
        val = self.gv.get_value_exact(fkey, ckey, pkey, default="(None)")
        self._log(f"GetParam => ({fkey}, {ckey}, {pkey}) = {val}")

    def on_list_all(self):
        """显示当前所有存储"""
        lines = self.gv.list_all_params()
        self._log("\n=== List All ===")
        for line in lines:
            self._log("  " + line)
        self._log("=== End ===\n")

    def on_test_fallback(self):
        """
        用户点击 "Get w/Fallback" 按钮: 
        使用 get_value_fallback() 的多级查找.
        """
        fkey = self.fb_file_var.get()
        ckey = self.fb_ch_var.get()
        pkey = self.fb_param_var.get().strip()
        if not pkey:
            messagebox.showwarning("警告", "ParamKey 不能为空")
            return
        val = get_value_fallback(self.gv, fkey, ckey, pkey, default="(None in fallback)")
        self._log(f"Fallback => File={fkey}, Ch={ckey}, Key={pkey}, Value={val}")

    def on_run_user_func(self):
        """
        演示“用户自定义脚本”可能的操作. 
        这里只调用 user_defined_function(self.gv).
        """
        result = user_defined_function(self.gv)
        self._log(result)

    # ============ 工具函数 ============
    def _log(self, msg):
        self.text_box.insert(tk.END, msg + "\n")
        self.text_box.see(tk.END)


# ============ 入口 ============
if __name__ == "__main__":
    app = TestGlobalValuesUI()
    app.mainloop()
