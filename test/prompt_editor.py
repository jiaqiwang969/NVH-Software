# prompt_editor.py

import tkinter as tk
import tkinter.ttk as ttk
import json
import os
from tkinter import filedialog, messagebox, scrolledtext

class PromptEditorDialog(tk.Toplevel):
    """
    用于编辑 examples_prompt.json 中的多个示例。
    特别处理: possible_output 为一个字符串数组 (多行代码)。
    """
    def __init__(self, parent, json_path="examples_prompt.json"):
        super().__init__(parent)
        self.title("Prompt 编辑器")
        self.json_path = json_path
        self.examples_data = {}  # 存储解析后的JSON

        # 加载 JSON
        self._load_json()

        # UI 布局
        self._create_widgets()

    def _load_json(self):
        """
        读取 JSON 文件到 self.examples_data
        格式形如: { "examples": [ {...}, {...}, ... ] }
        """
        if not os.path.exists(self.json_path):
            self.examples_data = {"examples": []}
            return
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                self.examples_data = json.load(f)
        except Exception as e:
            messagebox.showerror("错误", f"读取JSON失败: {e}")
            self.examples_data = {"examples": []}


    def _create_widgets(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧：示例列表
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(left_frame, text="示例列表:").pack(anchor=tk.W)
        self.examples_listbox = tk.Listbox(left_frame, height=20, width=30)
        self.examples_listbox.pack(fill=tk.Y, expand=True)
        self.examples_listbox.bind("<<ListboxSelect>>", self.on_select_example)

        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="新增示例", command=self.on_add_example).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="删除示例", command=self.on_delete_example).pack(side=tk.LEFT, padx=5)

        # 右侧：示例编辑区域
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # example_id
        tk.Label(right_frame, text="example_id:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=3)
        self.id_var = tk.StringVar()
        self.id_entry = tk.Entry(right_frame, textvariable=self.id_var)
        self.id_entry.grid(row=0, column=1, sticky=tk.W)

        # description
        tk.Label(right_frame, text="description:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=3)
        self.desc_var = tk.StringVar()
        self.desc_entry = tk.Entry(right_frame, textvariable=self.desc_var, width=50)
        self.desc_entry.grid(row=1, column=1, sticky=tk.W)

        # sample_prompt
        tk.Label(right_frame, text="sample_prompt:").grid(row=2, column=0, sticky=tk.NE, padx=5, pady=3)
        self.sample_prompt_text = scrolledtext.ScrolledText(right_frame, width=60, height=5)
        self.sample_prompt_text.grid(row=2, column=1, sticky=tk.W)

        # possible_output
        tk.Label(right_frame, text="possible_output: (多行代码)").grid(row=3, column=0, sticky=tk.NE, padx=5, pady=3)
        self.possible_output_text = scrolledtext.ScrolledText(right_frame, width=60, height=10)
        self.possible_output_text.grid(row=3, column=1, sticky=tk.W)

        # 操作按钮
        action_frame = tk.Frame(right_frame)
        action_frame.grid(row=4, column=1, sticky=tk.E, pady=5)

        tk.Button(action_frame, text="保存当前修改", command=self.on_save_changes).pack(side=tk.LEFT, padx=5)

        # 初始化列表
        self.refresh_listbox()

    def refresh_listbox(self):
        self.examples_listbox.delete(0, tk.END)
        for ex in self.examples_data.get("examples", []):
            txt = f"ID={ex.get('example_id','?')} | {ex.get('description','')}"
            self.examples_listbox.insert(tk.END, txt)

    def on_select_example(self, event):
        """
        选中某个示例后，在右侧显示其详细信息
        其中 possible_output 数组 -> 多行文本
        """
        sel = self.examples_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        ex = self.examples_data["examples"][idx]

        self.id_var.set(str(ex.get("example_id", "")))
        self.desc_var.set(ex.get("description", ""))
        self.sample_prompt_text.delete("1.0", tk.END)
        self.sample_prompt_text.insert("1.0", ex.get("sample_prompt",""))

        # 处理 possible_output 数组
        self.possible_output_text.delete("1.0", tk.END)
        code_lines = ex.get("possible_output", [])
        # 将行数组合并成多行字符串
        joined_code = "\n".join(code_lines)
        self.possible_output_text.insert("1.0", joined_code)

    def on_add_example(self):
        new_ex = {
            "example_id": 999,
            "description": "新示例",
            "sample_prompt": "示例的sample_prompt",
            # 这里的代码内容用数组形式
            "possible_output": [
                "# 在这里粘贴多行代码",
                "# 每个元素代表一行"
            ]
        }
        self.examples_data["examples"].append(new_ex)
        self.refresh_listbox()
        self.examples_listbox.select_set(tk.END)
        self.on_select_example(None)

    def on_delete_example(self):
        sel = self.examples_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择要删除的示例！")
            return
        idx = sel[0]
        confirm = messagebox.askyesno("确认删除","确定要删除该示例吗？")
        if confirm:
            del self.examples_data["examples"][idx]
            self.refresh_listbox()
            self.clear_edit_fields()

    def clear_edit_fields(self):
        self.id_var.set("")
        self.desc_var.set("")
        self.sample_prompt_text.delete("1.0", tk.END)
        self.possible_output_text.delete("1.0", tk.END)

    def on_save_changes(self):
        sel = self.examples_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示","请先选中一个示例再保存。")
            return
        idx = sel[0]
        ex = self.examples_data["examples"][idx]

        # 回写编辑内容
        try:
            ex["example_id"] = int(self.id_var.get())
        except ValueError:
            ex["example_id"] = self.id_var.get()

        ex["description"] = self.desc_var.get()
        ex["sample_prompt"] = self.sample_prompt_text.get("1.0", tk.END).rstrip("\n")

        # 将多行文本拆分为行数组
        code_str = self.possible_output_text.get("1.0", tk.END).rstrip("\n")
        lines = code_str.split("\n")
        ex["possible_output"] = lines

        # 更新列表显示
        self.refresh_listbox()
        self.examples_listbox.select_set(idx)
        messagebox.showinfo("提示","修改已保存(内存)，如需落盘请点击“保存到JSON文件”")
