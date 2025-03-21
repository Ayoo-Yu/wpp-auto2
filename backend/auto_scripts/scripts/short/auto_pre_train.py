# merged_auto_script.py
import os
import time
import logging
import sys
from threading import Thread, Lock, Event
import joblib
import pandas as pd
from datetime import datetime, timedelta

# 导入预测和训练所需的模块
from predict import predict
from data_processor import (
    load_data,
    preprocess_data,
    split_data,
    feature_engineering,
    scale_data,
    create_time_window,
    filter_data_by_date
)
from models import get_lightgbm_params, get_unified_params
from train import train_and_evaluate, train_multiple_datasets, calculate_model_weights, save_predictions
from utils import visualize_results
from config import WINDOW_SIZE, TRAIN_RATIO, LAGS, OUTPUT_DIR_TRAIN, Today, PREC_SV_FOLDER, DATASET_FOLDER, MODEL_FOLDER, OUTPUT_DIR_PRE

# 创建一个锁用于同步模型文件的访问
model_lock = Lock()
# 创建一个事件用于指示模型是否可用
model_available = Event()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# 确保日志目录存在
log_dir = "./logs/auto_pre_train"
os.makedirs(log_dir, exist_ok=True)
# 创建日志文件
log_file = os.path.join(log_dir, f"{Today}.log")
# 创建 FileHandler
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.INFO)

# 定义日志格式
formatter = logging.Formatter("%(asctime)s - %(message)s")
file_handler.setFormatter(formatter)

# 将处理器添加到日志记录器
logger.addHandler(file_handler)

# 添加控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 处理Windows控制台输出编码
if sys.platform == 'win32':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    # 确保stderr也使用utf-8编码
    sys.stderr.reconfigure(encoding='utf-8')

def print_section(title):
    """打印带分隔符的标题"""
    separator = "=" * 80
    print(f"\n{separator}")
    print(f">>> {title} <<<")
    print(f"{separator}\n")
    logging.info(f"\n{separator}")
    logging.info(f">>> {title} <<<")
    logging.info(f"{separator}\n")

def is_model_available(model_folder_today):
    """检查最佳模型是否可用"""
    print(f"检查模型目录: {model_folder_today}")
    logging.info(f"检查模型目录: {model_folder_today}")
    best_models_dir = os.path.join(model_folder_today, 'best_models')
    
    if os.path.exists(best_models_dir):
        print(f"发现best_models目录: {best_models_dir}")
        logging.info(f"发现best_models目录: {best_models_dir}")
        # 检查是否至少有一个算法类型的模型可用
        for algo_type in ['GBDT', 'DART', 'GOSS']:
            model_file = os.path.join(best_models_dir, f'{algo_type}.joblib')
            if os.path.exists(model_file):
                print(f"✅ 发现{algo_type}模型文件: {model_file}")
                logging.info(f"发现{algo_type}模型文件: {model_file}")
                return True
            else:
                print(f"❌ 未找到{algo_type}模型文件")
                logging.info(f"未找到{algo_type}模型文件")
    else:
        print(f"未找到best_models目录，检查传统模型文件")
        logging.info(f"未找到best_models目录，检查传统模型文件")
    
    # 检查传统模型文件
    model_file = os.path.join(model_folder_today, 'model.joblib')
    exists = os.path.exists(model_file)
    if exists:
        print(f"✅ 发现传统模型文件: {model_file}")
        logging.info(f"发现传统模型文件: {model_file}")
    else:
        print(f"❌ 未找到任何可用模型文件")
        logging.info(f"未找到任何可用模型文件")
    return exists

def train_model(data_file_path, model_folder_today):
    """执行模型训练和评估"""
    print_section("开始模型训练")
    # 配置
    window_size = WINDOW_SIZE
    lags = LAGS
    train_ratio = TRAIN_RATIO
    output_dir = OUTPUT_DIR_TRAIN
    print(f"配置信息:")
    print(f"  - 窗口大小: {window_size}")
    print(f"  - 滞后特征数: {lags}")
    print(f"  - 训练集比例: {train_ratio}")
    print(f"  - 输出目录: {output_dir}")
    print(f"  - 模型存储路径: {model_folder_today}")
    logging.info(f"配置信息:")
    logging.info(f"  - 窗口大小: {window_size}")
    logging.info(f"  - 滞后特征数: {lags}")
    logging.info(f"  - 训练集比例: {train_ratio}")
    logging.info(f"  - 输出目录: {output_dir}")
    logging.info(f"  - 模型存储路径: {model_folder_today}")
    logging.info(f"输出结果将保存到: {output_dir}")
    
    # 数据加载
    print_section("数据加载与预处理")
    print(f"加载数据文件: {data_file_path}")
    logging.info(f"加载数据文件: {data_file_path}")
    logging.info("开始加载和预处理数据...")
    data = load_data(data_file_path)
    print(f"数据加载完成，共 {len(data)} 条记录")
    print(f"数据前5行预览: \n{data.head()}")
    logging.info(f"数据加载完成，共 {len(data)} 条记录")
    logging.info(f"数据前5行预览: \n{data.head()}")
    
    # 使用不同时长的历史数据训练多个模型
    months_list = [1, 3, 6, 9, 12, None]  # None表示使用全部数据
    
    # 根据数据集的实际时间跨度优化months_list
    if 'Timestamp' in data.columns:
        # 确保Timestamp列是datetime类型
        if not pd.api.types.is_datetime64_any_dtype(data['Timestamp']):
            data['Timestamp'] = pd.to_datetime(data['Timestamp'])
        
        # 计算数据集的实际时间跨度（月数）
        earliest_date = data['Timestamp'].min()
        latest_date = data['Timestamp'].max()
        date_range_months = (latest_date.year - earliest_date.year) * 12 + latest_date.month - earliest_date.month
        
        print(f"数据集时间范围: {earliest_date.strftime('%Y-%m-%d')} 至 {latest_date.strftime('%Y-%m-%d')}, 共 {date_range_months} 个月")
        logging.info(f"数据集时间范围: {earliest_date.strftime('%Y-%m-%d')} 至 {latest_date.strftime('%Y-%m-%d')}, 共 {date_range_months} 个月")
        
        # 修剪months_list，去除超过实际月数的选项
        optimized_months = [m for m in months_list if m is None or m <= date_range_months]
        
        if len(optimized_months) < len(months_list):
            print(f"根据数据集实际时间范围({date_range_months}个月)，优化months_list: {months_list} -> {optimized_months}")
            logging.info(f"根据数据集实际时间范围({date_range_months}个月)，优化months_list: {months_list} -> {optimized_months}")
            months_list = optimized_months
    
    print(f"将使用以下时间段训练模型: {months_list}")
    logging.info(f"将使用以下时间段训练模型: {months_list}")
    
    try:
        print_section("开始多数据集训练")
        print(f"将使用多种时间跨度的数据训练模型...")
        logging.info(f"将使用多种时间跨度的数据训练模型...")
        # 运行多数据集训练，为每种算法选择最佳模型
        best_models_info = train_multiple_datasets(data, months_list, train_ratio, lags, window_size, model_folder_today)
        print(f"多数据集训练完成! 已为每种算法选择最佳模型")
        logging.info(f"多数据集训练完成! 已为每种算法选择最佳模型")
        for algo_type, model_info in best_models_info['models'].items():
            if model_info['model'] is not None:
                months_desc = f"{model_info['months']}个月" if model_info['months'] else "全部数据"
                print(f"  - 最佳{algo_type}模型: 使用{months_desc}数据, RMSE={model_info['rmse']:.4f}, K={model_info['k']:.4f}, 评分={model_info['score']:.4f}")
                logging.info(f"  - 最佳{algo_type}模型: 使用{months_desc}数据, RMSE={model_info['rmse']:.4f}, K={model_info['k']:.4f}, 评分={model_info['score']:.4f}")
        
        # 加载过去三天的数据进行权重优化
        print_section("开始计算模型权重")
        logging.info("开始计算模型权重")
        try:
            # 使用训练数据集中的最后三天数据进行权重优化，而不是从历史文件中查找
            print(f"从训练数据集中提取最后三天数据进行权重优化")
            logging.info(f"从训练数据集中提取最后三天数据进行权重优化")
            
            # 确保数据中有Timestamp列
            if 'Timestamp' in data.columns:
                # 获取原始数据的时间戳转为datetime类型
                if not pd.api.types.is_datetime64_any_dtype(data['Timestamp']):
                    data['Timestamp'] = pd.to_datetime(data['Timestamp'])
                
                # 计算最后三天的开始时间
                latest_date = data['Timestamp'].max()
                three_days_before = latest_date - pd.Timedelta(days=3)
                
                # 过滤出最后三天的数据
                last_three_days_data = data[data['Timestamp'] >= three_days_before]
                
                if len(last_three_days_data) >= 24:  # 至少需要一天的数据
                    print(f"✅ 已从训练数据集提取最后三天数据，共 {len(last_three_days_data)} 条记录")
                    logging.info(f"✅ 已从训练数据集提取最后三天数据，共 {len(last_three_days_data)} 条记录")
                    
                    # 计算最优权重
                    print(f"开始计算最优模型权重...")
                    logging.info(f"开始计算最优模型权重...")
                    weights = calculate_model_weights(best_models_info, last_three_days_data, lags, window_size)
                    print(f"计算得到的最优权重: {weights}")
                    logging.info(f"计算得到的最优权重: {weights}")
                    
                    # 保存权重到权重文件
                    weights_file = os.path.join(model_folder_today, 'model_weights.joblib')
                    joblib.dump(weights, weights_file)
                    print(f"模型权重已保存到: {weights_file}")
                    logging.info(f"模型权重已保存到: {weights_file}")
                else:
                    print(f"⚠️ 训练数据集中最后三天的数据不足（少于24条），将使用默认权重")
                    logging.info(f"⚠️ 训练数据集中最后三天的数据不足（少于24条），将使用默认权重")
            else:
                print(f"⚠️ 训练数据中没有Timestamp列，无法提取最后三天数据，将使用默认权重")
                logging.info(f"⚠️ 训练数据中没有Timestamp列，无法提取最后三天数据，将使用默认权重")
        except Exception as e:
            print(f"❌ 计算模型权重时出错: {str(e)}")
            print(f"将使用默认权重: GBDT=0.45, DART=0.1, GOSS=0.45")
            logging.error(f"❌ 计算模型权重时出错: {str(e)}")
            logging.info(f"将使用默认权重: GBDT=0.45, DART=0.1, GOSS=0.45")
    
    except Exception as e:
        print_section("多数据集训练失败")
        logging.error("多数据集训练失败")
        print(f"❌ 错误信息: {str(e)}")
        logging.error(f"❌ 错误信息: {str(e)}")
        print(f"回退到传统的单一模型训练方法...")
        logging.info(f"回退到传统的单一模型训练方法...")
        
        # 如果多数据集训练失败，回退到传统方法
        print_section("开始传统单一模型训练")
        logging.info("开始传统单一模型训练")
        print(f"使用全部数据进行预处理...")
        logging.info(f"使用全部数据进行预处理...")
        X, y = preprocess_data(data)
        X_train, X_val, y_train, y_val = split_data(X, y, train_ratio)
        print(f"数据集划分完成，训练集: {X_train.shape}, 验证集: {X_val.shape}")
        logging.info(f"数据集划分完成，训练集: {X_train.shape}, 验证集: {X_val.shape}")
        
        print(f"执行特征工程...")
        logging.info(f"执行特征工程...")
        X_train_fe, X_val_fe = feature_engineering(X_train, X_val, lags)
        print(f"特征工程后的数据集大小 - 训练: {X_train_fe.shape}, 验证: {X_val_fe.shape}")
        logging.info(f"特征工程后的数据集大小 - 训练: {X_train_fe.shape}, 验证: {X_val_fe.shape}")
        
        # 数据标准化
        print(f"执行数据标准化...")
        logging.info(f"执行数据标准化...")
        X_train_scaled, X_val_scaled, scaler = scale_data(X_train_fe, X_val_fe)
        print(f"数据标准化完成")
        logging.info(f"数据标准化完成")
        
        # 创建时间窗口
        print(f"创建时间窗口，窗口大小: {window_size}...")
        logging.info(f"创建时间窗口，窗口大小: {window_size}...")
        X_train_windows, y_train_windows = create_time_window(X_train_scaled, y_train.values, window_size)
        X_val_windows, y_val_windows = create_time_window(X_val_scaled, y_val.values, window_size)
        print(f"时间窗口创建完成，窗口数量 - 训练: {len(X_train_windows)}, 验证: {len(X_val_windows)}")
        logging.info(f"时间窗口创建完成，窗口数量 - 训练: {len(X_train_windows)}, 验证: {len(X_val_windows)}")
        
        # 获取模型参数
        print(f"获取模型参数...")
        logging.info(f"获取模型参数...")
        params_list = get_lightgbm_params()
        print(f"模型参数获取完成，共 {len(params_list)} 种参数配置")
        logging.info(f"模型参数获取完成，共 {len(params_list)} 种参数配置")
        
        # 训练与评估
        print_section("开始模型训练与评估")
        logging.info("开始模型训练与评估")
        print(f"训练3种不同的LightGBM模型: GBDT, DART, GOSS")
        logging.info(f"训练3种不同的LightGBM模型: GBDT, DART, GOSS")
        results_dict = train_and_evaluate(
            X_train_windows, y_train_windows,
            X_val_windows, y_val_windows,
            params_list, scaler, model_folder_today
        )
        print(f"模型训练与评估完成!")
        logging.info(f"模型训练与评估完成!")
        for model_name, result in results_dict.items():
            print(f"  - {model_name}: RMSE={result['rmse']:.4f}, K={result['k']:.4f}")
            logging.info(f"  - {model_name}: RMSE={result['rmse']:.4f}, K={result['k']:.4f}")
        
        # 保存预测结果
        print(f"保存预测结果到 {output_dir}...")
        logging.info(f"保存预测结果到 {output_dir}...")
        save_predictions(results_dict, y_val_windows, output_base_dir=output_dir)
        print(f"预测结果保存完成")
        logging.info(f"预测结果保存完成")
        
        # 可视化结果
        print(f"创建可视化结果...")
        logging.info(f"创建可视化结果...")
        visualize_results(results_dict, y_val_windows, output_dir)
        print(f"可视化结果创建完成")
        logging.info(f"可视化结果创建完成")

def monitor_training(today_date):
    """监视训练文件夹并执行训练"""
    print_section("启动训练监视线程")
    logging.info("启动训练监视线程")
    csv_file = os.path.join(DATASET_FOLDER, f'{today_date}.csv')
    model_folder_today = os.path.join(MODEL_FOLDER, today_date)
    flag_file = os.path.join(MODEL_FOLDER, today_date,f'{today_date}_train_done.flag')

    print(f"训练文件路径: {csv_file}")
    print(f"模型存储目录: {model_folder_today}")
    print(f"训练完成标志文件: {flag_file}")
    print(f"开始监视 {DATASET_FOLDER} 文件夹以进行训练...")
    logging.info(f"训练文件路径: {csv_file}")
    logging.info(f"模型存储目录: {model_folder_today}")
    logging.info(f"训练完成标志文件: {flag_file}")
    logging.info(f"开始监视 {DATASET_FOLDER} 文件夹以进行训练...")

    while True:
        if os.path.exists(flag_file):
            print(f"⚠️ 检测到今天的训练已经执行过，跳过...")
            logging.info(f"⚠️ 检测到今天的训练已经执行过，跳过...")
            if is_model_available(model_folder_today):
                model_available.set()
                print(f"✅ 模型已设置为可用状态")
                logging.info(f"✅ 模型已设置为可用状态")
            break

        if os.path.exists(csv_file):
            print(f"✅ 发现新的训练文件：{csv_file}，执行训练...")
            logging.info(f"✅ 发现新的训练文件：{csv_file}，执行训练...")
            with model_lock:
                train_model(csv_file, model_folder_today)
            with open(flag_file, 'w') as f:
                f.write(f'Training done for {today_date}\n')
            print(f"✅ 训练完成，已创建标志文件: {flag_file}")
            logging.info(f"✅ 训练完成，已创建标志文件: {flag_file}")
            
            # 验证模型是否可用
            if is_model_available(model_folder_today):
                model_available.set()
                print(f"✅ 模型已成功保存到 {model_folder_today}，模型可用。")
                logging.info(f"✅ 模型已成功保存到 {model_folder_today}，模型可用。")
            else:
                print(f"❌ 模型文件未找到在 {model_folder_today}，模型不可用。")
                logging.info(f"❌ 模型文件未找到在 {model_folder_today}，模型不可用。")
            break

        print(f"❌ 未找到训练 CSV 文件: {csv_file}，等待 30 秒后重试...")
        logging.info(f"❌ 未找到训练 CSV 文件: {csv_file}，等待 30 秒后重试...")
        time.sleep(30)  # 每30秒检查一次

def monitor_prediction(today_date):
    """监视预测文件夹并执行预测"""
    print_section("启动预测监视线程")
    logging.info("启动预测监视线程")
    csv_file = os.path.join(PREC_SV_FOLDER, f'{today_date}.csv')
    model_folder_today = os.path.join(MODEL_FOLDER, today_date)
    flag_file = os.path.join(OUTPUT_DIR_PRE, Today, f'{today_date}_predict_done.flag')

    print(f"预测数据文件路径: {csv_file}")
    print(f"模型目录: {model_folder_today}")
    print(f"预测完成标志文件: {flag_file}")
    print(f"开始监视 {PREC_SV_FOLDER} 文件夹以进行预测...")
    logging.info(f"预测数据文件路径: {csv_file}")
    logging.info(f"模型目录: {model_folder_today}")
    logging.info(f"预测完成标志文件: {flag_file}")
    logging.info(f"开始监视 {PREC_SV_FOLDER} 文件夹以进行预测...")

    while True:
        if os.path.exists(flag_file):
            print(f"⚠️ 检测到今天的预测已经执行过，跳过...")
            logging.info(f"⚠️ 检测到今天的预测已经执行过，跳过...")
            break

        # 等待模型可用
        if not (model_available.is_set() or is_model_available(model_folder_today)):
            print(f"⏳ 未有可用模型，等待模型训练完成...")
            logging.info(f"⏳ 未有可用模型，等待模型训练完成...")
            time.sleep(30)
            continue

        if os.path.exists(csv_file):
            print(f"✅ 发现新的预测文件：{csv_file}，执行预测...")
            logging.info(f"✅ 发现新的预测文件：{csv_file}，执行预测...")
            with model_lock:
                predict(csv_file, model_folder_today)
            print(f"✅ 预测执行完成")
            logging.info(f"✅ 预测执行完成")
            break

        print(f"❌ 未找到预测 CSV 文件: {csv_file}，等待 30 秒后重试...")
        logging.info(f"❌ 未找到预测 CSV 文件: {csv_file}，等待 30 秒后重试...")
        time.sleep(30)  # 每30秒检查一次

def main():
    """主函数，启动训练和预测的监视线程"""
    print_section("自动训练预测系统启动")
    logging.info("自动训练预测系统启动")
    today_date = Today
    print(f"今天的日期是: {today_date}")
    logging.info(f"今天的日期是: {today_date}")

    # 创建训练和预测的监视线程
    print(f"创建监视线程...")
    logging.info(f"创建监视线程...")
    train_thread = Thread(target=monitor_training, args=(today_date,), name="TrainThread")
    predict_thread = Thread(target=monitor_prediction, args=(today_date,), name="PredictThread")

    # 启动线程
    print(f"启动训练线程...")
    logging.info(f"启动训练线程...")
    train_thread.start()
    print(f"启动预测线程...")
    logging.info(f"启动预测线程...")
    predict_thread.start()

    # 等待线程完成
    print(f"等待线程完成...")
    logging.info(f"等待线程完成...")
    train_thread.join()
    predict_thread.join()

    print_section("系统任务完成")
    logging.info("系统任务完成")
    print("今天的训练和预测任务已完成。")
    logging.info("今天的训练和预测任务已完成。")

if __name__ == '__main__':
    main()
