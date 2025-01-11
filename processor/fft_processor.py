# processor/fft_processor.py

import os
import numpy as np
from scipy.fft import fft, fftfreq
from matplotlib.font_manager import FontProperties
import tkinter as tk
from tkinter import messagebox

from model.data_models import (
    ProcessingParameters, FFTResult, SensorSettings, ProcessingResults
)
from .vk2 import vk2

class FFTProcessor:
    """
    负责执行主要的数据处理:
      - 遍历文件、读取 .txt
      - 根据 sensor_settings 换算数据
      - (可选) 去除指定频率
      - FFT 计算
      - (可选) 计算频响函数 FRF
      - 返回 ProcessingResults
    """
    def __init__(self, parameters: ProcessingParameters, logger, controller):
        self.params = parameters
        self.logger = logger    # 用于输出日志
        self.controller = controller  # 用于在处理完成后通知控制器
        self.font_prop = FontProperties(fname='SimHei.ttf')

        # 如果 parameters 为空，尝试从 controller 获取
        if self.params is None and self.controller is not None:
            self.params = self.controller.params

    def process_files(self):
        """
        整体处理入口：对目标文件夹中符合前缀的 .txt 文件进行处理。
        最终生成 ProcessingResults，并通过 on_processing_finished(...) 通知 controller。
        """
        feature_file_path = os.path.join(self.params.output_folder, "features_with_fft.txt")
        os.makedirs(self.params.output_folder, exist_ok=True)

        # 是否存在参考通道 (用以决定是否计算 FRF)
        ref_channel_index = None
        for idx, ch_settings in enumerate(self.params.sensor_settings):
            if ch_settings.is_reference:
                ref_channel_index = idx
                break
        compute_frf = (ref_channel_index is not None)

        # 建立空的处理结果存储
        processing_results = ProcessingResults(self.params.sensor_settings)

        # 寻找匹配文件并排序
        matched_files = sorted(
                        [f for f in os.listdir(self.params.input_folder)
                        if f.startswith(self.params.filename_prefix) and f.endswith(".txt")]
)

        if not matched_files:
            self.log_message("未找到符合条件的文件。\n")
            return

        # 获取 vk2 参数
        vk2_params = self.controller.get_vk2_parameters()
        remove_frequencies = vk2_params is not None

        for file_name in matched_files:
            base_name = self.get_base_name(file_name)
            txt_file_path = os.path.join(self.params.input_folder, file_name)

            try:
                data = np.loadtxt(txt_file_path)
                if data.ndim == 1:
                    data = data.reshape(-1, 1)

                num_rows, num_columns = data.shape
                if num_columns > num_rows:
                    data = data.T
                    num_rows, num_columns = data.shape

                with open(feature_file_path, "a", encoding="utf-8") as feature_file:
                    feature_file.write(f"文件: {base_name}\n行数: {num_rows}\n列数: {num_columns}\n")

                    fft_results = []

                    total_length = num_rows
                    t = np.linspace(0, total_length / self.params.sampling_rate, total_length, endpoint=False)

                    for col_idx in range(num_columns):
                        column = data[:, col_idx]

                        # 数据换算
                        data_converted, unit, name = self.convert_data(column, col_idx)
                        data_processed = data_converted

                        N = len(data_processed)
                        fft_values = fft(data_processed)
                        freq = fftfreq(N, d=1 / self.params.sampling_rate)
                        idx_positive = np.where(freq >= 0)
                        freq = freq[idx_positive]
                        fft_values = fft_values[idx_positive]

                        fft_amplitude = np.abs(fft_values) * 2 / N
                        fft_amplitude[0] = fft_amplitude[0] / 2

                        fft_result = FFTResult(freq, fft_amplitude, np.angle(fft_values), name, unit)
                        fft_results.append({
                            'col_idx': col_idx,
                            'fft_result': fft_result,
                            'data_converted': data_converted
                        })

                    # 如果启用了频响曲线计算，进行计算并保存结果
                    frf_results = []
                    if compute_frf:
                        frf_results = self.compute_frequency_response(fft_results, ref_channel_index, base_name, feature_file)

                    feature_file.write("\n")

                    processing_results.add_file_result({
                        'file_name': file_name,
                        'fft_results': fft_results,
                        'frf_results': frf_results,
                        'base_name': base_name
                    })

                self.log_message(f"已处理: {file_name}\n")

            except Exception as e:
                self.log_message(f"处理文件 {file_name} 时出错: {e}\n")

        # 在处理完成后，通过主线程调用处理完成的方法
        self.controller.view.after(0, self.on_processing_finished, processing_results)

    def log_message(self, message):
        # 通过主线程更新日志
        self.controller.view.after(0, self.logger_insert, message)

    def logger_insert(self, message):
        self.logger.insert(tk.END, message)
        self.logger.see(tk.END)
        self.logger.update()

    def on_processing_finished(self, processing_results):
        messagebox.showinfo("完成", "文件处理完成！")
        # 在处理完成后，通知控制器
        self.controller.processing_finished(processing_results)

    def remove_specified_frequencies(self, data, fs, vk2_params):
        """
        从信号中去除指定的频率。

        参数：
        data       - 输入信号数据
        fs         - 采样频率
        vk2_params - vk2 函数所需的参数字典，包括 r、filtord 和 freq_list
        """
        freq_list = vk2_params.get('freq_list', None)
        r = vk2_params.get('r', 1000)
        filtord = vk2_params.get('filtord', 1)

        if freq_list is None:
            raise ValueError("需要提供要去除的频率列表 freq_list")

        N = len(data)
        t = np.arange(N) / fs

        # 初始化被提取的频率成分的总和
        extracted_components = np.zeros(N, dtype=np.float64)

        for freq in freq_list:
            f_vector = np.full(N, freq)
            x, bw, T, xr = vk2(data, f_vector, fs, r, filtord)
            extracted_components += xr  # 累加被提取的频率成分

        # 从原始信号中减去提取的频率成分
        y_filtered = data - extracted_components

        return y_filtered

    def get_base_name(self, file_name):
        base_name_parts = file_name.split("-")
        if len(base_name_parts) > 3:
            base_name = "-".join(base_name_parts[:-3]) + ".txt"
        else:
            base_name = file_name
        return base_name

    def convert_data(self, column, col_idx):
        ch_settings = self.params.sensor_settings[col_idx]
        sensor_type = ch_settings.sensor_type
        unit = ch_settings.unit
        name = ch_settings.name

        if sensor_type == '加速度':
            data_converted = column
        elif sensor_type == '脉动压力传感器':
            a = ch_settings.a
            b = ch_settings.b
            data_converted = a * column + b
        elif sensor_type in ['扭矩传感器', '力台传感器', '空载信号', '力锤', '电涡流', '力环']:
            sensitivity = ch_settings.sensitivity
            data_converted = column / sensitivity
        else:
            data_converted = column

        return data_converted, unit, name

    def compute_frequency_response(self, fft_results, ref_channel_index, base_name, feature_file):
        reference_result = None
        for result in fft_results:
            if result['col_idx'] == ref_channel_index:
                reference_result = result
                break
        if reference_result is None:
            self.log_message(f"未找到参考信号的 FFT 结果。\n")
            return []

        ref_fft_values = reference_result['fft_result'].amplitude
        ref_name = reference_result['fft_result'].name

        frf_results = []

        for result in fft_results:
            if result['col_idx'] == ref_channel_index:
                continue  # 跳过参考信号

            H_f = result['fft_result'].amplitude / ref_fft_values  # 计算频响函数
            H_f_magnitude = np.abs(H_f)
            H_f_phase = np.angle(H_f)

            freq = result['fft_result'].freq
            name = result['fft_result'].name
            response_name = f"{name}_FRF"

            # 写入特征文件
            feature_file.write(
                f"  频响函数 {name} / {ref_name}:\n"
                f"    频率范围: {freq[0]} - {freq[-1]} Hz\n"
            )

            frf_results.append({
                'freq': freq,
                'H_f_magnitude': H_f_magnitude,
                'H_f_phase': H_f_phase,
                'name': name
            })

        return frf_results


    def process_user_defined_signals(self, user_data, custom_name):
        """
        接收用户自定义的单路时域数据 (user_data)，并执行:
          1) 若需要去除频率(可选), remove_specified_frequencies
          2) 计算 FFT
          3) 若启用 FRF(并存在参考通道?), 可做 FRF 计算
        最终返回 (fft_result, frf_result)
        如果不计算FRF, frf_result 可返回 None
        """

        if self.params is None:
            raise ValueError("FFTProcessor: self.params 为空，无法处理用户信号。")

        # 1) 若有 VK2 参数并启用去频率，则先去除
        vk2_params = self.controller.get_vk2_parameters()
        remove_frequencies = (vk2_params is not None)

        data_processed = user_data

        # 2) 做 FFT
        N = len(data_processed)
        fft_values = np.fft.fft(data_processed)
        freq = np.fft.fftfreq(N, d=1.0/self.params.sampling_rate)
        idx_pos = np.where(freq >= 0)

        freq = freq[idx_pos]
        fft_values = fft_values[idx_pos]

        amplitude = np.abs(fft_values)*2/N
        amplitude[0] = amplitude[0]/2
        phase = np.angle(fft_values)

        user_fft_result = FFTResult(
            freq=freq,
            amplitude=amplitude,
            phase=phase,
            name=custom_name,
            unit="(UserDefined)"
        )

        # 3) 是否需要做 FRF? 取决于 self.params.sensor_settings 里有没有参考通道
        ref_channel_index = None
        for idx, ch_settings in enumerate(self.params.sensor_settings):
            if ch_settings.is_reference:
                ref_channel_index = idx
                break
        if ref_channel_index is not None:
            # 如果需要对这个自定义信号和参考通道做FRF，理论上要先获取参考通道的 FFT
            # 这里演示: 不做复杂处理, 仅返回 None 或者添加必要逻辑
            user_frf_result = None
        else:
            user_frf_result = None

        return user_fft_result, user_frf_result
