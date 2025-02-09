#run_auto_predict.py
import os
import time
from datetime import datetime
from predict import predict

precsv_folder = 'D:/my-vue-project/wind-power-forecast/backend/auto_scripts/precsv/middlecsv'
model_folder = 'D:/my-vue-project/wind-power-forecast/backend/auto_scripts/models/middlemodel'
result_folder = 'D:/my-vue-project/wind-power-forecast/backend/auto_scripts/results/middleresult'

today_date = datetime.today().strftime('%Y%m%d')
csv_file = os.path.join(precsv_folder, f'{today_date}.csv')
model_folder_today = os.path.join(model_folder, today_date)
model_file = os.path.join(model_folder_today, 'model.joblib')  # 模型文件名为'model.joblib'
scaler_file = os.path.join(model_folder_today, 'scaler.joblib')  # 假设缩放器文件名为'scaler.joblib'

flag_file = os.path.join(result_folder, f'{today_date}_done.flag')

def check_prediction_done():
    return os.path.exists(flag_file)

def watch_folder():
    print(f"开始监视 {precsv_folder} 文件夹...")
    while True:
        if check_prediction_done():
            print(f"今天的预测已经执行过，跳过...")
            break
        
        if os.path.exists(csv_file):
            print(f"发现新的文件：{csv_file}，执行预测...")
            predict(csv_file,model_folder_today)
            with open(flag_file, 'w') as f:
                f.write(f'Prediction done for {today_date}\n')
            break
        
        time.sleep(5)

# 启动监视程序
watch_folder()
