import schedule
import time
import os
import logging
import sys
from datetime import datetime, timedelta

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建文件处理器
file_handler = logging.FileHandler("scheduler.log", encoding="utf-8")
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

# 定义日志目录路径
log_dir_train = "./logs/auto_pre_train"
log_dir_param = "./logs/param_optimizer"

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
        task_executed = True
        return
    
    if train_done:
        logging.info(f"今天({today_date})的训练已执行，但预测尚未完成")
    elif predict_done:
        logging.info(f"今天({today_date})的预测已执行，但训练尚未完成")
    
    if not task_executed:
        logging.info("执行 auto_pre_train.py")
        # 使用 subprocess 以更好地控制子进程
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        print(current_dir)
        # 构建 auto_pre_train.py 的绝对路径
        script_path = os.path.normpath(os.path.join(current_dir, "auto_pre_train.py"))
        print(script_path)
        # 构建 conda 环境路径（相对路径）
        conda_env_path = os.path.normpath(os.path.join(current_dir, "..", "..", "..", "env"))
        print(conda_env_path)
        # 跨平台执行命令
        command = (
            f"conda run -p {conda_env_path} python {script_path}"
            if os.name == 'nt'  # Windows
            else f"conda run -p {conda_env_path.replace(os.sep, '/')} python {script_path.replace(os.sep, '/')}"
        )
        
        exit_code = os.system(command)
        if exit_code == 0:
            logging.info("auto_pre_train.py 执行成功")
            task_executed = True  # 标记当天任务已执行
        else:
            logging.error(f"auto_pre_train.py 执行失败，退出码: {exit_code}")

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
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建参数优化脚本路径
        optimizer_path = os.path.normpath(os.path.join(current_dir, "param_optimizer.py"))
        # 构建conda环境路径
        conda_env_path = os.path.normpath(os.path.join(current_dir, "..", "..", "..", "env"))
        
        # 跨平台执行命令
        command = (
            f"conda run -p {conda_env_path} python {optimizer_path}"
            if os.name == 'nt'  # Windows
            else f"conda run -p {conda_env_path.replace(os.sep, '/')} python {optimizer_path.replace(os.sep, '/')}"
        )
        
        exit_code = os.system(command)
        if exit_code == 0:
            logging.info("参数优化任务执行成功")
            param_opt_executed = True  # 标记本周任务已执行
        else:
            logging.error(f"参数优化任务执行失败，退出码: {exit_code}")

# 每天 2:00 执行训练预测任务
schedule.every().day.at("02:00").do(run_script)

# 每周四 1:00 执行参数优化任务
schedule.every().thursday.at("01:00").do(run_param_optimizer)

logging.info("定时任务启动成功，每周四 1:00 运行参数优化，每天 2:00 运行 auto_pre_train.py")

# 记录当前时间和状态
now = datetime.now()
current_weekday = now.weekday()
weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
today_date = now.strftime('%Y%m%d')

# 确保日志目录存在
os.makedirs(log_dir_train, exist_ok=True)
os.makedirs(log_dir_param, exist_ok=True)

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
        if current_hour >= 2:
            train_done = is_train_done(today_date)
            predict_done = is_predict_done(today_date)
            
            if not task_executed and (not train_done or not predict_done):
                if not train_done and not predict_done:
                    logging.warning("检测到 2:00 训练和预测均未执行，立即补救运行 auto_pre_train.py")
                elif not train_done:
                    logging.warning("检测到 2:00 训练未执行，立即补救运行 auto_pre_train.py")
                else:
                    logging.warning("检测到 2:00 预测未执行，立即补救运行 auto_pre_train.py")
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
