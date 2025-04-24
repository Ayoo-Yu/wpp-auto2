import schedule
import time
import os
import logging
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import shutil
import ftplib  # 用于FTP连接
import json

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建日志目录
log_dir = "./logs/ec_data"
os.makedirs(log_dir, exist_ok=True)

# 创建文件处理器
log_file = os.path.join(log_dir, "ec_data_scheduler.log")
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.INFO)

# 定义日志格式
formatter = logging.Formatter("%(asctime)s - %(message)s")
file_handler.setFormatter(formatter)

# 将处理器添加到日志记录器
logger.addHandler(file_handler)

# 添加控制台处理器，使日志同时显示在控制台
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 任务状态
task_executed = False  # 记录当天任务是否成功执行

# 开发模式：添加命令行参数解析
run_fetch_now = "--run-fetch-now" in sys.argv  # 检查是否有立即运行数据获取的参数

# 配置信息
CONFIG = {
    "server": {
        "host": "server_address",  # 需替换为实际服务器地址
        "port": 21,
        "username": "username",    # 需替换为实际用户名
        "password": "password",    # 需替换为实际密码
    },
    "ec_data_path": "/path/to/ec_data/",  # 服务器上EC数据的路径
    "local_data_path": "./data/ec_data/",  # 本地存储EC数据的路径
    "data_format": {
        "required_features": ["temperature", "humidity", "wind_speed", "wind_direction", "pressure", "precipitation"]  # 需要的特征列表
    }
}

# 确保本地数据目录存在
os.makedirs(CONFIG["local_data_path"], exist_ok=True)

def get_flag_file(date_str):
    """获取数据处理完成标志文件的路径"""
    return os.path.join(log_dir, f"{date_str}_ec_data_done.flag")

def is_data_processed(date_str):
    """检查指定日期的数据是否已处理"""
    flag_file = get_flag_file(date_str)
    if os.path.exists(flag_file):
        logging.info(f"检测到{date_str}的EC数据已经处理过 (标志文件: {flag_file})")
        return True
    return False

def create_flag_file(date_str):
    """创建数据处理完成标志文件"""
    flag_file = get_flag_file(date_str)
    with open(flag_file, "w") as f:
        f.write(f"EC数据处理完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"创建标志文件: {flag_file}")

def fetch_ec_data():
    """从服务器获取EC数据"""
    today_date = datetime.now().strftime('%Y%m%d')
    today_year = datetime.now().strftime('%Y')
    today_month = datetime.now().strftime('%m')
    
    # 构建服务器上数据文件的路径
    server_data_path = f"{CONFIG['ec_data_path']}/{today_year}/{today_month}/{today_date}/"
    
    # 构建本地保存路径
    local_save_path = f"{CONFIG['local_data_path']}/{today_year}/{today_month}/{today_date}/"
    os.makedirs(local_save_path, exist_ok=True)
    
    try:
        # 连接FTP服务器
        ftp = ftplib.FTP()
        ftp.connect(CONFIG['server']['host'], CONFIG['server']['port'])
        ftp.login(CONFIG['server']['username'], CONFIG['server']['password'])
        
        logging.info(f"成功连接到服务器，准备下载{today_date}的EC数据")
        
        # 切换到目标目录
        try:
            ftp.cwd(server_data_path)
        except ftplib.error_perm as e:
            logging.error(f"服务器路径不存在: {server_data_path}, 错误: {e}")
            ftp.quit()
            return False
        
        # 获取目录下所有文件
        file_list = ftp.nlst()
        if not file_list:
            logging.warning(f"服务器路径 {server_data_path} 中没有找到文件")
            ftp.quit()
            return False
        
        # 下载所有文件
        for filename in file_list:
            local_file = os.path.join(local_save_path, filename)
            with open(local_file, 'wb') as f:
                ftp.retrbinary(f"RETR {filename}", f.write)
            logging.info(f"成功下载文件: {filename}")
        
        ftp.quit()
        logging.info(f"{today_date}的EC数据下载完成")
        return True
    
    except Exception as e:
        logging.error(f"下载EC数据时发生错误: {e}")
        return False

def validate_data_format(data_file):
    """验证数据格式是否符合要求"""
    try:
        # 根据文件扩展名决定读取方法
        if data_file.endswith('.csv'):
            df = pd.read_csv(data_file)
        elif data_file.endswith('.xlsx') or data_file.endswith('.xls'):
            df = pd.read_excel(data_file)
        elif data_file.endswith('.json'):
            with open(data_file, 'r') as f:
                df = pd.DataFrame(json.load(f))
        else:
            logging.error(f"不支持的文件格式: {data_file}")
            return False, None
        
        # 检查是否包含所有必要的特征
        required_features = CONFIG['data_format']['required_features']
        missing_features = [feat for feat in required_features if feat not in df.columns]
        
        if missing_features:
            logging.error(f"数据缺少以下特征: {missing_features}")
            return False, df
        
        # 检查时间戳是否存在且格式正确
        if 'timestamp' not in df.columns:
            logging.error("数据中缺少时间戳列")
            return False, df
        
        # 尝试将时间戳转换为日期时间格式
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        except Exception as e:
            logging.error(f"时间戳格式不正确: {e}")
            return False, df
        
        # 检查时间序列是否连续
        timestamps = df['timestamp'].sort_values()
        time_diff = timestamps.diff().dropna()
        if not (time_diff == time_diff.iloc[0]).all():
            logging.warning("时间序列不连续，存在间隔不一致的情况")
        
        return True, df
    
    except Exception as e:
        logging.error(f"验证数据格式时发生错误: {e}")
        return False, None

def fill_missing_values(df):
    """对缺失值进行插值处理"""
    # 首先按时间戳排序
    df = df.sort_values(by='timestamp')
    
    # 对数值型特征进行线性插值
    numeric_features = df.select_dtypes(include=np.number).columns.tolist()
    for feature in numeric_features:
        if df[feature].isnull().any():
            missing_count = df[feature].isnull().sum()
            df[feature] = df[feature].interpolate(method='linear')
            logging.info(f"对特征 {feature} 进行线性插值，填充了 {missing_count} 个缺失值")
    
    # 对非数值型特征使用前项填充
    non_numeric_features = [col for col in df.columns if col not in numeric_features and col != 'timestamp']
    for feature in non_numeric_features:
        if df[feature].isnull().any():
            missing_count = df[feature].isnull().sum()
            df[feature] = df[feature].fillna(method='ffill')
            # 如果还有缺失值（如第一行就是缺失），则使用后项填充
            if df[feature].isnull().any():
                df[feature] = df[feature].fillna(method='bfill')
            logging.info(f"对特征 {feature} 进行前后项填充，填充了 {missing_count} 个缺失值")
    
    return df

def process_ec_data():
    """处理EC数据的主函数"""
    global task_executed
    today_date = datetime.now().strftime('%Y%m%d')
    
    # 检查今天的数据是否已经处理
    if is_data_processed(today_date):
        logging.info(f"今天({today_date})的EC数据已处理，无需重复执行")
        task_executed = True
        return
    
    logging.info(f"开始处理{today_date}的EC数据")
    
    # 1. 获取数据
    if not fetch_ec_data():
        logging.error("获取EC数据失败，任务中止")
        return
    
    # 2. 验证和处理数据
    # 构建数据目录路径
    today_year = datetime.now().strftime('%Y')
    today_month = datetime.now().strftime('%m')
    data_dir = f"{CONFIG['local_data_path']}/{today_year}/{today_month}/{today_date}/"
    
    # 检查目录是否存在
    if not os.path.exists(data_dir):
        logging.error(f"本地数据目录不存在: {data_dir}")
        return
    
    # 获取目录下所有文件
    file_list = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
    if not file_list:
        logging.error(f"本地数据目录 {data_dir} 中没有找到文件")
        return
    
    # 处理每个数据文件
    processed_files = []
    for filename in file_list:
        file_path = os.path.join(data_dir, filename)
        logging.info(f"处理文件: {filename}")
        
        # 验证数据格式
        valid, df = validate_data_format(file_path)
        if not valid:
            logging.warning(f"文件 {filename} 格式验证失败，尝试修复")
            if df is not None:
                # 尝试修复数据
                df = fill_missing_values(df)
                
                # 保存修复后的数据
                processed_file = os.path.join(data_dir, f"processed_{filename}")
                if file_path.endswith('.csv'):
                    df.to_csv(processed_file, index=False)
                elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                    df.to_excel(processed_file, index=False)
                elif file_path.endswith('.json'):
                    df.to_json(processed_file, orient='records')
                
                logging.info(f"修复后的数据已保存到: {processed_file}")
                processed_files.append(processed_file)
            else:
                logging.error(f"文件 {filename} 无法处理")
        else:
            logging.info(f"文件 {filename} 格式正确")
            
            # 检查是否有缺失值需要填充
            if df.isnull().any().any():
                logging.info(f"文件 {filename} 包含缺失值，进行插值处理")
                df = fill_missing_values(df)
                
                # 保存处理后的数据
                processed_file = os.path.join(data_dir, f"processed_{filename}")
                if file_path.endswith('.csv'):
                    df.to_csv(processed_file, index=False)
                elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                    df.to_excel(processed_file, index=False)
                elif file_path.endswith('.json'):
                    df.to_json(processed_file, orient='records')
                
                logging.info(f"处理后的数据已保存到: {processed_file}")
                processed_files.append(processed_file)
            else:
                logging.info(f"文件 {filename} 数据完整，无需处理")
                processed_files.append(file_path)
    
    if processed_files:
        logging.info(f"所有EC数据处理完成, 共处理 {len(processed_files)} 个文件")
        create_flag_file(today_date)
        task_executed = True
    else:
        logging.warning("没有成功处理任何文件")

# 每天上午 8:30 执行EC数据获取和处理任务
schedule.every().day.at("08:30").do(process_ec_data)

logging.info("EC数据定时任务启动成功，每天上午 8:30 运行数据获取和处理")

# 开发模式：根据命令行参数立即执行任务
if run_fetch_now:
    logging.info("收到立即执行EC数据获取和处理的命令，准备立即执行")
    process_ec_data()

while True:
    try:
        # 运行定时任务
        schedule.run_pending()

        # 获取当前时间
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        today_date = now.strftime('%Y%m%d')

        # 每小时记录一次状态（当分钟为0时）
        if current_minute == 0:
            logging.info(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            logging.info(f"当前任务状态: EC数据处理任务已执行={is_data_processed(today_date)}")

        # 检查每日任务
        if current_hour >= 8 and current_minute >= 30:
            if not task_executed and not is_data_processed(today_date):
                logging.warning("检测到 8:30 EC数据处理任务未执行，立即补救运行")
                process_ec_data()
            elif not task_executed and is_data_processed(today_date):
                logging.info("发现今天EC数据已处理过，更新任务状态")
                task_executed = True

        # 到了凌晨，重置日常任务状态
        if current_hour == 0 and current_minute == 0:
            task_executed = False  # 第二天任务重新开始
            logging.info("任务状态已重置，准备执行新一天的任务")

        time.sleep(30)  # 每 30 秒检查一次

    except Exception as e:
        logging.error(f"运行时发生错误: {e}")
        time.sleep(60)  # 遇到错误时等待 60 秒再继续 