import os
import time
import logging
import sys
import schedule
import subprocess
from datetime import datetime

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 确保日志目录存在
# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(current_dir, "logs", "scheduler_predict")
os.makedirs(log_dir, exist_ok=True)

# 创建日志文件
today = datetime.now().strftime("%Y%m%d")
log_file = os.path.join(log_dir, f"{today}.log")

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

def run_predict():
    """运行预测脚本"""
    now = datetime.now()
    current_time = now.strftime('%H:%M')
    logging.info(f"开始执行15分钟周期预测... 当前时间: {current_time}")
    
    # 使用绝对路径直接指向实际文件
    script_path = "/app/auto_scripts/scripts/supershort/auto_predict.py"
    logging.info(f"使用脚本路径: {script_path}")
    
    # 使用正确的Conda环境路径
    conda_env_path = "/opt/conda/envs/wind-power-env"
    logging.info(f"使用Conda环境: {conda_env_path}")
    
    # 跨平台执行命令
    cmd = f"conda run -p {conda_env_path} python {script_path}"
    logging.info(f"执行命令: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                 encoding='utf-8')
        logging.info(f"预测脚本执行完成: {result.stdout}")
        if result.stderr:
            logging.warning(f"预测脚本错误输出: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"预测脚本执行失败: {e}")
        logging.error(f"标准输出: {e.stdout}")
        logging.error(f"错误输出: {e.stderr}")
        return False

def reset_daily_counter():
    """在每天午夜重置计数"""
    logging.info("每日计数器重置")
    # 实际上不需要做什么，因为文件名是基于时间的

def print_section(title):
    """打印带分隔符的标题"""
    separator = "=" * 80
    print(f"\n{separator}")
    print(f">>> {title} <<<")
    print(f"{separator}\n")
    logging.info(f"\n{separator}")
    logging.info(f">>> {title} <<<")
    logging.info(f"{separator}\n")

def main():
    """主函数，设置调度任务"""
    print_section("启动15分钟周期预测调度器")
    logging.info("启动15分钟周期预测调度器")
    
    # 尝试初始预测
    logging.info("尝试执行初始预测任务...")
    try:
        # 初始调用 run_predict
        run_predict()  # 如果 auto_predict.py 退出非零码，会抛出 CalledProcessError
        logging.info("初始预测任务调用完成 (可能未执行预测，需检查 auto_predict 日志)")
    except subprocess.CalledProcessError as e:
        # 捕获 auto_predict.py 执行失败的情况 (例如退出码非0)
        logging.error(f"初始预测脚本执行失败: {e}")
        logging.error(f"标准输出: {e.stdout}")
        logging.error(f"错误输出: {e.stderr}")
        logging.warning("由于初始预测失败，调度器将继续运行，但首次预测未执行。")
    except Exception as e:
        # 捕获其他意外错误
        logging.exception(f"初始 run_predict 调用期间发生意外错误: {e}")
        logging.warning("尽管初始运行出错，调度器仍将继续运行。")
    
    # 每5分钟运行一次预测
    schedule.every(5).minutes.do(run_predict)
    
    # 每天午夜重置计数
    schedule.every().day.at("00:00").do(reset_daily_counter)
    
    logging.info(f"调度器已启动，将每5分钟执行一次预测")
    print(f"调度器已启动，将每5分钟执行一次预测")
    
    # 运行调度循环
    while True:
        schedule.run_pending()
        status = "下一次预测将在 " + str(schedule.next_run()) + " 执行"
        print(status, end="\r")
        time.sleep(1)

if __name__ == "__main__":
    main() 