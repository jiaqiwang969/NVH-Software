import numpy as np

# 输入信号: ch0
fs = 25600  # 假设采样率
deg_per_edge = 3.0

# 1. 信号二值化
binary_signal = np.where(ch0 > 2.5, 1, 0)

# 2. 检测跳变点
edges = np.diff(binary_signal)
rising_edges = np.where(edges == 1)[0] + 1  # 上升沿索引
falling_edges = np.where(edges == -1)[0] + 1  # 下降沿索引
all_edges = np.sort(np.concatenate((rising_edges, falling_edges)))

# 3. 计算时间间隔和瞬时转速
speed_array = np.zeros(len(ch0))
for i in range(len(all_edges) - 1):
    t1 = all_edges[i]
    t2 = all_edges[i + 1]
    time_interval = (t2 - t1) / fs  # 时间间隔（秒）
    if time_interval > 0:
        speed = (deg_per_edge / 360.0) / time_interval  # 转/秒
        speed_array[t1:t2] = speed

# 4. 处理信号开头和结尾部分
if len(all_edges) > 0:
    speed_array[:all_edges[0]] = speed_array[all_edges[0]]
    speed_array[all_edges[-1]:] = speed_array[all_edges[-1] - 1]

# 输出结果
result = speed_array  # 转换为 RPM
