# view/main_window.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from matplotlib.font_manager import FontProperties

# ====== 新增：pyoma2 相关导入 ======
import mplcursors
from pyoma2.functions.gen import example_data
from pyoma2.setup.single import SingleSetup
from pyoma2.algorithms.fdd import FDD
from pyoma2.algorithms.ssi import SSIdat




from .dialogs import UserDefineDialog, SensorSettingsDialog
from model.data_models import SensorSettings

class MainWindow(tk.Tk):
    """
    主界面: 包含 Notebook, 数据处理, 频谱分析, 时域信号, 频响函数, 工作模态(OMA) 五个 Tab,
    以及用户自定义脚本等。
    """
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.title("FFT 数据处理")
        try:
            self.font_prop = FontProperties(fname='SimHei.ttf')  # 确保字体文件存在
        except:
            self.font_prop = None  # 使用默认字体

        # 初始化变量
        self.init_variables()
        # 创建 Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.create_tabs()

        # 绑定复制、粘贴快捷键
        self.bind_copy_paste(self)

    def init_variables(self):
        # 数据处理变量
        self.input_folder_var = tk.StringVar()
        self.output_folder_var = tk.StringVar()
        self.filename_prefix_var = tk.StringVar(value="激励")
        self.sampling_rate_var = tk.StringVar(value="25600")
        # 频谱分析变量
        self.freq_lower_display_var = tk.StringVar(value="1")
        self.freq_upper_display_var = tk.StringVar(value="500")
        self.x_axis_log_var_spectrum = tk.BooleanVar()
        self.y_axis_log_var_spectrum = tk.BooleanVar()
        self.y_axis_auto_scale_var_spectrum = tk.BooleanVar(value=True)
        self.y_axis_min_var_spectrum = tk.StringVar()
        self.y_axis_max_var_spectrum = tk.StringVar()
        self.add_frequency_markers_var_spectrum = tk.BooleanVar()
        self.shaft_frequency_var_spectrum = tk.StringVar()
        self.blade_number_var_spectrum = tk.StringVar()
        self.reference_value_var_spectrum = tk.StringVar(value="1e-5")
        self.y_axis_db_var_spectrum = tk.BooleanVar()
        self.y_axis_scale_log_var_spectrum = tk.BooleanVar()
        # 频率去除变量
        self.freq_to_remove_var = tk.StringVar(value="50,120")
        self.vk2_r_var = tk.StringVar(value="1000")
        self.vk2_filtord_var = tk.StringVar(value="1")
        self.apply_freq_removal_var = tk.BooleanVar()
        # 时域信号变量
        self.time_lower_display_var = tk.StringVar(value="0")
        self.time_upper_display_var = tk.StringVar(value="1")
        self.y_axis_auto_scale_var_time = tk.BooleanVar(value=True)
        self.y_axis_min_var_time = tk.StringVar()
        self.y_axis_max_var_time = tk.StringVar()
        # 频响函数变量
        self.x_axis_log_var_frf = tk.BooleanVar()
        self.y_axis_log_var_frf = tk.BooleanVar()
        self.y_axis_auto_scale_var_frf = tk.BooleanVar(value=True)
        self.y_axis_min_var_frf = tk.StringVar()
        self.y_axis_max_var_frf = tk.StringVar()
        self.reference_value_var_frf = tk.StringVar(value="1e-5")
        self.freq_lower_display_var_frf = tk.StringVar(value="1")
        self.freq_upper_display_var_frf = tk.StringVar(value="500")
        self.add_frequency_markers_var_frf = tk.BooleanVar()
        self.shaft_frequency_var_frf = tk.StringVar()
        self.blade_number_var_frf = tk.StringVar()
        self.y_axis_db_var_frf = tk.BooleanVar()
        self.y_axis_scale_log_var_frf = tk.BooleanVar()

        # 通道选择变量
        self.channel_var_spectrum = tk.StringVar()
        self.channel_var_time = tk.StringVar()
        self.channel_var_frf = tk.StringVar()
        self.channel_options = []
        # 文件选择变量
        self.file_var_spectrum = tk.StringVar()
        self.file_var_time = tk.StringVar()
        self.file_var_frf = tk.StringVar()
        self.file_options = []

    def create_tabs(self):
        # 数据处理选项卡
        self.processing_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.processing_tab, text='数据处理')
        self.create_processing_widgets()
        # 频谱分析选项卡
        self.spectrum_analysis_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.spectrum_analysis_tab, text='频谱分析')
        self.create_spectrum_analysis_widgets()
        # 时域信号选项卡
        self.time_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.time_tab, text='时域信号')
        self.create_time_widgets()
        # 频响函数选项卡
        self.frf_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.frf_tab, text='频响函数')
        self.create_frf_widgets()
        # 工作模态(OMA)选项卡
        self.oma_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.oma_tab, text='工作模态(OMA)')
        self.create_oma_widgets(self.oma_tab)
        # Global Params 选项卡
        self.global_params_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.global_params_tab, text="Global Params")
        self.create_global_params_widgets()
        # 默认禁用可视化选项卡
        self.disable_visualization_tabs()

    def disable_visualization_tabs(self):
        # 默认禁用可视化选项卡
        self.notebook.tab(1, state='disabled')  # 频谱分析
        self.notebook.tab(2, state='disabled')  # 时域信号
        self.notebook.tab(3, state='disabled')  # 频响函数
        self.notebook.tab(4, state='disabled')  # 工作模态(OMA)

    def enable_visualization_tabs(self):
        # 启用可视化选项卡
        self.notebook.tab(1, state='normal')  # 频谱分析
        self.notebook.tab(2, state='normal')  # 时域信号
        self.notebook.tab(3, state='normal')  # 频响函数
        self.notebook.tab(4, state='normal')  # 工作模态(OMA)

    def create_processing_widgets(self):
        # 创建数据处理页的组件
        frame = self.processing_tab

        # 输入文件夹
        tk.Label(frame, text="输入文件夹:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.input_folder_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(frame, text="选择", command=self.select_input_folder).grid(row=0, column=2, padx=5, pady=5)

        # 输出文件夹
        tk.Label(frame, text="输出文件夹:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.output_folder_var, width=50).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(frame, text="选择", command=self.select_output_folder).grid(row=1, column=2, padx=5, pady=5)

        # 文件名前缀
        tk.Label(frame, text="文件名前缀:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.filename_prefix_var, width=20).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # 采样率
        tk.Label(frame, text="采样率:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        tk.Entry(frame, textvariable=self.sampling_rate_var, width=20).grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        # 开始处理按钮
        tk.Button(frame, text="开始处理", command=self.start_processing).grid(row=4, column=1, pady=10)

        # === 新增: 用户自定义按钮 ===
        # 仅在处理完成后再启用；可先默认 state='disabled'，处理完成后由 controller 启用
        self.user_define_btn = tk.Button(frame, text="用户自定义", state='disabled',
                                         command=self.open_user_define_dialog)
        self.user_define_btn.grid(row=4, column=2, padx=5, pady=10)
        # （示例把它放在与“开始处理”同一行，也可自行调整 row/column）

        # 日志显示
        self.log_text = scrolledtext.ScrolledText(frame, width=70, height=15)
        self.log_text.grid(row=5, column=0, columnspan=3, padx=5, pady=5)

    def select_input_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.input_folder_var.set(folder_selected)

    def select_output_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder_var.set(folder_selected)

    def start_processing(self):
        # 获取参数
        params = self.controller.get_processing_parameters()
        if params is None:
            return
        # 开始处理
        self.controller.start_processing(params)

    def enable_user_define_button(self, enabled=True):
        """
        在处理完成后，允许启用“用户自定义”按钮。
        """
        if enabled:
            self.user_define_btn.config(state='normal')
        else:
            self.user_define_btn.config(state='disabled')

    def open_user_define_dialog(self):
        """
        打开用户自定义对话框
        """
        # 如果尚未处理，或者 processing_results 不存在，则给出警告
        if self.controller.processing_results is None:
            messagebox.showwarning("警告", "请先完成数据处理。")
            return

        # 弹出对话框
        dialog = UserDefineDialog(self)
        self.wait_window(dialog)
        # 对话框关闭后，会调用 Controller 的 create_user_defined_signal(...)
        # 来完成新信号的增量处理
        # 如果需要更新界面，可以再调用 self.update_visualization_options(...)
        # 但控制器里通常会自动调用

    def bind_copy_paste(self, root):
        for widget in root.winfo_children():
            if isinstance(widget, tk.Entry):
                widget.bind('<Control-c>', self.copy_event)
                widget.bind('<Control-C>', self.copy_event)
                widget.bind('<Control-v>', self.paste_event)
                widget.bind('<Control-V>', self.paste_event)
                widget.bind('<Control-x>', self.cut_event)
                widget.bind('<Control-X>', self.cut_event)
            elif isinstance(widget, tk.Widget):
                self.bind_copy_paste(widget)

    def copy_event(self, event):
        event.widget.event_generate('<<Copy>>')
        return 'break'

    def paste_event(self, event):
        event.widget.event_generate('<<Paste>>')
        return 'break'

    def cut_event(self, event):
        event.widget.event_generate('<<Cut>>')
        return 'break'

    # ====== 频谱分析相关方法 ======
    def create_spectrum_analysis_widgets(self):
        frame = self.spectrum_analysis_tab

        # 使用 grid 布局
        frame.columnconfigure(0, weight=1)  # 绘图区域初始权重
        frame.columnconfigure(1, weight=0)  # 按钮区域
        frame.columnconfigure(2, weight=0)  # 参数配置区域初始权重
        frame.rowconfigure(0, weight=1)

        # 左侧绘图区域 Frame
        plot_frame = ttk.Frame(frame)
        plot_frame.grid(row=0, column=0, sticky='nsew')

        # 中间的隐藏/显示按钮 Frame
        toggle_frame = ttk.Frame(frame, width=10)
        toggle_frame.grid(row=0, column=1, sticky='ns')
        toggle_frame.rowconfigure(0, weight=1)

        # 在 toggle_frame 中添加隐藏/显示按钮
        toggle_button = tk.Button(toggle_frame, text=">>")
        toggle_button.grid(row=0, column=0)
        toggle_button.config(command=lambda: self.toggle_frame(frame, control_frame, toggle_button))

        # 右侧参数配置 Frame
        control_frame = ttk.Frame(frame, width=300)
        control_frame.grid(row=0, column=2, sticky='nsew')

        # 将参数配置的控件添加到 control_frame 中
        # 文件选择
        tk.Label(control_frame, text="选择文件:").pack(anchor=tk.W, padx=5, pady=5)
        self.file_menu_spectrum = ttk.Combobox(control_frame, textvariable=self.file_var_spectrum, values=self.file_options, state='readonly')
        self.file_menu_spectrum.pack(anchor=tk.W, padx=5, pady=5)

        # 通道选择
        tk.Label(control_frame, text="选择通道:").pack(anchor=tk.W, padx=5, pady=5)
        self.channel_menu_spectrum = ttk.Combobox(control_frame, textvariable=self.channel_var_spectrum, values=self.channel_options, state='readonly')
        self.channel_menu_spectrum.pack(anchor=tk.W, padx=5, pady=5)

        # 添加一个复选框，是否应用频率去除
        tk.Checkbutton(control_frame, text="应用频率去除", variable=self.apply_freq_removal_var, command=self.toggle_freq_removal_options).pack(anchor=tk.W, padx=5, pady=5)

        # 创建一个 Frame 来包含频率去除的选项
        self.freq_removal_frame = tk.Frame(control_frame)
        # 默认隐藏频率去除选项
        self.freq_removal_frame.pack_forget()

        # 在频率去除选项中添加控件
        # 输入需要去除的频率列表
        tk.Label(self.freq_removal_frame, text="要去除的频率 (Hz, 逗号分隔):").pack(anchor=tk.W, padx=5, pady=5)
        tk.Entry(self.freq_removal_frame, textvariable=self.freq_to_remove_var, width=20).pack(anchor=tk.W, padx=5, pady=5)

        # vk2 参数输入
        tk.Label(self.freq_removal_frame, text="vk2 参数:").pack(anchor=tk.W, padx=5, pady=5)
        vk2_params_frame = tk.Frame(self.freq_removal_frame)
        vk2_params_frame.pack(anchor=tk.W, padx=5, pady=5)

        tk.Label(vk2_params_frame, text="r:").grid(row=0, column=0)
        tk.Entry(vk2_params_frame, textvariable=self.vk2_r_var, width=10).grid(row=0, column=1)

        tk.Label(vk2_params_frame, text="滤波器阶数 filtord:").grid(row=1, column=0)
        tk.Entry(vk2_params_frame, textvariable=self.vk2_filtord_var, width=10).grid(row=1, column=1)

        # 频率显示范围
        tk.Label(control_frame, text="频率显示范围 (Hz):").pack(anchor=tk.W, padx=5, pady=5)
        freq_display_frame = tk.Frame(control_frame)
        freq_display_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Entry(freq_display_frame, textvariable=self.freq_lower_display_var, width=10).pack(side=tk.LEFT)
        tk.Label(freq_display_frame, text=" - ").pack(side=tk.LEFT)
        tk.Entry(freq_display_frame, textvariable=self.freq_upper_display_var, width=10).pack(side=tk.LEFT)

        # X轴刻度
        tk.Label(control_frame, text="X轴刻度:").pack(anchor=tk.W, padx=5, pady=5)
        x_axis_frame = tk.Frame(control_frame)
        x_axis_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Radiobutton(x_axis_frame, text="线性", variable=self.x_axis_log_var_spectrum, value=False).pack(side=tk.LEFT)
        tk.Radiobutton(x_axis_frame, text="对数", variable=self.x_axis_log_var_spectrum, value=True).pack(side=tk.LEFT)

        # Y轴选项
        tk.Label(control_frame, text="Y轴选项:").pack(anchor=tk.W, padx=5, pady=5)
        y_axis_frame = tk.Frame(control_frame)
        y_axis_frame.pack(anchor=tk.W, padx=5, pady=5)

        tk.Checkbutton(y_axis_frame, text="幅值以 dB 显示", variable=self.y_axis_db_var_spectrum).pack(anchor=tk.W)
        tk.Label(y_axis_frame, text="参考值:").pack(anchor=tk.W)
        tk.Entry(y_axis_frame, textvariable=self.reference_value_var_spectrum, width=10).pack(anchor=tk.W)
        tk.Checkbutton(y_axis_frame, text="Y轴对数坐标", variable=self.y_axis_scale_log_var_spectrum).pack(anchor=tk.W)

        # Y轴范围
        tk.Label(control_frame, text="Y轴范围:").pack(anchor=tk.W, padx=5, pady=5)
        y_range_frame = tk.Frame(control_frame)
        y_range_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Checkbutton(y_range_frame, text="自动缩放", variable=self.y_axis_auto_scale_var_spectrum).pack(side=tk.LEFT)
        tk.Label(y_range_frame, text="最小值:").pack(side=tk.LEFT)
        tk.Entry(y_range_frame, textvariable=self.y_axis_min_var_spectrum, width=10).pack(side=tk.LEFT)
        tk.Label(y_range_frame, text="最大值:").pack(side=tk.LEFT)
        tk.Entry(y_range_frame, textvariable=self.y_axis_max_var_spectrum, width=10).pack(side=tk.LEFT)

        # 添加频率标记
        tk.Checkbutton(control_frame, text="添加频率标记", variable=self.add_frequency_markers_var_spectrum).pack(anchor=tk.W, padx=5, pady=5)
        freq_marker_frame = tk.Frame(control_frame)
        freq_marker_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Label(freq_marker_frame, text="轴频 (rps):").pack(side=tk.LEFT)
        tk.Entry(freq_marker_frame, textvariable=self.shaft_frequency_var_spectrum, width=10).pack(side=tk.LEFT)
        tk.Label(freq_marker_frame, text="叶片数:").pack(side=tk.LEFT)
        tk.Entry(freq_marker_frame, textvariable=self.blade_number_var_spectrum, width=10).pack(side=tk.LEFT)

        # 绘制按钮和保存按钮
        button_frame = tk.Frame(control_frame)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="绘制", command=self.plot_spectrum_analysis).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="保存图片", command=self.save_spectrum_analysis_plot).pack(side=tk.LEFT, padx=5)
        # 添加“保存数据”按钮
        tk.Button(button_frame, text="保存数据", command=self.save_spectrum_data).pack(side=tk.LEFT, padx=5)

        # 在 plot_frame 中添加绘图区域
        self.figure_spectrum_analysis = plt.Figure(figsize=(8, 5))
        self.canvas_spectrum_analysis = FigureCanvasTkAgg(self.figure_spectrum_analysis, master=plot_frame)
        self.canvas_spectrum_analysis.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def toggle_freq_removal_options(self):
        if self.apply_freq_removal_var.get():
            self.freq_removal_frame.pack(anchor=tk.W, padx=5, pady=5)
        else:
            self.freq_removal_frame.pack_forget()

    def plot_spectrum_analysis(self):
        """
        当用户点击“绘制”时:
          1) 检查 file, channel
          2) 调用 controller.get_spectrum_data(file, channel) => freq, amplitude
          3) 做图
        """
        selected_file = self.file_var_spectrum.get()
        selected_channel = self.channel_var_spectrum.get()

        if self.controller.processing_results is None:
            messagebox.showwarning("警告", "请先处理数据。")
            return
        if not selected_file or not selected_channel:
            messagebox.showwarning("警告", "请选择文件和通道！")
            return

        # 调用 controller 获取 (freq, amplitude)
        freq, amplitude = self.controller.get_spectrum_data(selected_file, selected_channel)
        if freq is None or amplitude is None:
            # 说明获取失败 / 参数不足 / etc
            return

        # 后续做 freq range 筛选, dB 转换, plot ...
        try:
            freq_lower_display = float(self.freq_lower_display_var.get())
            freq_upper_display = float(self.freq_upper_display_var.get())
        except ValueError:
            messagebox.showwarning("警告", "频率显示范围必须是数字！")
            return

        idx = (freq >= freq_lower_display) & (freq <= freq_upper_display)
        freq_to_plot = freq[idx]
        amplitude_to_plot = amplitude[idx]

        # 4) dB, log, etc
        x_axis_log = self.x_axis_log_var_spectrum.get()
        y_axis_db = self.y_axis_db_var_spectrum.get()
        y_axis_scale_log = self.y_axis_scale_log_var_spectrum.get()
        y_axis_auto_scale = self.y_axis_auto_scale_var_spectrum.get()
        y_axis_min = None
        y_axis_max = None

        # 防止同时选择 dB 显示和 y 轴对数坐标
        if y_axis_db and y_axis_scale_log:
            messagebox.showwarning("警告", "不能同时选择幅值以 dB 显示和 Y 轴对数坐标！")
            return

        if not y_axis_auto_scale:
            try:
                y_axis_min = float(self.y_axis_min_var_spectrum.get())
                y_axis_max = float(self.y_axis_max_var_spectrum.get())
                if y_axis_min >= y_axis_max:
                    messagebox.showwarning("警告", "Y轴最小值必须小于最大值！")
                    return
            except ValueError:
                messagebox.showwarning("警告", "Y轴最小值和最大值必须是数字！")
                return

        # 添加频率标记
        add_frequency_markers = self.add_frequency_markers_var_spectrum.get()
        shaft_frequency = None
        blade_number = None
        if add_frequency_markers:
            try:
                shaft_frequency = float(self.shaft_frequency_var_spectrum.get())
                blade_number = int(self.blade_number_var_spectrum.get())
            except ValueError:
                messagebox.showwarning("警告", "轴频必须是数字，叶片数必须是整数！")
                return

        # 获取参考值
        try:
            reference_value = float(self.reference_value_var_spectrum.get())
            if reference_value <= 0:
                messagebox.showwarning("警告", "参考值必须是正数！")
                return
        except ValueError:
            messagebox.showwarning("警告", "参考值必须是数字！")
            return

        # 将频率和幅值数据保存到实例变量中
        self.current_freq_data = freq_to_plot
        self.current_amplitude_data = amplitude_to_plot

        y_label = "幅值"
        if y_axis_db:
            amplitude_to_plot = 20 * np.log10(amplitude_to_plot / reference_value + 1e-12)
            y_label = "幅值 (dB)"

        # 清除之前的图像
        self.figure_spectrum_analysis.clear()
        ax = self.figure_spectrum_analysis.add_subplot(111)

        ax.plot(freq_to_plot, amplitude_to_plot, label=selected_channel)
        ax.set_title(f"频谱分析 - {selected_channel}", fontproperties=self.font_prop)
        ax.set_xlabel("频率 (Hz)", fontproperties=self.font_prop)
        ax.set_ylabel(y_label, fontproperties=self.font_prop)
        ax.legend(prop=self.font_prop)
        ax.grid()

        if x_axis_log:
            ax.set_xscale('log')
        if y_axis_scale_log:
            ax.set_yscale('log')
        if not y_axis_auto_scale:
            ax.set_ylim(y_axis_min, y_axis_max)

        # 添加频率标记
        if add_frequency_markers:
            marker_freqs = [
                    ('1x轴频', shaft_frequency),
                    ('2x轴频', shaft_frequency * 2),
                    ('1x叶频', shaft_frequency * blade_number),
                    ('2x叶频', shaft_frequency * blade_number * 2)
                    ]
            ylim = ax.get_ylim()
            y_position = ylim[1] - (ylim[1] - ylim[0]) * 0.1
            for label, freq_value in marker_freqs:
                ax.axvline(x=freq_value, color='k', linestyle='--')
                ax.text(freq_value, y_position, label, rotation=90, verticalalignment='center',
                        color='r', fontproperties=self.font_prop)

        # 添加交互式光标
        vertical_line = ax.axvline(color='k', linestyle='--', alpha=0.5)
        horizontal_line = ax.axhline(color='k', linestyle='--', alpha=0.5)
        annotation = ax.annotate('', xy=(0, 0), xytext=(10, 10), textcoords='offset points',
                                 bbox=dict(boxstyle='round', fc='w'),
                                 fontsize=8, fontproperties=self.font_prop)

        def mouse_move(event):
            if event.inaxes == ax:
                x, y = event.xdata, event.ydata
                vertical_line.set_xdata([x, x])
                horizontal_line.set_ydata([y, y])
                annotation.xy = (x, y)
                text = f'频率={x:.2f}Hz\n幅值={y:.2f}'
                annotation.set_text(text)
                self.canvas_spectrum_analysis.draw_idle()
            else:
                vertical_line.set_xdata([None, None])
                horizontal_line.set_ydata([None, None])
                annotation.set_text('')
                self.canvas_spectrum_analysis.draw_idle()

        self.canvas_spectrum_analysis.mpl_connect('motion_notify_event', mouse_move)
        self.canvas_spectrum_analysis.draw()

    def save_spectrum_analysis_plot(self):
        file_path = filedialog.asksaveasfilename(title="保存图片", defaultextension=".png",
                                                 filetypes=[("PNG 文件", "*.png"), ("JPEG 文件", "*.jpg"), ("所有文件", "*.*")])
        if file_path:
            self.figure_spectrum_analysis.savefig(file_path)
            messagebox.showinfo("成功", "图片已保存！")

    def save_spectrum_data(self):
        if not hasattr(self, 'current_freq_data') or not hasattr(self, 'current_amplitude_data'):
            messagebox.showwarning("警告", "没有可保存的数据，请先绘制频谱。")
            return

        # 让用户选择保存文件的位置
        file_path = filedialog.asksaveasfilename(title="保存数据", defaultextension=".txt",
                                                 filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if file_path:
            try:
                # 将频率和幅值数据保存到文本文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("频率(Hz)\t幅值\n")
                    for freq, amp in zip(self.current_freq_data, self.current_amplitude_data):
                        f.write(f"{freq}\t{amp}\n")
                messagebox.showinfo("成功", "数据已成功保存！")
            except Exception as e:
                messagebox.showerror("错误", f"保存数据时发生错误：{e}")

    # ====== 时域信号相关方法 ======
    def create_time_widgets(self):
        frame = self.time_tab

        # 使用 grid 布局
        frame.columnconfigure(0, weight=1)  # 绘图区域初始权重
        frame.columnconfigure(1, weight=0)  # 按钮区域
        frame.columnconfigure(2, weight=0)  # 参数配置区域初始权重
        frame.rowconfigure(0, weight=1)

        # 左侧绘图区域 Frame
        plot_frame = ttk.Frame(frame)
        plot_frame.grid(row=0, column=0, sticky='nsew')

        # 中间的隐藏/显示按钮 Frame
        toggle_frame = ttk.Frame(frame, width=10)
        toggle_frame.grid(row=0, column=1, sticky='ns')
        toggle_frame.rowconfigure(0, weight=1)

        # 在 toggle_frame 中添加隐藏/显示按钮
        toggle_button = tk.Button(toggle_frame, text=">>")
        toggle_button.grid(row=0, column=0)
        toggle_button.config(command=lambda: self.toggle_frame(frame, control_frame, toggle_button))

        # 右侧参数配置 Frame
        control_frame = ttk.Frame(frame, width=300)
        control_frame.grid(row=0, column=2, sticky='nsew')

        # 将参数配置的控件添加到 control_frame 中
        # 文件选择
        tk.Label(control_frame, text="选择文件:").pack(anchor=tk.W, padx=5, pady=5)
        self.file_menu_time = ttk.Combobox(control_frame, textvariable=self.file_var_time, values=self.file_options, state='readonly')
        self.file_menu_time.pack(anchor=tk.W, padx=5, pady=5)

        # 通道选择
        tk.Label(control_frame, text="选择通道:").pack(anchor=tk.W, padx=5, pady=5)
        self.channel_menu_time = ttk.Combobox(control_frame, textvariable=self.channel_var_time, values=self.channel_options, state='readonly')
        self.channel_menu_time.pack(anchor=tk.W, padx=5, pady=5)

        # 时域显示范围
        tk.Label(control_frame, text="时间显示范围 (0-1):").pack(anchor=tk.W, padx=5, pady=5)
        time_display_frame = tk.Frame(control_frame)
        time_display_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Entry(time_display_frame, textvariable=self.time_lower_display_var, width=10).pack(side=tk.LEFT)
        tk.Label(time_display_frame, text=" - ").pack(side=tk.LEFT)
        tk.Entry(time_display_frame, textvariable=self.time_upper_display_var, width=10).pack(side=tk.LEFT)

        # Y轴范围
        tk.Label(control_frame, text="Y轴范围:").pack(anchor=tk.W, padx=5, pady=5)
        y_range_frame = tk.Frame(control_frame)
        y_range_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Checkbutton(y_range_frame, text="自动缩放", variable=self.y_axis_auto_scale_var_time).pack(side=tk.LEFT)
        tk.Label(y_range_frame, text="最小值:").pack(side=tk.LEFT)
        tk.Entry(y_range_frame, textvariable=self.y_axis_min_var_time, width=10).pack(side=tk.LEFT)
        tk.Label(y_range_frame, text="最大值:").pack(side=tk.LEFT)
        tk.Entry(y_range_frame, textvariable=self.y_axis_max_var_time, width=10).pack(side=tk.LEFT)

        # 绘制按钮和保存按钮
        button_frame = tk.Frame(control_frame)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="绘制", command=self.plot_time_domain).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="保存图片", command=self.save_time_plot).pack(side=tk.LEFT, padx=5)

        # 在 plot_frame 中添加绘图区域
        self.figure_time = plt.Figure(figsize=(8, 5))
        self.canvas_time = FigureCanvasTkAgg(self.figure_time, master=plot_frame)
        self.canvas_time.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def plot_time_domain(self):
        selected_file = self.file_var_time.get()
        selected_channel = self.channel_var_time.get()
        if not selected_file or not selected_channel:
            messagebox.showwarning("警告", "请选择文件和通道！")
            return

        # 获取对应的时域数据
        data_converted = self.controller.get_time_domain_data(selected_file, selected_channel)
        if data_converted is None:
            messagebox.showwarning("警告", "未找到对应的通道数据！")
            return

        try:
            time_start = float(self.time_lower_display_var.get())
            time_end = float(self.time_upper_display_var.get())
            if not (0 <= time_start < time_end <= 1):
                messagebox.showwarning("警告", "时域信号范围应在 0 到 1 之间，且起始值小于结束值！")
                return
        except ValueError:
            messagebox.showwarning("警告", "时域信号范围必须是数字！")
            return

        sampling_rate = float(self.controller.params.sampling_rate) if self.controller.params else 25600
        total_length = len(data_converted)
        t = np.linspace(0, total_length / sampling_rate, total_length, endpoint=False)
        start_idx = int(time_start * total_length)
        end_idx = int(time_end * total_length)
        t_segment = t[start_idx:end_idx]
        data_segment = data_converted[start_idx:end_idx]

        # 清除之前的图像
        self.figure_time.clear()
        ax = self.figure_time.add_subplot(111)

        ax.plot(t_segment, data_segment, label=selected_channel)
        ax.set_title(f"时域信号 - {selected_channel}", fontproperties=self.font_prop)
        ax.set_xlabel("时间 (s)", fontproperties=self.font_prop)
        ax.set_ylabel("幅值", fontproperties=self.font_prop)
        ax.legend(prop=self.font_prop)
        ax.grid()

        # Y 轴自动缩放 vs 手动设置
        y_axis_auto_scale = self.y_axis_auto_scale_var_time.get()
        if y_axis_auto_scale:
            # 让Matplotlib自动计算并缩放
            ax.relim()              # 重新计算数据边界
            ax.autoscale_view()     # 更新视图
            # 若想为自动缩放加留白，可写：ax.margins(y=0.1)
        else:
            # 手动缩放
            try:
                y_axis_min = float(self.y_axis_min_var_time.get())
                y_axis_max = float(self.y_axis_max_var_time.get())
                if y_axis_min >= y_axis_max:
                    messagebox.showwarning("警告", "Y轴最小值必须小于最大值！")
                    return
                ax.set_ylim(y_axis_min, y_axis_max)
            except ValueError:
                messagebox.showwarning("警告", "Y轴最小值和最大值必须是数字！")
                return

        # 添加交互式光标
        vertical_line = ax.axvline(color='k', linestyle='--', alpha=0.5)
        horizontal_line = ax.axhline(color='k', linestyle='--', alpha=0.5)
        annotation = ax.annotate('', xy=(0, 0), xytext=(10, 10), textcoords='offset points',
                                 bbox=dict(boxstyle='round', fc='w'),
                                 fontsize=8, fontproperties=self.font_prop)

        def mouse_move(event):
            if event.inaxes == ax:
                x, y = event.xdata, event.ydata
                vertical_line.set_xdata([x, x])
                horizontal_line.set_ydata([y, y])
                annotation.xy = (x, y)
                text = f'时间={x:.4f}s\n幅值={y:.4f}'
                annotation.set_text(text)
                self.canvas_time.draw_idle()
            else:
                vertical_line.set_xdata([None, None])
                horizontal_line.set_ydata([None, None])
                annotation.set_text('')
                self.canvas_time.draw_idle()

        self.canvas_time.mpl_connect('motion_notify_event', mouse_move)
        self.canvas_time.draw()

    def save_time_plot(self):
        file_path = filedialog.asksaveasfilename(title="保存图片", defaultextension=".png",
                                                 filetypes=[("PNG 文件", "*.png"), ("JPEG 文件", "*.jpg"), ("所有文件", "*.*")])
        if file_path:
            self.figure_time.savefig(file_path)
            messagebox.showinfo("成功", "图片已保存！")

    # ====== 频响函数相关方法 ======
    def create_frf_widgets(self):
        frame = self.frf_tab

        # 使用 grid 布局
        frame.columnconfigure(0, weight=1)  # 绘图区域初始权重
        frame.columnconfigure(1, weight=0)  # 按钮区域
        frame.columnconfigure(2, weight=0)  # 参数配置区域初始权重
        frame.rowconfigure(0, weight=1)

        # 左侧绘图区域 Frame
        plot_frame = ttk.Frame(frame)
        plot_frame.grid(row=0, column=0, sticky='nsew')

        # 中间的隐藏/显示按钮 Frame
        toggle_frame = ttk.Frame(frame, width=10)
        toggle_frame.grid(row=0, column=1, sticky='ns')
        toggle_frame.rowconfigure(0, weight=1)

        # 在 toggle_frame 中添加隐藏/显示按钮
        toggle_button = tk.Button(toggle_frame, text=">>")
        toggle_button.grid(row=0, column=0)
        toggle_button.config(command=lambda: self.toggle_frame(frame, control_frame, toggle_button))

        # 右侧参数配置 Frame
        control_frame = ttk.Frame(frame, width=300)
        control_frame.grid(row=0, column=2, sticky='nsew')

        # 将参数配置的控件添加到 control_frame 中
        # 文件选择
        tk.Label(control_frame, text="选择文件:").pack(anchor=tk.W, padx=5, pady=5)
        self.file_menu_frf = ttk.Combobox(control_frame, textvariable=self.file_var_frf, values=self.file_options, state='readonly')
        self.file_menu_frf.pack(anchor=tk.W, padx=5, pady=5)

        # 通道选择
        tk.Label(control_frame, text="选择通道:").pack(anchor=tk.W, padx=5, pady=5)
        self.channel_menu_frf = ttk.Combobox(control_frame, textvariable=self.channel_var_frf, values=self.channel_options, state='readonly')
        self.channel_menu_frf.pack(anchor=tk.W, padx=5, pady=5)

        # 频率显示范围
        tk.Label(control_frame, text="频率显示范围 (Hz):").pack(anchor=tk.W, padx=5, pady=5)
        freq_display_frame = tk.Frame(control_frame)
        freq_display_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Entry(freq_display_frame, textvariable=self.freq_lower_display_var_frf, width=10).pack(side=tk.LEFT)
        tk.Label(freq_display_frame, text=" - ").pack(side=tk.LEFT)
        tk.Entry(freq_display_frame, textvariable=self.freq_upper_display_var_frf, width=10).pack(side=tk.LEFT)

        # X轴刻度
        tk.Label(control_frame, text="X轴刻度:").pack(anchor=tk.W, padx=5, pady=5)
        x_axis_frame = tk.Frame(control_frame)
        x_axis_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Radiobutton(x_axis_frame, text="线性", variable=self.x_axis_log_var_frf, value=False).pack(side=tk.LEFT)
        tk.Radiobutton(x_axis_frame, text="对数", variable=self.x_axis_log_var_frf, value=True).pack(side=tk.LEFT)

        # Y轴选项
        tk.Label(control_frame, text="Y轴选项:").pack(anchor=tk.W, padx=5, pady=5)
        y_axis_frame = tk.Frame(control_frame)
        y_axis_frame.pack(anchor=tk.W, padx=5, pady=5)

        tk.Checkbutton(y_axis_frame, text="幅值以 dB 显示", variable=self.y_axis_db_var_frf).pack(anchor=tk.W)
        tk.Label(y_axis_frame, text="参考值:").pack(anchor=tk.W)
        tk.Entry(y_axis_frame, textvariable=self.reference_value_var_frf, width=10).pack(anchor=tk.W)
        tk.Checkbutton(y_axis_frame, text="Y轴对数坐标", variable=self.y_axis_scale_log_var_frf).pack(anchor=tk.W)

        # Y轴范围
        tk.Label(control_frame, text="Y轴范围:").pack(anchor=tk.W, padx=5, pady=5)
        y_range_frame = tk.Frame(control_frame)
        y_range_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Checkbutton(y_range_frame, text="自动缩放", variable=self.y_axis_auto_scale_var_frf).pack(side=tk.LEFT)
        tk.Label(y_range_frame, text="最小值:").pack(side=tk.LEFT)
        tk.Entry(y_range_frame, textvariable=self.y_axis_min_var_frf, width=10).pack(side=tk.LEFT)
        tk.Label(y_range_frame, text="最大值:").pack(side=tk.LEFT)
        tk.Entry(y_range_frame, textvariable=self.y_axis_max_var_frf, width=10).pack(side=tk.LEFT)

        # 添加频率标记
        tk.Checkbutton(control_frame, text="添加频率标记", variable=self.add_frequency_markers_var_frf).pack(anchor=tk.W, padx=5, pady=5)
        freq_marker_frame = tk.Frame(control_frame)
        freq_marker_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Label(freq_marker_frame, text="轴频 (rps):").pack(side=tk.LEFT)
        tk.Entry(freq_marker_frame, textvariable=self.shaft_frequency_var_frf, width=10).pack(side=tk.LEFT)
        tk.Label(freq_marker_frame, text="叶片数:").pack(side=tk.LEFT)
        tk.Entry(freq_marker_frame, textvariable=self.blade_number_var_frf, width=10).pack(side=tk.LEFT)

        # 绘制按钮和保存按钮
        button_frame = tk.Frame(control_frame)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="绘制", command=self.plot_frf).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="保存图片", command=self.save_frf_plot).pack(side=tk.LEFT, padx=5)

        # 在 plot_frame 中添加绘图区域
        self.figure_frf = plt.Figure(figsize=(8, 5))
        self.canvas_frf = FigureCanvasTkAgg(self.figure_frf, master=plot_frame)
        self.canvas_frf.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def plot_frf(self):
        selected_file = self.file_var_frf.get()
        selected_channel = self.channel_var_frf.get()
        if not selected_file or not selected_channel:
            messagebox.showwarning("警告", "请选择文件和通道！")
            return

        # 获取对应的 FRF 结果
        frf_result = self.controller.get_frf_result(selected_file, selected_channel)
        if not frf_result:
            messagebox.showwarning("警告", "未找到对应的通道数据！")
            return

        # 获取频率显示范围
        try:
            freq_lower_display = float(self.freq_lower_display_var_frf.get())
            freq_upper_display = float(self.freq_upper_display_var_frf.get())
        except ValueError:
            messagebox.showwarning("警告", "频率显示范围必须是数字！")
            return

        x_axis_log = self.x_axis_log_var_frf.get()
        y_axis_db = self.y_axis_db_var_frf.get()
        y_axis_scale_log = self.y_axis_scale_log_var_frf.get()
        y_axis_auto_scale = self.y_axis_auto_scale_var_frf.get()
        y_axis_min = None
        y_axis_max = None

        # 防止同时选择 dB 显示和 y 轴对数坐标
        if y_axis_db and y_axis_scale_log:
            messagebox.showwarning("警告", "不能同时选择幅值以 dB 显示和 Y 轴对数坐标！")
            return

        if not y_axis_auto_scale:
            try:
                y_axis_min = float(self.y_axis_min_var_frf.get())
                y_axis_max = float(self.y_axis_max_var_frf.get())
                if y_axis_min >= y_axis_max:
                    messagebox.showwarning("警告", "Y轴最小值必须小于最大值！")
                    return
            except ValueError:
                messagebox.showwarning("警告", "Y轴最小值和最大值必须是数字！")
                return

        # 添加频率标记
        add_frequency_markers = self.add_frequency_markers_var_frf.get()
        shaft_frequency = None
        blade_number = None
        if add_frequency_markers:
            try:
                shaft_frequency = float(self.shaft_frequency_var_frf.get())
                blade_number = int(self.blade_number_var_frf.get())
            except ValueError:
                messagebox.showwarning("警告", "轴频必须是数字，叶片数必须是整数！")
                return

        # 获取参考值
        try:
            reference_value = float(self.reference_value_var_frf.get())
            if reference_value <= 0:
                messagebox.showwarning("警告", "参考值必须是正数！")
                return
        except ValueError:
            messagebox.showwarning("警告", "参考值必须是数字！")
            return

        # 清除之前的图像
        self.figure_frf.clear()
        ax = self.figure_frf.add_subplot(111)

        freq = frf_result['freq']
        H_f_magnitude = frf_result['H_f_magnitude']

        # 根据频率显示范围选择数据
        idx = (freq >= freq_lower_display) & (freq <= freq_upper_display)
        freq_to_plot = freq[idx]
        H_f_magnitude_to_plot = H_f_magnitude[idx]

        y_label = "幅值"
        if y_axis_db:
            # dB 计算公式：Amplitude (dB) = 20 * log10(Amplitude / Reference Value)
            H_f_magnitude_to_plot = 20 * np.log10(H_f_magnitude_to_plot / reference_value + 1e-12)
            y_label = "幅值 (dB)"

        ax.plot(freq_to_plot, H_f_magnitude_to_plot, label=selected_channel)
        ax.set_title(f"频响函数 - {selected_channel}", fontproperties=self.font_prop)
        ax.set_xlabel("频率 (Hz)", fontproperties=self.font_prop)
        ax.set_ylabel(y_label, fontproperties=self.font_prop)
        ax.legend(prop=self.font_prop)
        ax.grid()

        if x_axis_log:
            ax.set_xscale('log')
        if y_axis_scale_log:
            ax.set_yscale('log')
        if not y_axis_auto_scale:
            ax.set_ylim(y_axis_min, y_axis_max)

        # 添加频率标记
        if add_frequency_markers:
            marker_freqs = [
                    ('1x轴频', shaft_frequency),
                    ('2x轴频', shaft_frequency * 2),
                    ('1x叶频', shaft_frequency * blade_number),
                    ('2x叶频', shaft_frequency * blade_number * 2)
                    ]
            ylim = ax.get_ylim()
            y_position = ylim[1] - (ylim[1] - ylim[0]) * 0.1
            for label, freq_value in marker_freqs:
                ax.axvline(x=freq_value, color='k', linestyle='--')
                ax.text(freq_value, y_position, label, rotation=90, verticalalignment='center',
                        color='r', fontproperties=self.font_prop)

        # 添加交互式光标
        vertical_line = ax.axvline(color='k', linestyle='--', alpha=0.5)
        horizontal_line = ax.axhline(color='k', linestyle='--', alpha=0.5)
        annotation = ax.annotate('', xy=(0, 0), xytext=(10, 10), textcoords='offset points',
                                 bbox=dict(boxstyle='round', fc='w'),
                                 fontsize=8, fontproperties=self.font_prop)

        def mouse_move(event):
            if event.inaxes == ax:
                x, y = event.xdata, event.ydata
                vertical_line.set_xdata([x, x])
                horizontal_line.set_ydata([y, y])
                annotation.xy = (x, y)
                text = f'频率={x:.2f}Hz\n幅值={y:.2f}'
                annotation.set_text(text)
                self.canvas_frf.draw_idle()
            else:
                vertical_line.set_xdata([None, None])
                horizontal_line.set_ydata([None, None])
                annotation.set_text('')
                self.canvas_frf.draw_idle()

        self.canvas_frf.mpl_connect('motion_notify_event', mouse_move)
        self.canvas_frf.draw()

    def save_frf_plot(self):
        file_path = filedialog.asksaveasfilename(title="保存图片", defaultextension=".png",
                                                 filetypes=[("PNG 文件", "*.png"), ("JPEG 文件", "*.jpg"), ("所有文件", "*.*")])
        if file_path:
            self.figure_frf.savefig(file_path)
            messagebox.showinfo("成功", "图片已保存！")


    def create_oma_widgets(self, parent_frame):
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.columnconfigure(1, weight=0)
        parent_frame.columnconfigure(2, weight=0)
        parent_frame.rowconfigure(0, weight=1)

        # 左侧绘图区域
        plot_frame = ttk.Frame(parent_frame)
        plot_frame.grid(row=0, column=0, sticky='nsew')

        # 中间的隐藏/显示按钮 Frame
        toggle_frame = ttk.Frame(parent_frame, width=10)
        toggle_frame.grid(row=0, column=1, sticky="ns")
        toggle_frame.rowconfigure(0, weight=1)
        toggle_btn = tk.Button(toggle_frame, text=">>")
        toggle_btn.grid(row=0, column=0)
        toggle_btn.config(command=lambda: self.toggle_frame(parent_frame, control_frame, toggle_btn))

        # 右侧控制区
        control_frame = ttk.Frame(parent_frame, width=300)
        control_frame.grid(row=0, column=2, sticky="nsew")

        # 在右侧增加一个“一次性绘制”按钮
        ttk.Button(control_frame, text="绘制 SSI+FDD", command=self.plot_oma_combined).pack(padx=5, pady=5)
        ttk.Button(control_frame, text="保存 OMA 图", command=self.save_oma_figure).pack(padx=5, pady=5)

        ttk.Label(control_frame, text="(此处可放一些 OMA 算法参数设置)").pack(pady=20)

        # 创建一个空白 Figure，用于承载合并图
        self.figure_oma = plt.Figure(figsize=(8, 5))
        self.canvas_oma = FigureCanvasTkAgg(self.figure_oma, master=plot_frame)
        self.canvas_oma.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 为了后续能随时清空/重画，这里先不创建轴
        # 等真正点击按钮时，再创建 ax_left/ax_right




    def create_oma_widgets(self, parent_frame):
        parent_frame.columnconfigure(0, weight=1)
        parent_frame.columnconfigure(1, weight=0)
        parent_frame.columnconfigure(2, weight=0)
        parent_frame.rowconfigure(0, weight=1)

        # 左侧绘图区域
        plot_frame = ttk.Frame(parent_frame)
        plot_frame.grid(row=0, column=0, sticky='nsew')

        # 中间的隐藏/显示按钮 Frame
        toggle_frame = ttk.Frame(parent_frame, width=10)
        toggle_frame.grid(row=0, column=1, sticky="ns")
        toggle_frame.rowconfigure(0, weight=1)
        toggle_btn = tk.Button(toggle_frame, text=">>")
        toggle_btn.grid(row=0, column=0)
        toggle_btn.config(command=lambda: self.toggle_frame(parent_frame, control_frame, toggle_btn))

        # 右侧控制区
        control_frame = ttk.Frame(parent_frame, width=300)
        control_frame.grid(row=0, column=2, sticky="nsew")

        # 在右侧增加一个“一次性绘制”按钮
        ttk.Button(control_frame, text="绘制 SSI+FDD", command=self.plot_oma_combined).pack(padx=5, pady=5)
        ttk.Button(control_frame, text="保存 OMA 图", command=self.save_oma_figure).pack(padx=5, pady=5)

        ttk.Label(control_frame, text="(此处可放一些 OMA 算法参数设置)").pack(pady=20)

        # == 不在这里创建 figure_oma；只保留一个容器 Frame，用于容纳 Canvas ==
        #   我们留一个变量保存这个位置
        self.oma_plot_frame = plot_frame

        # 用于存放后续生成的 Figure 对象
        self.fig_oma = None
        self.canvas_oma = None



    def plot_oma_combined(self):
        """
        在同一个 Figure 上绘制 SSI(左轴) + FDD(右轴)，并嵌入 Tkinter。
        """
        # （1）先让 PyOMA2 直接创建 SSI 图：
        data, ground_truth = example_data()
        simp_5dof = SingleSetup(data, fs=200)
        simp_5dof.decimate_data(q=10)

        fdd = FDD(name="FDD", nxseg=1024, method_SD="cor")
        ssidat = SSIdat(name="SSIdat", br=30, ordmax=30)
        simp_5dof.add_algorithms(fdd, ssidat)
        simp_5dof.run_all()

        # PyOMA2 -> 画 SSI 稳定图
        fig_ssi, ax_ssi = ssidat.plot_stab(freqlim=(0, 10), hide_poles=False)

        # （2）在同一个 fig_ssi 上加一条右轴
        ax_fdd = ax_ssi.twinx()
        ax_fdd.set_ylabel("FDD Magnitude", color='blue')
        ax_ssi.set_title("SSI + FDD (CMIF) on the same figure", fontproperties=self.font_prop)

        # （3）PyOMA2 的 fdd.plot_CMIF() 会创建一个临时 fig/cmif
        fig_cmif_tmp, ax_cmif_tmp = fdd.plot_CMIF(freqlim=(0, 8))

        # （4）复制 CMIF 的线到 ax_fdd
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
        plt.close(fig_cmif_tmp)  # 用完临时图就关闭

        # （5）如果想让 x 范围都显示 0~10Hz，可以：
        # ax_ssi.set_xlim(0, 10)
        # ax_fdd.set_xlim(0, 10)

        # （6）在嵌入 Tkinter 前，如果老的 canvas 存在，先销毁
        if self.canvas_oma:
            self.canvas_oma.get_tk_widget().destroy()
            self.canvas_oma = None

        # （7）将“PyOMA2 画好的 fig_ssi”嵌入到 tkinter
        self.fig_oma = fig_ssi    # 保存引用，以便后续保存
        self.canvas_oma = FigureCanvasTkAgg(self.fig_oma, master=self.oma_plot_frame)
        self.canvas_oma.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # （8）如果需要 mplcursors 交互，可启用：
        # import mplcursors
        # mplcursors.cursor(ax_ssi, hover=True)
        # mplcursors.cursor(ax_fdd, hover=True)

        self.canvas_oma.draw()

    def save_oma_figure(self):
        """
        保存一次性绘制好的 OMA 图 (SSI+FDD)。
        """
        if not self.fig_oma:
            messagebox.showwarning("警告", "还没有绘制 OMA 图，无法保存！")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存 OMA 图",
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png"), ("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_path:
            self.fig_oma.savefig(file_path, dpi=300)
            messagebox.showinfo("提示", f"已保存 OMA 图到：{file_path}")











    # ====== Global Params 相关方法 ======
    def create_global_params_widgets(self):
        """
        在 "Global Params" 选项卡中添加简单UI，用于查看/修改 self.controller.global_values。
        动态获取已处理的文件列表和通道列表，供用户选择。
        """
        frame = self.global_params_tab

        # =========== 动态获取文件/通道列表 ===========
        file_list = self._get_file_list()
        ch_list   = self._get_channel_list()

        # 在列表前面插入一个 "ALL_FILES"/"ALL_CHANNELS" 选项，代表“全局”或“不区分通道”
        file_options = ["ALL_FILES"] + file_list
        channel_options = ["ALL_CHANNELS"] + ch_list

        # =========== GUI布局 ===========
        tk.Label(frame, text="FileKey:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.gp_file_var = tk.StringVar(value="ALL_FILES")
        self.gp_file_combo = ttk.Combobox(
            frame, textvariable=self.gp_file_var, values=file_options, width=20, state='readonly'
        )
        self.gp_file_combo.grid(row=0, column=1, sticky=tk.W, padx=5)

        tk.Label(frame, text="ChannelKey:").grid(row=0, column=2, sticky=tk.E, padx=5)
        self.gp_ch_var = tk.StringVar(value="ALL_CHANNELS")
        self.gp_ch_combo = ttk.Combobox(
            frame, textvariable=self.gp_ch_var, values=channel_options, width=20, state='readonly'
        )
        self.gp_ch_combo.grid(row=0, column=3, sticky=tk.W, padx=5)

        tk.Label(frame, text="ParamKey:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.gp_param_key = tk.StringVar(value="freq_to_remove")
        tk.Entry(frame, textvariable=self.gp_param_key, width=20).grid(row=1, column=1, sticky=tk.W, padx=5)

        tk.Label(frame, text="ParamValue:").grid(row=1, column=2, sticky=tk.E, padx=5)
        self.gp_param_val = tk.StringVar(value="50,120")
        tk.Entry(frame, textvariable=self.gp_param_val, width=20).grid(row=1, column=3, sticky=tk.W, padx=5)

        # 按钮区
        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=0, column=4, rowspan=2, padx=15)
        tk.Button(btn_frame, text="Set Param", command=self.on_set_global_param).pack(pady=5)
        tk.Button(btn_frame, text="Get Param", command=self.on_get_global_param).pack(pady=5)
        tk.Button(btn_frame, text="List All", command=self.on_list_all_global_params).pack(pady=5)

        # 下方文本区
        self.global_params_text = scrolledtext.ScrolledText(frame, width=80, height=15)
        self.global_params_text.grid(row=2, column=0, columnspan=5, padx=5, pady=5)

    def refresh_global_params_tab(self):
        """
        当文件处理完成、通道更新后，主动调用此方法，
        以更新“Global Params” Tab 上的文件下拉框、通道下拉框，避免重启软件。
        """
        file_list = self._get_file_list()
        ch_list = self._get_channel_list()

        file_options = ["ALL_FILES"] + file_list
        channel_options = ["ALL_CHANNELS"] + ch_list

        # 更新 ComboBox:
        # 1) File:
        self.gp_file_combo.configure(values=file_options)
        if file_options:
            self.gp_file_var.set(file_options[0])
        else:
            self.gp_file_var.set("ALL_FILES")

        # 2) Channel:
        self.gp_ch_combo.configure(values=channel_options)
        if channel_options:
            self.gp_ch_var.set(channel_options[0])
        else:
            self.gp_ch_var.set("ALL_CHANNELS")

    def _get_file_list(self):
        """
        从实际处理结果中收集“文件名”列表，若无 processing_results 或未处理，则返回空列表。
        """
        file_list = []
        if self.controller.processing_results:
            for f_res in self.controller.processing_results.files:
                fn = f_res.get('file_name')
                if fn and fn not in file_list:
                    file_list.append(fn)
        return file_list

    def _get_channel_list(self):
        """
        从实际的 channel_options 或者 processing_results 收集通道名称。
        这里演示取 self.controller.channel_options，您也可遍历 fft_results 里 channel_name。
        """
        ch_list = list(self.controller.channel_options)  # 若 channel_options 是个 set/list
        return ch_list

    def on_set_global_param(self):
        """
        将 ParamValue 写入 self.controller.global_values
        """
        if not hasattr(self.controller, "global_values"):
            messagebox.showwarning("警告", "controller.global_values 不存在！")
            return

        fkey = self.gp_file_var.get()
        ckey = self.gp_ch_var.get()
        pkey = self.gp_param_key.get().strip()
        val_str = self.gp_param_val.get().strip()

        # 简单解析
        final_val = val_str
        if "," in val_str:
            try:
                final_val = [float(x.strip()) for x in val_str.split(",")]
            except:
                pass
        else:
            try:
                final_val = float(val_str)
            except:
                pass

        # 写入 global_values
        self.controller.global_values.set_value(fkey, ckey, pkey, final_val)
        self._log_global_params(f"[Set Param] => ({fkey}, {ckey}, {pkey}) = {final_val}")

    def on_get_global_param(self):
        """
        从 self.controller.global_values 读取 exact匹配 (fkey, ckey, pkey)
        """
        if not hasattr(self.controller, "global_values"):
            messagebox.showwarning("警告", "controller.global_values 不存在！")
            return

        fkey = self.gp_file_var.get()
        ckey = self.gp_ch_var.get()
        pkey = self.gp_param_key.get().strip()

        val = self.controller.global_values.get_value_exact(fkey, ckey, pkey, default="(None)")
        self._log_global_params(f"[Get Param] => ({fkey}, {ckey}, {pkey}) => {val}")

    def on_list_all_global_params(self):
        """
        列出目前 global_values 里所有条目
        """
        if not hasattr(self.controller, "global_values"):
            messagebox.showwarning("警告", "controller.global_values 不存在！")
            return

        lines = self.controller.global_values.list_all_params()
        self._log_global_params("=== List All ===")
        for line in lines:
            self._log_global_params("  " + line)
        self._log_global_params("=== End ===")

    def _log_global_params(self, msg):
        self.global_params_text.insert(tk.END, msg + "\n")
        self.global_params_text.see(tk.END)

    def update_visualization_options(self, results):
        """
        同时从 self.controller.sensor_settings + results.files[*]['fft_results']
        中收集所有通道名称，用于多文件场景下也能显示新通道（自定义信号）。
        还负责更新文件名下拉菜单。
        """
        # --- 1) 收集所有“硬件传感器”名称 ---
        sensor_names = [s.name for s in self.controller.sensor_settings]

        # --- 2) 遍历多文件，收集在 fft_results 中出现的所有通道名（包括自定义信号） ---
        all_fft_names = set(sensor_names)  # 初始化 set
        for file_result in results.files:
            fft_list = file_result.get('fft_results', [])
            for fft_entry in fft_list:
                ch_name = fft_entry['fft_result'].name
                all_fft_names.add(ch_name)

        # --- 3) 合并之后转换成一个列表，赋给 self.channel_options ---
        self.channel_options = sorted(all_fft_names)  # 可以排序或不排序

        # 如果 channel_options 不为空，就设为第一个，否则设为空
        if self.channel_options:
            self.channel_var_spectrum.set(self.channel_options[0])
            self.channel_var_time.set(self.channel_options[0])
            self.channel_var_frf.set(self.channel_options[0])
        else:
            self.channel_var_spectrum.set('')
            self.channel_var_time.set('')
            self.channel_var_frf.set('')

        # --- 4) 更新下拉菜单（频谱/时域/FRF） ---
        self.file_menu_spectrum['values'] = self.file_options
        self.file_menu_time['values']     = self.file_options
        self.file_menu_frf['values']      = self.file_options

        self.channel_menu_spectrum['values'] = self.channel_options
        self.channel_menu_time['values']     = self.channel_options
        self.channel_menu_frf['values']      = self.channel_options

        # --- 5) 多文件场景下，更新文件选择下拉菜单 ---
        self.file_options = [file_result['file_name'] for file_result in results.files]
        if self.file_options:
            self.file_var_spectrum.set(self.file_options[0])
            self.file_var_time.set(self.file_options[0])
            self.file_var_frf.set(self.file_options[0])
        else:
            self.file_var_spectrum.set('')
            self.file_var_time.set('')
            self.file_var_frf.set('')












    # ====== 通用方法 ======
    def toggle_frame(self, frame, control_frame, toggle_button):
        if control_frame and control_frame.winfo_viewable():
            control_frame.grid_remove()
            frame.columnconfigure(2, weight=0)
            frame.columnconfigure(1, weight=0)
            frame.columnconfigure(0, weight=1)
            toggle_button.config(text="<<")
        elif control_frame:
            control_frame.grid()
            frame.columnconfigure(0, weight=1)
            frame.columnconfigure(1, weight=0)
            frame.columnconfigure(2, weight=0)
            toggle_button.config(text=">>")
            # 延时更新布局
            self.after(100, lambda: frame.columnconfigure(2, weight=0))
            self.after(100, lambda: frame.columnconfigure(1, weight=0))
            self.after(100, lambda: frame.columnconfigure(0, weight=1))
            self.after(100, lambda: frame.columnconfigure(2, weight=0))
            self.after(100, lambda: frame.columnconfigure(1, weight=0))
            self.after(100, lambda: frame.columnconfigure(0, weight=1))

    # ====== 工作模态(OMA)相关绘图方法 ======
    # 这些方法已经在 controller/app_controller.py 中实现，通过调用 refresh_fdd_plot 和 refresh_ssi_plot

    # ====== 方法结束 ======

