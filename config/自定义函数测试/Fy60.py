# 示例:
# import numpy as np
# # 通道映射: ch0, ch1, ch2, ...
# # 时间向量: t (与通道长度一致)
# # 最终请把结果保存到 'result' (numpy 数组)

# # 例1: 把 ch0 和 ch1 相加:
# result = ch0 + ch1

# # 例2: 叠加正弦信号:
# # result = ch0 + np.sin(2*np.pi*50 * t)

# # 例3: 对某通道做符号处理:
# # import numpy as np
# # result = np.sign(ch0)

# # 如果要再次使用自定义信号 (如 Custom1 ),
# # 可以在对话框里勾选 'Custom1', 并在脚本里写 ch0.
# # (假设 'Custom1' 对应 ch0)

# # 提示: 只需确保脚本最后有 'result = ...' 即可.

result = - ch0 * np.sin(2*np.pi* 8.3 * t + np.pi/6 *2 ) + ch1 * np.cos(2*np.pi* 8.3 * t + np.pi/6 *2) 




