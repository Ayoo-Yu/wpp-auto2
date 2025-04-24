import os
import time
import logging
import sys
import shutil
import pandas as pd
import glob
import ftplib
import schedule
import paramiko
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建文件处理器
log_dir = "./logs/report_predictions"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y%m%d')}.log")
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

# 获取当前脚本所在目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 回溯到wind-power-forecast目录
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..', '..', '..'))

# 结果文件夹路径
MIDDLE_RESULT_DIR = os.path.join(BASE_DIR, 'backend', 'auto_scripts', 'results', 'middleresult')
SHORT_RESULT_DIR = os.path.join(BASE_DIR, 'backend', 'auto_scripts', 'results', 'shortresult')
SUPERSHORT_RESULT_DIR = os.path.join(BASE_DIR, 'backend', 'auto_scripts', 'results', 'supershortresult')

# 上报结果存储路径
REPORT_OUTPUT_DIR = os.path.join(BASE_DIR, 'backend', 'auto_scripts', 'reports')
SHORT_MIDDLE_OUTPUT_DIR = os.path.join(REPORT_OUTPUT_DIR, 'short_middle')
SUPERSHORT_OUTPUT_DIR = os.path.join(REPORT_OUTPUT_DIR, 'supershort')

# 创建所需目录
os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)
os.makedirs(SHORT_MIDDLE_OUTPUT_DIR, exist_ok=True)
os.makedirs(SUPERSHORT_OUTPUT_DIR, exist_ok=True)

# 上传服务器信息
SERVER_HOST = "example.server.com"  # 替换为实际服务器地址
SERVER_PORT = 22  # SSH端口，如果使用FTP可能是21
SERVER_USER = "username"  # 替换为实际用户名
SERVER_PASS = "password"  # 替换为实际密码
SERVER_PATH_SHORT_MIDDLE = "/path/to/short_middle"  # 替换为实际路径
SERVER_PATH_SUPERSHORT = "/path/to/supershort"  # 替换为实际路径

# 上报标记文件目录
REPORT_FLAG_DIR = os.path.join(log_dir, 'flags')
os.makedirs(REPORT_FLAG_DIR, exist_ok=True)

def get_report_flag_file(file_name):
    """获取上报完成标志文件的路径"""
    file_base_name = os.path.basename(file_name)
    return os.path.join(REPORT_FLAG_DIR, f"{file_base_name}_reported.flag")

def is_reported(file_name):
    """检查文件是否已上报"""
    flag_file = get_report_flag_file(file_name)
    return os.path.exists(flag_file)

def mark_as_reported(file_name):
    """标记文件已上报"""
    flag_file = get_report_flag_file(file_name)
    with open(flag_file, 'w') as f:
        f.write(f"Reported at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"已标记文件为已上报: {file_name}")

def merge_short_middle_predictions(short_file, middle_file, output_file):
    """合并短期和中期预测结果"""
    logging.info(f"合并短期文件: {short_file} 和中期文件: {middle_file}")
    
    # 读取CSV文件
    try:
        df_short = pd.read_csv(short_file)
        df_middle = pd.read_csv(middle_file)
        
        # 确保时间戳列是datetime类型
        df_short['Timestamp'] = pd.to_datetime(df_short['Timestamp'])
        df_middle['Timestamp'] = pd.to_datetime(df_middle['Timestamp'])
        
        # 创建合并结果的DataFrame，以短期预测为基础
        df_merged = df_short.copy()
        
        # 对于中期预测中存在的相同时间戳，用中期预测值替换短期预测值
        for idx, row in df_middle.iterrows():
            timestamp = row['Timestamp']
            mask = df_merged['Timestamp'] == timestamp
            if mask.any():
                df_merged.loc[mask, 'Predicted Power'] = row['Predicted Power']
        
        # 保存合并后的结果
        df_merged.to_csv(output_file, index=False)
        logging.info(f"合并完成，已保存到: {output_file}")
        return True
    except Exception as e:
        logging.error(f"合并短期和中期预测时出错: {str(e)}")
        return False

def upload_file_sftp(local_file, remote_dir):
    """使用SFTP上传文件到服务器"""
    try:
        logging.info(f"正在上传文件 {local_file} 到 {remote_dir}")
        
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 连接到服务器
        ssh.connect(SERVER_HOST, port=SERVER_PORT, username=SERVER_USER, password=SERVER_PASS)
        
        # 创建SFTP客户端
        sftp = ssh.open_sftp()
        
        # 获取文件名
        filename = os.path.basename(local_file)
        remote_file = os.path.join(remote_dir, filename)
        
        # 上传文件
        sftp.put(local_file, remote_file)
        
        # 关闭连接
        sftp.close()
        ssh.close()
        
        logging.info(f"文件上传成功: {local_file} -> {remote_file}")
        return True
    except Exception as e:
        logging.error(f"上传文件时出错: {str(e)}")
        return False

def process_short_middle_files():
    """处理短期和中期预测文件"""
    today_date = datetime.now().strftime('%Y%m%d')
    
    # 查找今天的短期和中期预测文件
    short_dir = os.path.join(SHORT_RESULT_DIR, today_date)
    middle_dir = os.path.join(MIDDLE_RESULT_DIR, today_date)
    
    # 检查目录是否存在
    if not os.path.exists(short_dir) or not os.path.exists(middle_dir):
        logging.info(f"短期或中期预测目录不存在，跳过处理")
        return
    
    # 获取文件路径
    short_file = os.path.join(short_dir, f"{today_date}.csv")
    middle_file = os.path.join(middle_dir, f"{today_date}.csv")
    
    # 检查文件是否存在
    if not os.path.exists(short_file):
        logging.info(f"短期预测文件不存在: {short_file}")
        return
    if not os.path.exists(middle_file):
        logging.info(f"中期预测文件不存在: {middle_file}")
        return
    
    # 检查是否已处理
    output_file = os.path.join(SHORT_MIDDLE_OUTPUT_DIR, f"short_middle_{today_date}.csv")
    if is_reported(output_file):
        logging.info(f"短期和中期预测合并文件已上报: {output_file}")
        return
    
    # 合并预测结果
    if merge_short_middle_predictions(short_file, middle_file, output_file):
        # 上传合并后的文件
        if upload_file_sftp(output_file, SERVER_PATH_SHORT_MIDDLE):
            # 标记为已上报
            mark_as_reported(output_file)

def process_supershort_file(file_path):
    """处理超短期预测文件"""
    if not os.path.exists(file_path):
        logging.error(f"超短期预测文件不存在: {file_path}")
        return False
        
    # 检查是否已处理
    if is_reported(file_path):
        logging.info(f"超短期预测文件已上报: {file_path}")
        return True
        
    # 复制文件到上报目录
    file_name = os.path.basename(file_path)
    output_file = os.path.join(SUPERSHORT_OUTPUT_DIR, file_name)
    try:
        shutil.copy2(file_path, output_file)
        logging.info(f"已复制超短期预测文件: {file_path} -> {output_file}")
        
        # 上传文件
        if upload_file_sftp(output_file, SERVER_PATH_SUPERSHORT):
            # 标记为已上报
            mark_as_reported(output_file)
            return True
    except Exception as e:
        logging.error(f"处理超短期预测文件时出错: {str(e)}")
    
    return False

def scan_supershort_files():
    """扫描并处理超短期预测文件"""
    today_date = datetime.now().strftime('%Y%m%d')
    supershort_dir = os.path.join(SUPERSHORT_RESULT_DIR, today_date)
    
    # 检查目录是否存在
    if not os.path.exists(supershort_dir):
        logging.info(f"超短期预测目录不存在: {supershort_dir}")
        return
    
    # 获取所有预测文件
    prediction_files = glob.glob(os.path.join(supershort_dir, "prediction_*.csv"))
    
    if not prediction_files:
        logging.info(f"未找到超短期预测文件")
        return
    
    # 处理每个文件
    for file_path in prediction_files:
        process_supershort_file(file_path)

class PredictionFileHandler(FileSystemEventHandler):
    """监控新文件的事件处理器"""
    
    def on_created(self, event):
        """当创建新文件时触发"""
        if event.is_directory:
            return
            
        file_path = event.src_path
        
        # 等待文件写入完成
        time.sleep(1)
        
        if not os.path.exists(file_path):
            return
            
        logging.info(f"检测到新文件: {file_path}")
        
        # 处理文件
        if SUPERSHORT_RESULT_DIR in file_path and file_path.endswith('.csv'):
            # 处理超短期预测文件
            process_supershort_file(file_path)
        elif SHORT_RESULT_DIR in file_path or MIDDLE_RESULT_DIR in file_path:
            # 当检测到新的短期或中期预测文件时，尝试处理
            process_short_middle_files()

def setup_file_monitoring():
    """设置文件监控"""
    # 创建监控器
    observer = Observer()
    
    # 创建事件处理器
    event_handler = PredictionFileHandler()
    
    # 监控结果目录
    today_date = datetime.now().strftime('%Y%m%d')
    for result_dir in [SHORT_RESULT_DIR, MIDDLE_RESULT_DIR, SUPERSHORT_RESULT_DIR]:
        dir_path = os.path.join(result_dir, today_date)
        os.makedirs(dir_path, exist_ok=True)
        observer.schedule(event_handler, dir_path, recursive=False)
    
    # 启动监控
    observer.start()
    logging.info("文件监控已启动")
    
    return observer

def main():
    """主函数"""
    logging.info("预测结果上报脚本已启动")
    
    # 初始扫描一次
    process_short_middle_files()
    scan_supershort_files()
    
    # 设置文件监控
    observer = setup_file_monitoring()
    
    # 定期扫描
    schedule.every(5).minutes.do(process_short_middle_files)
    schedule.every(5).minutes.do(scan_supershort_files)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("预测结果上报脚本已停止")
    finally:
        observer.join()

if __name__ == "__main__":
    main() 