# utils.py

import matplotlib
# 设置后端为 Agg 以避免使用 Tkinter
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import numpy as np
import math
from config import Today
import logging

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def visualize_results(results_dict, y_val, output_path):
    """
    可视化不同模型的预测结果与实际值
    """
    plt.figure(figsize=(20, 10))
    for model_name, result in results_dict.items():
        plt.plot(range(len(result['y_pred'])), result['y_pred'], label=f'{model_name} Predicted Power')
    
    plt.plot(range(len(y_val)), y_val, label='Actual Power', linestyle='dashed')
    plt.xlabel('Index')
    plt.ylabel('Power')
    plt.title('Verify set power predictions - Different LightGBM Models')
    plt.legend()
    
    # 确保输出目录存在
    output_dir = os.path.join(output_path, Today)
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存图像
    output_file = os.path.join(output_dir, 'Predictions.png')
    plt.savefig(output_file)
    plt.close()  # 关闭图表以释放资源
    print(f"图像已保存为 {output_file}")

def calculate_rmse(y_true, y_pred):
    """
    计算RMSE(均方根误差)
    
    参数:
    y_true: 实际值
    y_pred: 预测值
    
    返回:
    RMSE值
    """
    if len(y_true) != len(y_pred):
        raise ValueError("实际值和预测值长度必须相同")
    
    return np.sqrt(np.mean((y_true - y_pred) ** 2))

def calculate_k(y_true, y_pred, threshold=None):
    """
    计算合格率K值
    
    参数:
    y_true: 实际值
    y_pred: 预测值
    threshold: 阈值，如果不提供则使用实际值的20%
    
    返回:
    K值
    """
    if len(y_true) != len(y_pred):
        raise ValueError("实际值和预测值长度必须相同")
    
    if threshold is None:
        # 使用风电场装机容量的20%作为阈值
        threshold = 453.5 * 0.2
    
    # 计算K值
    denominators = np.maximum(np.abs(y_true), threshold)
    m_values = ((y_pred - y_true) / denominators) ** 2
    k_value = 1 - np.sqrt(np.mean(m_values))
    
    return k_value

def evaluate_with_time_weights(y_true, y_pred, timestamps, rmse_weight=0.5, k_weight=0.5, time_decay=0.9):
    """
    使用时间权重计算综合评分
    
    参数:
    y_true: 实际值
    y_pred: 预测值
    timestamps: 时间戳列表，格式为pandas datetime
    rmse_weight: RMSE在综合评分中的权重 (0到1之间)
    k_weight: K值在综合评分中的权重 (0到1之间)
    time_decay: 时间衰减系数，越小衰减越快
    
    返回:
    综合评分、RMSE值、K值
    """
    if len(y_true) != len(y_pred) or len(y_true) != len(timestamps):
        print("实际值长度", len(y_true))
        print("预测值长度", len(y_pred))
        print("时间戳长度", len(timestamps))
        logger.info(f"实际值长度: {len(y_true)}")
        logger.info(f"预测值长度: {len(y_pred)}")
        logger.info(f"时间戳长度: {len(timestamps)}")
        raise ValueError("实际值、预测值和时间戳长度必须相同")
    
    # 计算时间权重
    latest_time = max(timestamps)
    # 将时间差转换为小时数
    time_deltas = []
    for t in timestamps:
        time_diff = latest_time - t
        # 处理numpy.timedelta64对象
        if hasattr(time_diff, 'total_seconds'):
            # 标准的datetime.timedelta对象
            seconds = time_diff.total_seconds()
        else:
            # numpy.timedelta64对象
            seconds = time_diff / np.timedelta64(1, 's')
        time_deltas.append(seconds / 3600)  # 转换为小时
    
    max_delta = max(time_deltas) if time_deltas else 1  # 避免除以零
    
    # 计算归一化的时间权重 (越近的时间权重越大)
    time_weights = np.array([time_decay ** (delta / max_delta) for delta in time_deltas])
    time_weights = time_weights / sum(time_weights)  # 归一化权重
    
    # 计算带权重的RMSE
    squared_errors = (y_true - y_pred) ** 2
    weighted_rmse = np.sqrt(np.sum(squared_errors * time_weights))
    
    # 计算带权重的K值
    threshold = 453.5 * 0.2  # 风电场装机容量的20%
    denominators = np.maximum(np.abs(y_true), threshold)
    m_values = ((y_pred - y_true) / denominators) ** 2
    weighted_k = 1 - np.sqrt(np.sum(m_values * time_weights))
    
    # 计算标准RMSE和K值(不带权重，用于参考)
    rmse = calculate_rmse(y_true, y_pred)
    k = calculate_k(y_true, y_pred, threshold)
    
    # 归一化RMSE (使其在0到1之间，越小越好)
    # 这里假设RMSE最大不超过装机容量
    norm_rmse = min(1.0, weighted_rmse / 453.5)
    norm_weighted_rmse = 1 - norm_rmse  # 转换为越大越好
    
    # 综合评分 (加权平均)
    score = norm_weighted_rmse * rmse_weight + weighted_k * k_weight
    
    return score, rmse, k
          