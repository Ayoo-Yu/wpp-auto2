from scripts.predict import predict
from scripts.prediction_timestamp import post_process_predictions

def run_predict(CSV_FILE_PATH, MODEL_PATH, SCALER_PATH):
    # 调用训练与预测函数
    print("开始预测,执行run_predict函数")
    predcit_file_path_temp = predict(CSV_FILE_PATH=CSV_FILE_PATH, MODEL_PATH=MODEL_PATH, SCALER_PATH=SCALER_PATH,WINDOW_SIZE=16)
    # 后处理预测结果
    # print("开始后处理预测结果,执行post_process_predictions函数")
    # forecast_file_path = post_process_predictions(CSV_FILE_PATH, predcit_file_path_temp)
    return predcit_file_path_temp
