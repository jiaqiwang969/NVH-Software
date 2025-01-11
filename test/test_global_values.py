# 文件名: test_global_values.py

class GlobalValues:
    """
    利用多级键 (file_name, channel_name, param_key) 来管理自定义参数。
    file_name=None 表示适用于所有文件 (global)。
    channel_name=None 表示适用于所有通道。
    param_key 是对具体参数的命名，如 "freq_to_remove", "axis_freq" 等。
    """
    def __init__(self):
        # 用字典存储所有参数，key 是 (fkey, ckey, pkey) 的元组
        self._values = {}

    def set_value(self, file_name: str, channel_name: str, param_key: str, value):
        fkey = file_name if file_name else "__GLOBAL__"
        ckey = channel_name if channel_name else "__ALL__"
        self._values[(fkey, ckey, param_key)] = value

    def get_value(self, file_name: str, channel_name: str, param_key: str, default=None):
        fkey = file_name if file_name else "__GLOBAL__"
        ckey = channel_name if channel_name else "__ALL__"
        return self._values.get((fkey, ckey, param_key), default)

    def has_value(self, file_name: str, channel_name: str, param_key: str) -> bool:
        fkey = file_name if file_name else "__GLOBAL__"
        ckey = channel_name if channel_name else "__ALL__"
        return (fkey, ckey, param_key) in self._values

    def delete_value(self, file_name: str, channel_name: str, param_key: str) -> bool:
        fkey = file_name if file_name else "__GLOBAL__"
        ckey = channel_name if channel_name else "__ALL__"
        if (fkey, ckey, param_key) in self._values:
            del self._values[(fkey, ckey, param_key)]
            return True
        return False

    def list_all_params(self):
        """ 返回一个可读列表(字符串)，调试或查看用。 """
        result_list = []
        for (fkey, ckey, pkey), val in self._values.items():
            result_list.append(f"({fkey}, {ckey}, {pkey}) => {val}")
        return result_list


def demo_global_values():
    """
    演示如何使用 GlobalValues 来添加/获取/删除 各种类型的参数
    （标量、向量、矩阵等），并区分不同的 file_name、channel_name。
    """
    gv = GlobalValues()

    print("\n=== 1. 设置一些‘全局’参数(不区分文件,通道) ===")
    # 1) 全局标量
    gv.set_value(None, None, "sample_rate", 25600)
    # 2) 全局向量(如 要去除的频率)
    gv.set_value(None, None, "freq_to_remove", [50.0, 120.0])
    # 3) 全局矩阵(也可以)
    import numpy as np
    matrix_val = np.array([[1, 2], [3, 4]])
    gv.set_value(None, None, "test_matrix", matrix_val)

    # 查看结果
    for line in gv.list_all_params():
        print("  ", line)

    print("\n=== 2. 给某个文件 + 通道 设置专属参数 ===")
    fileA = "FileA.txt"
    ch0   = "ch0"
    # 2.1) 给 FileA + ch0 单独设 freq_to_remove = [60, 180]
    gv.set_value(fileA, ch0, "freq_to_remove", [60.0, 180.0])
    # 2.2) 给 FileA + ch1 设置 axis_freq = 47.12
    gv.set_value(fileA, "ch1", "axis_freq", 47.12)
    # 2.3) 给 FileA (所有通道) 设置 filtord=2
    gv.set_value(fileA, None, "filtord", 2)

    print("[输出] 已为 fileA.txt + ch0/ch1 等设置一些参数.\n当前列表:")
    for line in gv.list_all_params():
        print("  ", line)

    print("\n=== 3. 模拟读取: 先精确找(file, ch)没有就默认回退 ===")
    # 3.1) 优先找 (FileA.txt, ch0, 'freq_to_remove')
    #      如果找不到再看看 (FileA.txt, __ALL__, 'freq_to_remove')
    #      如果还没, 再看 (__GLOBAL__, __ALL__, 'freq_to_remove')
    # 演示一个简单的“回退”函数:
    def get_value_fallback(file_name, channel_name, param_key, default=None):
        val = gv.get_value(file_name, channel_name, param_key, None)
        if val is not None:
            return val
        # 若 channel_name 不为空, 试 (file_name, None, param_key)
        if channel_name is not None:
            val = gv.get_value(file_name, None, param_key, None)
            if val is not None:
                return val
        # 最后试 (None, None, param_key)
        val = gv.get_value(None, None, param_key, default)
        return val

    # 3.2) 测试回退
    freq_list_for_ch0 = get_value_fallback(fileA, "ch0", "freq_to_remove", default=[])
    freq_list_for_ch2 = get_value_fallback(fileA, "ch2", "freq_to_remove", default=[])
    freq_list_global  = get_value_fallback(None, None, "freq_to_remove", default=[])

    print(f"[FileA, ch0] freq_to_remove = {freq_list_for_ch0}")  # 期望是 [60.0, 180.0]
    print(f"[FileA, ch2] freq_to_remove = {freq_list_for_ch2}")  # 未显式设置, 会回退到全局 [50.0, 120.0]
    print(f"[Global] freq_to_remove   = {freq_list_global}")     # [50.0, 120.0]

    # 3.3) filtord 测试
    # 给 ch0 优先查 (FileA, ch0, "filtord") => 没有设置 => 再查 (FileA, None, "filtord") => 2 => OK
    filtord_ch0 = get_value_fallback(fileA, "ch0", "filtord", default=1)
    print(f"[FileA, ch0] filtord = {filtord_ch0} (从 fileA 通道级回退到 fileA 全局)")

    # 3.4) matrix
    mat_global = gv.get_value(None, None, "test_matrix")
    print(f"[Global] test_matrix => \n{mat_global}")

    print("\n=== 4. 删除某个键 ===")
    removed = gv.delete_value(fileA, "ch0", "freq_to_remove")
    print(f"尝试删除 (FileA, ch0, freq_to_remove)，结果: {removed}")
    for line in gv.list_all_params():
        print("  ", line)


if __name__ == "__main__":
    demo_global_values()
