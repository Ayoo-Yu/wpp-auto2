# train.py
from sklearn.metrics import mean_squared_error
import lightgbm as lgb
import pandas as pd
import os
from datetime import datetime
import joblib  # 用于保存模型和 scaler

def train_and_evaluate(X_train, y_train, X_val, y_val, params, scaler, models_dir='models'):
    """
    训练并评估每种模型，并将模型和 scaler 保存到本地路径
    """
    results_dict = {}
    
    # 获取当前时间戳，用于创建子文件夹
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_path = os.path.join(models_dir, current_time)
    
    # 创建目录结构
    os.makedirs(save_path, exist_ok=True)
    print(f"模型和 scaler 将被保存到目录: {save_path}")
    
    model = lgb.LGBMRegressor(**params)
    print(f"开始训练 {params['name']} 模型...")
    model.fit(X_train.reshape(X_train.shape[0], -1), y_train)
    y_pred = model.predict(X_val.reshape(X_val.shape[0], -1))
    mse = mean_squared_error(y_val, y_pred)
    
    results_dict[params['name']] = {
        'model': model,
        'y_pred': y_pred,
        'mse': mse
    }
    print(f"{params['name']} 均方误差: {mse}")
    
    # 保存模型
    model_filename = f"{params['name']}.joblib"
    model_filepath = os.path.join(save_path, model_filename)
    joblib.dump(model, model_filepath)
    print(f"{params['name']} 模型已保存到 {model_filepath}")
    
    # 保存 scaler
    scaler_filename = 'scaler.joblib'
    scaler_filepath = os.path.join(save_path, scaler_filename)
    joblib.dump(scaler, scaler_filepath)
    print(f"Scaler 已保存到 {scaler_filepath}")
    
    return results_dict


def save_predictions(results_dict, y_val, output_base_dir='results/'):
    """
    保存预测结果到以时间戳命名的子文件夹中的CSV文件
    """
    
    # 创建目录结构
    os.makedirs(output_base_dir, exist_ok=True)
    print(f"预测结果将保存到目录: {output_base_dir}")
    
    for model_name, result in results_dict.items():
        results = pd.DataFrame({
            'Predicted Power': result['y_pred'],
            'Actual Power': y_val
        })
        csv_filename = f'{model_name}_predicted_vs_actual_power.csv'
        csv_filepath = os.path.join(output_base_dir, csv_filename)
        results.to_csv(csv_filepath, index=False)
        print(f"预测结果已保存到 {csv_filepath}")
        print(os.path.abspath(csv_filepath))
    return csv_filepath


