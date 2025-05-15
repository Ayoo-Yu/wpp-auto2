import schedule
import time
import os
import logging
import sys
import subprocess
from datetime import datetime, timedelta

# 获取当前脚本的绝对路径和目录
current_script_path = os.path.abspath(__file__)
current_script_dir = os.path.dirname(current_script_path)

# 基于脚本位置设置绝对路径
base_log_dir = os.path.join(current_script_dir, 'logs')
log_dir_train = os.path.join(base_log_dir, 'auto_pre_train')
log_dir_param = os.path.join(base_log_dir, 'param_optimizer')
log_file_path = os.path.join(current_script_dir, "scheduler.log")

# 确保日志目录存在
os.makedirs(log_dir_train, exist_ok=True)
os.makedirs(log_dir_param, exist_ok=True)

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建文件处理器，使用绝对路径
file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
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
param_opt_executed = False  # 记录本周参数优化任务是否执行

# 开发模式：添加命令行参数解析
run_param_optimization_now = "--run-param-now" in sys.argv  # 检查是否有立即运行参数优化的参数
run_training_now = "--run-train-now" in sys.argv  # 检查是否有立即运行训练的参数

# 动态构建脚本路径，基于当前脚本的位置
auto_pre_train_script = os.path.join(current_script_dir, "auto_pre_train.py")
param_optimizer_script = os.path.join(current_script_dir, "param_optimizer.py")
logging.info(f"auto_pre_train脚本路径: {auto_pre_train_script}")
logging.info(f"param_optimizer脚本路径: {param_optimizer_script}")

# 根据操作系统动态确定 Python 解释器路径和Conda环境
def get_python_interpreter():
    if sys.platform.startswith('linux'):
        # 假设在 Linux/Docker 环境中，使用固定的 Conda 环境路径
        conda_env_path = "/opt/conda/envs/wind-power-env"
        logging.info(f"检测到 Linux/Docker 环境，使用Conda环境: {conda_env_path}")
        return conda_env_path, f"conda run -p {conda_env_path} python"
    elif sys.platform.startswith('win'):
        # 在 Windows 开发环境中，尝试使用当前激活的Conda环境
        if 'CONDA_PREFIX' in os.environ:
            conda_env_path = os.environ['CONDA_PREFIX']
            logging.info(f"检测到 Windows 环境，使用当前激活的Conda环境: {conda_env_path}")
            return conda_env_path, f"conda run -p {conda_env_path} python"
        else:
            # 如果没有激活Conda环境，使用当前Python解释器
            logging.info(f"检测到 Windows 环境，但未找到激活的Conda环境，使用当前Python解释器: {sys.executable}")
            return None, sys.executable
    elif sys.platform.startswith('darwin'):
        # macOS环境，与Windows类似处理
        if 'CONDA_PREFIX' in os.environ:
            conda_env_path = os.environ['CONDA_PREFIX']
            logging.info(f"检测到 macOS 环境，使用当前激活的Conda环境: {conda_env_path}")
            return conda_env_path, f"conda run -p {conda_env_path} python"
        else:
            logging.info(f"检测到 macOS 环境，但未找到激活的Conda环境，使用当前Python解释器: {sys.executable}")
            return None, sys.executable
    else:
        # 其他未知操作系统，使用系统默认Python
        logging.warning(f"未知的操作系统平台 '{sys.platform}'，尝试使用系统默认Python")
        return None, "python"

# 获取适用于当前平台的Python解释器命令
conda_env_path, python_cmd = get_python_interpreter()
logging.info(f"将使用以下命令执行Python脚本: {python_cmd}")

# 使用subprocess执行命令的辅助函数
def run_command(command):
    """
    使用subprocess执行命令，捕获输出并记录状态
    
    Args:
        command: 要执行的命令列表或字符串
    
    Returns:
        bool: 命令是否成功（返回码为0）
        int: 命令的返回码
    """
    logging.info(f"执行命令: {command}")
    try:
        # 如果是字符串命令，我们需要设置shell=True
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, text=True, 
                                   capture_output=True, check=False)
        else:
            result = subprocess.run(command, text=True, 
                                   capture_output=True, check=False)
        
        # 记录标准输出和错误
        if result.stdout:
            logging.info(f"命令输出: {result.stdout}")
        if result.stderr:
            logging.warning(f"命令错误: {result.stderr}")
            
        # 检查返回状态
        if result.returncode == 0:
            logging.info(f"命令执行成功，返回码: {result.returncode}")
            return True, result.returncode
        else:
            logging.error(f"命令执行失败，返回码: {result.returncode}")
            return False, result.returncode
    except Exception as e:
        logging.error(f"执行命令时发生异常: {str(e)}")
        return False, -1

def get_train_flag_file(date_str):
    """获取训练完成标志文件的路径"""
    return os.path.join(log_dir_train, f"{date_str}_train_done.flag")

def is_train_done(date_str):
    """检查指定日期的训练是否已完成"""
    flag_file = get_train_flag_file(date_str)
    if os.path.exists(flag_file):
        logging.info(f"检测到{date_str}的训练已经执行过 (标志文件: {flag_file})")
        return True
    return False

def get_predict_flag_file(date_str):
    """获取预测完成标志文件的路径"""
    return os.path.join(log_dir_train, f"{date_str}_predict_done.flag")

def is_predict_done(date_str):
    """检查指定日期的预测是否已完成"""
    flag_file = get_predict_flag_file(date_str)
    if os.path.exists(flag_file):
        logging.info(f"检测到{date_str}的预测已经执行过 (标志文件: {flag_file})")
        return True
    return False

def get_param_opt_flag_file():
    """获取本周参数优化标志文件的路径"""
    # 获取当前日期
    today = datetime.now()
    # 计算本周的周一日期（作为标识符）
    monday = today - timedelta(days=today.weekday())
    monday_str = monday.strftime('%Y%m%d')
    # 返回标志文件路径
    return os.path.join(log_dir_param, f"{monday_str}_param_opt_done.flag")

def is_param_opt_done():
    """检查本周是否已经完成参数优化"""
    flag_file = get_param_opt_flag_file()
    if os.path.exists(flag_file):
        logging.info(f"检测到本周参数优化已经执行过 (标志文件: {flag_file})")
        return True
    return False

def run_script():
    global task_executed
    
    # 检查今天的训练和预测是否都已完成
    today_date = datetime.now().strftime('%Y%m%d')
    train_done = is_train_done(today_date)
    predict_done = is_predict_done(today_date)
    
    if train_done and predict_done:
        logging.info(f"今天({today_date})的训练和预测都已执行过，无需重复执行")
        if not task_executed: # Update status if not already set for this scheduler run
            task_executed = True
            logging.info("任务状态更新为已执行 (基于标志文件)")
        return
    
    # --- Check task_executed *before* proceeding ---
    # 如果在本轮调度器运行中已经尝试执行过，则跳过
    if task_executed:
        logging.info("检测到任务已在本次调度器运行中尝试执行，跳过")
        return
    # ----------------------------------------------
    
    # 如果到达这里，说明标志文件显示任务未完成，且本轮调度器尚未执行过

    logging.info("执行 auto_pre_train.py")
        
    # --- Set flag *before* running --- 
    # 标记任务已尝试执行，防止在本轮调度中重复启动
    task_executed = True
    logging.info("标记当天任务为正在执行/已尝试执行...")
    # ---------------------------------
    
    # 使用动态构建的脚本路径
    logging.info(f"使用脚本路径: {auto_pre_train_script}")
        
    # 使用动态确定的Python命令
    command = f"{python_cmd} {auto_pre_train_script}"
        
    # 使用辅助函数执行命令
    success, exit_code = run_command(command)
        
    if success:
        logging.info("auto_pre_train.py 执行成功")
    # task_executed is already True
    else:
        logging.error(f"auto_pre_train.py 执行失败，退出码: {exit_code}")
    # Keep task_executed as True to prevent immediate re-run by the same scheduler instance.
    # The flag will be reset at midnight.

def run_param_optimizer():
    """运行参数优化脚本"""
    global param_opt_executed
    
    # 检查本周的参数优化是否已完成
    if is_param_opt_done():
        logging.info("本周的参数优化已执行过，无需重复执行")
        param_opt_executed = True
        return
    
    if not param_opt_executed:
        logging.info("开始执行参数优化任务")
        
        # 使用动态构建的脚本路径
        logging.info(f"使用脚本路径: {param_optimizer_script}")
        
        # 使用动态确定的Python命令
        command = f"{python_cmd} {param_optimizer_script}"
        
        # 使用辅助函数执行命令
        success, exit_code = run_command(command)
        
        if success:
            logging.info("参数优化任务执行成功")
            param_opt_executed = True  # 标记本周任务已执行
        else:
            logging.error(f"参数优化任务执行失败，退出码: {exit_code}")

# 每天 2:00 执行训练预测任务
schedule.every().day.at("02:00").do(run_script)

# 每周四 1:00 执行参数优化任务
#schedule.every().thursday.at("01:00").do(run_param_optimizer)

logging.info("定时任务启动成功，每天 2:00 运行 auto_pre_train.py")

# 记录当前时间和状态
now = datetime.now()
current_weekday = now.weekday()
weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
today_date = now.strftime('%Y%m%d')

logging.info(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}, 星期: {weekday_names[current_weekday]}")
logging.info(f"当前任务状态: 训练预测任务已执行={is_train_done(today_date)}, 参数优化任务已执行={is_param_opt_done()}")

# 开发模式：根据命令行参数立即执行任务
if run_param_optimization_now:
    logging.info("收到立即执行参数优化的命令，准备立即执行")
    run_param_optimizer()

if run_training_now:
    logging.info("收到立即执行训练的命令，准备立即执行")
    run_script()

while True:
    try:
        # 运行定时任务
        schedule.run_pending()

        # 获取当前时间
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        current_weekday = now.weekday()  
        today_date = now.strftime('%Y%m%d')

        # 每小时记录一次状态（当分钟为0时）
        if current_minute == 0:
            logging.info(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}, 星期: {weekday_names[current_weekday]}")
            logging.info(f"当前任务状态: 训练预测任务已执行={is_train_done(today_date)}, 参数优化任务已执行={is_param_opt_done()}")

        # 处理参数优化任务的运行监控（对周五进行监控）
        if current_weekday == 3 and current_hour >= 1: 
            if not param_opt_executed and not is_param_opt_done():
                logging.warning("检测到周四 1:00 参数优化未执行，立即补救运行")
                run_param_optimizer()
            elif not param_opt_executed and is_param_opt_done():
                logging.info("发现本周参数优化已执行过，更新任务状态")
                param_opt_executed = True
        
        # 检查每日训练任务
        if current_hour >= 3:
            train_done = is_train_done(today_date)
            predict_done = is_predict_done(today_date)
            
            if not task_executed and (not train_done or not predict_done):
                if not train_done and not predict_done:
                    logging.warning("检测到 3:00 训练和预测均未执行，立即补救运行 auto_pre_train.py")
                elif not train_done:
                    logging.warning("检测到 3:00 训练未执行，立即补救运行 auto_pre_train.py")
                else:
                    logging.warning("检测到 3:00 预测未执行，立即补救运行 auto_pre_train.py")
                run_script()
            elif not task_executed and train_done and predict_done:
                logging.info("发现今天训练和预测都已执行过，更新任务状态")
                task_executed = True

        # 到了周五凌晨，重置参数优化任务状态（为下周做准备）
        if current_weekday == 3 and current_hour == 0 and current_minute == 0:
            param_opt_executed = False
            logging.info("重置每周参数优化任务状态")

        # 到了凌晨，重置日常任务状态
        if current_hour == 0 and current_minute == 0:
            task_executed = False  # 第二天任务重新开始
            logging.info("任务状态已重置，准备执行新一天的任务")

        time.sleep(30)  # 每 30 秒检查一次

    except Exception as e:
        logging.error(f"运行时发生错误: {e}")
        time.sleep(60)  # 遇到错误时等待 60 秒再继续
