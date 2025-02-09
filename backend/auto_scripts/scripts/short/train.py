# train.py
from sklearn.metrics import mean_squared_error
import lightgbm as lgb
import pandas as pd
import os
import joblib  # 用于保存模型和 scaler
from config import Today

def train_and_evaluate(X_train, y_train, X_val, y_val, params_list, scaler, model_folder_today):
    results_dict = {}
    save_path = model_folder_today
    
    # 创建目录结构
    os.makedirs(save_path, exist_ok=True)
    print(f"模型和 scaler 将被保存到目录: {save_path}")
    
    # 初始化变量以跟踪最佳模型
    best_mse = float('inf')
    best_model = None
    best_model_name = ""
    
    for params in params_list:
        # 初始化模型
        model = lgb.LGBMRegressor(**params)
        
        # 训练模型
        model.fit(X_train.reshape(X_train.shape[0], -1), y_train)
        
        # 预测验证集
        y_pred = model.predict(X_val.reshape(X_val.shape[0], -1))
        
        # 计算 MSE
        mse = mean_squared_error(y_val, y_pred)
        
        # 存储结果
        results_dict[params['name']] = {
            'model': model,
            'y_pred': y_pred,
            'mse': mse
        }
        print(f"{params['name']} 均方误差 (MSE): {mse}")
        
        # 检查是否为当前最佳模型
        if mse < best_mse:
            best_mse = mse
            best_model = model
            best_model_name = params['name']
        
        # 保存当前模型
        model_filename = f"{params['name']}.joblib"
        model_filepath = os.path.join(save_path, model_filename)
        joblib.dump(model, model_filepath)
        print(f"{params['name']} 模型已保存到 {model_filepath}")
    
    # 保存 scaler
    scaler_filename = 'scaler.joblib'
    scaler_filepath = os.path.join(save_path, scaler_filename)
    joblib.dump(scaler, scaler_filepath)
    print(f"Scaler 已保存到 {scaler_filepath}")
    
    # 如果找到最佳模型，则额外保存为 'model.joblib'
    if best_model is not None:
        best_model_filepath = os.path.join(save_path, 'model.joblib')
        joblib.dump(best_model, best_model_filepath)
        print(f"最佳模型 '{best_model_name}' 已额外保存到 {best_model_filepath}")
    else:
        print("未找到最佳模型。")
    
    return results_dict

def save_predictions(results_dict, y_val, output_base_dir):
    # 获取当前时间戳，用于创建子文件夹
    output_dir = os.path.join(output_base_dir, Today)
    
    # 创建目录结构
    os.makedirs(output_dir, exist_ok=True)
    print(f"预测结果将保存到目录: {output_dir}")
    
    for model_name, result in results_dict.items():
        results = pd.DataFrame({
            'Predicted Power': result['y_pred'],
            'Actual Power': y_val
        })
        csv_filename = f'{model_name}_predicted_vs_actual_power.csv'
        csv_filepath = os.path.join(output_dir, csv_filename)
        results.to_csv(csv_filepath, index=False)
        print(f"预测结果已保存到 {csv_filepath}")