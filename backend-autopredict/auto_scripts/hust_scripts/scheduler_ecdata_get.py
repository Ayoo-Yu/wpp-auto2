import os
import schedule
import time
import os
import logging

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建文件处理器
file_handler = logging.FileHandler("D:\\my-vue-project\\wind-power-forecast\\backend\\auto_scripts\\hust_scripts\\scheduler_ecdata_get.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)

# 定义日志格式
formatter = logging.Formatter("%(asctime)s - %(message)s")
file_handler.setFormatter(formatter)

# 将处理器添加到日志记录器
logger.addHandler(file_handler)

def run_script():
    logging.info("执行 ecdata_get.py")
    # 使用 subprocess 以更好地控制子进程
    exit_code = os.system(
        "conda activate D:\\my-vue-project\\wind-power-forecast\\backend\\env && python D:\\my-vue-project\\wind-power-forecast\\backend\\auto_scripts\\hust_scripts\\ecdata_get.py"
    )
    if exit_code == 0:
        logging.info("ecdata_get.py 执行成功")
    else:
        logging.error(f"ecdata_get.py 执行失败，退出码: {exit_code}")
    exit_code0 = os.system(
        "conda activate D:\\anaconda3\\envs\\wpprediction && python D:\\my-vue-project\\wind-power-forecast\\backend\\auto_scripts\\hust_scripts\\dataset_process.py"
    )
    if exit_code0 == 0:
        logging.info("dataset_process.py 执行成功")
    else:
        logging.error(f"dataset_process.py 执行失败，退出码: {exit_code0}")

# 每天 8:30 计划执行
schedule.every().day.at("03:00").do(run_script)
schedule.every().day.at("08:30").do(run_script)
schedule.every().day.at("15:00").do(run_script)
schedule.every().day.at("20:30").do(run_script)

while True:
    try:
        # 运行定时任务
        schedule.run_pending()
        print('运行脚本中！')
        time.sleep(10)  # 每 10 秒检查一次

    except Exception as e:
        logging.error(f"运行时发生错误: {e}")
        time.sleep(10)  # 遇到错误时等待 60 秒再继续
