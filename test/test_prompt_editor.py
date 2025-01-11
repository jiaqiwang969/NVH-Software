# test_prompt_editor.py

import tkinter as tk
from prompt_editor import PromptEditorDialog

def main():
    root = tk.Tk()
    root.title("Prompt Editor 测试窗口")

    def open_editor():
        editor = PromptEditorDialog(root, json_path="examples_prompt.json")
        editor.grab_set()  # 模态对话框
        root.wait_window(editor)

    btn = tk.Button(root, text="打开 Prompt 编辑器", command=open_editor)
    btn.pack(padx=50, pady=30)

    root.mainloop()

if __name__ == "__main__":
    main()
