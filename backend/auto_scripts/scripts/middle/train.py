# train.py
from sklearn.metrics import mean_squared_error
import lightgbm as lgb
import pandas as pd
import numpy as np
import os
import logging
import sys
import joblib  # 用于保存模型和 scaler
from config import Today
from utils import calculate_rmse, calculate_k, evaluate_with_time_weights
from data_processor import preprocess_data, filter_data_by_date, feature_engineering, scale_data, create_time_window, create_time_window_pre
from models import get_unified_params

# 获取logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 添加控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 处理Windows控制台输出编码
if sys.platform == 'win32':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    # 确保stderr也使用utf-8编码
    sys.stderr.reconfigure(encoding='utf-8')

def print_separator(msg=None):
    """打印分隔符"""
    print("\n" + "-" * 50)
    if msg:
        print(f"【{msg}】")
    if msg:
        logger.info(f"\n{'-' * 50}\n【{msg}】\n{'-' * 50}")
    else:
        logger.info(f"\n{'-' * 50}")

def train_and_evaluate(X_train, y_train, X_val, y_val, params_list, scaler, model_folder_today, val_timestamps=None):
    print_separator("开始模型训练与评估")
    results_dict = {}
    save_path = model_folder_today
    
    # 创建目录结构
    os.makedirs(save_path, exist_ok=True)
    print(f"模型和 scaler 将被保存到目录: {save_path}")
    logger.info(f"模型和 scaler 将被保存到目录: {save_path}")
    
    # 初始化变量以跟踪最佳模型
    best_mse = float('inf')
    best_model = None
    best_model_name = ""
    
    for params in params_list:
        print_separator(f"训练 {params['name']} 模型")
        # 初始化模型
        print(f"模型参数: {params}")
        logger.info(f"模型参数: {params}")
        model = lgb.LGBMRegressor(**params)
        
        # 训练模型
        print(f"开始训练 {params['name']} 模型...")
        logger.info(f"开始训练 {params['name']} 模型...")
        model.fit(X_train.reshape(X_train.shape[0], -1), y_train)
        print(f"{params['name']} 模型训练完成")
        logger.info(f"{params['name']} 模型训练完成")
        
        # 预测验证集
        print(f"使用 {params['name']} 模型预测验证集...")
        logger.info(f"使用 {params['name']} 模型预测验证集...")
        y_pred = model.predict(X_val.reshape(X_val.shape[0], -1))
        
        # 计算 MSE
        mse = mean_squared_error(y_val, y_pred)
        rmse = np.sqrt(mse)
        k = calculate_k(y_val, y_pred)
        
        # 计算带时间权重的评分（如果提供了时间戳）
        weighted_score = None
        if val_timestamps is not None:
            # 确保时间戳与预测值长度一致
            if len(val_timestamps) != len(y_val):
                print(f"⚠️ 时间戳长度 ({len(val_timestamps)}) 与预测值长度 ({len(y_val)}) 不匹配，调整时间戳...")
                logger.info(f"⚠️ 时间戳长度 ({len(val_timestamps)}) 与预测值长度 ({len(y_val)}) 不匹配，调整时间戳...")
                
                if len(val_timestamps) > len(y_val):
                    val_timestamps = val_timestamps[-len(y_val):]
                    print(f"时间戳已截断至匹配验证集长度: {len(val_timestamps)}")
                    logger.info(f"时间戳已截断至匹配验证集长度: {len(val_timestamps)}")
                else:
                    print(f"时间戳长度不足，将使用非时间加权评分")
                    logger.info(f"时间戳长度不足，将使用非时间加权评分")
                    val_timestamps = None
            
            if val_timestamps is not None:
                print(f"使用时间加权方式计算模型评分...")
                logger.info(f"使用时间加权方式计算模型评分...")
                try:
                    weighted_score, _, _ = evaluate_with_time_weights(y_val, y_pred, val_timestamps)
                except Exception as e:
                    print(f"⚠️ 时间加权评分计算失败: {str(e)}，将使用简单加权评分")
                    logger.info(f"⚠️ 时间加权评分计算失败: {str(e)}，将使用简单加权评分")
                    weighted_score = None
        
        if weighted_score is None:
            # 没有时间戳或计算失败时使用简单评分：(1-归一化RMSE)*0.5 + k*0.5
            print(f"使用简单加权方式计算模型评分...")
            logger.info(f"使用简单加权方式计算模型评分...")
            norm_rmse = min(1.0, rmse / 453.5)  # 归一化RMSE
            weighted_score = (1 - norm_rmse) * 0.5 + k * 0.5
        
        # 存储结果
        results_dict[params['name']] = {
            'model': model,
            'y_pred': y_pred,
            'mse': mse,
            'rmse': rmse,
            'k': k,
            'weighted_score': weighted_score
        }
        print(f"{params['name']} 评估结果 - RMSE: {rmse:.4f}, K: {k:.4f}, 加权评分: {weighted_score:.4f}")
        logger.info(f"{params['name']} 评估结果 - RMSE: {rmse:.4f}, K: {k:.4f}, 加权评分: {weighted_score:.4f}")
        
        # 检查是否为当前最佳模型（基于加权评分）
        if weighted_score is not None and (best_model is None or weighted_score > results_dict[best_model_name]['weighted_score']):
            best_model = model
            best_model_name = params['name']
            print(f"✅ {params['name']} 成为当前最佳模型 (基于加权评分)")
            logger.info(f"✅ {params['name']} 成为当前最佳模型 (基于加权评分)")
        # 如果没有加权评分，则使用MSE
        elif weighted_score is None and mse < best_mse:
            best_mse = mse
            best_model = model
            best_model_name = params['name']
            print(f"✅ {params['name']} 成为当前最佳模型 (基于MSE)")
            logger.info(f"✅ {params['name']} 成为当前最佳模型 (基于MSE)")
        
        # 保存当前模型
        model_filename = f"{params['name']}.joblib"
        model_filepath = os.path.join(save_path, model_filename)
        joblib.dump(model, model_filepath)
        print(f"{params['name']} 模型已保存到 {model_filepath}")
        logger.info(f"{params['name']} 模型已保存到 {model_filepath}")
    
    # 保存 scaler
    scaler_filename = 'scaler.joblib'
    scaler_filepath = os.path.join(save_path, scaler_filename)
    joblib.dump(scaler, scaler_filepath)
    print(f"Scaler 已保存到 {scaler_filepath}")
    logger.info(f"Scaler 已保存到 {scaler_filepath}")
    
    # 如果找到最佳模型，则额外保存为 'model.joblib'
    if best_model is not None:
        best_model_filepath = os.path.join(save_path, 'model.joblib')
        joblib.dump(best_model, best_model_filepath)
        print(f"最佳模型 '{best_model_name}' 已额外保存到 {best_model_filepath}")
        logger.info(f"最佳模型 '{best_model_name}' 已额外保存到 {best_model_filepath}")
    else:
        print("未找到最佳模型。")
        logger.info("未找到最佳模型。")
    
    return results_dict

def split_data(X, y, train_ratio):
    """
    按顺序拆分训练集和验证集
    """
    split_index = int(len(X) * train_ratio)
    X_train, X_val = X[:split_index], X[split_index:]
    y_train, y_val = y[:split_index], y[split_index:]
    return X_train, X_val, y_train, y_val

def train_multiple_datasets(data, months_list, train_ratio, lags, window_size, model_folder_today):
    """
    使用不同时间段的数据训练多个模型，并选择最佳模型
    
    参数:
    data: 原始数据
    months_list: 要使用的月份列表 [1, 3, 6, 9, 12, None]
    train_ratio: 训练集比例
    lags: 滞后特征数量
    window_size: 窗口大小
    model_folder_today: 模型保存路径
    
    返回:
    最佳模型信息的字典
    """
    print_separator("使用多个数据集训练模型")
    # 创建存储最佳模型的目录
    best_models_dir = os.path.join(model_folder_today, 'best_models')
    os.makedirs(best_models_dir, exist_ok=True)
    print(f"最佳模型将保存到: {best_models_dir}")
    logger.info(f"最佳模型将保存到: {best_models_dir}")
    
    # 获取统一参数
    all_params = get_unified_params()
    print(f"获取统一参数成功，包含 {len(all_params)} 种模型类型")
    logger.info(f"获取统一参数成功，包含 {len(all_params)} 种模型类型")
    
    # 为每种算法类型存储最佳模型
    best_models = {
        'GBDT': {'model': None, 'score': -float('inf'), 'months': None, 'scaler': None},
        'DART': {'model': None, 'score': -float('inf'), 'months': None, 'scaler': None},
        'GOSS': {'model': None, 'score': -float('inf'), 'months': None, 'scaler': None},
    }
    
    # 存储所有训练结果
    all_results = {}
    
    # 1. 对每个时间段分别训练
    for months in months_list:
        print_separator(f"训练数据集: {months}个月" if months else "训练数据集: 全部数据")
        months_desc = f"{months}个月" if months else "全部数据"
        print(f"使用{months_desc}的数据进行训练...")
        logger.info(f"使用{months_desc}的数据进行训练...")
        
        # 过滤数据
        print(f"过滤数据为最近{months_desc}..." if months else "使用全部数据...")
        logger.info(f"过滤数据为最近{months_desc}..." if months else "使用全部数据...")
        filtered_data = filter_data_by_date(data, months)
        print(f"过滤后的数据量: {len(filtered_data)}")
        logger.info(f"过滤后的数据量: {len(filtered_data)}")
        
        # 预处理数据
        print(f"对{months_desc}数据进行预处理...")
        logger.info(f"对{months_desc}数据进行预处理...")
        X, y = preprocess_data(filtered_data)
        print(f"预处理后的特征维度: {X.shape}, 目标变量维度: {y.shape}")
        logger.info(f"预处理后的特征维度: {X.shape}, 目标变量维度: {y.shape}")
        
        X_train, X_val, y_train, y_val = split_data(X, y, train_ratio)
        print(f"数据集划分完成，训练集: {X_train.shape}, 验证集: {X_val.shape}")
        logger.info(f"数据集划分完成，训练集: {X_train.shape}, 验证集: {X_val.shape}")
        
        # 提取验证集的时间戳，用于时间加权评估
        val_timestamps = None
        if 'Timestamp' in filtered_data.columns:
            val_timestamps = filtered_data['Timestamp'].iloc[int(len(filtered_data) * train_ratio):].values
            print(f"提取了 {len(val_timestamps)} 个验证集时间戳，用于时间加权评估")
            logger.info(f"提取了 {len(val_timestamps)} 个验证集时间戳，用于时间加权评估")
        else:
            print("无法获取时间戳，将使用简单加权评估")
            logger.info("无法获取时间戳，将使用简单加权评估")
        
        # 特征工程
        print(f"执行特征工程，滞后特征数: {lags}...")
        logger.info(f"执行特征工程，滞后特征数: {lags}...")
        X_train_fe, X_val_fe = feature_engineering(X_train, X_val, lags)
        print(f"特征工程后的特征维度 - 训练集: {X_train_fe.shape}, 验证集: {X_val_fe.shape}")
        logger.info(f"特征工程后的特征维度 - 训练集: {X_train_fe.shape}, 验证集: {X_val_fe.shape}")
        
        # 数据标准化
        print(f"数据标准化...")
        logger.info(f"数据标准化...")
        X_train_scaled, X_val_scaled, scaler = scale_data(X_train_fe, X_val_fe)
        print(f"数据标准化完成")
        logger.info(f"数据标准化完成")
        
        # 创建时间窗口
        print(f"创建时间窗口，窗口大小: {window_size}...")
        logger.info(f"创建时间窗口，窗口大小: {window_size}...")
        X_train_windows, y_train_windows = create_time_window(X_train_scaled, y_train.values, window_size)
        X_val_windows, y_val_windows = create_time_window(X_val_scaled, y_val.values, window_size)
        print(f"时间窗口创建完成 - 训练集: {X_train_windows.shape}, 验证集: {X_val_windows.shape}")
        logger.info(f"时间窗口创建完成 - 训练集: {X_train_windows.shape}, 验证集: {X_val_windows.shape}")
        
        # 调整时间戳长度以匹配窗口化后的验证集长度
        if val_timestamps is not None and len(val_timestamps) != len(y_val_windows):
            print(f"调整时间戳长度以匹配窗口化后的验证集 - 原始长度: {len(val_timestamps)}, 目标长度: {len(y_val_windows)}")
            logger.info(f"调整时间戳长度以匹配窗口化后的验证集 - 原始长度: {len(val_timestamps)}, 目标长度: {len(y_val_windows)}")
            
            if len(val_timestamps) > len(y_val_windows):
                # 如果时间戳太长，就取最后len(y_val_windows)个
                val_timestamps = val_timestamps[-len(y_val_windows):]
                print(f"时间戳已截断至匹配窗口化后的验证集长度: {len(val_timestamps)}")
                logger.info(f"时间戳已截断至匹配窗口化后的验证集长度: {len(val_timestamps)}")
            else:
                # 如果时间戳太短，就设为None，使用替代评分方法
                print(f"时间戳长度不足，将使用非时间加权评分")
                logger.info(f"时间戳长度不足，将使用非时间加权评分") 
                val_timestamps = None
        
        # 创建子目录
        months_dir = os.path.join(model_folder_today, f"{months}months" if months else "all_data")
        os.makedirs(months_dir, exist_ok=True)
        print(f"为{months_desc}数据创建模型目录: {months_dir}")
        logger.info(f"为{months_desc}数据创建模型目录: {months_dir}")
        
        # 训练模型
        print(f"开始训练{months_desc}数据的模型...")
        logger.info(f"开始训练{months_desc}数据的模型...")
        results = train_and_evaluate(
            X_train_windows, y_train_windows,
            X_val_windows, y_val_windows,
            all_params, scaler, months_dir, val_timestamps
        )
        print(f"{months_desc}数据的模型训练完成")
        logger.info(f"{months_desc}数据的模型训练完成")
        
        # 存储结果
        all_results[months] = results
        
        # 更新每种算法类型的最佳模型
        print_separator(f"更新每种算法的最佳模型")
        for algo_type in ['GBDT', 'DART', 'GOSS']:
            if algo_type in results:
                current_score = results[algo_type]['weighted_score']
                if current_score > best_models[algo_type]['score']:
                    print(f"✅ 发现更好的{algo_type}模型 (来自{months_desc}数据)")
                    print(f"   新评分: {current_score:.4f}, 旧评分: {best_models[algo_type]['score']:.4f}")
                    logger.info(f"✅ 发现更好的{algo_type}模型 (来自{months_desc}数据)")
                    logger.info(f"   新评分: {current_score:.4f}, 旧评分: {best_models[algo_type]['score']:.4f}")
                    best_models[algo_type] = {
                        'model': results[algo_type]['model'],
                        'score': current_score,
                        'months': months,
                        'scaler': scaler,
                        'rmse': results[algo_type]['rmse'],
                        'k': results[algo_type]['k']
                    }
                else:
                    print(f"❌ {months_desc}数据的{algo_type}模型不是最佳模型")
                    print(f"   当前评分: {current_score:.4f}, 最佳评分: {best_models[algo_type]['score']:.4f}")
                    logger.info(f"❌ {months_desc}数据的{algo_type}模型不是最佳模型")
                    logger.info(f"   当前评分: {current_score:.4f}, 最佳评分: {best_models[algo_type]['score']:.4f}")
    
    # 2. 保存每种算法类型的最佳模型
    print_separator("保存每种算法的最佳模型")
    for algo_type, model_info in best_models.items():
        if model_info['model'] is not None:
            # 保存模型
            model_path = os.path.join(best_models_dir, f"{algo_type}.joblib")
            joblib.dump(model_info['model'], model_path)
            
            # 保存scaler
            scaler_path = os.path.join(best_models_dir, f"{algo_type}_scaler.joblib")
            joblib.dump(model_info['scaler'], scaler_path)
            
            months_desc = f"{model_info['months']}个月" if model_info['months'] else "全部数据"
            print(f"最佳{algo_type}模型 (使用{months_desc}数据) 已保存到 {model_path}")
            print(f"RMSE: {model_info['rmse']:.4f}, K: {model_info['k']:.4f}, 评分: {model_info['score']:.4f}")
            logger.info(f"最佳{algo_type}模型 (使用{months_desc}数据) 已保存到 {model_path}")
            logger.info(f"RMSE: {model_info['rmse']:.4f}, K: {model_info['k']:.4f}, 评分: {model_info['score']:.4f}")
    
    # 创建一个包含最佳模型信息的字典
    best_models_info = {
        'models': best_models,
        'best_models_dir': best_models_dir
    }
    
    return best_models_info

def calculate_model_weights(best_models_info, validation_data, lags, window_size):
    """
    根据过去三天的预测结果计算最佳模型权重
    
    参数:
    best_models_info: 包含最佳模型的字典
    validation_data: 用于验证的数据 (过去三天)
    lags: 滞后特征数量
    window_size: 窗口大小
    
    返回:
    模型权重字典 {'GBDT': weight, 'DART': weight, 'GOSS': weight}
    """
    print_separator("计算模型权重")
    from sklearn.linear_model import LinearRegression
    
    # 默认权重
    default_weights = {'GBDT': 0.45, 'DART': 0.1, 'GOSS': 0.45}
    
    # 如果没有足够的验证数据，返回默认权重
    if validation_data is None or len(validation_data) < 24:  # 至少需要一天的数据
        print("❌ 验证数据不足，使用默认权重")
        logger.info("❌ 验证数据不足，使用默认权重")
        return default_weights
    
    try:
        # 获取模型和scaler
        models = {}
        scalers = {}
        print("加载最佳模型和对应的scaler...")
        logger.info("加载最佳模型和对应的scaler...")
        for algo_type in ['GBDT', 'DART', 'GOSS']:
            if algo_type in best_models_info['models'] and best_models_info['models'][algo_type]['model'] is not None:
                models[algo_type] = best_models_info['models'][algo_type]['model']
                scalers[algo_type] = best_models_info['models'][algo_type]['scaler']
                print(f"✅ 已加载 {algo_type} 模型和scaler")
                logger.info(f"✅ 已加载 {algo_type} 模型和scaler")
            else:
                print(f"❌ 未找到 {algo_type} 模型")
                logger.info(f"❌ 未找到 {algo_type} 模型")
        
        # 如果没有足够的模型，返回默认权重
        if len(models) < 2:
            print("❌ 有效模型不足（少于2个），使用默认权重")
            logger.info("❌ 有效模型不足（少于2个），使用默认权重")
            return default_weights
        
        # 预处理验证数据
        print(f"预处理验证数据，共 {len(validation_data)} 条记录...")
        logger.info(f"预处理验证数据，共 {len(validation_data)} 条记录...")
        X, y = preprocess_data(validation_data)
        print(f"验证数据预处理完成，特征维度: {X.shape}")
        logger.info(f"验证数据预处理完成，特征维度: {X.shape}")
        
        X_fe, _ = feature_engineering(X, X, lags)  # 只需要X_fe
        print(f"验证数据特征工程完成，特征维度: {X_fe.shape}")
        logger.info(f"验证数据特征工程完成，特征维度: {X_fe.shape}")
        
        # 创建预测结果矩阵
        predictions = {}
        print("使用各模型进行预测...")
        logger.info("使用各模型进行预测...")
        for algo_type, model in models.items():
            # 使用对应的scaler
            X_scaled = scalers[algo_type].transform(X_fe)
            X_windows = create_time_window_pre(X_scaled, window_size)
            print(f"使用 {algo_type} 模型预测...")
            logger.info(f"使用 {algo_type} 模型预测...")
            predictions[algo_type] = model.predict(X_windows.reshape(X_windows.shape[0], -1))
            print(f"✅ {algo_type} 模型预测完成，预测结果数量: {len(predictions[algo_type])}")
            logger.info(f"✅ {algo_type} 模型预测完成，预测结果数量: {len(predictions[algo_type])}")
        
        # 确保所有预测结果长度一致
        min_length = min(len(pred) for pred in predictions.values())
        y_true = y.values[-min_length:]
        print(f"对齐预测结果，使用最小长度: {min_length}")
        logger.info(f"对齐预测结果，使用最小长度: {min_length}")
        
        if len(y_true) != min_length:
            print(f"⚠️ 实际值长度 ({len(y_true)}) 与最小预测长度 ({min_length}) 不匹配，进行调整...")
            logger.info(f"⚠️ 实际值长度 ({len(y_true)}) 与最小预测长度 ({min_length}) 不匹配，进行调整...")
            if len(y_true) > min_length:
                y_true = y_true[-min_length:]
            else:
                # 如果实际值长度不足，截断预测值
                min_length = len(y_true)
                for algo_type in predictions:
                    predictions[algo_type] = predictions[algo_type][-min_length:]
                print(f"预测值已截断至匹配实际值长度: {min_length}")
                logger.info(f"预测值已截断至匹配实际值长度: {min_length}")
        
        # 创建特征矩阵和目标向量
        X_lr = np.column_stack([predictions[algo_type][-min_length:] for algo_type in models.keys()])
        y_lr = y_true
        print(f"创建线性回归的特征矩阵 {X_lr.shape} 和目标向量 {y_lr.shape}")
        logger.info(f"创建线性回归的特征矩阵 {X_lr.shape} 和目标向量 {y_lr.shape}")
        
        # 训练线性回归模型
        print("训练线性回归模型计算最优权重...")
        logger.info("训练线性回归模型计算最优权重...")
        lr = LinearRegression(fit_intercept=True, positive=True)  # 修改为包含偏置项
        lr.fit(X_lr, y_lr)
        
        # 获取权重
        weights = dict(zip(models.keys(), lr.coef_))
        # 添加偏置项到权重字典中
        weights['INTERCEPT'] = lr.intercept_
        print(f"线性回归得到的权重: {weights}")
        logger.info(f"线性回归得到的权重: {weights}")
        
        # 不再进行归一化，保留原始权重
        # 确保所有算法类型都有权重
        for algo_type in ['GBDT', 'DART', 'GOSS']:
            if algo_type not in weights:
                weights[algo_type] = 0.0
                print(f"为缺失的 {algo_type} 模型添加权重: 0.0")
                logger.info(f"为缺失的 {algo_type} 模型添加权重: 0.0")
        
        print(f"最终计算的模型权重: {weights}")
        logger.info(f"最终计算的模型权重: {weights}")
        return weights
        
    except Exception as e:
        print(f"❌ 计算模型权重时出错: {str(e)}")
        print(f"使用默认权重: {default_weights}")
        logger.error(f"❌ 计算模型权重时出错: {str(e)}")
        logger.info(f"使用默认权重: {default_weights}")
        return default_weights

def save_predictions(results_dict, y_val, output_base_dir):
    print_separator("保存预测结果")
    # 获取当前时间戳，用于创建子文件夹
    output_dir = os.path.join(output_base_dir, Today)
    
    # 创建目录结构
    os.makedirs(output_dir, exist_ok=True)
    print(f"预测结果将保存到目录: {output_dir}")
    logger.info(f"预测结果将保存到目录: {output_dir}")
    
    for model_name, result in results_dict.items():
        results = pd.DataFrame({
            'Predicted Power': result['y_pred'],
            'Actual Power': y_val
        })
        csv_filename = f'{model_name}_predicted_vs_actual_power.csv'
        csv_filepath = os.path.join(output_dir, csv_filename)
        results.to_csv(csv_filepath, index=False)
        print(f"预测结果已保存到 {csv_filepath}")
        logger.info(f"预测结果已保存到 {csv_filepath}")