# predict.py

import os
import pandas as pd
import numpy as np
import joblib
from data_processor import preprocess_data, feature_engineering, scale_data, create_time_window
import sys
sys.path.append('./config')
from config import LAGS, OUTPUT_DIR
from train import train_and_evaluate, save_predictions  # 如果不需要，可以移除
from utils import visualize_results  # 从 utils 导入
import matplotlib.pyplot as plt

def load_models_and_scaler(models_dir='models'):
    """
    加载最新保存的模型和 scaler
    """
    # 获取 models_dir 下最新的子文件夹
    subdirs = [d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d))]
    if not subdirs:
        raise FileNotFoundError("没有找到任何模型目录。请确保已训练并保存了模型。")
    
    latest_subdir = sorted(subdirs)[-1]  # 假设按时间戳命名，取最新的
    latest_path = os.path.join(models_dir, latest_subdir)
    
    # 加载 scaler
    scaler_path = os.path.join(latest_path, 'scaler.joblib')
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler 文件未找到: {scaler_path}")
    scaler = joblib.load(scaler_path)
    
    # 加载所有模型
    models = {}
    for file in os.listdir(latest_path):
        if file.endswith('.joblib') and file != 'scaler.joblib':
            model_name = file.replace('.joblib', '')
            model_path = os.path.join(latest_path, file)
            models[model_name] = joblib.load(model_path)
    
    print(f"已加载 {len(models)} 个模型和 scaler。")
    return models, scaler, latest_path

def preprocess_new_data(file_path, lags):
    """
    对新数据进行预处理，包括特征工程和标准化
    """
    # 加载数据
    data = pd.read_csv(file_path)
    data = data.dropna()
    
    # 预处理
    X, _ = preprocess_data(data)  # 不需要 y
    
    # 特征工程
    X_fe, _ = feature_engineering(X, X, lags)  # 对新数据，验证集可以忽略
    
    return X_fe

def make_predictions(models, scaler, X_new, window_size):
    """
    对新数据进行预测
    """
    # 标准化
    X_scaled = scaler.transform(X_new)
    
    # 创建时间窗口
    X_windows, _ = create_time_window(X_scaled, np.zeros(X_scaled.shape[0]+3), window_size)  # y 无关紧要
    
    # 预测
    predictions = {}
    for model_name, model in models.items():
        preds = model.predict(X_windows.reshape(X_windows.shape[0], -1))
        predictions[model_name] = preds
        print(f"{model_name} 预测完成，共 {len(preds)} 个预测值。")
    
    return predictions

def save_predictions_to_csv(predictions, output_dir, latest_path):
    """
    保存预测结果到 CSV 文件
    """
    os.makedirs(output_dir, exist_ok=True)
    for model_name, preds in predictions.items():
        df = pd.DataFrame({
            'Predicted Power': preds
        })
        csv_filename = f'{model_name}_new_data_predictions.csv'
        csv_filepath = os.path.join(output_dir, csv_filename)
        df.to_csv(csv_filepath, index=False)
        print(f"{model_name} 的预测结果已保存到 {csv_filepath}")
    

def main():
    """
    主函数
    """
    # 配置
    new_data_file_path = input("请输入新数据的文件路径（CSV 格式）: ").strip()
    window_size = int(input("请输入时间窗口大小（如 16）: ").strip())
    models_dir = 'models'  # 默认模型保存目录
    output_dir = OUTPUT_DIR
    
    # 加载模型和 scaler
    try:
        models, scaler, latest_path = load_models_and_scaler(models_dir)
    except FileNotFoundError as e:
        print(e)
        return
    
    # 预处理新数据
    X_new = preprocess_new_data(new_data_file_path, LAGS)
    
    # 预测
    predictions = make_predictions(models, scaler, X_new, window_size)
    
    # 保存预测结果
    save_predictions_to_csv(predictions, output_dir, latest_path)
    
    print("新数据的预测过程完成。")

if __name__ == "__main__":
    main()
