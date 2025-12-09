# view/main_window.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from matplotlib.font_manager import FontProperties
import os
import json

# ====== 新增：pyoma2 相关导入 ======
import mplcursors
from pyoma2.functions.gen import example_data
from pyoma2.setup.single import SingleSetup
from pyoma2.algorithms.fdd import FDD
from pyoma2.algorithms.ssi import SSIdat


from .dialogs import UserDefineDialog, SensorSettingsDialog, OmaParamDialog
from model.data_models import SensorSettings

# 用户配置文件路径：放在项目根目录，保存上一次启动时的数据处理主界面的常用参数
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
USER_SETTINGS_FILE = os.path.join(_BASE_DIR, "user_settings.json")

class MainWindow(tk.Tk):
    """
    主界面: 包含 Notebook, 数据处理, 频谱分析, 时域信号, 频响函数, 工作模态(OMA) 五个 Tab,
    以及用户自定义脚本等。
    """
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.last_oma_channels_for_file = {}
        self.title("FFT 数据处理")
        try:
            self.font_prop = FontProperties(fname='SimHei.ttf')  # 确保字体文件存在
        except:
            self.font_prop = None  # 使用默认字体

        # 初始化变量
        self.init_variables()
        # 在创建界面前，尝试加载用户上一次保存的设置（路径、采样率等）
        self.load_user_settings()

        self.canvas_oma = None
        self.fig_oma = None
        # 创建 Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 绑定复制、粘贴快捷键
        self.bind_copy_paste(self)
        self.create_tabs()

        # 拦截窗口关闭事件：先保存用户设置，再正常退出
        self.protocol("WM_DELETE_WINDOW", self.on_close)

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
        # 切分分析变量
        self.segment_mode_var = tk.BooleanVar(value=False)  # 是否启用切分模式
        self.segment_length_var = tk.StringVar(value="1.0")  # 切分长度（秒）
        self.segment_overlap_var = tk.StringVar(value="50")  # 重叠率（%）
        self.segment_window_var = tk.StringVar(value="Hanning")  # 窗函数
        self.segment_current_idx = 0  # 当前段索引
        self.segment_total_count = 0  # 总段数
        self.segment_slider = None  # 滑块控件引用
        self.segment_info_label = None  # 段信息标签引用
        # 时域信号变量
        # 注意：time_lower/upper_display_var 为“用户当前想看的时间窗口”，
        # 在同一个文件内切换通道时，我们希望保持这个窗口不变，便于对比。
        self.file_var_time = tk.StringVar()
        self.channel_var_time = tk.StringVar()
        self.time_lower_display_var = tk.StringVar(value="0")
        self.time_upper_display_var = tk.StringVar()  # 初始值留空，在显示时动态设置为总时长
        self.y_axis_auto_scale_var_time = tk.BooleanVar(value=True)
        self.y_axis_min_var_time = tk.StringVar()
        self.y_axis_max_var_time = tk.StringVar()
        # 记录上一次绘图使用的文件，用于判断是否需要重置时间范围
        self.last_plotted_file = None
        # 播放/交互相关状态（时域音频）
        self.time_audio_is_playing = False
        self.time_audio_stop_flag = False
        self.time_audio_thread = None
        self.time_ax = None                  # 时域主坐标轴引用，用于绘制红线
        self.time_play_line = None           # 播放指示红线
        self.time_audio_segment_start_sec = 0.0
        self.time_audio_segment_end_sec = 0.0
        self.time_audio_start_walltime = None
        self.time_audio_duration = 0.0
        self.time_audio_update_job = None    # Tk after 任务句柄，用于更新播放指示线
        self.time_motion_cid = None  # mpl_connect 句柄，避免重复绑定导致卡顿
        # 新增：用于控制是否将当前时间范围应用于频谱分析
        self.apply_truncation_to_spectrum_var = tk.BooleanVar(value=False)
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

        # 用于防止同步回调无限循环的标志
        self._syncing_file = False
        self._syncing_channel = False

    # ====== 用户设置的加载/保存（路径、采样率等） ======
    def load_user_settings(self):
        """
        从 USER_SETTINGS_FILE 读取上次运行时保存的基础参数，
        目前包含：输入/输出文件夹、文件名前缀、采样率。
        """
        if not os.path.exists(USER_SETTINGS_FILE):
            return
        try:
            with open(USER_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            # 读取失败不阻塞启动，只简单提示一次
            try:
                messagebox.showwarning("警告", f"读取用户配置失败，将使用默认参数。\n{e}")
            except Exception:
                # 在某些环境下 messagebox 还未准备好，直接忽略
                pass
            return

        self.input_folder_var.set(data.get("input_folder", ""))
        self.output_folder_var.set(data.get("output_folder", ""))
        self.filename_prefix_var.set(data.get("filename_prefix", "激励"))
        self.sampling_rate_var.set(str(data.get("sampling_rate", "25600")))

    def save_user_settings(self):
        """
        将当前基础参数写入 USER_SETTINGS_FILE，供下次启动自动恢复。
        """
        data = {
            "input_folder": self.input_folder_var.get(),
            "output_folder": self.output_folder_var.get(),
            "filename_prefix": self.filename_prefix_var.get(),
            "sampling_rate": self.sampling_rate_var.get(),
        }
        try:
            with open(USER_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            try:
                messagebox.showwarning("警告", f"保存用户配置失败：{e}")
            except Exception:
                pass

    def on_close(self):
        """
        关闭主窗口前，先把常用参数持久化到本地文件。
        """
        try:
            self.save_user_settings()
        finally:
            self.destroy()

    # ====== 文件/通道选择同步 ======
    def _sync_file_selection(self, source):
        """
        当某个 tab 的文件选择变化时，同步到其他 tab。
        source: 'spectrum', 'time', 或 'frf'
        """
        if self._syncing_file:
            return
        self._syncing_file = True
        try:
            if source == 'spectrum':
                value = self.file_var_spectrum.get()
            elif source == 'time':
                value = self.file_var_time.get()
            else:  # frf
                value = self.file_var_frf.get()

            # 同步到其他两个 tab
            if source != 'spectrum':
                self.file_var_spectrum.set(value)
            if source != 'time':
                self.file_var_time.set(value)
            if source != 'frf':
                self.file_var_frf.set(value)
        finally:
            self._syncing_file = False

    def _sync_channel_selection(self, source):
        """
        当某个 tab 的通道选择变化时，同步到其他 tab。
        source: 'spectrum', 'time', 或 'frf'
        """
        if self._syncing_channel:
            return
        self._syncing_channel = True
        try:
            if source == 'spectrum':
                value = self.channel_var_spectrum.get()
            elif source == 'time':
                value = self.channel_var_time.get()
            else:  # frf
                value = self.channel_var_frf.get()

            # 同步到其他两个 tab
            if source != 'spectrum':
                self.channel_var_spectrum.set(value)
            if source != 'time':
                self.channel_var_time.set(value)
            if source != 'frf':
                self.channel_var_frf.set(value)
        finally:
            self._syncing_channel = False

    def _on_file_selected_spectrum(self, event=None):
        self._sync_file_selection('spectrum')

    def _on_file_selected_time(self, event=None):
        self._sync_file_selection('time')

    def _on_file_selected_frf(self, event=None):
        self._sync_file_selection('frf')

    def _on_channel_selected_spectrum(self, event=None):
        self._sync_channel_selection('spectrum')

    def _on_channel_selected_time(self, event=None):
        self._sync_channel_selection('time')

    def _on_channel_selected_frf(self, event=None):
        self._sync_channel_selection('frf')

    def create_tabs(self):
        # 数据处理选项卡
        self.processing_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.processing_tab, text='数据处理')
        self.create_processing_widgets()
        
        # 时域信号选项卡 (移到频谱之前)
        self.time_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.time_tab, text='时域信号')
        self.create_time_widgets()
        
        # 频谱分析选项卡
        self.spectrum_analysis_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.spectrum_analysis_tab, text='频谱分析')
        self.create_spectrum_analysis_widgets()
        
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
        # 默认禁用可视化选项卡 (注意索引变化)
        self.notebook.tab(1, state='disabled')  # 时域信号
        self.notebook.tab(2, state='disabled')  # 频谱分析
        self.notebook.tab(3, state='disabled')  # 频响函数
        self.notebook.tab(4, state='disabled')  # 工作模态(OMA)

    def enable_visualization_tabs(self):
        # 启用可视化选项卡 (注意索引变化)
        self.notebook.tab(1, state='normal')  # 时域信号
        self.notebook.tab(2, state='normal')  # 频谱分析
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
        # （示例把它放在与"开始处理"同一行，也可自行调整 row/column）

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
        在处理完成后，允许启用"用户自定义"按钮。
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
        self.file_menu_spectrum.bind('<<ComboboxSelected>>', self._on_file_selected_spectrum)

        # 通道选择
        tk.Label(control_frame, text="选择通道:").pack(anchor=tk.W, padx=5, pady=5)
        self.channel_menu_spectrum = ttk.Combobox(control_frame, textvariable=self.channel_var_spectrum, values=self.channel_options, state='readonly')
        self.channel_menu_spectrum.pack(anchor=tk.W, padx=5, pady=5)
        self.channel_menu_spectrum.bind('<<ComboboxSelected>>', self._on_channel_selected_spectrum)

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

        # ====== 切分分析区域 ======
        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', padx=5, pady=10)
        tk.Label(control_frame, text="── 切分分析 ──", font=('TkDefaultFont', 9, 'bold')).pack(anchor=tk.W, padx=5)

        # 启用切分模式复选框
        tk.Checkbutton(control_frame, text="启用切分模式", variable=self.segment_mode_var,
                       command=self.toggle_segment_mode).pack(anchor=tk.W, padx=5, pady=2)

        # 切分参数 Frame（可隐藏）
        self.segment_params_frame = tk.Frame(control_frame)

        # 切分长度
        seg_len_frame = tk.Frame(self.segment_params_frame)
        seg_len_frame.pack(anchor=tk.W, padx=5, pady=2)
        tk.Label(seg_len_frame, text="切分长度(秒):").pack(side=tk.LEFT)
        tk.Entry(seg_len_frame, textvariable=self.segment_length_var, width=8).pack(side=tk.LEFT, padx=5)

        # 重叠率
        seg_overlap_frame = tk.Frame(self.segment_params_frame)
        seg_overlap_frame.pack(anchor=tk.W, padx=5, pady=2)
        tk.Label(seg_overlap_frame, text="重叠率(%):").pack(side=tk.LEFT)
        tk.Entry(seg_overlap_frame, textvariable=self.segment_overlap_var, width=8).pack(side=tk.LEFT, padx=5)

        # 窗函数选择
        seg_window_frame = tk.Frame(self.segment_params_frame)
        seg_window_frame.pack(anchor=tk.W, padx=5, pady=2)
        tk.Label(seg_window_frame, text="窗函数:").pack(side=tk.LEFT)
        window_options = ["Hanning", "Hamming", "Blackman", "矩形", "Flattop"]
        self.segment_window_menu = ttk.Combobox(seg_window_frame, textvariable=self.segment_window_var,
                                                 values=window_options, state='readonly', width=10)
        self.segment_window_menu.pack(side=tk.LEFT, padx=5)

        # 导航控制 Frame
        nav_frame = tk.Frame(self.segment_params_frame)
        nav_frame.pack(anchor=tk.W, padx=5, pady=5)

        # 前进/后退按钮和段信息
        tk.Button(nav_frame, text="◄", width=3, command=self.segment_prev).pack(side=tk.LEFT)
        self.segment_info_label = tk.Label(nav_frame, text="0 / 0", width=10)
        self.segment_info_label.pack(side=tk.LEFT, padx=5)
        tk.Button(nav_frame, text="►", width=3, command=self.segment_next).pack(side=tk.LEFT)

        # 时间范围显示
        self.segment_time_label = tk.Label(self.segment_params_frame, text="时间: 0.0s - 0.0s")
        self.segment_time_label.pack(anchor=tk.W, padx=5, pady=2)

        # 滑块
        self.segment_slider = tk.Scale(self.segment_params_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                                        length=200, command=self.on_segment_slider_change)
        self.segment_slider.pack(anchor=tk.W, padx=5, pady=2)

        # 默认隐藏切分参数
        self.segment_params_frame.pack_forget()

        # 绘制按钮和保存按钮
        button_frame = tk.Frame(control_frame)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="绘制", command=self.plot_spectrum_analysis).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="保存图片", command=self.save_spectrum_analysis_plot).pack(side=tk.LEFT, padx=5)
        # 添加"保存数据"按钮
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

    # ====== 切分分析相关函数 ======
    def toggle_segment_mode(self):
        """切换切分模式的显示/隐藏"""
        if self.segment_mode_var.get():
            self.segment_params_frame.pack(anchor=tk.W, padx=5, pady=5)
        else:
            self.segment_params_frame.pack_forget()

    def segment_prev(self):
        """切换到上一段"""
        if self.segment_current_idx > 0:
            self.segment_current_idx -= 1
            self.segment_slider.set(self.segment_current_idx)
            self.update_segment_info()
            self.plot_spectrum_analysis()

    def segment_next(self):
        """切换到下一段"""
        if self.segment_current_idx < self.segment_total_count - 1:
            self.segment_current_idx += 1
            self.segment_slider.set(self.segment_current_idx)
            self.update_segment_info()
            self.plot_spectrum_analysis()

    def on_segment_slider_change(self, value):
        """滑块值改变时的回调"""
        new_idx = int(float(value))
        if new_idx != self.segment_current_idx:
            self.segment_current_idx = new_idx
            self.update_segment_info()
            self.plot_spectrum_analysis()

    def update_segment_info(self):
        """更新段信息显示"""
        if self.segment_total_count > 0:
            self.segment_info_label.config(text=f"{self.segment_current_idx + 1} / {self.segment_total_count}")
            # 计算当前段的时间范围
            seg_start, seg_end = self.get_segment_time_range(self.segment_current_idx)
            self.segment_time_label.config(text=f"时间: {seg_start:.2f}s - {seg_end:.2f}s")
        else:
            self.segment_info_label.config(text="0 / 0")
            self.segment_time_label.config(text="时间: 0.0s - 0.0s")

    def get_segment_time_range(self, idx):
        """获取指定段的时间范围"""
        try:
            seg_length = float(self.segment_length_var.get())
            overlap_pct = float(self.segment_overlap_var.get()) / 100.0
            step = seg_length * (1 - overlap_pct)
            start_time = idx * step
            end_time = start_time + seg_length
            return start_time, end_time
        except ValueError:
            return 0.0, 0.0

    def calculate_segment_count(self, total_duration):
        """根据总时长和切分参数计算总段数"""
        try:
            seg_length = float(self.segment_length_var.get())
            overlap_pct = float(self.segment_overlap_var.get()) / 100.0
            if seg_length <= 0:
                return 0
            step = seg_length * (1 - overlap_pct)
            if step <= 0:
                step = seg_length  # 防止无限段
            # 计算可以切出多少段
            count = int((total_duration - seg_length) / step) + 1
            return max(count, 1) if total_duration >= seg_length else 0
        except ValueError:
            return 0

    def get_window_function(self, n):
        """根据选择返回窗函数数组"""
        window_name = self.segment_window_var.get()
        if window_name == "Hanning":
            return np.hanning(n)
        elif window_name == "Hamming":
            return np.hamming(n)
        elif window_name == "Blackman":
            return np.blackman(n)
        elif window_name == "Flattop":
            # scipy 的 flattop 窗
            from scipy.signal import windows
            return windows.flattop(n)
        else:  # 矩形窗
            return np.ones(n)

    def compute_segment_spectrum(self, data, sampling_rate, seg_idx):
        """计算指定段的频谱"""
        try:
            seg_length = float(self.segment_length_var.get())
            overlap_pct = float(self.segment_overlap_var.get()) / 100.0
        except ValueError:
            return None, None

        step = seg_length * (1 - overlap_pct)
        start_time = seg_idx * step
        end_time = start_time + seg_length

        # 转换为采样点索引
        start_idx = int(start_time * sampling_rate)
        end_idx = int(end_time * sampling_rate)

        if start_idx >= len(data) or end_idx > len(data):
            return None, None

        segment_data = data[start_idx:end_idx]
        n = len(segment_data)
        if n == 0:
            return None, None

        # 应用窗函数
        window = self.get_window_function(n)
        windowed_data = segment_data * window

        # 计算 FFT
        fft_result = np.fft.fft(windowed_data)
        freq = np.fft.fftfreq(n, 1.0 / sampling_rate)

        # 只取正频率部分
        positive_mask = freq >= 0
        freq = freq[positive_mask]
        amplitude = np.abs(fft_result[positive_mask]) * 2 / n  # 单边幅值

        # 窗函数幅值修正（可选，这里简单补偿）
        window_sum = np.sum(window)
        if window_sum > 0:
            amplitude = amplitude * n / window_sum

        return freq, amplitude

    def plot_spectrum_analysis(self):
        """
        当用户点击"绘制"时:
          1) 检查 file, channel
          2) 调用 controller.get_spectrum_data(file, channel) => freq, amplitude
             或在切分模式下，从时域数据计算切分段的频谱
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

        # 判断是否启用切分模式
        segment_mode = self.segment_mode_var.get()
        title_suffix = ""  # 用于在标题中显示时间范围

        if segment_mode:
            # 切分模式：从时域数据计算当前段的频谱
            time_data = self.controller.get_time_domain_data(selected_file, selected_channel)
            if time_data is None:
                messagebox.showwarning("警告", "未找到对应的时域数据！")
                return

            sampling_rate = float(self.controller.params.sampling_rate) if self.controller.params else 25600.0
            total_duration = len(time_data) / sampling_rate

            # 计算总段数并更新 UI
            self.segment_total_count = self.calculate_segment_count(total_duration)
            if self.segment_total_count == 0:
                messagebox.showwarning("警告", "切分长度超过数据总时长，无法切分！")
                return

            # 确保当前索引在有效范围内
            if self.segment_current_idx >= self.segment_total_count:
                self.segment_current_idx = self.segment_total_count - 1
            if self.segment_current_idx < 0:
                self.segment_current_idx = 0

            # 更新滑块范围
            self.segment_slider.config(from_=0, to=max(0, self.segment_total_count - 1))
            self.segment_slider.set(self.segment_current_idx)
            self.update_segment_info()

            # 计算当前段的频谱
            freq, amplitude = self.compute_segment_spectrum(time_data, sampling_rate, self.segment_current_idx)
            if freq is None or amplitude is None:
                messagebox.showwarning("警告", "计算切分段频谱失败！")
                return

            # 获取时间范围用于标题
            seg_start, seg_end = self.get_segment_time_range(self.segment_current_idx)
            title_suffix = f" [{seg_start:.2f}s - {seg_end:.2f}s]"
        else:
            # 非切分模式：使用原有逻辑
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
        ax.set_title(f"频谱分析 - {selected_channel}{title_suffix}", fontproperties=self.font_prop)
        ax.set_xlabel("频率 (Hz)", fontproperties=self.font_prop)
        ax.set_ylabel(y_label, fontproperties=self.font_prop)
        ax.legend(prop=self.font_prop)
        ax.grid()

        # 设置x轴范围为用户设置的频率范围
        ax.set_xlim(freq_lower_display, freq_upper_display)

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
        selected_file = self.file_var_spectrum.get()
        selected_channel = self.channel_var_spectrum.get()
        # 使用文件名+传感器名作为默认文件名
        default_filename = f"{selected_file}_{selected_channel}.png" if selected_file and selected_channel else ""
        
        file_path = filedialog.asksaveasfilename(title="保存图片", defaultextension=".png",
                                                 filetypes=[("PNG 文件", "*.png"), ("JPEG 文件", "*.jpg"), ("所有文件", "*.*")],
                                                 initialfile=default_filename)
        if file_path:
            self.figure_spectrum_analysis.savefig(file_path)
            messagebox.showinfo("成功", "图片已保存！")

    def save_spectrum_data(self):
        if not hasattr(self, 'current_freq_data') or not hasattr(self, 'current_amplitude_data'):
            messagebox.showwarning("警告", "没有可保存的数据，请先绘制频谱。")
            return

        selected_file = self.file_var_spectrum.get()
        selected_channel = self.channel_var_spectrum.get()
        # 使用文件名+传感器名作为默认文件名
        default_filename = f"{selected_file}_{selected_channel}.txt" if selected_file and selected_channel else ""
        
        # 让用户选择保存文件的位置
        file_path = filedialog.asksaveasfilename(title="保存数据", defaultextension=".txt",
                                                 filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                                                 initialfile=default_filename)
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
        self.file_menu_time.bind('<<ComboboxSelected>>', self._on_file_selected_time)

        # 通道选择
        tk.Label(control_frame, text="选择通道:").pack(anchor=tk.W, padx=5, pady=5)
        self.channel_menu_time = ttk.Combobox(control_frame, textvariable=self.channel_var_time, values=self.channel_options, state='readonly')
        self.channel_menu_time.pack(anchor=tk.W, padx=5, pady=5)
        self.channel_menu_time.bind('<<ComboboxSelected>>', self._on_channel_selected_time)

        # 时域显示范围
        tk.Label(control_frame, text="时间显示范围 (秒):").pack(anchor=tk.W, padx=5, pady=5)
        time_display_frame = tk.Frame(control_frame)
        time_display_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Entry(time_display_frame, textvariable=self.time_lower_display_var, width=10).pack(side=tk.LEFT)
        tk.Label(time_display_frame, text=" - ").pack(side=tk.LEFT)
        tk.Entry(time_display_frame, textvariable=self.time_upper_display_var, width=10).pack(side=tk.LEFT)

        # 恢复/添加 时域信号截断按钮 (注意调整布局，避免与下方复选框重叠)
        truncate_button_frame = tk.Frame(control_frame) # 使用单独的Frame
        truncate_button_frame.pack(anchor=tk.W, padx=5, pady=2) # 调整pady
        tk.Button(truncate_button_frame, text="截断并生成新分析结果", 
                  command=self.truncate_signal).pack(side=tk.LEFT, padx=0)
        # 可选：添加简短说明
        # tk.Label(truncate_button_frame, text="(基于上方时间范围)").pack(side=tk.LEFT, padx=5)

        # Y轴范围 Frame
        y_range_frame = tk.Frame(control_frame)
        y_range_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Checkbutton(y_range_frame, text="自动缩放", variable=self.y_axis_auto_scale_var_time).pack(side=tk.LEFT)
        tk.Label(y_range_frame, text="最小值:").pack(side=tk.LEFT)
        tk.Entry(y_range_frame, textvariable=self.y_axis_min_var_time, width=10).pack(side=tk.LEFT)
        tk.Label(y_range_frame, text="最大值:").pack(side=tk.LEFT)
        tk.Entry(y_range_frame, textvariable=self.y_axis_max_var_time, width=10).pack(side=tk.LEFT)

        # 应用时间范围到后续分析的控件 (动态过滤)
        spectrum_apply_frame = tk.Frame(control_frame)
        spectrum_apply_frame.pack(anchor=tk.W, padx=5, pady=5)
        tk.Checkbutton(spectrum_apply_frame, text="将此时间范围用于后续分析 (频谱/OMA)", # 修改标签文本
                       variable=self.apply_truncation_to_spectrum_var,
                       command=self.toggle_spectrum_truncation).pack(side=tk.LEFT)

        # 绘制 / 播放 / 停止 / 保存按钮
        button_frame = tk.Frame(control_frame)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="绘制", command=self.plot_time_domain).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="播放声音", command=self.play_time_segment_audio).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="停止播放", command=self.stop_time_audio_playback).pack(side=tk.LEFT, padx=5)
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

        # 若正在播放上一段音频，先请求停止，避免一边重绘一边播放造成卡顿
        self.stop_time_audio_playback()

        # 获取对应的时域数据
        data_converted = self.controller.get_time_domain_data(selected_file, selected_channel)
        if data_converted is None:
            messagebox.showwarning("警告", "未找到对应的通道数据！")
            return

        # 计算时间向量和总时长
        sampling_rate = float(self.controller.params.sampling_rate) if self.controller.params else 25600
        total_length = len(data_converted)
        t = np.linspace(0, total_length / sampling_rate, total_length, endpoint=False)
        total_time = total_length / sampling_rate
        
        # 如果上限为空或选择了新的文件，则设置为完整时间范围。
        # 仅在“文件变化”时重置时间范围；在同一文件内切换通道时保持用户设定，方便对比不同通道。
        if not self.time_upper_display_var.get() or self.last_plotted_file != selected_file:
            self.time_lower_display_var.set("0")
            self.time_upper_display_var.set(f"{total_time:.4f}")
            # 记录当前显示的文件
            self.last_plotted_file = selected_file

        try:
            time_start = float(self.time_lower_display_var.get())
            time_end = float(self.time_upper_display_var.get())
            if not (0 <= time_start < time_end <= total_time):
                messagebox.showwarning("警告", f"时间范围应在 0 到 {total_time:.4f} 秒之间，且起始值小于结束值！")
                return
        except ValueError:
            messagebox.showwarning("警告", "时间范围必须是数字！")
            return

        # 根据实际时间值计算索引
        start_idx = int(time_start * sampling_rate)
        end_idx = min(int(time_end * sampling_rate) + 1, total_length)
        t_segment = t[start_idx:end_idx]
        data_segment = data_converted[start_idx:end_idx]

        # 清除之前的图像
        self.figure_time.clear()
        # 上方：时域波形；下方：时间-频率分析图（谱图）
        ax = self.figure_time.add_subplot(211)
        ax_spec = self.figure_time.add_subplot(212, sharex=ax)
        self.figure_time.tight_layout()

        # 保存当前坐标轴引用，用于后续绘制播放指示红线
        self.time_ax = ax
        # 每次重绘时域图时，清空旧的播放指示线引用
        self.time_play_line = None

        # 为了减少大数据量绘图时的卡顿，对显示数据进行适当下采样
        max_points = 5000  # 屏幕上最多画这么多点，一般已经足够观察趋势
        if len(t_segment) > max_points:
            step = max(1, len(t_segment) // max_points)
            t_plot = t_segment[::step]
            data_plot = data_segment[::step]
        else:
            t_plot = t_segment
            data_plot = data_segment

        ax.plot(t_plot, data_plot, label=selected_channel)
        ax.set_title(f"时域信号 - {selected_channel}", fontproperties=self.font_prop)
        ax.set_xlabel("时间 (s)", fontproperties=self.font_prop)
        ax.set_ylabel("幅值", fontproperties=self.font_prop)
        ax.legend(prop=self.font_prop)
        ax.grid()

        # 设置x轴范围为用户设置的时间范围
        time_absolute_start = t[start_idx]
        time_absolute_end = t[end_idx-1]
        ax.set_xlim(time_absolute_start, time_absolute_end)

        # Y 轴自动缩放 vs 手动设置（针对上方时域波形）
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

        # ====== 下方：时间-频率分析图（谱图） ======
        try:
            from scipy.signal import spectrogram

            # 选择合适的窗口长度，避免对很长数据导致计算过慢
            # 经验：nperseg 至少 256，至多 4096，且不超过数据长度
            default_nperseg = 1024
            nperseg = min(max(256, default_nperseg), len(data_segment))
            noverlap = nperseg // 2

            f_spec, t_spec, Sxx = spectrogram(
                data_segment,
                fs=sampling_rate,
                nperseg=nperseg,
                noverlap=noverlap,
                scaling="density",
                mode="magnitude",
            )

            # 转换为 dB，避免 log(0)
            Sxx_db = 20 * np.log10(Sxx + 1e-12)

            # --- 降采样谱图维度，避免绘制超大矩阵导致卡顿 ---
            max_freq_bins = 256
            max_time_bins = 512

            n_freq, n_time = Sxx_db.shape
            if n_freq > max_freq_bins:
                step_f = max(1, n_freq // max_freq_bins)
                Sxx_db = Sxx_db[::step_f, :]
                f_spec = f_spec[::step_f]
                n_freq = Sxx_db.shape[0]

            if n_time > max_time_bins:
                step_t = max(1, n_time // max_time_bins)
                Sxx_db = Sxx_db[:, ::step_t]
                t_spec = t_spec[::step_t]
                n_time = Sxx_db.shape[1]

            # t_spec 是相对时间，从 0 开始；加上 time_start，变成绝对时间
            t_spec_abs = t_spec + time_start

            # 使用 imshow 而不是 pcolormesh，把谱图当成一张"图片"绘制，性能更好
            if n_freq > 0 and n_time > 0:
                # 频率范围用于设置 extent 和对数坐标
                f_min_raw = float(f_spec[0])
                f_max_raw = float(f_spec[-1])
                # 避免 f_min 为 0
                f_min = f_min_raw if f_min_raw > 0 else max(1.0, sampling_rate / 1e6)
                f_max = f_max_raw if f_max_raw > f_min else sampling_rate / 2.0

                extent = [
                    float(t_spec_abs[0]),
                    float(t_spec_abs[-1]),
                    f_min,
                    f_max,
                ]

                im = ax_spec.imshow(
                    Sxx_db,
                    origin="lower",
                    aspect="auto",
                    extent=extent,
                    cmap="viridis",
                )

                ax_spec.set_ylabel("频率 (Hz)", fontproperties=self.font_prop)
                ax_spec.set_xlabel("时间 (s)", fontproperties=self.font_prop)

                # 纵轴使用对数刻度（频率对数变化）
                ax_spec.set_yscale("log")
                ax_spec.set_ylim(f_min, f_max)
                ax_spec.set_xlim(time_absolute_start, time_absolute_end)

                # 添加颜色条，显示幅值（dB），放在下方，保证与时域信号的横坐标对齐
                cbar = self.figure_time.colorbar(
                    im,
                    ax=ax_spec,
                    orientation="horizontal",
                    pad=0.15,
                )
                cbar.set_label("幅值 (dB)")
            else:
                ax_spec.text(
                    0.5,
                    0.5,
                    "谱图数据为空",
                    ha="center",
                    va="center",
                    transform=ax_spec.transAxes,
                )
                ax_spec.set_axis_off()
        except Exception as e:
            # 谱图计算失败时，不影响上面的时域图
            ax_spec.text(
                0.5,
                0.5,
                f"谱图计算失败:\n{e}",
                ha="center",
                va="center",
                transform=ax_spec.transAxes,
            )
            ax_spec.set_axis_off()

        # 添加交互式光标（仅在上方时域波形上）
        vertical_line = ax.axvline(color='k', linestyle='--', alpha=0.5)
        horizontal_line = ax.axhline(color='k', linestyle='--', alpha=0.5)

        # 创建独立的播放指示红线（不与十字光标共用，避免冲突）
        play_line = ax.axvline(color='r', linestyle='-', alpha=0.0, linewidth=2)  # 初始透明
        self.time_play_line = play_line
        annotation = ax.annotate('', xy=(0, 0), xytext=(10, 10), textcoords='offset points',
                                 bbox=dict(boxstyle='round', fc='w'),
                                 fontsize=8, fontproperties=self.font_prop)

        def mouse_move(event):
            # 十字光标与播放红线现在是独立的，无需检查播放状态
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

        # 避免重复绑定过多的 motion 事件导致回调堆积，引起卡顿
        if self.time_motion_cid is not None:
            try:
                self.canvas_time.mpl_disconnect(self.time_motion_cid)
            except Exception:
                pass
            self.time_motion_cid = None

        self.time_motion_cid = self.canvas_time.mpl_connect('motion_notify_event', mouse_move)
        self.canvas_time.draw()

    def play_time_segment_audio(self):
        """
        根据当前“时间显示范围(秒)”播放该时间段的时域信号。
        使用后台线程+PyAudio 播放音频本身。目前不再绘制播放红线，专注保证声音流畅。
        """
        if self.time_audio_is_playing:
            messagebox.showinfo("提示", "当前正在播放，请先点击“停止播放”再重新播放。")
            return

        selected_file = self.file_var_time.get()
        selected_channel = self.channel_var_time.get()
        if not selected_file or not selected_channel:
            messagebox.showwarning("警告", "请选择文件和通道！")
            return

        # 获取时域数据
        data_converted = self.controller.get_time_domain_data(selected_file, selected_channel)
        if data_converted is None:
            messagebox.showwarning("警告", "未找到对应的通道数据！")
            return

        # 采样率和总时长
        sampling_rate = float(self.controller.params.sampling_rate) if self.controller.params else 25600.0
        total_length = len(data_converted)
        total_time = total_length / sampling_rate

        # 读取当前设定的时间范围
        try:
            time_start = float(self.time_lower_display_var.get())
            time_end = float(self.time_upper_display_var.get())
            if not (0 <= time_start < time_end <= total_time):
                messagebox.showwarning("警告", f"时间范围应在 0 到 {total_time:.4f} 秒之间，且起始值小于结束值！")
                return
        except ValueError:
            messagebox.showwarning("警告", "时间范围必须是数字！")
            return

        # 根据时间范围截取数据
        start_idx = int(time_start * sampling_rate)
        end_idx = min(int(time_end * sampling_rate) + 1, total_length)
        segment = np.asarray(data_converted[start_idx:end_idx], dtype=np.float32)

        if segment.size < 100:
            messagebox.showwarning("警告", "选定时间段太短，无法播放！")
            return

        # 归一化到 [-1, 1]，再转成 float32，避免爆音
        max_abs = float(np.max(np.abs(segment)))
        if max_abs <= 0:
            messagebox.showwarning("警告", "该时间段信号幅值为 0，无法播放！")
            return
        segment_norm = np.clip(segment / max_abs, -1.0, 1.0).astype(np.float32)

        # 记录当前播放段信息，供红线更新使用
        self.time_audio_segment_start_sec = time_start
        self.time_audio_segment_end_sec = time_end
        self.time_audio_duration = max(time_end - time_start, 1e-6)
        self.time_audio_start_walltime = None
        # 重置播放控制标志
        self.time_audio_stop_flag = False
        # 在主线程提前设置播放状态，避免定时器竞态条件
        self.time_audio_is_playing = True

        import threading
        import time as _time

        def worker():
            import pyaudio
            from scipy.signal import resample
            p = None
            stream = None
            try:
                # 首先尝试使用原始采样率
                play_rate = int(sampling_rate)
                segment_play = segment_norm
                data_int16 = np.int16(segment_play * 32767)

                p = pyaudio.PyAudio()
                try:
                    stream = p.open(format=pyaudio.paInt16,
                                    channels=1,
                                    rate=play_rate,
                                    output=True)
                except Exception:
                    # 如果声卡不支持该采样率，则重采样到 44100 Hz 再试
                    if stream is not None:
                        stream.close()
                    if p is not None:
                        p.terminate()
                    p = pyaudio.PyAudio()
                    target_rate = 44100
                    num_samples = int(len(segment_norm) * target_rate / sampling_rate)
                    if num_samples <= 0:
                        raise ValueError("重采样后的长度无效")
                    segment_play = resample(segment_norm, num_samples).astype(np.float32)
                    data_int16 = np.int16(segment_play * 32767)
                    play_rate = target_rate
                    stream = p.open(format=pyaudio.paInt16,
                                    channels=1,
                                    rate=play_rate,
                                    output=True)

                # 记录 wall-clock 起始时间（在实际开始播放前）
                self.time_audio_start_walltime = _time.perf_counter()

                total_samples = len(data_int16)
                if total_samples <= 0:
                    return
                # 仅用于音频缓冲的 chunk
                chunk = 4096
                idx = 0
                while idx < total_samples and not self.time_audio_stop_flag:
                    end = min(idx + chunk, total_samples)
                    chunk_bytes = data_int16[idx:end].tobytes()
                    stream.write(chunk_bytes)
                    idx = end

                # 播放结束后不强制清除光标，保留在最后位置
            except Exception as e:
                err_msg = f"播放音频失败：{e}"
                self.after(0, lambda: messagebox.showerror("错误", err_msg))
            finally:
                if stream is not None:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass
                if p is not None:
                    try:
                        p.terminate()
                    except Exception:
                        pass
                self.time_audio_is_playing = False
                self.time_audio_stop_flag = False

        # 启动后台线程播放
        self.time_audio_thread = threading.Thread(target=worker, daemon=True)
        self.time_audio_thread.start()

        # 启动 UI 定时器，用于根据时间更新播放红线
        self.start_time_play_line_timer()

    def stop_time_audio_playback(self):
        """停止当前的时域音频播放。"""
        if self.time_audio_is_playing:
            self.time_audio_stop_flag = True
        # 停止红线定时器
        if self.time_audio_update_job is not None:
            try:
                self.after_cancel(self.time_audio_update_job)
            except Exception:
                pass
            self.time_audio_update_job = None

    def start_time_play_line_timer(self):
        """
        使用 Tk 的定时器，根据 wall-clock 时间更新时域图上的播放指示红线。
        为了简单可靠，这里使用整图重绘（draw_idle），音频播放由后台线程完成，
        不会被绘图阻塞。
        """
        # 若有旧的定时任务，先取消
        if self.time_audio_update_job is not None:
            try:
                self.after_cancel(self.time_audio_update_job)
            except Exception:
                pass
            self.time_audio_update_job = None

        def _update():
            # 播放已结束或被停止
            if not self.time_audio_is_playing:
                # 播放结束，隐藏红线
                if self.time_play_line is not None:
                    self.time_play_line.set_alpha(0.0)
                    try:
                        self.canvas_time.draw_idle()
                    except Exception:
                        pass
                self.time_audio_update_job = None
                return

            # 尚未拿到播放开始时间，稍后再试
            if self.time_audio_start_walltime is None:
                self.time_audio_update_job = self.after(30, _update)
                return

            import time as _time
            elapsed = _time.perf_counter() - self.time_audio_start_walltime
            duration = max(self.time_audio_duration, 1e-6)
            progress = min(max(elapsed / duration, 0.0), 1.0)

            cur_t = self.time_audio_segment_start_sec + \
                    (self.time_audio_segment_end_sec - self.time_audio_segment_start_sec) * progress

            # 在上方时域轴上绘制/更新红线
            if self.time_ax is not None and self.time_play_line is not None:
                # 更新独立的播放红线位置和样式
                self.time_play_line.set_xdata([cur_t, cur_t])
                self.time_play_line.set_alpha(0.9)  # 显示红线

                # 简单整图重绘（非阻塞），主线程自己调度
                self.canvas_time.draw_idle()

            # 若还在播放，则继续下一次更新
            if self.time_audio_is_playing:
                self.time_audio_update_job = self.after(30, _update)
            else:
                self.time_audio_update_job = None

        # 启动首次更新
        self.time_audio_update_job = self.after(30, _update)



    def save_time_plot(self):
        selected_file = self.file_var_time.get()
        selected_channel = self.channel_var_time.get()
        # 使用文件名+传感器名作为默认文件名
        default_filename = f"{selected_file}_{selected_channel}.png" if selected_file and selected_channel else ""
        
        file_path = filedialog.asksaveasfilename(title="保存图片", defaultextension=".png",
                                                 filetypes=[("PNG 文件", "*.png"), ("JPEG 文件", "*.jpg"), ("所有文件", "*.*")],
                                                 initialfile=default_filename)
        if file_path:
            self.figure_time.savefig(file_path)
            messagebox.showinfo("成功", "图片已保存！")
            
    def truncate_signal(self):
        """
        截断当前选择的文件的所有通道信号，调用Controller生成新的分析结果集。
        """
        selected_file = self.file_var_time.get()
        # 不再需要获取 selected_channel
        # selected_channel = self.channel_var_time.get()
        
        if not selected_file:
            messagebox.showwarning("警告", "请选择文件！")
            return
            
        # 获取任一通道数据以验证时间范围 (或在Controller中验证)
        # 为了简化View层逻辑，主要验证交给Controller
        # data_converted = self.controller.get_time_domain_data(selected_file, ???) # 不易获取
            
        try:
            time_start = float(self.time_lower_display_var.get())
            time_end = float(self.time_upper_display_var.get())
            # 基本范围检查 (更严格的基于总时长的检查移至Controller)
            if time_start < 0 or time_end <= time_start:
                 raise ValueError("时间范围无效 (起始<0 或 结束<=起始)")
        except ValueError:
            messagebox.showwarning("警告", "时间范围必须是有效的数字！")
            return
            
        # 弹出确认对话框 - 针对整个文件
        if not messagebox.askyesno("确认", f"确定要截取文件 '{selected_file}' 的所有通道 {time_start:.4f}s - {time_end:.4f}s 的数据，并生成新的分析结果吗？"):
            return
            
        # 调用controller进行文件截断和重新处理
        new_file_name = self.controller.process_truncated_file_segment(selected_file, time_start, time_end)
        
        if new_file_name:
            messagebox.showinfo("成功", f"已成功生成基于文件截断信号的分析结果！\n新文件名: {new_file_name}\n请在文件下拉框中选择它进行查看。")
        else:
            messagebox.showerror("错误", "生成截断文件分析结果失败！请查看日志获取详情。")

    # 新增：处理频谱截断 Checkbutton 状态变化的方法
    def toggle_spectrum_truncation(self):
        selected_file = self.file_var_time.get()
        # selected_channel is not strictly needed for the key anymore, but keep for context/validation
        selected_channel = self.channel_var_time.get() 
        apply_truncation = self.apply_truncation_to_spectrum_var.get()
        
        if not selected_file:
            # 只需检查文件
            self.apply_truncation_to_spectrum_var.set(False)
            messagebox.showwarning("警告", "请先选择文件！")
            return
            
        if apply_truncation:
            # 如果选中，尝试设置截断范围
            try:
                # 验证并获取时间范围
                time_start_str = self.time_lower_display_var.get()
                time_end_str = self.time_upper_display_var.get()
                if not time_start_str or not time_end_str:
                     raise ValueError("时间范围不能为空")
                time_start = float(time_start_str)
                time_end = float(time_end_str)
                
                # 简单的本地验证
                if time_start >= time_end or time_start < 0:
                    raise ValueError("无效的时间范围 (起始>=结束 或 起始<0)")

                # 调用controller设置范围 (现在是按文件设置)
                success = self.controller.set_analysis_truncation_range(selected_file, time_start, time_end)
                
                if not success:
                     # 如果controller验证失败（例如超出总时长），恢复checkbox
                     self.apply_truncation_to_spectrum_var.set(False)
                     # Controller内部应该已经log了错误信息
                     # messagebox.showwarning(...) # 可选：在View层再次提示

            except ValueError as e:
                messagebox.showwarning("警告", f"无效的时间范围: {e}\n请先在上方设置有效的时间范围（秒）。")
                # 如果设置失败，恢复为未选中状态
                self.apply_truncation_to_spectrum_var.set(False)
        else:
            # 如果取消选中，则清除截断范围 (按文件清除)
            self.controller.clear_analysis_truncation_range(selected_file)
            # Controller内部已经log了清除信息

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
        self.file_menu_frf.bind('<<ComboboxSelected>>', self._on_file_selected_frf)

        # 通道选择
        tk.Label(control_frame, text="选择通道:").pack(anchor=tk.W, padx=5, pady=5)
        self.channel_menu_frf = ttk.Combobox(control_frame, textvariable=self.channel_var_frf, values=self.channel_options, state='readonly')
        self.channel_menu_frf.pack(anchor=tk.W, padx=5, pady=5)
        self.channel_menu_frf.bind('<<ComboboxSelected>>', self._on_channel_selected_frf)

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

        # 设置x轴范围为用户设置的频率范围
        ax.set_xlim(freq_lower_display, freq_upper_display)

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
        selected_file = self.file_var_frf.get()
        selected_channel = self.channel_var_frf.get()
        # 使用文件名+传感器名作为默认文件名
        default_filename = f"{selected_file}_{selected_channel}.png" if selected_file and selected_channel else ""
        
        file_path = filedialog.asksaveasfilename(title="保存图片", defaultextension=".png",
                                                 filetypes=[("PNG 文件", "*.png"), ("JPEG 文件", "*.jpg"), ("所有文件", "*.*")],
                                                 initialfile=default_filename)
        if file_path:
            self.figure_frf.savefig(file_path)
            messagebox.showinfo("成功", "图片已保存！")


    def create_oma_widgets(self, parent_frame):
        """
        在 OMA 选项卡上，用 grid() 来布置左侧 plot_frame、右侧 control_frame。
        """
        parent_frame.columnconfigure(0, weight=1)  # 让第0列可扩展
        parent_frame.columnconfigure(1, weight=0)
        parent_frame.columnconfigure(2, weight=0)
        parent_frame.rowconfigure(0, weight=1)

        # 左侧绘图区域
        plot_frame = ttk.Frame(parent_frame)
        plot_frame.grid(row=0, column=0, sticky='nsew')
        # 我们让 plot_frame 自己再做一次 row/column configure，以便内部的 canvas 能自适应
        plot_frame.rowconfigure(0, weight=1)
        plot_frame.columnconfigure(0, weight=1)

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

        # ========== 1) 文件选择 =============
        tk.Label(control_frame, text="选择文件:").pack(anchor=tk.W, padx=5, pady=5)
        self.oma_file_var = tk.StringVar()
        self.file_menu_oma = ttk.Combobox(
            control_frame,
            textvariable=self.oma_file_var,
            values=self.file_options,  # 处理完成后再通过 update_visualization_options() 更新
            state='readonly',
            width=24
        )
        self.file_menu_oma.pack(anchor=tk.W, padx=5, pady=2)

        # 绑定事件：当用户切换"选择文件"下拉时，调用 on_oma_file_changed
        self.file_menu_oma.bind("<<ComboboxSelected>>", self.on_oma_file_changed)

        # ========== 2) 多选通道 =============
        tk.Label(control_frame, text="选择通道(可多选):").pack(anchor=tk.W, padx=5, pady=5)
        channel_frame = tk.Frame(control_frame)
        channel_frame.pack(fill=tk.X, padx=5, pady=2)
        scrollbar = tk.Scrollbar(channel_frame, orient=tk.VERTICAL)
        self.oma_channel_listbox = tk.Listbox(
            channel_frame, selectmode=tk.MULTIPLE,
            yscrollcommand=scrollbar.set, height=6, width=24
        )
        scrollbar.config(command=self.oma_channel_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.oma_channel_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 绑定事件：当用户在 listbox 中点选/取消通道时，调用 on_oma_channel_changed
        self.oma_channel_listbox.bind("<<ListboxSelect>>", self.on_oma_channel_changed)


        # ========== 3) OMA 参数(SSI/FDD) ===========
        param_frame = tk.LabelFrame(control_frame, text="OMA参数(SSI/FDD)")
        param_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(param_frame, text="ordmax:").grid(row=0, column=0, padx=3, pady=3, sticky=tk.E)
        self.oma_ordmax_var = tk.StringVar(value="30")
        tk.Entry(param_frame, textvariable=self.oma_ordmax_var, width=5).grid(row=0, column=1, sticky=tk.W)

        tk.Label(param_frame, text="br:").grid(row=0, column=2, padx=3, sticky=tk.E)
        self.oma_br_var = tk.StringVar(value="30")
        tk.Entry(param_frame, textvariable=self.oma_br_var, width=5).grid(row=0, column=3, sticky=tk.W)

        tk.Label(param_frame, text="nxseg:").grid(row=1, column=0, padx=3, sticky=tk.E)
        self.oma_nxseg_var = tk.StringVar(value="1024")
        tk.Entry(param_frame, textvariable=self.oma_nxseg_var, width=6).grid(row=1, column=1, sticky=tk.W)

        tk.Label(param_frame, text="method_SD:").grid(row=1, column=2, padx=3, sticky=tk.E)
        self.oma_method_var = tk.StringVar(value="cor")
        tk.Entry(param_frame, textvariable=self.oma_method_var, width=6).grid(row=1, column=3, sticky=tk.W)

        tk.Label(param_frame, text="decimate:").grid(row=2, column=0, padx=3, sticky=tk.E)
        self.oma_decimate_var = tk.StringVar(value="10")
        tk.Entry(param_frame, textvariable=self.oma_decimate_var, width=6).grid(row=2, column=1, sticky=tk.W)

        # ========== 4) 统一频率范围 ==============
        tk.Label(control_frame, text="统一频率范围:").pack(anchor=tk.W, padx=5, pady=5)
        freq_frame = tk.Frame(control_frame)
        freq_frame.pack(anchor=tk.W, padx=5, pady=2)
        tk.Label(freq_frame, text="下限:").pack(side=tk.LEFT)
        self.freq_min_var = tk.StringVar(value="0.0")
        tk.Entry(freq_frame, textvariable=self.freq_min_var, width=6).pack(side=tk.LEFT, padx=2)
        tk.Label(freq_frame, text="上限:").pack(side=tk.LEFT)
        self.freq_max_var = tk.StringVar(value="10.0")
        tk.Entry(freq_frame, textvariable=self.freq_max_var, width=6).pack(side=tk.LEFT, padx=2)

        # ========== 5) 按钮区 =============
        ttk.Button(control_frame, text="绘制 SSI+FDD", command=self.plot_oma_combined).pack(padx=5, pady=5)
        ttk.Button(control_frame, text="保存 OMA 图", command=self.save_oma_figure).pack(padx=5, pady=5)

        tk.Label(control_frame, text="(此处可放更多设置)").pack(pady=10)

        # ========== 左侧图像区域 =============
        # 注意：这次我们统一用 grid()，所以：
        # self.fig_oma 是实际的Figure
        self.fig_oma = plt.Figure(figsize=(8, 5))
        # 在 Python 里，这里先不显示 / 不贴任何东西。等后面 plot_oma_combined 时再画。
        # 如果需要先来个空白画布，也可以马上做 canvas_oma


        # 先清掉旧的 canvas
        if self.canvas_oma:
            self.canvas_oma.get_tk_widget().destroy()

        #self.fig_oma = fig_ssi  # 或者 new figure
        self.canvas_oma = FigureCanvasTkAgg(self.fig_oma, master=plot_frame)
        # 不要再 pack() 了，统一用 grid：
        self.canvas_oma.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # 画图
        self.canvas_oma.draw()




    def save_oma_figure(self):
        """
        保存一次性绘制好的 OMA 图 (SSI+FDD)。
        """
        if not self.fig_oma:
            messagebox.showwarning("警告", "还没有绘制 OMA 图，无法保存！")
            return
            
        selected_file = self.oma_file_var.get()
        # 使用文件名作为默认文件名（OMA是多通道分析）
        default_filename = f"{selected_file}_OMA.png" if selected_file else ""

        file_path = filedialog.asksaveasfilename(
            title="保存 OMA 图",
            defaultextension=".png",
            filetypes=[("PNG 文件", "*.png"), ("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
            initialfile=default_filename
        )
        if file_path:
            self.fig_oma.savefig(file_path, dpi=300)
            messagebox.showinfo("提示", f"已保存 OMA 图到：{file_path}")

    def on_oma_channel_changed(self, event=None):
        """
        当用户在 OMA 多选通道的 listbox 中做了选择变更，就更新 self.last_oma_channels_for_file
        """
        selected_file = self.oma_file_var.get()
        if not selected_file:
            return

        # 获取当前 listbox 中的所有被选中的通道
        sel_indices = self.oma_channel_listbox.curselection()
        selected_channels = [self.oma_channel_listbox.get(i) for i in sel_indices]

        # 存入字典，记住：选中的通道列表
        self.last_oma_channels_for_file[selected_file] = selected_channels


    def on_oma_file_changed(self, event=None):
        """
        当用户在 OMA 选项卡的文件下拉框里切换文件时，尝试恢复该文件上次记住的通道多选
        """
        selected_file = self.oma_file_var.get()
        if not selected_file:
            return

        # 先清除当前 listbox 的选中状态
        self.oma_channel_listbox.select_clear(0, tk.END)

        # 如果我们以前记住过这个文件的通道选项
        if selected_file in self.last_oma_channels_for_file:
            saved_channels = self.last_oma_channels_for_file[selected_file]  # list of str
            # 在当前 listbox 里找到这些通道的 index，并选中
            for ch_name in saved_channels:
                # 找到 ch_name 在 listbox 中的 index
                index = self._find_listbox_index(self.oma_channel_listbox, ch_name)
                if index is not None:
                    self.oma_channel_listbox.select_set(index)
        else:
            # 如果没记过，就不做额外操作，也可以考虑默认选第一个或都不选
            pass


    def _find_listbox_index(self, listbox, target_str):
        """
        小工具：在给定 listbox 中查找某字符串并返回下标，找不到就返回 None
        """
        size = listbox.size()
        for i in range(size):
            if listbox.get(i) == target_str:
                return i
        return None



    def _refresh_oma_channel_list(self):
        """将 self.channel_options 填充到 self.oma_channel_listbox."""
        self.oma_channel_listbox.delete(0, tk.END)
        for ch in self.channel_options:
            self.oma_channel_listbox.insert(tk.END, ch)



    def plot_oma_combined(self):
        # 1) 读取"文件"与"多选通道"
        file_name = self.oma_file_var.get()
        if not file_name:
            messagebox.showwarning("警告", "请选择要做 OMA 的文件！")
            return

        sel_indices = self.oma_channel_listbox.curselection()
        if not sel_indices:
            messagebox.showwarning("警告", "请至少选择一个通道做 OMA！")
            return
        selected_channels = [self.oma_channel_listbox.get(i) for i in sel_indices]

        # 2) 读取 OMA 参数
        try:
            ordmax = int(self.oma_ordmax_var.get())
            br = int(self.oma_br_var.get())
            nxseg = int(self.oma_nxseg_var.get())
            method_SD = self.oma_method_var.get().strip()
            decimate_q = int(self.oma_decimate_var.get())
        except ValueError:
            messagebox.showwarning("警告", "SSI/FDD参数(ordmax, br, nxseg, decimate)必须是数字！")
            return

        # 3) 读取频率范围
        try:
            freq_min = float(self.freq_min_var.get())
            freq_max = float(self.freq_max_var.get())
            if freq_min < 0 or freq_min >= freq_max:
                messagebox.showwarning("警告", "频率范围不合法，请检查输入！")
                return
        except ValueError:
            messagebox.showwarning("警告", "频率上下限应是数字！")
            return

        # 4) 从 controller 中获取时域数据
        data_array, fs = self.controller.get_oma_time_data(file_name, selected_channels)
        if data_array is None or data_array.size == 0:
            messagebox.showerror("错误", "未能获取 OMA 时域数据，请检查通道/文件。")
            return

        print("拿到的时域数据形状:", data_array.shape, "采样率:", fs)

        # 5) 构建 SingleSetup
        from pyoma2.setup.single import SingleSetup
        from pyoma2.algorithms.fdd import FDD
        from pyoma2.algorithms.ssi import SSIdat

        simp = SingleSetup(data_array, fs=fs)
        simp.decimate_data(q=decimate_q)

        fdd = FDD(name="FDD", nxseg=nxseg, method_SD=method_SD)
        ssidat = SSIdat(name="SSIdat", br=br, ordmax=ordmax)
        simp.add_algorithms(fdd, ssidat)
        simp.run_all()

        # 6) 绘图
        fig_ssi, ax_ssi = ssidat.plot_stab(freqlim=(freq_min, freq_max), hide_poles=False)
        ax_fdd = ax_ssi.twinx()

        fig_fdd_tmp, ax_fdd_tmp = fdd.plot_CMIF(freqlim=(freq_min, freq_max))

        for line in ax_fdd_tmp.lines:
            x_data = line.get_xdata()
            y_data = line.get_ydata()
            ax_fdd.plot(x_data, y_data,
                        linestyle=line.get_linestyle(),
                        color=line.get_color(),
                        linewidth=line.get_linewidth())
        import matplotlib.pyplot as plt
        plt.close(fig_fdd_tmp)

        # 把旧画布先删掉
        if self.canvas_oma:
            self.canvas_oma.get_tk_widget().destroy()

        self.fig_oma = fig_ssi
        # 注意：此处要和 create_oma_widgets() 里的那个 plot_frame 统一。
        # 最好在 create_oma_widgets() 中保留对 plot_frame 的引用，比如 self.oma_plot_frame = plot_frame
        # 然后这里用 master=self.oma_plot_frame 即可

        self.canvas_oma = FigureCanvasTkAgg(self.fig_oma, master=self.oma_tab)

        # 不再调用 pack()，而是 grid()
        self.canvas_oma.get_tk_widget().grid(row=0, column=0, sticky="nsew")  # 也可以放到同一个 plot_frame

        self.canvas_oma.draw()




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

        # 在列表前面插入一个 "ALL_FILES"/"ALL_CHANNELS" 选项，代表"全局"或"不区分通道"
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
        以更新"Global Params" Tab 上的文件下拉框、通道下拉框，避免重启软件。
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
        从实际处理结果中收集"文件名"列表，若无 processing_results 或未处理，则返回空列表。
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
        # --- 1) 收集所有"硬件传感器"名称 ---
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

        # --- 4) 因为下文要用 self.file_options，这里先更新它
        # 注意：有些人会先更新 file_options 再去更新频谱/时域FRF的 combobox。
        #       也可以调整顺序，只要确保 file_options 里的值最终正确。
        self.file_options = [file_result['file_name'] for file_result in results.files]

        # --- 5) 更新 频谱/时域/FRF 这三处的下拉菜单 ---
        self.file_menu_spectrum['values'] = self.file_options
        self.file_menu_time['values']     = self.file_options
        self.file_menu_frf['values']      = self.file_options

        # 根据 file_options 是否为空，设定默认选中
        if self.file_options:
            self.file_var_spectrum.set(self.file_options[0])
            self.file_var_time.set(self.file_options[0])
            self.file_var_frf.set(self.file_options[0])
        else:
            self.file_var_spectrum.set('')
            self.file_var_time.set('')
            self.file_var_frf.set('')

        self.channel_menu_spectrum['values'] = self.channel_options
        self.channel_menu_time['values']     = self.channel_options
        self.channel_menu_frf['values']      = self.channel_options

        old_file = self.oma_file_var.get()     # 先记下用户当前选的文件
        self.file_menu_oma['values'] = self.file_options  # 更新下拉值

        if old_file in self.file_options:
            # 如果旧文件依然在新的 file_options 里，则用回它
            self.oma_file_var.set(old_file)
        elif self.file_options:
            # 否则才用第一个
            self.oma_file_var.set(self.file_options[0])
        else:
            # 实在没文件就空
            self.oma_file_var.set('')

        # 再把 channel listbox 清空并插入
        self.oma_channel_listbox.delete(0, tk.END)
        for ch in self.channel_options:
            self.oma_channel_listbox.insert(tk.END, ch)

        # 最后手动触发 on_oma_file_changed() 让它自动恢复之前勾选的通道
        self.on_oma_file_changed()




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
