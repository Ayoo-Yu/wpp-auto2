# config.py
import os
from datetime import datetime

Today = datetime.now().strftime('%Y%m%d')
WINDOW_SIZE = 16
TRAIN_RATIO = 0.9
OUTPUT_DIR_PRE = r'D:\my-vue-project\wind-power-forecast\backend\auto_scripts\results\middleresult'
OUTPUT_DIR_TRAIN = r'D:\my-vue-project\wind-power-forecast\backend\auto_scripts\train_predictions\middle_predictions'
PREC_SV_FOLDER = r'D:\my-vue-project\wind-power-forecast\backend\auto_scripts\precsv\middlecsv'
DATASET_FOLDER = r'D:\my-vue-project\wind-power-forecast\backend\auto_scripts\dataset\dataset_middle'
MODEL_FOLDER = r'D:\my-vue-project\wind-power-forecast\backend\auto_scripts\models\middlemodel'
LAGS = 4
# 确保输出目录存在
os.makedirs(OUTPUT_DIR_PRE, exist_ok=True)
os.makedirs(OUTPUT_DIR_TRAIN, exist_ok=True)
