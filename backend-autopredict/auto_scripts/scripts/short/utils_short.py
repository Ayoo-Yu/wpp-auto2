# utils_short.py

import matplotlib
# 设置后端为 Agg 以避免使用 Tkinter
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import numpy as np
import math
from config_short import Today
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
    计算合格率K值（整体计算方式）
    
    注意：此函数将所有数据视为一个整体计算单一K值。
    对于按天分别计算K值并取平均的方式，请使用 calculate_daily_averaged_k 函数。
    
    参数:
    y_true: 实际值
    y_pred: 预测值
    threshold: 阈值，如果不提供则使用风电场装机容量的20%
    
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

def calculate_daily_averaged_k(y_true, y_pred, capacity=453.5, threshold=None, points_per_day=96):
    """
    计算日平均合格率K值。

    K值首先按天计算，每天包含 'points_per_day' 个数据点（通常是96个15分钟点）。
    如果最后一天的数据点不足 'points_per_day'，则基于实际可用点数计算该天的K值。
    最终返回所有天K值的平均值。

    参数:
    y_true (array-like): 实际值时间序列。numpy数组或类似列表的结构。
    y_pred (array-like): 预测值时间序列。numpy数组或类似列表的结构。
    capacity (float, 可选): 用于计算默认阈值的参考容量 (例如风电场装机容量)。
                            默认为 453.5。仅在 threshold 参数为 None 时使用。
    threshold (float, 可选): 用于计算K值的绝对阈值。
                             如果为 None (默认值)，则使用 capacity * 0.2 作为阈值。
                             如果提供了具体数值，则直接使用该数值。
    points_per_day (int, 可选): 每天的数据点数量。默认为 96 (对应15分钟一个点)。

    返回:
    float: 所有计算出的日K值的算术平均值。如果输入数据为空，或者无法计算任何一天的K值，则返回 np.nan。

    异常:
    ValueError: 如果 y_true 和 y_pred 的长度不同。
                如果计算得到的阈值小于或等于0。
    """
    # 1. 输入处理与验证
    # 确保输入是numpy数组，方便进行向量化计算
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    # 检查实际值和预测值的长度是否一致
    if len(y_true) != len(y_pred):
        raise ValueError("实际值和预测值长度必须相同")

    n_points = len(y_true) # 获取总数据点数
    # 如果没有数据点，直接返回 NaN
    if n_points == 0:
        print("警告: 输入数据为空，返回 NaN。")
        return np.nan

    # 2. 确定阈值 (Threshold)
    if threshold is None:
        # 如果用户没有指定阈值，则使用容量的20%作为阈值
        effective_threshold = capacity * 0.2
    else:
        # 使用用户指定的阈值
        effective_threshold = threshold

    # 阈值必须是正数，否则分母可能为0或负数，导致计算错误
    if effective_threshold <= 0:
        raise ValueError(f"计算出的阈值必须为正数, 但得到的是 {effective_threshold}")

    # 3. 按天计算K值
    daily_k_values = [] # 用于存储每天计算出的K值
    # 计算总共需要处理多少天 (向上取整，处理不足一天的情况)
    num_days = math.ceil(n_points / points_per_day)

    # 循环处理每一天的数据
    for i in range(num_days):
        # 计算当天数据在总数据中的起始和结束索引
        start_index = i * points_per_day
        # 结束索引不能超过总数据长度
        end_index = min((i + 1) * points_per_day, n_points)

        # 获取当天对应的实际值和预测值数据段
        y_true_day = y_true[start_index:end_index]
        y_pred_day = y_pred[start_index:end_index]

        # 理论上如果 n_points > 0，这里的 len(y_true_day) 不会为0，但作为安全检查
        if len(y_true_day) == 0:
            continue # 如果当天没有数据点，跳过这一天

        # --- 开始计算当天的K值 ---
        # 计算分母：取 实际值的绝对值 和 阈值 中的较大者
        denominators = np.maximum(np.abs(y_true_day), effective_threshold)

        # 计算 M = [ (预测值 - 实际值) / 分母 ]^2
        # 使用 np.errstate 避免潜在的除零警告 (虽然理论上因为有正阈值不会发生)
        with np.errstate(divide='ignore', invalid='ignore'):
            m_values = ((y_pred_day - y_true_day) / denominators) ** 2

        # 处理计算中可能出现的 NaN 或 Inf (例如分母极小接近0的情况)
        # 将 NaN 替换为 0，将 Inf 替换为该数据类型的最大/最小值
        m_values = np.nan_to_num(m_values, nan=0.0, posinf=np.finfo(m_values.dtype).max, neginf=np.finfo(m_values.dtype).min)

        # 计算当天所有 M 值的平均值
        if m_values.size > 0: # 确保有 M 值可以计算平均
             mean_m_value = np.mean(m_values)
             # 计算当天的K值: K = 1 - sqrt(平均M值)
             # 在开方前确保 mean_m_value 不小于0，防止因浮点精度问题产生复数
             k_day = 1 - np.sqrt(max(0, mean_m_value))
             # 将当天计算出的K值添加到列表中
             daily_k_values.append(k_day)
        else:
             # 如果没有有效的 M 值（不太可能发生，但作为保障）
             print(f"警告: 索引 {start_index} 开始的当天没有有效的 M 值，已跳过。")
        # --- 当天K值计算结束 ---

    # 4. 计算最终结果
    # 如果列表为空 (例如输入数据不足一天，或者所有天的数据都有问题)
    if not daily_k_values:
        print("警告: 未能计算出任何有效的日K值 (可能是因为输入长度问题或数据导致计算错误)。返回 NaN。")
        return np.nan
    else:
        # 计算所有日K值的平均值
        final_k = np.mean(daily_k_values)
        return final_k

def evaluate_with_time_weights(y_true, y_pred, timestamps, rmse_weight=0.2, k_weight=0.8, time_decay=0.9):
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
    
    # 计算带权重的K值 - 考虑使用按天平均的方式
    # 此处仍使用旧方法计算K值，可根据需要修改为使用calculate_daily_averaged_k
    threshold = 453.5 * 0.2  # 风电场装机容量的20%
    denominators = np.maximum(np.abs(y_true), threshold)
    m_values = ((y_pred - y_true) / denominators) ** 2
    weighted_k = 1 - np.sqrt(np.sum(m_values * time_weights))
    
    # 计算标准RMSE和K值(不带权重，用于参考)
    rmse = calculate_rmse(y_true, y_pred)
    k = calculate_daily_averaged_k(y_true, y_pred, capacity=453.5, threshold=None, points_per_day=96)
    
    # 归一化RMSE (使其在0到1之间，越小越好)
    # 这里假设RMSE最大不超过装机容量
    norm_rmse = min(1.0, weighted_rmse / 453.5)
    norm_weighted_rmse = 1 - norm_rmse  # 转换为越大越好
    
    # 综合评分 (加权平均)
    score = norm_weighted_rmse * rmse_weight + weighted_k * k_weight
    
    return score, rmse, k
          