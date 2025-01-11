# model/data_models.py

class SensorSettings:
    """描述每个通道的传感器配置。"""
    def __init__(self, sensor_type, sensitivity, unit, name, a=None, b=None, is_reference=False):
        self.sensor_type = sensor_type
        self.sensitivity = sensitivity
        self.unit = unit
        self.name = name
        self.a = a
        self.b = b
        self.is_reference = is_reference

class FFTResult:
    """存放单路信号的 FFT 结果。"""
    def __init__(self, freq, amplitude, phase, name, unit):
        self.freq = freq
        self.amplitude = amplitude
        self.phase = phase
        self.name = name
        self.unit = unit

class ProcessingParameters:
    """处理过程所需的参数集合。"""
    def __init__(
        self, input_folder, output_folder, filename_prefix,
        sampling_rate, sensor_settings
    ):
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.filename_prefix = filename_prefix
        self.sampling_rate = sampling_rate
        self.sensor_settings = sensor_settings

    def validate(self):
        errors = []
        if not self.input_folder or not self.output_folder:
            errors.append("输入和输出文件夹不能为空。")
        return errors

class ProcessingResults:
    """
    整个处理完成后保存的结果。
    files: [{ 'file_name', 'fft_results', 'frf_results', 'base_name'}, ...]
    sensor_settings
    has_reference_sensor
    """
    def __init__(self, sensor_settings):
        self.files = []
        self.sensor_settings = sensor_settings
        self.has_reference_sensor = any(s.is_reference for s in sensor_settings)

    def add_file_result(self, file_result):
        self.files.append(file_result)
