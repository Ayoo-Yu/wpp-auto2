from .data_processor import load_data, preprocess_data, split_data, feature_engineering, scale_data, create_time_window
from .models import get_lightgbm_params
from .train import train_and_evaluate, save_predictions
from .utils import visualize_results
import sys
sys.path.append('./config')
from .config import WINDOW_SIZE, TRAIN_RATIO, LAGS
import os
from datetime import datetime

def train_run(DATA_FILE_PATH, MODEL):
    # 配置
    file_path = DATA_FILE_PATH
    model_name = MODEL
    window_size = WINDOW_SIZE
    lags = LAGS
    
    # 动态生成输出目录，带时间戳
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join('results', current_time)
    os.makedirs(output_dir, exist_ok=True)  # 确保创建目录
    print(f"输出结果将保存到: {output_dir}")
    
    # 数据加载与预处理
    data = load_data(file_path)
    print(f"数据加载完成!")
    X, y = preprocess_data(data)
    print(f"数据预处理完成!")
    X_train, X_val, y_train, y_val = split_data(X, y)
    X_train_fe, X_val_fe = feature_engineering(X_train, X_val, lags)
    print("特征工程完成!")
    # 数据标准化
    X_train_scaled, X_val_scaled, scaler = scale_data(X_train_fe, X_val_fe)
    print("数据标准化完成!")
    # 创建时间窗口
    X_train_windows, y_train_windows = create_time_window(X_train_fe, y_train.values, window_size)
    X_val_windows, y_val_windows = create_time_window(X_val_fe, y_val.values, window_size)
    print("时间窗口创建完成!")
    params = get_lightgbm_params(model=model_name)
    print("模型参数获取完成!")
    print(params)
    # 训练与评估
    results_dict = train_and_evaluate(X_train_windows, y_train_windows, X_val_windows, y_val_windows, params, scaler)
    print("模型训练与评估完成!")
    # 保存预测结果
    forecast_df = save_predictions(results_dict, y_val_windows, output_base_dir=output_dir)
    print("预测结果保存完成!")
    # 可视化结果
    visualize_results(results_dict, y_val_windows, output_path=os.path.join(output_dir, 'power_predictions_comparison.png'))
    print("可视化结果完成!")
    return forecast_df
