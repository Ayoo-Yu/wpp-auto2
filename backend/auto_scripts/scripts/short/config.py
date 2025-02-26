# config.py
import os
from datetime import datetime

Today = datetime.now().strftime('%Y%m%d')
WINDOW_SIZE = 16
TRAIN_RATIO = 0.9
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # 当前脚本目录
# 回溯到wind-power-forecast目录 (从middle到scripts到auto_scripts到backend到根目录)
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..', '..', '..'))
print(f"BASE_DIR: {BASE_DIR}")
# 使用os.path.join构建路径
OUTPUT_DIR_PRE = os.path.join(BASE_DIR, 'backend', 'auto_scripts', 'results', 'shortresult')
OUTPUT_DIR_TRAIN = os.path.join(BASE_DIR, 'backend', 'auto_scripts', 'train_predictions', 'short_predictions')
PREC_SV_FOLDER = os.path.join(BASE_DIR, 'backend', 'auto_scripts', 'precsv', 'shortcsv')
DATASET_FOLDER = os.path.join(BASE_DIR, 'backend', 'auto_scripts', 'dataset', 'dataset_short')
MODEL_FOLDER = os.path.join(BASE_DIR, 'backend', 'auto_scripts', 'models', 'shortmodel')
print(f"OUTPUT_DIR_PRE: {OUTPUT_DIR_PRE}")
print(f"OUTPUT_DIR_TRAIN: {OUTPUT_DIR_TRAIN}")
print(f"PREC_SV_FOLDER: {PREC_SV_FOLDER}")
print(f"DATASET_FOLDER: {DATASET_FOLDER}")
print(f"MODEL_FOLDER: {MODEL_FOLDER}")
LAGS = 4
# 确保输出目录存在
os.makedirs(OUTPUT_DIR_PRE, exist_ok=True)
os.makedirs(OUTPUT_DIR_TRAIN, exist_ok=True)
os.makedirs(PREC_SV_FOLDER, exist_ok=True)
os.makedirs(DATASET_FOLDER, exist_ok=True)
os.makedirs(MODEL_FOLDER, exist_ok=True)

