import os
import shutil
from datetime import datetime
import schedule
import time

# 配置源文件路径
SOURCE_FILE_1 = "train_test.csv"  # 替换为实际路径
SOURCE_FILE_2 = "pre_test.csv"  # 替换为实际路径
SOURCE_FILE_3 = "pre_supershort_test.csv"  # 替换为实际路径

# 配置目标路径
DEST_PATHS_A = r"D:\my-vue-project\wind-power-forecast\backend\auto_scripts\dataset\dataset_supershort" 
DEST_PATHS_B = r"D:\my-vue-project\wind-power-forecast\backend\auto_scripts\dataset\dataset_short" 
DEST_PATHS_C = r"D:\my-vue-project\wind-power-forecast\backend\auto_scripts\dataset\dataset_middle" 

DEST_PATHS_D_E = [
    r"D:\my-vue-project\wind-power-forecast\backend\auto_scripts\precsv\shortcsv",
    r"D:\my-vue-project\wind-power-forecast\backend\auto_scripts\precsv\middlecsv"
]  # 替换为实际路径

DEST_PATH_F = r"D:\my-vue-project\wind-power-forecast\backend\auto_scripts\precsv\supershortcsv"  # 替换为实际路径

def rename_and_move_file(source, dest_paths, new_name_format):
    Today = datetime.now().strftime('%Y%m%d')
    try:
        now = datetime.now()
        if new_name_format == "date":
            new_name = now.strftime("%Y%m%d") + ".csv"
        elif new_name_format == "datetime":
            new_name = now.strftime("%Y%m%d%H%M") + ".csv"
        else:
            print("指定的名称格式无效。")
            return
        new_file_path = os.path.join(os.path.dirname(source), new_name)
        # 重命名文件（移动到新的名称）
        shutil.copy(source, new_file_path)
        print(f"文件已重命名并移动为: {new_file_path}")

        # 复制或移动到目标路径
        for path in dest_paths:
            # 确保目标目录存在
            os.makedirs(path, exist_ok=True)
            # 移动文件到目标路径
            if new_name_format == "date":
                dest_file_path = os.path.join(path, new_name)
            else:
                path0 = os.path.join(path,Today)
                os.makedirs(path0, exist_ok=True)
                dest_file_path = os.path.join(path0,new_name)
            shutil.copy(new_file_path, dest_file_path)
            print(f"已移动到: {dest_file_path}")
        os.remove(new_file_path)
    except Exception as e:
        print(f"在重命名和移动文件时发生错误: {e}")

def task_daily_0010():
    print("执行每日0:10的任务")
    rename_and_move_file(SOURCE_FILE_1, [DEST_PATHS_A], "date")

def task_daily_0020():
    print("执行每日0:20的任务")
    rename_and_move_file(SOURCE_FILE_1, [DEST_PATHS_B], "date")

def task_daily_0030():
    print("执行每日0:30的任务")
    rename_and_move_file(SOURCE_FILE_1, [DEST_PATHS_C], "date")

def task_daily_0830():
    print("执行每日8:30的任务")
    rename_and_move_file(SOURCE_FILE_2, DEST_PATHS_D_E, "date")

def task_every_15min():
    now = datetime.now()
    # 确保分钟是00,15,30,45
    if now.minute % 15 == 0:
        print("执行每2分钟的任务")
        rename_and_move_file(SOURCE_FILE_3, [DEST_PATH_F], "datetime")
    else:
        print("当前时间不在指定的分钟范围内，跳过任务")

# 安排任务
# schedule.every().day.at("00:30").do(task_daily_0030)  # 修改为正确的时间格式
# schedule.every().day.at("08:30").do(task_daily_0830)
schedule.every().day.at("00:10").do(task_daily_0010)
schedule.every().day.at("00:20").do(task_daily_0020)
schedule.every().day.at("00:30").do(task_daily_0030)
schedule.every().day.at("08:30").do(task_daily_0830)
schedule.every(10).seconds.do(task_every_15min)  # 每分钟检查一次

def main():
    print("任务调度脚本已启动")
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    main()
