import os
import sys
import numpy as np

# Add the directory we executed the script from to path:
sys.path.insert(0, os.path.realpath('__file__'))

# import the function to generate the example dataset
from pyoma2.functions.gen import example_data

# 生成示例数据
data, ground_truth = example_data()
print("data 的形状:", data.shape)  # 先看下形状

# 把 data 数组存成 txt 文本文件，比如用逗号分隔
np.savetxt("example_data.txt", data, delimiter=" ", fmt="%.6f")

print("已将 data 存为 example_data.txt")
