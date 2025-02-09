# data_processor.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from .config import LAGS

lags = LAGS
def load_data(file_path):
    """
    加载数据并处理NaN值
    """
    data = pd.read_csv(file_path)
    data = data.dropna()
    return data

def preprocess_data(data):
    """
    数据预处理：转换时间戳，提取时间特征，分离特征和目标变量
    """
    data['Timestamp'] = pd.to_datetime(data['Timestamp'])
    data['Year'] = data['Timestamp'].dt.year
    data['Month'] = data['Timestamp'].dt.month
    data['Day'] = data['Timestamp'].dt.day
    data['Hour'] = data['Timestamp'].dt.hour
    features = [col for col in data.columns if col not in ['Timestamp','wp_true','ws_all']]
    X = data[features]
    y = data['wp_true'].fillna(data['wp_true'].mean())
    
    return X, y

def preprocess_data_pre(data):
    """
    数据预处理：转换时间戳，提取时间特征，分离特征和目标变量
    """
    data['Timestamp'] = pd.to_datetime(data['Timestamp'])
    data['Year'] = data['Timestamp'].dt.year
    data['Month'] = data['Timestamp'].dt.month
    data['Day'] = data['Timestamp'].dt.day
    data['Hour'] = data['Timestamp'].dt.hour
    features = [col for col in data.columns if col not in ['Timestamp']]
    X = data[features]
    return X

def split_data(X, y, train_ratio=0.9):
    """
    按顺序拆分训练集和验证集
    """
    split_index = int(len(X) * train_ratio)
    X_train, X_val = X[:split_index], X[split_index:]
    y_train, y_val = y[:split_index], y[split_index:]
    return X_train, X_val, y_train, y_val

# def feature_engineering(X_train, X_val, lags):
#     """
#     特征工程：特征组合、滞后特征等
#     """
#     combined_features = {}
#     wind_speeds_10 = [f'ws10_{i}' for i in range(1, 16)]
#     wind_speeds_100 = [f'ws100_{i}' for i in range(1, 16)]
#     wind_speeds_200 = [f'ws200_{i}' for i in range(1, 16)]
    
#     # 生成高度10和100的风速差异特征
#     for wind_speeds in [wind_speeds_100, wind_speeds_200]:
#         for i in range(len(wind_speeds)):
#             for j in range(i + 1, len(wind_speeds)):
#                 combined_features[f'{wind_speeds[i]}_{wind_speeds[j]}_diff1'] = X_train[wind_speeds[i]] - X_train[wind_speeds[j]]
    
#     # 生成高度10和200的风速差异特征
#     for wind_speeds in [wind_speeds_10, wind_speeds_200]:
#         for i in range(len(wind_speeds)):
#             for j in range(i + 1, len(wind_speeds)):
#                 combined_features[f'{wind_speeds[i]}_{wind_speeds[j]}_diff2'] = X_train[wind_speeds[i]] - X_train[wind_speeds[j]]
    
#     # 引入滞后风速特征
#     lag_features = {}
#     for lag in range(1, lags):  # 使用前3小时的滞后特征
#         for col in wind_speeds_10 + wind_speeds_100 + wind_speeds_200:
#             lag_features[f'{col}_lag{lag}'] = X_train[col].shift(lag)
    
#     combined_features_df = pd.DataFrame(combined_features)
#     lag_features_df = pd.DataFrame(lag_features)
    
#     X_train = pd.concat([X_train, combined_features_df, lag_features_df], axis=1).dropna()
    
#     # 对验证集进行相同的特征工程处理
#     combined_features_val = {}
#     lag_features_val = {}
#     for wind_speeds in [wind_speeds_100, wind_speeds_200]:
#         for i in range(len(wind_speeds)):
#             for j in range(i + 1, len(wind_speeds)):
#                 combined_features_val[f'{wind_speeds[i]}_{wind_speeds[j]}_diff1'] = X_val[wind_speeds[i]] - X_val[wind_speeds[j]]
    
#     for wind_speeds in [wind_speeds_10, wind_speeds_200]:
#         for i in range(len(wind_speeds)):
#             for j in range(i + 1, len(wind_speeds)):
#                 combined_features_val[f'{wind_speeds[i]}_{wind_speeds[j]}_diff2'] = X_val[wind_speeds[i]] - X_val[wind_speeds[j]]
    
#     for lag in range(1, lags):
#         for col in wind_speeds_10 + wind_speeds_100 + wind_speeds_200:
#             lag_features_val[f'{col}_lag{lag}'] = X_val[col].shift(lag)
    
#     combined_features_df_val = pd.DataFrame(combined_features_val)
#     lag_features_df_val = pd.DataFrame(lag_features_val)
    
#     X_val = pd.concat([X_val, combined_features_df_val, lag_features_df_val], axis=1).dropna()
    
#     return X_train, X_val

from collections import defaultdict
import itertools

def feature_engineering(X_train, X_val, lags):
    """
    动态生成特征工程：跨高度的风速差异和滞后特征
    """
    
    def get_wind_features_info(df):
        """收集数据集中各高度层的风速特征及其索引"""
        features_by_height = defaultdict(dict)  # {高度: {索引: 列名}}
        for col in df.columns:
            if col.startswith('ws'):
                parts = col.split('_')
                if len(parts) >= 2 and parts[0][2:].isdigit():
                    height = int(parts[0][2:])
                    index = parts[1]
                    if index.isdigit():
                        features_by_height[height][int(index)] = col
        return features_by_height

    # 获取训练集的特征信息
    train_feature_info = get_wind_features_info(X_train)
    heights = list(train_feature_info.keys())

    # === 训练集特征生成 ===
    # 1. 跨高度风速差异特征
    combined_train = {}
    for h1, h2 in itertools.combinations(heights, 2):
        # 获取两个高度的共有索引
        common_indices = set(train_feature_info[h1]) & set(train_feature_info[h2])
        for idx in common_indices:
            col1 = train_feature_info[h1][idx]
            col2 = train_feature_info[h2][idx]
            combined_train[f'ws_diff_{h1}_{h2}_{idx}'] = X_train[col1] - X_train[col2]

    # 2. 滞后特征
    lag_train = {}
    all_wind_cols = {col for h in train_feature_info for col in train_feature_info[h].values()}
    for lag in range(1, lags):
        for col in all_wind_cols:
            lag_train[f'{col}_lag{lag}'] = X_train[col].shift(lag)

    # 合并新特征
    X_train = pd.concat([X_train, pd.DataFrame(combined_train), pd.DataFrame(lag_train)], axis=1,sort=False)

    # === 验证集特征生成 ===
    # 使用训练集发现的模式（确保特征一致性）
    combined_val = {}
    for h1, h2 in itertools.combinations(heights, 2):
        common_indices = set(train_feature_info[h1]) & set(train_feature_info[h2])
        for idx in common_indices:
            col1 = f'ws{h1}_{idx}'
            col2 = f'ws{h2}_{idx}'
            if col1 in X_val and col2 in X_val:
                combined_val[f'ws_diff_{h1}_{h2}_{idx}'] = X_val[col1] - X_val[col2]

    lag_val = {}
    for lag in range(1, lags):
        for col in all_wind_cols:
            if col in X_val:
                lag_val[f'{col}_lag{lag}'] = X_val[col].shift(lag)

    # 合并新特征
    X_val = pd.concat([X_val, pd.DataFrame(combined_val), pd.DataFrame(lag_val)], axis=1,sort=False)

    # 统一删除缺失值
    X_train = X_train.dropna()
    X_val = X_val.dropna()
    
    return X_train, X_val

def scale_data(X_train, X_val):
    """
    标准化数据
    """
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    return X_train_scaled, X_val_scaled, scaler

def create_time_window(X, y, window_size):
    """
    创建时间窗口
    """
    X_windows = []
    y_windows = []
    for i in range(len(X) - window_size + 1):
        X_windows.append(X[i:i + window_size])
        y_windows.append(y[i + window_size + lags-2])  # 注意这里的索引
    return np.array(X_windows), np.array(y_windows)

def create_time_window_pre(X, window_size):
    """
    创建时间窗口
    """
    X_windows = []
    for i in range(len(X) - window_size + 1):
        X_windows.append(X[i:i + window_size])
    return np.array(X_windows)