import numpy as np

def calculate_average_speed(ch2, fs=25600, deg_per_edge=3.0):
    # 信号二值化
    binary_signal = np.where(ch2 > 2.5, 1, 0)

    # 检测跳变点
    edges = np.diff(binary_signal)
    rising_edges = np.where(edges == 1)[0] + 1  # 上升沿索引
    falling_edges = np.where(edges == -1)[0] + 1  # 下降沿索引
    all_edges = np.sort(np.concatenate((rising_edges, falling_edges)))

    # 计算时间间隔和瞬时转速
    speed_array = np.zeros(len(ch2))
    for i in range(len(all_edges) - 1):
        t1 = all_edges[i]
        t2 = all_edges[i + 1]
        time_interval = (t2 - t1) / fs  # 时间间隔（秒）
        if time_interval > 0:
            speed = (deg_per_edge / 360.0) / time_interval  # 转/秒
            speed_array[t1:t2] = speed

    # 处理信号开头和结尾部分
    if len(all_edges) > 0:
        speed_array[:all_edges[0]] = speed_array[all_edges[0]]
        speed_array[all_edges[-1]:] = speed_array[all_edges[-1] - 1]

    # 计算平均转速
    average_speed = np.mean(speed_array)  # 转/秒
    return average_speed

# 使用 channel2 计算平均转速
average_speed = calculate_average_speed(ch2)

# 生成最终结果
result = ch0 * np.cos(2 * np.pi * average_speed * t) + ch1 * np.sin(2 * np.pi * average_speed * t)
