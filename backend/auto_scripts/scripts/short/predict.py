import os
import pandas as pd
import numpy as np
import joblib
import logging
import sys
from data_processor import preprocess_data_pre, feature_engineering, create_time_window_pre
from config import LAGS, OUTPUT_DIR_PRE,Today
import requests

# 获取logger
logger = logging.getLogger()

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
    print("\n" + "=" * 60)
    if msg:
        print(f"【{msg}】")
    if msg:
        logger.info(f"\n{'=' * 60}\n【{msg}】\n{'=' * 60}")
    else:
        logger.info(f"\n{'=' * 60}")

def load_models_and_scaler(model_path, scaler_path):
    """
    根据传入的模型路径和 scaler 文件路径加载模型和 scaler
    """
    print_separator("加载模型和标准化器")
    # 加载 scaler
    if not os.path.exists(scaler_path):
        print(f"❌ Scaler 文件未找到: {scaler_path}")
        logger.error(f"Scaler 文件未找到: {scaler_path}")
        raise FileNotFoundError(f"Scaler 文件未找到: {scaler_path}")
    print(f"加载 scaler: {scaler_path}")
    logger.info(f"加载 scaler: {scaler_path}")
    scaler = joblib.load(scaler_path)
    print(f"✅ 已成功加载 scaler")
    logger.info(f"✅ 已成功加载 scaler")
    
    # 加载模型
    print(f"加载模型: {model_path}")
    logger.info(f"加载模型: {model_path}")
    model = joblib.load(model_path)
    print(f"✅ 已成功加载模型")
    logger.info(f"✅ 已成功加载模型")
    return model, scaler

def load_multiple_models(models_dir):
    """
    加载多个模型及其对应的scaler
    
    参数:
    models_dir: 包含多个模型的目录
    
    返回:
    模型和scaler的字典
    """
    print_separator("加载多个模型")
    print(f"从目录加载模型和 scaler: {models_dir}")
    logger.info(f"从目录加载模型和 scaler: {models_dir}")
    models = {}
    scalers = {}
    
    for algo_type in ['GBDT', 'DART', 'GOSS']:
        model_path = os.path.join(models_dir, f"{algo_type}.joblib")
        scaler_path = os.path.join(models_dir, f"{algo_type}_scaler.joblib")
        
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            try:
                print(f"加载 {algo_type} 模型和 scaler...")
                logger.info(f"加载 {algo_type} 模型和 scaler...")
                model = joblib.load(model_path)
                scaler = joblib.load(scaler_path)
                models[algo_type] = model
                scalers[algo_type] = scaler
                print(f"✅ 已成功加载 {algo_type} 模型和对应的 scaler")
                logger.info(f"✅ 已成功加载 {algo_type} 模型和对应的 scaler")
            except Exception as e:
                print(f"❌ 加载 {algo_type} 模型时出错: {str(e)}")
                logger.error(f"❌ 加载 {algo_type} 模型时出错: {str(e)}")
        else:
            missing_files = []
            if not os.path.exists(model_path):
                missing_files.append(f"{algo_type}.joblib")
            if not os.path.exists(scaler_path):
                missing_files.append(f"{algo_type}_scaler.joblib")
            print(f"❌ 未找到 {algo_type} 模型或 scaler 文件: {', '.join(missing_files)}")
            logger.info(f"❌ 未找到 {algo_type} 模型或 scaler 文件: {', '.join(missing_files)}")
    
    print(f"加载完成，共加载了 {len(models)} 个模型: {', '.join(models.keys())}")
    logger.info(f"加载完成，共加载了 {len(models)} 个模型: {', '.join(models.keys())}")
    return models, scalers

def preprocess_new_data(file_path, lags):
    """
    对新数据进行预处理，包括特征工程和标准化
    """
    print_separator("预处理新数据")
    # 加载数据
    print(f"加载数据文件: {file_path}")
    logger.info(f"加载数据文件: {file_path}")
    data = pd.read_csv(file_path)
    data = data.dropna()
    print(f"数据加载完成，去除缺失值后共 {len(data)} 条记录")
    logger.info(f"数据加载完成，去除缺失值后共 {len(data)} 条记录")
    print(f"数据前5行预览:\n{data.head()}")
    logger.info(f"数据前5行预览:\n{data.head()}")
    
    # 预处理
    print(f"预处理数据...")
    logger.info(f"预处理数据...")
    X, timestamp = preprocess_data_pre(data)  # 不需要 y
    print(f"预处理完成，特征维度: {X.shape}")
    logger.info(f"预处理完成，特征维度: {X.shape}")
    
    # 特征工程
    print(f"执行特征工程，滞后特征数: {lags}...")
    logger.info(f"执行特征工程，滞后特征数: {lags}...")
    X_fe, _ = feature_engineering(X, X, lags)  # 对新数据，验证集可以忽略
    print(f"特征工程完成，特征维度: {X_fe.shape}")
    logger.info(f"特征工程完成，特征维度: {X_fe.shape}")
    
    return X_fe, timestamp

def make_predictions(model, scaler, X_new, window_size, LAGS):
    """
    对新数据进行预测
    """
    print_separator("使用单一模型进行预测")
    # 标准化
    print(f"标准化数据...")
    logger.info(f"标准化数据...")
    X_scaled = scaler.transform(X_new)
    print(f"数据标准化完成，维度: {X_scaled.shape}")
    logger.info(f"数据标准化完成，维度: {X_scaled.shape}")
    
    # 创建时间窗口
    print(f"创建时间窗口，窗口大小: {window_size}...")
    logger.info(f"创建时间窗口，窗口大小: {window_size}...")
    X_windows = create_time_window_pre(X_scaled, window_size)  # y 无关紧要
    print(f"时间窗口创建完成，窗口数量: {X_windows.shape[0]}")
    logger.info(f"时间窗口创建完成，窗口数量: {X_windows.shape[0]}")
    
    # 预测
    print(f"开始预测...")
    logger.info(f"开始预测...")
    preds = model.predict(X_windows.reshape(X_windows.shape[0], -1))
    print(f"预测完成，共生成 {len(preds)} 个预测值")
    logger.info(f"预测完成，共生成 {len(preds)} 个预测值")
    print(f"预测结果统计: 最小值={preds.min():.2f}, 最大值={preds.max():.2f}, 平均值={preds.mean():.2f}")
    logger.info(f"预测结果统计: 最小值={preds.min():.2f}, 最大值={preds.max():.2f}, 平均值={preds.mean():.2f}")
    return preds

def make_weighted_predictions(models, scalers, X_new, window_size, LAGS, weights=None):
    """
    使用多个模型进行加权预测
    
    参数:
    models: 模型字典 {'GBDT': model, 'DART': model, 'GOSS': model}
    scalers: 对应的scaler字典
    X_new: 新数据
    window_size: 窗口大小
    LAGS: 滞后特征数量
    weights: 权重字典 {'GBDT': weight, 'DART': weight, 'GOSS': weight}
    
    返回:
    加权预测结果
    """
    print_separator("使用多模型加权预测")
    if not models:
        print("❌ 没有可用模型进行预测")
        logger.error("❌ 没有可用模型进行预测")
        raise ValueError("没有可用模型进行预测")
    
    # 默认权重
    if weights is None:
        weights = {'GBDT': 0.45, 'DART': 0.1, 'GOSS': 0.45}
        print(f"使用默认权重: {weights}")
        logger.info(f"使用默认权重: {weights}")
    else:
        print(f"使用自定义权重: {weights}")
        logger.info(f"使用自定义权重: {weights}")
    
    all_predictions = {}
    
    # 使用每个模型进行预测
    for algo_type, model in models.items():
        if algo_type in scalers and algo_type in weights and weights[algo_type] > 0:
            try:
                print(f"使用 {algo_type} 模型进行预测 (权重: {weights[algo_type]:.4f})...")
                logger.info(f"使用 {algo_type} 模型进行预测 (权重: {weights[algo_type]:.4f})...")
                # 标准化
                X_scaled = scalers[algo_type].transform(X_new)
                print(f"{algo_type}: 数据标准化完成")
                logger.info(f"{algo_type}: 数据标准化完成")
                
                # 创建时间窗口
                X_windows = create_time_window_pre(X_scaled, window_size)
                print(f"{algo_type}: 时间窗口创建完成，窗口数量: {X_windows.shape[0]}")
                logger.info(f"{algo_type}: 时间窗口创建完成，窗口数量: {X_windows.shape[0]}")
                
                # 预测
                preds = model.predict(X_windows.reshape(X_windows.shape[0], -1))
                all_predictions[algo_type] = preds
                print(f"✅ {algo_type} 模型预测完成，生成了 {len(preds)} 个预测值")
                logger.info(f"✅ {algo_type} 模型预测完成，生成了 {len(preds)} 个预测值")
                print(f"   统计: 最小值={preds.min():.2f}, 最大值={preds.max():.2f}, 平均值={preds.mean():.2f}")
                logger.info(f"   统计: 最小值={preds.min():.2f}, 最大值={preds.max():.2f}, 平均值={preds.mean():.2f}")
            except Exception as e:
                print(f"❌ {algo_type} 模型预测出错: {str(e)}")
                logger.error(f"❌ {algo_type} 模型预测出错: {str(e)}")
        else:
            if algo_type not in scalers:
                print(f"❌ {algo_type} 模型没有对应的scaler")
                logger.info(f"❌ {algo_type} 模型没有对应的scaler")
            elif algo_type not in weights:
                print(f"❌ {algo_type} 模型在权重字典中不存在")
                logger.info(f"❌ {algo_type} 模型在权重字典中不存在")
            elif weights[algo_type] <= 0:
                print(f"❌ {algo_type} 模型权重为0，跳过")
                logger.info(f"❌ {algo_type} 模型权重为0，跳过")
    
    if not all_predictions:
        print("❌ 所有模型预测均失败")
        logger.error("❌ 所有模型预测均失败")
        raise ValueError("所有模型预测均失败")
    
    # 确保所有预测结果长度一致
    min_length = min(len(preds) for preds in all_predictions.values())
    print(f"所有预测结果对齐到最小长度: {min_length}")
    logger.info(f"所有预测结果对齐到最小长度: {min_length}")
    
    # 加权求和
    print(f"开始计算加权平均预测结果...")
    logger.info(f"开始计算加权平均预测结果...")
    # 初始化为偏置项（如果存在）
    intercept = weights.get('INTERCEPT', 0)
    weighted_preds = np.ones(min_length) * intercept
    
    for algo_type, preds in all_predictions.items():
        if weights.get(algo_type, 0) > 0:
            weighted_preds += preds[-min_length:] * weights[algo_type]
            print(f"  加入 {algo_type} 模型贡献 (权重: {weights[algo_type]:.4f})")
            logger.info(f"  加入 {algo_type} 模型贡献 (权重: {weights[algo_type]:.4f})")
    
    if 'INTERCEPT' in weights and weights['INTERCEPT'] != 0:
        print(f"  加入常数偏置项 (值: {weights['INTERCEPT']:.4f})")
        logger.info(f"  加入常数偏置项 (值: {weights['INTERCEPT']:.4f})")
    
    print(f"加权平均预测完成，生成了 {len(weighted_preds)} 个预测值")
    logger.info(f"加权平均预测完成，生成了 {len(weighted_preds)} 个预测值")
    print(f"加权预测结果统计: 最小值={weighted_preds.min():.2f}, 最大值={weighted_preds.max():.2f}, 平均值={weighted_preds.mean():.2f}")
    logger.info(f"加权预测结果统计: 最小值={weighted_preds.min():.2f}, 最大值={weighted_preds.max():.2f}, 平均值={weighted_preds.mean():.2f}")
    return weighted_preds

def save_predictions_to_csv(predictions, timestamp):
    """
    保存预测结果到 CSV 文件
    """
    print_separator("保存预测结果")
    today = Today
    output_dir = os.path.join(OUTPUT_DIR_PRE, today)
    os.makedirs(output_dir, exist_ok=True)
    print(f"创建输出目录: {output_dir}")
    logger.info(f"创建输出目录: {output_dir}")
    
    # 创建预测结果数据框
    df = pd.DataFrame({
        'Timestamp': timestamp[len(timestamp)-len(predictions):],
        'Predicted Power': predictions
    })
    print(f"预测结果数据框创建完成，共 {len(df)} 行")
    logger.info(f"预测结果数据框创建完成，共 {len(df)} 行")
    
    # 保存为CSV
    csv_filepath = os.path.join(output_dir, f'{today}.csv')
    df.to_csv(csv_filepath, index=False)
    print(f"✅ 预测结果已保存到文件: {csv_filepath}")
    logger.info(f"✅ 预测结果已保存到文件: {csv_filepath}")
    
    # 尝试将结果导入数据库
    try:
        print(f"尝试将预测结果导入数据库...")
        logger.info(f"尝试将预测结果导入数据库...")
        url = 'http://localhost:5000/prediction2database/batch_shortl_power'
        files = {'file': open(csv_filepath, 'rb')}
        print(f"发送HTTP请求到: {url}")
        logger.info(f"发送HTTP请求到: {url}")
        response = requests.post(url, files=files)
        
        if response.status_code == 201:
            try:
                result = response.json()
                print(f"✅ 数据已成功导入数据库")
                print(f"   总记录数: {result['total']}, 更新: {result['updated']}, 插入: {result['inserted']}")
                logger.info(f"✅ 数据已成功导入数据库")
                logger.info(f"   总记录数: {result['total']}, 更新: {result['updated']}, 插入: {result['inserted']}")
            except Exception as e:
                print(f"✅ 数据已成功导入数据库，但解析响应失败: {str(e)}")
                logger.info(f"✅ 数据已成功导入数据库，但解析响应失败: {str(e)}")
        else:
            try:
                error_msg = response.json().get('error', f"HTTP错误: {response.status_code}")
                print(f"❌ 数据导入失败: {error_msg}")
                logger.error(f"❌ 数据导入失败: {error_msg}")
            except Exception as json_err:
                print(f"❌ 数据导入失败: HTTP错误 {response.status_code}, 响应解析失败: {str(json_err)}")
                print(f"   响应内容: {response.text}")
                logger.error(f"❌ 数据导入失败: HTTP错误 {response.status_code}, 响应解析失败: {str(json_err)}")
                logger.error(f"   响应内容: {response.text}")
    except Exception as e:
        print(f"❌ 调用数据库接口失败: {str(e)}")
        logger.error(f"❌ 调用数据库接口失败: {str(e)}")
        
        # 如果调用失败，尝试重新传输一次
        try:
            print("尝试重新传输数据...")
            logger.info("尝试重新传输数据...")
            # 确保文件句柄已关闭后重新打开
            files = {'file': open(csv_filepath, 'rb')}
            response = requests.post(url, files=files)
            files['file'].close()
            
            if response.status_code == 201:
                print(f"✅ 重试后成功导入数据库")
                logger.info(f"✅ 重试后成功导入数据库")
            else:
                print(f"❌ 重试后仍然失败: HTTP错误 {response.status_code}")
                logger.error(f"❌ 重试后仍然失败: HTTP错误 {response.status_code}")
        except Exception as retry_err:
            print(f"❌ 重试导入数据库失败: {str(retry_err)}")
            logger.error(f"❌ 重试导入数据库失败: {str(retry_err)}")
    
    return csv_filepath

def predict(CSV_FILE_PATH, MODEL_Folder, WINDOW_SIZE=16):
    """
    主预测函数，接收数据文件路径、模型文件路径和 scaler 文件路径
    """
    print_separator("风电功率预测开始")
    # 配置
    new_data_file_path = CSV_FILE_PATH
    window_size = WINDOW_SIZE
    print(f"配置信息:")
    print(f"  - 数据文件: {new_data_file_path}")
    print(f"  - 模型目录: {MODEL_Folder}")
    print(f"  - 窗口大小: {window_size}")
    print(f"  - 滞后特征数: {LAGS}")
    logger.info(f"配置信息:")
    logger.info(f"  - 数据文件: {new_data_file_path}")
    logger.info(f"  - 模型目录: {MODEL_Folder}")
    logger.info(f"  - 窗口大小: {window_size}")
    logger.info(f"  - 滞后特征数: {LAGS}")
    
    # 检查是否有最佳模型目录
    best_models_dir = os.path.join(MODEL_Folder, 'best_models')
    
    # 预处理新数据
    X_new, timestamp = preprocess_new_data(new_data_file_path, LAGS)
    print(f"新数据预处理完成，共 {len(X_new)} 个样本")
    logger.info(f"新数据预处理完成，共 {len(X_new)} 个样本")
    
    # 检查是否使用多模型加权预测
    if os.path.exists(best_models_dir):
        print(f"✅ 发现最佳模型目录: {best_models_dir}，尝试使用多模型加权预测")
        logger.info(f"✅ 发现最佳模型目录: {best_models_dir}，尝试使用多模型加权预测")
        try:
            # 加载多个模型
            models, scalers = load_multiple_models(best_models_dir)
            
            if not models:
                print("❌ 未找到可用的模型，将回退到单一模型预测")
                logger.warning("❌ 未找到可用的模型，将回退到单一模型预测")
                raise ValueError("没有找到可用的模型")
            
            # 使用权重文件（如果存在）
            weights_file = os.path.join(MODEL_Folder, 'model_weights.joblib')
            weights = None
            if os.path.exists(weights_file):
                try:
                    print(f"尝试加载模型权重文件: {weights_file}")
                    logger.info(f"尝试加载模型权重文件: {weights_file}")
                    weights = joblib.load(weights_file)
                    print(f"✅ 已加载模型权重: {weights}")
                    logger.info(f"✅ 已加载模型权重: {weights}")
                except Exception as e:
                    print(f"❌ 加载权重文件出错，使用默认权重: {str(e)}")
                    logger.error(f"❌ 加载权重文件出错，使用默认权重: {str(e)}")
            else:
                print(f"未找到权重文件，使用默认权重")
                logger.info(f"未找到权重文件，使用默认权重")
            
            # 加权预测
            predictions = make_weighted_predictions(models, scalers, X_new, window_size, LAGS, weights)
            print(f"✅ 多模型加权预测完成，使用模型: {', '.join(models.keys())}")
            logger.info(f"✅ 多模型加权预测完成，使用模型: {', '.join(models.keys())}")
        except Exception as e:
            print_separator("多模型预测失败")
            logger.error("多模型预测失败")
            print(f"❌ 错误信息: {str(e)}")
            logger.error(f"❌ 错误信息: {str(e)}")
            print(f"回退到单一模型预测...")
            logger.info(f"回退到单一模型预测...")
            # 回退到单一模型
            model_path = os.path.join(MODEL_Folder, 'model.joblib')
            scaler_path = os.path.join(MODEL_Folder, 'scaler.joblib')
            model, scaler = load_models_and_scaler(model_path, scaler_path)
            predictions = make_predictions(model, scaler, X_new, window_size, LAGS)
    else:
        # 使用单一模型
        print(f"未发现最佳模型目录，使用单一模型预测")
        logger.info(f"未发现最佳模型目录，使用单一模型预测")
        model_path = os.path.join(MODEL_Folder, 'model.joblib')
        scaler_path = os.path.join(MODEL_Folder, 'scaler.joblib')
        model, scaler = load_models_and_scaler(model_path, scaler_path)
        predictions = make_predictions(model, scaler, X_new, window_size, LAGS)
        print("✅ 单一模型预测完成")
        logger.info("✅ 单一模型预测完成")
    
    # 保存预测结果
    csv_file = save_predictions_to_csv(predictions, timestamp)
    print(f"✅ 预测结果已保存到: {csv_file}")
    logger.info(f"✅ 预测结果已保存到: {csv_file}")
    
    print_separator("风电功率预测完成")
    logger.info("风电功率预测完成")
