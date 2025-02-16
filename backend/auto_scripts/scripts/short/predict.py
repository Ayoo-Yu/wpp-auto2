import os
import pandas as pd
import joblib
from data_processor import preprocess_data_pre, feature_engineering, create_time_window_pre
from config import LAGS, OUTPUT_DIR_PRE,Today
import requests

flag_file = os.path.join(OUTPUT_DIR_PRE, Today,f'{Today}_predict_done.flag')
def load_models_and_scaler(model_path, scaler_path):
    """
    根据传入的模型路径和 scaler 文件路径加载模型和 scaler
    """
    # 加载 scaler
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(f"Scaler 文件未找到: {scaler_path}")
    scaler = joblib.load(scaler_path)
    print(f"已加载 scaler。")
    # 加载模型
    model = joblib.load(model_path)
    print(f"已加载模型。")
    return model, scaler

def preprocess_new_data(file_path, lags):
    """
    对新数据进行预处理，包括特征工程和标准化
    """
    # 加载数据
    data = pd.read_csv(file_path)
    data = data.dropna()
    
    # 预处理
    X,timestamp= preprocess_data_pre(data)  # 不需要 y
    
    # 特征工程
    X_fe, _ = feature_engineering(X, X, lags)  # 对新数据，验证集可以忽略
    
    return X_fe,timestamp

def make_predictions(model, scaler, X_new, window_size,LAGS):
    """
    对新数据进行预测
    """
    # 标准化
    X_scaled = scaler.transform(X_new)
    print(f"已对新数据进行标准化。")
    # 创建时间窗口
    X_windows = create_time_window_pre(X_scaled, window_size)  # y 无关紧要
    print(f"已创建时间窗口。")
    # 预测
    preds = model.predict(X_windows.reshape(X_windows.shape[0], -1))
    return preds

def save_predictions_to_csv(predictions,timestamp):
    """
    保存预测结果到 CSV 文件
    """
    today = Today
    output_dir = os.path.join(OUTPUT_DIR_PRE,today)
    os.makedirs(output_dir, exist_ok=True)
    df = pd.DataFrame({
        'Timestamp':timestamp[len(timestamp)-len(predictions):],
        'Predicted Power': predictions
    })
    csv_filepath = os.path.join(output_dir,f'{today}.csv')
    df.to_csv(csv_filepath, index=False)
    print(f"预测结果已保存到 {csv_filepath}")
    try:
        url = 'http://localhost:5000/prediction2database/batch_shortl_power'
        files = {'file': open(csv_filepath, 'rb')}
        response = requests.post(url, files=files)
        
        if response.status_code == 201:
            print("数据已成功导入数据库")
            result = response.json()
            print(f"总记录数: {result['total']}, 更新: {result['updated']}, 插入: {result['inserted']}")
        else:
            print(f"数据导入失败: {response.json()['error']}")
    except Exception as e:
        print(f"调用接口失败: {str(e)}")
    
    return csv_filepath
    
def predict(CSV_FILE_PATH, MODEL_Folder, WINDOW_SIZE=16):
    """
    主预测函数，接收数据文件路径、模型文件路径和 scaler 文件路径
    """
    # 配置
    new_data_file_path = CSV_FILE_PATH
    MODEL_PATH = MODEL_Folder
    model_path = os.path.join(MODEL_Folder,'model.joblib')
    scaler_path = os.path.join(MODEL_Folder,'scaler.joblib')
    window_size = WINDOW_SIZE
    print(f"开始预测，使用的模型路径为：{MODEL_PATH}")
    # 加载模型和 scaler
    try:
        models, scaler = load_models_and_scaler(model_path,scaler_path)
    except FileNotFoundError as e:
        print(e)
        return None
    # 预处理新数据
    X_new,timestamp = preprocess_new_data(new_data_file_path, LAGS)
    print(f"新数据预处理完成，共 {len(X_new)} 个样本。")
    predictions = make_predictions(models, scaler, X_new, window_size, LAGS)
    print("预测完成。")
    # 保存预测结果
    save_predictions_to_csv(predictions,timestamp)
    print("预测结果已保存。")
    with open(flag_file, 'w') as f:
        f.write(f'Prediction done for {Today}\n')
