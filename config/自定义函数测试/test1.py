# 示例:
# import numpy as np
# # ch0, ch1, ..., t -> result
# result = ch0 + ch1
import numpy as np

# 计算 average_speed
binary_signal = np.where(ch2 > 2.5, 1, 0)
edges = np.diff(binary_signal)
rising_edges = np.where(edges == 1)[0] + 1
falling_edges = np.where(edges == -1)[0] + 1
all_edges = np.sort(np.concatenate((rising_edges, falling_edges)))

speed_array = np.zeros_like(ch2)
for i in range(len(all_edges) - 1):
    t1 = all_edges[i]
    t2 = all_edges[i + 1]
    time_interval = (t2 - t1)/fs
    if time_interval>0:
        speed = (3.0/360.0)/time_interval
        speed_array[t1:t2] = speed

average_speed = np.mean(speed_array)

freq_vector_np = np.arange(1, 10) * average_speed  # 逐元素相乘 => ndarray
freq_vector = freq_vector_np.tolist()             # 转成 Python 列表

# 存入GlobalValues
# 假设针对于当前 file_name，所有channel
global_values.set_value(file_name, "ALL_CHANNELS", "avg_speed", float(average_speed))
global_values.set_value(file_name, "ALL_CHANNELS", "freq_to_remove", freq_vector)




# 用这个速度合成 result
result = ch0 * np.cos(2*np.pi*average_speed*t) + ch1 * np.sin(2*np.pi*average_speed*t)

