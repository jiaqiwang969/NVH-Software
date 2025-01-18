import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from pyoma2.functions.gen import example_data
from pyoma2.setup.single import SingleSetup
from pyoma2.algorithms.fdd import FDD
from pyoma2.algorithms.ssi import SSIdat

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Example OMA Plot")
        
        self.font_prop = None  # 你可以自行设置字体，这里简化
        
        # 主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建绘图区
        self.figure_oma = plt.Figure(figsize=(8, 5))
        self.canvas_oma = FigureCanvasTkAgg(self.figure_oma, master=self.main_frame)
        self.canvas_oma.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 按钮
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        ttk.Button(btn_frame, text="绘制SSI+FDD", command=self.plot_oma_combined).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btn_frame, text="保存图像", command=self.save_oma_figure).pack(side=tk.LEFT, padx=5, pady=5)

    def plot_oma_combined(self):
        """
        在 self.figure_oma 上绘制 SSI (左轴) + FDD(右轴)，
        并将原先在临时 figure 里的所有线/散点“移除后添加”。
        同时，确保左右轴的 x 轴范围匹配。
        """
        self.figure_oma.clear()  # 清空旧图

        ax_left = self.figure_oma.add_subplot(111)
        ax_right = ax_left.twinx()

        # (1) 准备数据
        data, ground_truth = example_data()
        simp_5dof = SingleSetup(data, fs=200)
        simp_5dof.decimate_data(q=10)

        fdd = FDD(name="FDD", nxseg=1024, method_SD="cor")
        ssidat = SSIdat(name="SSIdat", br=30, ordmax=30)
        simp_5dof.add_algorithms(fdd, ssidat)
        simp_5dof.run_all()

        # (2) 先让 PyOMA2 画 SSI 到一个临时 figure
        fig_ssi_tmp, ax_ssi_tmp = ssidat.plot_stab(freqlim=(0,10), hide_poles=False)

        # 将临时 figure 上的线和散点“移除后添加”到 ax_left
        for line in ax_ssi_tmp.lines:
            ax_left.add_line(line)       
        for coll in ax_ssi_tmp.collections:
            ax_left.add_collection(coll)

        plt.close(fig_ssi_tmp)

        # (3) 让 PyOMA2 画 FDD 到另一个临时 figure
        fig_fdd_tmp, ax_fdd_tmp = fdd.plot_CMIF(freqlim=(0,8))

        # 同理，移除后添加到 ax_right
        for line in ax_fdd_tmp.lines:
            line.remove()
            ax_right.add_line(line)
        for coll in ax_fdd_tmp.collections:
            coll.remove()
            ax_right.add_collection(coll)

        plt.close(fig_fdd_tmp)

        # (4) 设置坐标轴标题
        ax_left.set_title("SSI(左) + FDD(右)", fontproperties=self.font_prop)
        ax_left.set_xlabel("Freq (Hz)", fontproperties=self.font_prop)
        ax_left.set_ylabel("SSI Stabilization", fontproperties=self.font_prop, color='green')
        ax_right.set_ylabel("FDD CMIF", fontproperties=self.font_prop, color='blue')

        # (5) 让 Matplotlib 重新计算左右轴的显示范围
        ax_left.relim()
        ax_left.autoscale_view()
        ax_right.relim()
        ax_right.autoscale_view()

        # 这时，左右轴默认会根据各自数据自动设置 x 范围。如果你想让它们完全匹配，
        # 例如都显示 0~10 Hz，则可以手动设置：
        ax_left.set_xlim(0, 10)
        ax_right.set_xlim(0, 10)
        
        self.canvas_oma.draw()

    def save_oma_figure(self):
        """
        保存一次性绘制好的 OMA 图 (SSI+FDD)。
        """
        if not self.figure_oma:
            messagebox.showwarning("警告", "没有可保存的 OMA 图像！")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存 OMA 图",
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png"), ("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_path:
            self.figure_oma.savefig(file_path, dpi=300)
            messagebox.showinfo("提示", f"已保存 OMA 图到：{file_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
