import schedule
import time
import os
import logging
from datetime import datetime

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

# 任务状态
task_executed = False  # 记录当天任务是否成功执行

def run_script():
    global task_executed
    if not task_executed:
        logging.info("执行 auto_pre_train.py")
        # 使用 subprocess 以更好地控制子进程
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 构建 auto_pre_train.py 的绝对路径
        script_path = os.path.normpath(os.path.join(current_dir, "auto_pre_train.py"))
        # 构建 conda 环境路径（相对路径）
        conda_env_path = os.path.normpath(os.path.join(current_dir, "..", "..", "env"))
        
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

# 每天 8:30 计划执行
schedule.every().day.at("01:00").do(run_script)

logging.info("定时任务启动成功，每天 1:00 运行 auto_pre_train.py")

while True:
    try:
        # 运行定时任务
        schedule.run_pending()

        # 获取当前时间
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute

        if 1 <= current_hour:
            if not task_executed:
                logging.warning("检测到 1:00 未执行，立即补救运行 auto_pre_train.py")
                run_script()

        # 到了第二天凌晨，重置任务状态
        if current_hour == 0 and current_minute == 0:
            task_executed = False  # 第二天任务重新开始
            logging.info("任务状态已重置，准备执行新一天的任务")

        time.sleep(30)  # 每 10 秒检查一次

    except Exception as e:
        logging.error(f"运行时发生错误: {e}")
        time.sleep(60)  # 遇到错误时等待 60 秒再继续
