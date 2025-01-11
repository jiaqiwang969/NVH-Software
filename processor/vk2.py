# vk2.py

import numpy as np
from scipy.sparse import diags, eye
from scipy.sparse.linalg import spsolve

def vk2(y, f, fs, r, filtord):
    """
    Vold-Kalman 二代滤波器，用于提取单个频率成分。
    
    参数：
    y       - 数据向量，长度为 N
    f       - 频率向量（Hz），长度为 N
    fs      - 采样频率（Hz）
    r       - 权重因子（正数）
    filtord - 滤波器阶数，1 或 2

    返回：
    x   - 提取的频率成分的复包络
    bw  - 滤波器 -3 dB 带宽（Hz）
    T   - 滤波器的 10% - 90% 过渡时间
    xr  - 重建的信号（实部）
    """
    y = np.asarray(y).flatten()
    N = len(y)
    f = np.asarray(f).flatten()
    if len(f) != N:
        raise ValueError('f 和 y 的长度必须相同')
    if filtord not in [1, 2]:
        raise ValueError('filtord 必须为 1 或 2')
        return None
    
    dt = 1 / fs
    if filtord == 1:
        NR = N - 2
        e = np.ones(NR)
        data = np.vstack([e, -2*e, e])
        offsets = np.array([0, 1, 2])
        A = diags(data, offsets, shape=(NR, N))
        bw = fs / (2 * np.pi) * (1.58 * r ** -0.5)
        T = 2.85 * r ** 0.5
    elif filtord == 2:
        NR = N - 3
        e = np.ones(NR)
        data = np.vstack([e, -3*e, 3*e, -e])
        offsets = np.array([0, 1, 2, 3])
        A = diags(data, offsets, shape=(NR, N))
        bw = fs / (2 * np.pi) * (1.70 * r ** (-1/3))
        T = 2.80 * r ** (1/3)
    
    AA = r * r * A.T @ A + eye(N, format='csc')
    jay = 1j
    ejth = np.exp(jay * 2 * np.pi * np.cumsum(f) * dt)
    yy = np.conj(ejth) * y
    x = 2 * spsolve(AA, yy)
    xr = np.real(x * ejth)
    return x, bw, T, xr

