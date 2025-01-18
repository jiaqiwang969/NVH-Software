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
        self.root.title("SSI + FDD on the same figure")

        # 主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 放置Canvas的frame
        self.plot_frame = ttk.Frame(self.main_frame)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)

        # 按钮
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(btn_frame, text="绘制SSI+FDD", command=self.plot_oma_combined).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btn_frame, text="保存图像", command=self.save_oma_figure).pack(side=tk.LEFT, padx=5, pady=5)

        # 先给一个 None 占位，用于存放“主图”
        self.fig_ssi = None
        self.canvas_oma = None

    def plot_oma_combined(self):
        """
        用与“测试代码”相同的方式来绘制：先让 PyOMA2 直接生成 SSI 图，再在同一个 figure 上 twin x 叠加 FDD
        """
        # 1) 准备数据
        data, ground_truth = example_data()
        simp_5dof = SingleSetup(data, fs=200)
        simp_5dof.decimate_data(q=10)

        fdd = FDD(name="FDD", nxseg=1024, method_SD="cor")
        ssidat = SSIdat(name="SSIdat", br=30, ordmax=30)
        simp_5dof.add_algorithms(fdd, ssidat)
        simp_5dof.run_all()

        # 2) 先让 PyOMA2 直接画 SSI；它会自动返回 fig_ssi, ax_ssi
        fig_ssi, ax_ssi = ssidat.plot_stab(freqlim=(0, 10), hide_poles=False)

        # 3) 在这同一个 fig_ssi 上加一个右轴，用来叠加 FDD
        ax_fdd = ax_ssi.twinx()
        ax_fdd.set_ylabel("FDD Magnitude", color='blue')

        ax_ssi.set_title("SSI + FDD (CMIF) on the same figure")

        # 4) PyOMA2 的 fdd.plot_CMIF() 会新开一张临时图，我们只复制它的 lines
        fig_cmif_tmp, ax_cmif_tmp = fdd.plot_CMIF(freqlim=(0, 8))

        # 从 ax_cmif_tmp 把每一条线的 (x,y) 数据复制到 ax_fdd
        for line in ax_cmif_tmp.lines:
            x_data = line.get_xdata()
            y_data = line.get_ydata()
            ax_fdd.plot(
                x_data, y_data,
                linestyle=line.get_linestyle(),
                color=line.get_color(),
                linewidth=line.get_linewidth(),
                label=line.get_label()
            )

        # 关掉临时图
        plt.close(fig_cmif_tmp)

        # 5) 如果需要手动设置 x 范围(比如都显示到 0~10Hz)，可以:
        #    ax_ssi.set_xlim(0, 10)
        #    ax_fdd.set_xlim(0, 10)

        # 6) 现在 fig_ssi 已经是最终想要的图 (SSI + FDD)
        #    如果之前已经有老的 canvas，需要先销毁
        if self.canvas_oma:
            self.canvas_oma.get_tk_widget().destroy()

        # 7) 把 fig_ssi 嵌到 Tkinter 的 canvas
        self.fig_ssi = fig_ssi
        self.canvas_oma = FigureCanvasTkAgg(self.fig_ssi, master=self.plot_frame)
        self.canvas_oma.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas_oma.draw()

    def save_oma_figure(self):
        """保存一次性绘制好的 OMA 图 (SSI+FDD)。"""
        if not self.fig_ssi:
            messagebox.showwarning("警告", "还没有绘制过图，无法保存！")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存 OMA 图",
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png"), ("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_path:
            self.fig_ssi.savefig(file_path, dpi=300)
            messagebox.showinfo("提示", f"已保存 OMA 图到：{file_path}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
