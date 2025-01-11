# controller/app_controller.py

import threading
import tkinter as tk
from tkinter import messagebox
import numpy as np
import os

from model.data_models import (
    ProcessingParameters, ProcessingResults,
    SensorSettings, FFTResult
)
from processor.fft_processor import FFTProcessor
from view.main_window import MainWindow
from view.dialogs import SensorSettingsDialog

class AppController:
    """
    AppController 负责主逻辑、管理数据处理和结果存储，
    并在View层与Processor层之间扮演协调者角色。
    """

    def __init__(self):
        # 创建主窗口（View），并将 self 作为 controller 传入
        self.view = MainWindow(controller=self)

        # 处理结果 / 参数
        self.processing_results = None
        self.sensor_settings = None
        self.params = None

    def run(self):
        """启动主事件循环"""
        self.view.mainloop()

    def get_processing_parameters(self):
        """从 View 中读取必要信息，组装成 ProcessingParameters。"""
        try:
            sampling_rate = float(self.view.sampling_rate_var.get())
        except ValueError:
            messagebox.showwarning("警告", "采样率必须是数字！")
            return None

        num_channels = self.get_num_channels(
            self.view.input_folder_var.get(),
            self.view.filename_prefix_var.get()
        )
        if num_channels == 0:
            messagebox.showwarning("警告", "无法确定通道数！")
            return None

        sensor_settings = self.get_sensor_settings(
            num_channels, self.view.output_folder_var.get()
        )
        if sensor_settings is None:
            return None

        params = ProcessingParameters(
            input_folder=self.view.input_folder_var.get(),
            output_folder=self.view.output_folder_var.get(),
            filename_prefix=self.view.filename_prefix_var.get(),
            sampling_rate=sampling_rate,
            sensor_settings=sensor_settings
        )

        errors = params.validate()
        if errors:
            messagebox.showwarning("警告", "\n".join(errors))
            return None

        self.sensor_settings = sensor_settings
        return params

    def start_processing(self, params: ProcessingParameters):
        """用户点击“开始处理”后，异步调用 Processor。"""
        self.params = params
        self.view.disable_visualization_tabs()

        processor = FFTProcessor(params, self.view.log_text, self)
        threading.Thread(target=processor.process_files).start()

    def processing_finished(self, results):
        """Processor 处理完回调此方法，更新 View。"""
        self.processing_results = results
        self.view.enable_visualization_tabs()
        self.view.update_visualization_options(results)
        self.view.enable_user_define_button(True)

    def get_num_channels(self, input_folder, filename_prefix):
        """尝试读取首个符合前缀的TXT文件，以确定通道数。"""
        for file_name in os.listdir(input_folder):
            if file_name.startswith(filename_prefix) and file_name.endswith(".txt"):
                txt_file_path = os.path.join(input_folder, file_name)
                try:
                    data = np.loadtxt(txt_file_path)
                    if data.ndim == 1:
                        data = data.reshape(-1, 1)
                    num_rows, num_columns = data.shape
                    if num_columns > num_rows:
                        data = data.T
                        num_rows, num_columns = data.shape
                    return num_columns
                except:
                    pass
        return 0

    def get_sensor_settings(self, num_channels, output_folder):
        """弹出 SensorSettingsDialog，阻塞等待用户输入；返回 settings。"""
        dialog = SensorSettingsDialog(num_channels, output_folder)
        self.view.wait_window(dialog)
        return dialog.settings

    def get_fft_result(self, file_name, sensor_name):
        """从 processing_results 中找到对应 FFTResult。"""
        if not self.processing_results:
            return None
        for f in self.processing_results.files:
            if f['file_name'] == file_name:
                for fft_entry in f['fft_results']:
                    if fft_entry['fft_result'].name == sensor_name:
                        return fft_entry['fft_result']
        return None

    def get_time_domain_data(self, file_name, sensor_name):
        """获取时域数据 data_converted。"""
        if not self.processing_results:
            return None
        for f in self.processing_results.files:
            if f['file_name'] == file_name:
                for fft_entry in f['fft_results']:
                    if fft_entry['fft_result'].name == sensor_name:
                        return fft_entry['data_converted']
        return None

    def get_frf_result(self, file_name, sensor_name):
        """获取频响函数结果。"""
        if not self.processing_results:
            return None
        for f in self.processing_results.files:
            if f['file_name'] == file_name:
                frf_list = f.get('frf_results', [])
                for item in frf_list:
                    if item['name'] == sensor_name:
                        return item
        return None

    def get_vk2_parameters(self):
        """从View读取 vk2_r, vk2_filtord, freq_list。"""
        try:
            vk2_r = float(self.view.vk2_r_var.get())
            vk2_filtord = int(self.view.vk2_filtord_var.get())
            freq_list = [float(x.strip()) for x in self.view.freq_to_remove_var.get().split(',')]
            if not freq_list:
                return None
            return {
                'r': vk2_r,
                'filtord': vk2_filtord,
                'freq_list': freq_list
            }
        except ValueError:
            return None

    def remove_specified_frequencies(self, data, fs, vk2_params):
        """调用 Processor.remove_specified_frequencies。"""
        if not self.params:
            self.params = self.get_processing_parameters()
            if not self.params:
                messagebox.showwarning("警告", "无法获取处理参数。")
                return None
        processor = FFTProcessor(self.params, None, self)
        return processor.remove_specified_frequencies(data, fs, vk2_params)

    def create_user_defined_signal(self, code_str, selected_channels, custom_name):
        """
        多文件 + 变量名映射 + 脚本执行 + 调用 Processor 再做FFT/FRF。
        """
        import numpy as np
        import math

        if not self.processing_results:
            messagebox.showwarning("警告", "请先完成数据处理。")
            return

        # 一些提示信息
        info_msg = (
            "[提示] 您正在进行用户自定义信号。\n"
            "脚本中的时间向量 t，每个通道映射到 ch0, ch1, ch2...\n"
            "请在脚本中最终以 `result = ...` 方式输出。\n"
        )
        self.log_message(info_msg)

        # 收集多文件时域数据
        all_files_data_map = {}
        min_length = None
        for f_res in self.processing_results.files:
            file_name = f_res['file_name']
            channel_data_map = {}
            length_this_file = None

            for ch_name in selected_channels:
                data_arr = None
                found = False
                for fft_entry in f_res['fft_results']:
                    if fft_entry['fft_result'].name == ch_name:
                        data_arr = fft_entry['data_converted']
                        found = True
                        break
                if not found or data_arr is None:
                    msg = f"文件 '{file_name}' 未找到通道 '{ch_name}'，无法生成新信号。"
                    self.log_message(msg + "\n")
                    messagebox.showwarning("警告", msg)
                    return

                if length_this_file is None:
                    length_this_file = len(data_arr)
                else:
                    if len(data_arr) != length_this_file:
                        msg = f"文件 '{file_name}' 中通道长度不一致，无法合成。"
                        self.log_message(msg + "\n")
                        messagebox.showwarning("警告", msg)
                        return

                channel_data_map[ch_name] = data_arr

            all_files_data_map[file_name] = channel_data_map
            if length_this_file is not None:
                if min_length is None or length_this_file < min_length:
                    min_length = length_this_file

        if min_length is None:
            messagebox.showwarning("警告", "未能获取任何通道数据。")
            return

        # 变量名映射
        safe_var_map = {}
        mapping_info = "[通道映射表]\n"
        for idx, ch_name in enumerate(selected_channels):
            var_name = f"ch{idx}"
            safe_var_map[ch_name] = var_name
            mapping_info += f"  {ch_name} -> {var_name}\n"
        self.log_message(mapping_info + "\n")

        fs = self.params.sampling_rate if self.params else 25600

        # 逐文件执行脚本
        from processor.fft_processor import FFTProcessor
        for f_res in self.processing_results.files:
            file_name = f_res['file_name']
            channel_data_map = all_files_data_map[file_name]

            local_dict = {}
            global_dict = {"np": np, "math": math}
            t = np.linspace(0, min_length/fs, min_length, endpoint=False)
            local_dict["t"] = t

            # 注入通道
            for ch_name, arr in channel_data_map.items():
                data_arr = arr[:min_length]
                var_name = safe_var_map[ch_name]
                local_dict[var_name] = data_arr

            # 执行脚本
            try:
                exec(code_str, global_dict, local_dict)
            except Exception as e:
                msg = f"自定义脚本在文件 '{file_name}' 执行出错:\n{e}"
                self.log_message(msg + "\n")
                messagebox.showerror("错误", msg)
                return

            if "result" not in local_dict:
                msg = f"文件 '{file_name}' 未定义 'result' 变量。"
                self.log_message(msg + "\n")
                messagebox.showwarning("警告", msg)
                return

            result_data = local_dict["result"]
            if not isinstance(result_data, np.ndarray):
                msg = f"文件 '{file_name}' 的 result 不是 np.ndarray!"
                self.log_message(msg + "\n")
                messagebox.showwarning("警告", msg)
                return
            if len(result_data) != min_length:
                msg = f"文件 '{file_name}' 的 result 长度({len(result_data)}) != {min_length}"
                self.log_message(msg + "\n")
                messagebox.showwarning("警告", msg)
                return

            # 调用 Processor
            processor = FFTProcessor(self.params, None, self)
            try:
                user_fft_result, user_frf_result = processor.process_user_defined_signals(
                    result_data, custom_name
                )
            except Exception as e:
                msg = f"process_user_defined_signals 错误 (文件 '{file_name}'):\n{e}"
                self.log_message(msg + "\n")
                messagebox.showerror("错误", msg)
                return

            # 插入到 fft_results
            f_res['fft_results'].append({
                "col_idx": -1,
                "fft_result": user_fft_result,
                "data_converted": result_data
            })
            if user_frf_result is not None:
                if 'frf_results' not in f_res:
                    f_res['frf_results'] = []
                f_res['frf_results'].append(user_frf_result)

        self.view.update_visualization_options(self.processing_results)
        finish_msg = f"自定义信号 '{custom_name}' 已生成。"
        self.log_message("[完成]" + finish_msg + "\n")
        messagebox.showinfo("提示", finish_msg)

    def get_spectrum_data(self, file_name, channel_name):
        """
        若勾选频率去除 => remove_specified_frequencies => FFT
        否则 => 直接用已有结果 或 现算。
        """
        if not self.processing_results:
            return None, None

        apply_removal = self.view.apply_freq_removal_var.get()
        if apply_removal:
            vk2_params = self.get_vk2_parameters()
            if not vk2_params or not vk2_params.get('freq_list'):
                return None, None

            data_converted = self.get_time_domain_data(file_name, channel_name)
            if data_converted is None:
                return None, None
            return self.do_fft_with_removal(data_converted, vk2_params)
        else:
            fft_res = self.get_fft_result(file_name, channel_name)
            if fft_res:
                return fft_res.freq, fft_res.amplitude
            else:
                data_converted = self.get_time_domain_data(file_name, channel_name)
                if data_converted is None:
                    return None, None
                return self.do_fft_no_removal(data_converted)

    def do_fft_with_removal(self, data, vk2_params):
        from processor.fft_processor import FFTProcessor
        processor = FFTProcessor(self.params, None, self)
        data_processed = processor.remove_specified_frequencies(data, self.params.sampling_rate, vk2_params)

        import numpy as np
        from scipy.fft import fft, fftfreq
        N = len(data_processed)
        fft_values = fft(data_processed)
        freq = fftfreq(N, d=1/self.params.sampling_rate)
        idx = freq >= 0
        freq = freq[idx]
        fft_values = fft_values[idx]
        amplitude = np.abs(fft_values)*2/N
        amplitude[0] = amplitude[0]/2
        return freq, amplitude

    def do_fft_no_removal(self, data):
        import numpy as np
        from scipy.fft import fft, fftfreq
        N = len(data)
        fft_values = fft(data)
        freq = fftfreq(N, d=1.0/self.params.sampling_rate)
        idx = freq >= 0
        freq = freq[idx]
        fft_values = fft_values[idx]
        amplitude = np.abs(fft_values)*2/N
        amplitude[0] = amplitude[0]/2
        return freq, amplitude

    def log_message(self, message):
        """往日志窗口or控制台输出信息。"""
        if self.view and hasattr(self.view, 'log_text'):
            self.view.log_text.insert(tk.END, message)
            self.view.log_text.see(tk.END)
        else:
            print(message)
