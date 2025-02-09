import os
import time
import logging
from threading import Thread, Lock, Event

# 导入预测和训练所需的模块
from predict import predict
from data_processor import (
    load_data,
    preprocess_data,
    split_data,
    feature_engineering,
    scale_data,
    create_time_window
)
from models import get_lightgbm_params
from train import train_and_evaluate, save_predictions
from utils import visualize_results
from config import WINDOW_SIZE, TRAIN_RATIO, LAGS, OUTPUT_DIR_TRAIN, Today, PREC_SV_FOLDER, DATASET_FOLDER, MODEL_FOLDER, OUTPUT_DIR_PRE

# 创建一个锁用于同步模型文件的访问
model_lock = Lock()
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 确保日志目录存在
log_dir = "./logs/auto_pre_train"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"{Today}.log")
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
def monitor_training(today_date):
    """监视训练文件夹并执行训练"""
    csv_file = os.path.join(DATASET_FOLDER, f'{today_date}.csv')
    model_folder_today = os.path.join(MODEL_FOLDER, today_date)
    flag_file = os.path.join(MODEL_FOLDER, today_date,f'{today_date}_train_done.flag')

    print(f"开始监视 {DATASET_FOLDER} 文件夹以进行训练...")
    logging.info(f"开始监视 {DATASET_FOLDER} 文件夹以进行训练...")

    while True:
        if os.path.exists(flag_file):
            print(f"今天的训练已经执行过，跳过...")
            logging.info(f"今天的训练已经执行过，跳过...")
            break

        if os.path.exists(csv_file):
            print(f"发现新的训练文件：{csv_file}，执行训练...")
            logging.info(f"发现新的训练文件：{csv_file}，执行训练...")
            with model_lock:
                train_model(csv_file, model_folder_today)
            with open(flag_file, 'w') as f:
                f.write(f'Training done for {today_date}\n')
            # 验证模型是否可用
            if is_model_available(model_folder_today):
                print(f"模型已成功保存到 {model_folder_today}，模型可用。")
                logging.info(f"模型已成功保存到 {model_folder_today}，模型可用。")
            else:
                print(f"模型文件未找到在 {model_folder_today}，模型不可用。")
                logging.info(f"模型文件未找到在 {model_folder_today}，模型不可用。")
            break

        print("未找到训练 CSV 文件，等待 30 秒后重试...")
        logging.info("未找到训练 CSV 文件，等待 30 秒后重试...")
        time.sleep(30)  # 每5秒检查一次
def train_model(data_file_path, model_folder_today):
    """执行模型训练和评估"""
    # 配置
    window_size = WINDOW_SIZE
    lags = LAGS
    train_ratio = TRAIN_RATIO
    output_dir = OUTPUT_DIR_TRAIN
    print(f"输出结果将保存到: {output_dir}")
    logging.info(f"输出结果将保存到: {output_dir}")
    # 数据加载与预处理
    data = load_data(data_file_path)
    X, y = preprocess_data(data)
    X_train, X_val, y_train, y_val = split_data(X, y, train_ratio)
    X_train_fe, X_val_fe = feature_engineering(X_train, X_val, lags)
    logging.info("数据加载与预处理完成")
    # 数据标准化
    X_train_scaled, X_val_scaled, scaler = scale_data(X_train_fe, X_val_fe)
    logging.info("数据标准化完成")
    # 创建时间窗口
    X_train_windows, y_train_windows = create_time_window(X_train_scaled, y_train.values, window_size)
    X_val_windows, y_val_windows = create_time_window(X_val_scaled, y_val.values, window_size)
    logging.info("创建时间窗口完成")
    # 获取模型参数
    params_list = get_lightgbm_params()
    logging.info("获取模型参数完成")
    # 训练与评估
    results_dict = train_and_evaluate(
        X_train_windows, y_train_windows,
        X_val_windows, y_val_windows,
        params_list, scaler, model_folder_today
    )
    logging.info("训练与评估完成")
    # 保存预测结果
    save_predictions(results_dict, y_val_windows, output_base_dir=output_dir)
    logging.info("保存预测结果完成")
    # 可视化结果
    visualize_results(results_dict, y_val_windows, output_dir)
    logging.info("可视化结果完成")
def is_model_available(MODEL_FOLDER):
    model_file = os.path.join(MODEL_FOLDER, 'model.joblib')  # 修改为实际的模型文件名
    return os.path.exists(model_file)

def monitor_prediction(today_date):
    """持续监视预测文件夹，每3分钟检查一次新文件并执行预测"""
    model_folder_today = os.path.join(MODEL_FOLDER, today_date)
    processed_files = set()  # 记录已处理的文件
    PREC_SV_FOLDER_TODAY = os.path.join(PREC_SV_FOLDER,today_date)
    os.makedirs(PREC_SV_FOLDER_TODAY,exist_ok=True)
    print(f"开始监视 {PREC_SV_FOLDER_TODAY} 文件夹以进行预测...")
    logging.info(f"开始监视 {PREC_SV_FOLDER_TODAY} 文件夹以进行预测...")

    while True:
        # 确保模型可用
        if not (is_model_available(MODEL_FOLDER)):
            print("模型不可用，等待模型训练完成...")
            logging.info("模型不可用，等待模型训练完成...")
            time.sleep(150)
            continue

        # 获取文件夹下所有 CSV 文件
        files = [f for f in os.listdir(PREC_SV_FOLDER_TODAY) if f.endswith(".csv")]
        files.sort()  # 按名称排序，确保按时间顺序处理

        for file in files:
            file_path = os.path.join(PREC_SV_FOLDER_TODAY, file)

            if file_path in processed_files:
                continue  # 跳过已处理的文件

            print(f"发现新的预测文件：{file}，执行预测...")
            logging.info(f"发现新的预测文件：{file}，执行预测...")

            with model_lock:
                predict(file_path, MODEL_FOLDER)
            
            processed_files.add(file_path)  # 记录已处理的文件

        print("等待 3 分钟后重新检查新文件...")
        logging.info("等待 3 分钟后重新检查新文件...")
        time.sleep(180)  # 每3分钟检查一次

def main():
    """主函数，启动训练和预测的监视线程"""
    today_date = Today
    print(f"今天的日期是: {today_date}")
    logging.info(f"今天的日期是: {today_date}")

    # 创建训练和预测的监视线程
    train_thread = Thread(target=monitor_training, args=(today_date,), name="TrainThread")
    predict_thread = Thread(target=monitor_prediction, args=(today_date,), name="PredictThread")

    # 启动线程
    train_thread.start()
    predict_thread.start()

    # 等待线程完成
    train_thread.join()
    predict_thread.join()

    print("今天的训练和预测任务已完成。")
    logging.info("今天的训练和预测任务已完成。")

if __name__ == '__main__':
    main()
