# auto_predict.py
import os
import time
import logging
import sys
from datetime import datetime

# 导入预测所需的模块
from predict import predict
from config import Today, PREC_SV_FOLDER, MODEL_FOLDER, OUTPUT_DIR_PRE

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 确保日志目录存在
log_dir = "./logs/auto_predict"
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

def get_predict_period_flag_file(csv_filename):
    """
    根据预测文件名创建标志文件路径
    
    参数:
    - csv_filename: 预测CSV文件名 (如: 202503221500.csv)
    
    返回:
    标志文件路径
    """
    # 从文件名中提取日期和时间信息 (例如从 202503221500.csv 提取出 20250322_15_00)
    if csv_filename.endswith('.csv'):
        csv_filename = csv_filename[:-4]  # 去掉 .csv 后缀
    
    # 假设文件名格式为 YYYYMMDDHHMM
    if len(csv_filename) >= 12:
        date = csv_filename[:8]  # YYYYMMDD
        hour = csv_filename[8:10]  # HH
        minute = csv_filename[10:12]  # MM
        period_str = f"{date}_{hour}_{minute}"
    else:
        # 如果文件名格式不符合预期，使用其本身作为标识
        period_str = csv_filename
    
    # 创建标志文件路径
    log_dir = "./logs/auto_predict"
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"predict_{period_str}.flag")

def is_predict_done_for_file(csv_filename):
    """
    检查特定预测文件是否已处理
    
    参数:
    - csv_filename: 预测CSV文件名
    
    返回:
    是否已处理
    """
    flag_file = get_predict_period_flag_file(csv_filename)
    if os.path.exists(flag_file):
        logging.info(f"该预测文件已处理过 (标志文件: {flag_file})")
        return True
    return False

def mark_predict_done_for_file(csv_filename):
    """
    标记特定预测文件已处理
    
    参数:
    - csv_filename: 预测CSV文件名
    """
    flag_file = get_predict_period_flag_file(csv_filename)
    with open(flag_file, 'w') as f:
        f.write(f'Prediction completed at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
    logging.info(f"已创建预测标志文件: {flag_file}")

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

def monitor_prediction(today_date):
    """监视预测文件夹并执行预测"""
    print_section("开始执行预测")
    logging.info("开始执行预测")
    
    # 构建今天的日期目录
    today_csv_dir = os.path.join(PREC_SV_FOLDER, today_date)
    # 确保日期目录存在
    os.makedirs(today_csv_dir, exist_ok=True)
    
    model_folder_today = os.path.join(MODEL_FOLDER, today_date)
    
    # 确保输出目录存在
    output_dir = os.path.join(OUTPUT_DIR_PRE, today_date)
    os.makedirs(output_dir, exist_ok=True)

    logging.info(f"扫描预测数据文件目录: {today_csv_dir}")
    
    # 检查模型是否可用
    if not is_model_available(model_folder_today):
        print(f"❌ 未有可用模型，无法执行预测")
        logging.error(f"❌ 未有可用模型，无法执行预测")
        return False
    
    # 获取目录中的所有CSV文件
    prediction_success = False
    
    if not os.path.exists(today_csv_dir):
        print(f"❌ 预测文件目录不存在: {today_csv_dir}")
        logging.error(f"❌ 预测文件目录不存在: {today_csv_dir}")
        return False
    
    csv_files = [f for f in os.listdir(today_csv_dir) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"❌ 未找到任何预测CSV文件")
        logging.error(f"❌ 未找到任何预测CSV文件")
        return False
    
    print(f"找到 {len(csv_files)} 个CSV文件")
    logging.info(f"找到 {len(csv_files)} 个CSV文件")
    
    # 记录已处理的文件
    processed_files = []
    
    # 处理每个CSV文件
    for csv_filename in csv_files:
        csv_file = os.path.join(today_csv_dir, csv_filename)
        
        # 检查是否已经处理过此文件
        if is_predict_done_for_file(csv_filename):
            print(f"⏩ 跳过已处理的文件: {csv_filename}")
            logging.info(f"⏩ 跳过已处理的文件: {csv_filename}")
            processed_files.append(csv_filename)
            continue
        
        # 检查对应的输出文件是否已存在
        output_filename = csv_filename.replace('.csv', '_result.csv')
        output_file = os.path.join(output_dir, output_filename)
        
        if os.path.exists(output_file):
            print(f"⏩ 已存在输出文件，标记为已处理: {csv_filename}")
            logging.info(f"⏩ 已存在输出文件，标记为已处理: {csv_filename}")
            mark_predict_done_for_file(csv_filename)
            processed_files.append(csv_filename)
            continue
        
        print(f"✅ 处理预测文件: {csv_file}")
        logging.info(f"✅ 处理预测文件: {csv_file}")
        
        try:
            predict(csv_file, model_folder_today)
            print(f"✅ {csv_filename} 预测执行完成")
            logging.info(f"✅ {csv_filename} 预测执行完成")
            
            # 标记此文件已处理
            mark_predict_done_for_file(csv_filename)
            
            processed_files.append(csv_filename)
            prediction_success = True
        except Exception as e:
            print(f"❌ 预测执行失败 {csv_filename}: {str(e)}")
            logging.error(f"❌ 预测执行失败 {csv_filename}: {str(e)}")
    
    if processed_files:
        print(f"本次共处理了 {len(processed_files)} 个预测文件")
        logging.info(f"本次共处理了 {len(processed_files)} 个预测文件")
    
    return prediction_success

def main():
    """主函数，执行预测任务"""
    print_section("自动预测系统启动")
    logging.info("自动预测系统启动")
    today_date = Today
    print(f"当前日期: {today_date}, 时间: {datetime.now().strftime('%H:%M:%S')}")
    logging.info(f"当前日期: {today_date}, 时间: {datetime.now().strftime('%H:%M:%S')}")

    # 执行预测（移除了周期检查，直接处理所有未处理的文件）
    success = monitor_prediction(today_date)

    print_section("预测任务结束")
    logging.info("预测任务结束")

if __name__ == '__main__':
    main() 