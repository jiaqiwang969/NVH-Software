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


class GlobalValues:
    """
    用字典存储 (file_key, channel_key, param_key) => value
    可以代表全局/文件/通道三级配置，也可扩展更多维度。
    """
    def __init__(self):
        self._values = {}

    def set_value(self, fkey: str, ckey: str, pkey: str, value):
        self._values[(fkey, ckey, pkey)] = value

    def get_value_exact(self, fkey: str, ckey: str, pkey: str, default=None):
        return self._values.get((fkey, ckey, pkey), default)

    def delete_value(self, fkey: str, ckey: str, pkey: str) -> bool:
        if (fkey, ckey, pkey) in self._values:
            del self._values[(fkey, ckey, pkey)]
            return True
        return False

    def list_all_params(self):
        lines = []
        for (f, c, p), v in self._values.items():
            lines.append(f"({f}, {c}, {p}) => {v}")
        return sorted(lines)

class AppController:
    """
    AppController 负责主逻辑、管理数据处理和结果存储，
    并在View层与Processor层之间扮演协调者角色。
    """

    def __init__(self):
        # 创建主窗口（View），并将 self 作为 controller 传入

        self.channel_options = []
        # 处理结果 / 参数
        self.processing_results = None
        self.sensor_settings = None
        self.params = None

        # 修改：频谱/OMA分析的时间范围设置 (按文件存储)
        self.truncation_settings = {}

        # 2) 新增: 全局参数管理器 (多级键)
        self.global_values = GlobalValues()  # 全局/文件/通道 配置都保存在这里
        
        self.view = MainWindow(controller=self)


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
        """用户点击"开始处理"后，异步调用 Processor。"""
        self.params = params
        self.view.disable_visualization_tabs()

        processor = FFTProcessor(params, self.view.log_text, self)
        threading.Thread(target=processor.process_files).start()

    def processing_finished(self, results):
        """Processor 处理完回调此方法，更新 View。"""
        self.processing_results = results

        self.channel_options = self._collect_channels_from_results(results)

        self.view.enable_visualization_tabs()
        self.view.update_visualization_options(results)
        self.view.enable_user_define_button(True)
        self.view.refresh_global_params_tab()


    def _collect_channels_from_results(self, results):
        """
        遍历 results.files[*]['fft_results'][*]['fft_result'].name 以收集所有通道名称。
        返回一个"去重后的"列表或集合。
        """
        all_channels = set()
        if results and hasattr(results, 'files'):
            for f_res in results.files:
                fft_list = f_res.get('fft_results', [])
                for fft_entry in fft_list:
                    ch_name = fft_entry['fft_result'].name
                    if ch_name:
                        all_channels.add(ch_name)
        return sorted(all_channels)


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
            
        # 查找对应的文件条目
        target_file_entry = None
        for f_entry in self.processing_results.files:
            if f_entry['file_name'] == file_name:
                target_file_entry = f_entry
                break
        
        if target_file_entry is None:
            # self.log_message(f"错误：在 get_time_domain_data 中未找到文件条目 '{file_name}'\n") # 可能过于频繁
            return None

        # 检查是否是截断文件
        if target_file_entry.get('is_truncated', False):
            # --- 处理截断文件 --- 
            channels_data = target_file_entry.get('channels')
            if channels_data:
                channel_info = channels_data.get(sensor_name)
                if channel_info:
                    return channel_info.get('data') # 返回存储的截断数据
            # 如果找不到截断数据，返回 None
            return None
        else:
            # --- 处理原始文件 (保持原有逻辑) --- 
            fft_results_list = target_file_entry.get('fft_results', [])
            for fft_entry in fft_results_list:
                # 检查 fft_entry 是否是预期的字典结构，并且包含 'fft_result'
                if isinstance(fft_entry, dict) and 'fft_result' in fft_entry: 
                    fft_result_obj = fft_entry['fft_result']
                    # 确保 fft_result_obj 有 name 属性
                    if hasattr(fft_result_obj, 'name') and fft_result_obj.name == sensor_name:
                         # 返回存储在原始条目中的 data_converted
                         return fft_entry.get('data_converted') 
                else:
                     # 如果结构不符合预期，记录一个警告或错误
                     self.log_message(f"警告：文件 '{file_name}' 中的 fft_results 结构异常。条目: {fft_entry}\n")
            # 如果在原始文件中未找到匹配的通道
            return None

    def get_frf_result(self, file_name, sensor_name):
        """
        获取频响函数结果。
        对于原始文件，查找预计算结果。
        对于截断文件，实时计算FRF。
        """
        if not self.processing_results:
            return None
            
        # 查找对应的文件条目
        target_file_entry = None
        for f_entry in self.processing_results.files:
            if f_entry['file_name'] == file_name:
                target_file_entry = f_entry
                break
                
        if target_file_entry is None:
            self.log_message(f"错误：在FRF获取中未找到文件条目 '{file_name}'\n")
            return None

        # 检查是否是截断文件
        if target_file_entry.get('is_truncated', False):
            # --- 处理截断文件：实时计算 FRF ---
            self.log_message(f"信息：正在为截断文件 '{file_name}' 实时计算通道 '{sensor_name}' 的 FRF...\n")
            
            channels_data = target_file_entry.get('channels')
            sampling_rate = target_file_entry.get('sampling_rate')
            
            if not channels_data or sampling_rate is None:
                 self.log_message(f"错误：截断文件 '{file_name}' 缺少通道数据或采样率信息\n")
                 return None
                 
            # 寻找输入通道数据
            input_channel_data = None
            input_channel_name = None
            for ch_name, ch_info in channels_data.items():
                if ch_info.get('is_input', False):
                    input_channel_data = ch_info.get('data')
                    input_channel_name = ch_name
                    break
                    
            if input_channel_data is None:
                 self.log_message(f"错误：在截断文件 '{file_name}' 中未找到标记为输入的通道数据\n")
                 return None
                 
            # 寻找请求的输出通道数据
            output_channel_info = channels_data.get(sensor_name)
            if not output_channel_info:
                self.log_message(f"错误：在截断文件 '{file_name}' 中未找到请求的输出通道 '{sensor_name}'\n")
                return None
            if output_channel_info.get('is_input', False):
                self.log_message(f"警告：不能计算输入通道 '{sensor_name}' 对自身的FRF\n")
                return None
                
            output_channel_data = output_channel_info.get('data')
            if output_channel_data is None:
                 self.log_message(f"错误：通道 '{sensor_name}' 在截断文件 '{file_name}' 中缺少时域数据\n")
                 return None
                 
            # 调用 Processor 进行计算
            processor = FFTProcessor(self.params, self.view.log_text, self)
            try:
                frf_calc_result = processor.calculate_frf_from_data(
                    input_channel_data,
                    output_channel_data,
                    sampling_rate
                )
            except Exception as e:
                 self.log_message(f"错误：实时计算FRF时出错: {e}\n")
                 return None
                 
            if frf_calc_result is None:
                 self.log_message(f"错误：实时FRF计算未能返回有效结果。\n")
                 return None
                 
            # 添加通道名称并返回
            frf_calc_result['name'] = sensor_name 
            return frf_calc_result
            
        else:
            # --- 处理原始文件：查找预计算结果 --- 
            frf_list = target_file_entry.get('frf_results', [])
            for item in frf_list:
                if item['name'] == sensor_name:
                    return item
            # 如果原始文件没有预计算的FRF结果（例如没有设置参考通道）
            # self.log_message(f"警告：原始文件 '{file_name}' 未包含通道 '{sensor_name}' 的预计算FRF结果。\n")
            return None

    def get_oma_time_data(self, file_name, channel_list):
        import numpy as np
        if not self.processing_results:
            return None, 0.0
        fs = self.params.sampling_rate if self.params else 25600.0

        # 检查是否需要应用文件级截断
        apply_truncation = False
        truncation_range = None
        start_idx, end_idx = 0, -1 # 默认不截断
        if self.view.apply_truncation_to_spectrum_var.get(): # Checkbox state from view
            truncation_range = self.truncation_settings.get(file_name)
            if truncation_range:
                apply_truncation = True
                start_sec = truncation_range['start_sec']
                end_sec = truncation_range['end_sec']
                start_idx = int(start_sec * fs)
                # end_idx needs total_length, which we get after reading the first channel
                self.log_message(f"信息：OMA分析将使用文件 {file_name} 的截断范围 {start_sec:.4f}s - {end_sec:.4f}s\n")

        # 找到指定 file_name
        target_file = None
        for f_res in self.processing_results.files:
            if f_res['file_name'] == file_name:
                target_file = f_res
                break
        if not target_file:
            print(f"未找到文件: {file_name}")
            return None, fs

        fft_list = target_file.get('fft_results', [])

        arrays = []
        used_channels = []
        min_len = None
        first_channel = True

        for ch in channel_list:
            arr = None
            for e in fft_list:
                if e['fft_result'].name == ch:
                    arr = e['data_converted']
                    break
            if arr is None:
                print(f"通道 {ch} 不在 file '{file_name}' 里!")
                continue  # or raise

            # 如果应用截断
            if apply_truncation:
                if first_channel:
                    # 第一次获取通道时，计算 end_idx
                    total_length = len(arr)
                    end_idx = min(int(truncation_range['end_sec'] * fs) + 1, total_length)
                    first_channel = False
                
                arr_truncated = arr[start_idx:end_idx]
                if len(arr_truncated) < 10: # OMA对长度要求可能不高，但至少要有一些点
                     print(f"警告：截断后通道 {ch} 数据点数过少 ({len(arr_truncated)}点)，可能影响OMA分析\n")
                     # 不跳过，让用户决定后续
                arr = arr_truncated # 使用截断后的数据

            # --- 后续处理使用 arr (可能是截断后的) ---
            this_len = len(arr)
            if this_len == 0: continue # 如果截断后没数据了，跳过此通道
            
            if min_len is None:
                min_len = this_len
            else:
                min_len = min(min_len, this_len)

            arrays.append(arr)
            used_channels.append(ch)

        if not arrays:
            print(f"文件 '{file_name}' 未获取到任何有效通道数据 (可能因截断后为空)!")
            return None, fs

        # 截断到最短长度 (在所有通道都被读取并可能被截断后进行)
        for i in range(len(arrays)):
            arrays[i] = arrays[i][:min_len]

        data_array = np.column_stack(arrays)
        return data_array, fs



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
            if hasattr(self, "global_values"):
                global_dict["global_values"] = self.global_values

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

        self.channel_options = self._collect_channels_from_results(self.processing_results)
        self.view.refresh_global_params_tab()

        finish_msg = f"自定义信号 '{custom_name}' 已生成。"
        self.log_message("[完成]" + finish_msg + "\n")
        messagebox.showinfo("提示", finish_msg)

    def get_spectrum_data(self, file_name, channel_name):
        """
        获取频谱数据。如果设置了截断范围并且View中勾选了应用，则使用截断后的数据计算FFT。
        """
        if not self.processing_results:
            return None, None
            
        # 检查是否需要应用截断 (按文件检查)
        apply_truncation = False
        truncation_range = None
        if self.view.apply_truncation_to_spectrum_var.get(): # Checkbox state from view
            truncation_range = self.truncation_settings.get(file_name)
            if truncation_range:
                apply_truncation = True
                
        # 获取原始时域数据
        data_converted = self.get_time_domain_data(file_name, channel_name)
        if data_converted is None:
            return None, None
            
        # 如果应用截断，则截取数据段
        data_to_process = data_converted
        if apply_truncation:
            start_sec = truncation_range['start_sec']
            end_sec = truncation_range['end_sec']
            sampling_rate = self.params.sampling_rate
            start_idx = int(start_sec * sampling_rate)
            end_idx = min(int(end_sec * sampling_rate) + 1, len(data_converted))
            data_to_process = data_converted[start_idx:end_idx]
            
            if len(data_to_process) < 1024: # 检查截断后长度
                self.log_message(f"警告：截断后数据点数过少 ({len(data_to_process)}点)，无法进行频谱分析 (通道: {channel_name})\n")
                return None, None
            # self.log_message(f"信息：正在使用 {start_sec:.4f}s - {end_sec:.4f}s 时间段进行频谱分析 (通道: {channel_name})\n") # 避免过多日志

        # 检查是否需要应用频率去除 (VK2)
        apply_removal = self.view.apply_freq_removal_var.get()
        if apply_removal:
            vk2_params = self.get_vk2_parameters()
            if not vk2_params or not vk2_params.get('freq_list'):
                 self.log_message("警告：VK2参数无效或频率列表为空，无法去除频率\n")
                 # 即使VK2失败，也继续进行FFT
                 pass # 继续执行下面的FFT
            else:
                # 对截断后（或完整）的数据应用VK2
                from processor.fft_processor import FFTProcessor
                processor = FFTProcessor(self.params, None, self)
                data_to_process = processor.remove_specified_frequencies(data_to_process, self.params.sampling_rate, vk2_params)
                if data_to_process is None: # VK2处理失败
                    return None, None 

        # 对截断后（或完整，可能已VK2处理）的数据进行FFT
        import numpy as np
        from scipy.fft import fft, fftfreq
        N = len(data_to_process)
        fft_values = fft(data_to_process)
        freq = fftfreq(N, d=1.0/self.params.sampling_rate)
        idx = freq >= 0
        freq = freq[idx]
        fft_values = fft_values[idx]
        amplitude = np.abs(fft_values)*2/N
        if N > 0: # 避免除零错误
             amplitude[0] = amplitude[0]/2
        return freq, amplitude

    def set_analysis_truncation_range(self, file_name, start_sec, end_sec):
        """存储指定文件用于后续分析(频谱/OMA)的时间范围（秒）"""
        if not self.params:
             self.log_message("错误：无法获取采样率等参数以验证时间范围\n")
             return False # 表示失败
             
        # 获取任一通道数据以验证总时长（假设同一文件下通道等长）
        # 优化：可以只在首次处理或需要时获取一次总时长
        data = None
        if self.processing_results:
             for f_res in self.processing_results.files:
                  if f_res['file_name'] == file_name and f_res['fft_results']:
                       first_channel_name = f_res['fft_results'][0]['fft_result'].name
                       data = self.get_time_domain_data(file_name, first_channel_name)
                       break
                       
        if data is None:
            self.log_message(f"错误：无法获取文件 {file_name} 的数据以验证时间范围\n")
            return False
            
        total_length = len(data)
        sampling_rate = self.params.sampling_rate
        total_time = total_length / sampling_rate
        
        if not (0 <= start_sec < end_sec <= total_time):
             self.log_message(f"错误：时间范围 {start_sec:.4f}s - {end_sec:.4f}s 超出信号总时长 {total_time:.4f}s\n")
             return False
             
        # 存储设置 (按文件存储)
        self.truncation_settings[file_name] = {
            'start_sec': start_sec,
            'end_sec': end_sec
        }
        self.log_message(f"[设置] 文件 {file_name} 的后续分析时间范围已设为 {start_sec:.4f}s - {end_sec:.4f}s\n")
        return True # 表示成功

    def clear_analysis_truncation_range(self, file_name):
        """清除指定文件的后续分析时间范围设置"""
        if file_name in self.truncation_settings:
            del self.truncation_settings[file_name]
            self.log_message(f"[清除] 已取消文件 {file_name} 的后续分析时间范围限制\n")
            return True
        return False

    def log_message(self, message):
        """往日志窗口or控制台输出信息。"""
        if self.view and hasattr(self.view, 'log_text'):
            self.view.log_text.insert(tk.END, message)
            self.view.log_text.see(tk.END)
        else:
            print(message)

    def process_truncated_file_segment(self, file_name, start_sec, end_sec):
        """
        处理指定文件的所有通道在指定时间段的时域信号，
        生成新的FFT结果集，并添加到processing_results中。
        
        返回: 成功则返回新生成的文件名，失败返回None
        """
        if not self.processing_results or not self.params:
            self.log_message("错误：没有处理结果或参数，无法进行截断处理\n")
            return None
            
        # 找到原始文件结果和sensor_settings
        original_file_data = None
        original_sensor_settings = None
        if self.processing_results:
             for i, f_res in enumerate(self.processing_results.files):
                 if f_res['file_name'] == file_name:
                     original_file_data = f_res
                     # 假设 sensor_settings 列表与 files 列表中的文件顺序或标识有对应关系
                     # 或者 sensor_settings 是全局的，适用于所有文件
                     # 这里假设 sensor_settings 是与初始处理关联的全局设置
                     original_sensor_settings = self.params.sensor_settings 
                     break
        
        if not original_file_data or not original_file_data.get('fft_results') or not original_sensor_settings:
            self.log_message(f"错误：未找到文件 '{file_name}' 或其有效的通道数据/传感器设置\n")
            return None
            
        # 确定参考(输入)通道索引和名称
        ref_channel_index = -1
        ref_channel_name = None
        for idx, setting in enumerate(original_sensor_settings):
            if setting.is_reference:
                ref_channel_index = idx
                ref_channel_name = setting.name
                break
        
        # 验证时间范围 (需要先获取一次数据以得到总时长)
        first_fft_entry = original_file_data['fft_results'][0]
        first_channel_data = first_fft_entry.get('data_converted')
        first_channel_name = first_fft_entry['fft_result'].name
        if first_channel_data is None:
             # 尝试从 get_time_domain_data 获取 (如果上面没有)
             first_channel_data = self.get_time_domain_data(file_name, first_channel_name)
             if first_channel_data is None:
                  self.log_message(f"错误：无法获取文件 '{file_name}' 的示例数据以验证时间范围\n")
                  return None
                  
        total_length = len(first_channel_data)
        sampling_rate = self.params.sampling_rate
        total_time = total_length / sampling_rate
        
        if not (0 <= start_sec < end_sec <= total_time):
             self.log_message(f"错误：指定的时间范围 {start_sec:.4f}s - {end_sec:.4f}s 无效或超出信号总时长 {total_time:.4f}s\n")
             return None
             
        start_idx = int(start_sec * sampling_rate)
        end_idx = min(int(end_sec * sampling_rate) + 1, total_length)
        min_len_required = 1024
        if (end_idx - start_idx) < min_len_required:
            self.log_message(f"错误：截断后的数据点数过少 ({end_idx - start_idx}点)，无法进行有效分析\n")
            return None
            
        # 创建新文件名
        new_file_name = f"{file_name}_truncated_{start_sec:.3f}s-{end_sec:.3f}s"
        self.log_message(f"信息：正在为文件 '{file_name}' 的所有通道生成截断分析结果 ({start_sec:.3f}s-{end_sec:.3f}s)，新文件名: {new_file_name}\n")

        new_channels_dict = {} # 使用字典存储新通道数据
        processor = FFTProcessor(self.params, self.view.log_text, self)
        success_count = 0

        # 遍历原始文件的所有通道结果
        for original_fft_entry in original_file_data['fft_results']:
            original_channel_name = original_fft_entry['fft_result'].name
            original_data = original_fft_entry.get('data_converted')
            col_idx = original_fft_entry.get('col_idx', -1)
            is_input_channel = (original_channel_name == ref_channel_name)

            if original_data is None:
                original_data = self.get_time_domain_data(file_name, original_channel_name)
                if original_data is None:
                    self.log_message(f"警告：无法获取通道 '{original_channel_name}' 的原始数据，跳过截断处理\n")
                    continue
            
            truncated_data = original_data[start_idx:end_idx]
            
            try:
                new_fft_result, _ = processor.process_user_defined_signals(
                    truncated_data, original_channel_name
                )
            except Exception as e:
                self.log_message(f"警告：处理通道 '{original_channel_name}' 的截断FFT时出错: {e}，跳过\n")
                continue
                
            if new_fft_result is None:
                self.log_message(f"警告：未能计算通道 '{original_channel_name}' 的截断FFT结果，跳过\n")
                continue

            # 存储通道信息到字典
            new_channels_dict[original_channel_name] = {
                'data': truncated_data,
                'fft_result': new_fft_result,
                'is_input': is_input_channel,
                'original_col_idx': col_idx # 可选，保留原始索引
            }
            success_count += 1

        if success_count == 0:
            self.log_message(f"错误：未能成功处理文件 '{file_name}' 中的任何通道的截断数据\n")
            return None

        # 构建新的文件结果条目 - 使用新结构
        new_file_result_entry = {
            'file_name': new_file_name,
            'is_truncated': True,
            'sampling_rate': sampling_rate,
            'channels': new_channels_dict
            # 不包含预计算的 'frf_results' 或 'fft_results' 列表
        }
        self.log_message(f"注意：截断生成的结果 '{new_file_name}' 包含各通道截断的时域数据和频谱(FFT)分析。FRF将在查看时实时计算。\n")
        
        # 将新结果添加到 processing_results 列表中
        self.processing_results.files.append(new_file_result_entry)
        
        # 更新UI
        self.view.update_visualization_options(self.processing_results)
        
        self.log_message(f"成功：已为文件 '{file_name}' 生成新的截断分析结果集 {new_file_name} ({success_count} 个通道已处理)\n")
        return new_file_name
