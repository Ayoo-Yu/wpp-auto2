import os
from scripts.train_run import train_run
from scripts.prediction_timestamp import post_process_predictions

def run_prediction(upload_path, model):
    # 调用训练与预测函数
    forecast_file_path_temp = train_run(DATA_FILE_PATH=upload_path, MODEL=model)
    # 后处理预测结果
    forecast_file_path = post_process_predictions(upload_path, forecast_file_path_temp)
    return forecast_file_path
