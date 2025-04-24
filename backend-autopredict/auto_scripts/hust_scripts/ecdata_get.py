import paramiko
import time
import os

# ===== 配置参数 =====
REMOTE_HOST = '49.232.246.73'    # 例如 '123.45.67.89'
REMOTE_PORT = 22                 # 一般为22，如果有变化请修改
USERNAME = 'root'
PASSWORD = 'yzz0216yhAAAA'
REMOTE_DIR = '/ECMWF/data_hn'    # 远程目录路径
import datetime
# 获取当前日期和时间
now = datetime.datetime.now()
# 提取年份
year = now.year

# 本地存放文件的根目录，下载后文件会在此目录下按子文件夹分类存放
LOCAL_DIR = f'D:\\my-vue-project\\wind-power-forecast\\backend\\auto_scripts\\hust_scripts\\ecdata\\{year}'  
RECORD_FILE = 'D:\\my-vue-project\\wind-power-forecast\\backend\\auto_scripts\\hust_scripts\\downloaded_files.txt'  # 持久化记录文件

# 设置轮询检查时间间隔（单位：秒）
POLL_INTERVAL = 600

def load_downloaded_files():
    """从本地记录文件中加载已下载文件名集合。"""
    if os.path.exists(RECORD_FILE):
        with open(RECORD_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_downloaded_file(filename):
    """将新下载或处理的文件名追加到记录文件中。"""
    with open(RECORD_FILE, 'a', encoding='utf-8') as f:
        f.write(filename + '\n')

def process_legacy_files(downloaded_files):
    """
    处理遗留文件：
      检查本地存放目录（根目录）中是否存在已经下载但未进行分类、命名及记录的文件，
      若存在则提取文件名中的时间信息，将其移动至对应子文件夹，同时添加 .grib 后缀，
      并记录该文件已处理。
    """
    # 列举 LOCAL_DIR 根目录下的文件（仅处理文件，不递归处理子目录中已分类的文件）
    for item in os.listdir(LOCAL_DIR):
        full_path = os.path.join(LOCAL_DIR, item)
        if os.path.isfile(full_path):
            # 如果该文件已经在记录中，则跳过
            if item in downloaded_files:
                continue

            # 判断是否已经加上 .grib 后缀
            has_suffix = item.endswith('.grib')
            # 原始文件名（记录用）我们认为下载时的文件名没有 .grib 后缀
            original_name = item if not has_suffix else item[:-5]
            
            # 根据文件名长度和格式提取分类信息（示例中提取索引 3 到 9 的子串）
            if len(original_name) >= 9:
                subfolder = original_name[3:9]
            else:
                subfolder = "others"

            target_folder = os.path.join(LOCAL_DIR, subfolder)
            if not os.path.exists(target_folder):
                os.makedirs(target_folder)
            
            # 如果文件还没有加后缀，则在文件名后追加 .grib；否则保持现有文件名不变
            if not has_suffix:
                new_name = original_name + ".grib"
            else:
                new_name = item
            target_filepath = os.path.join(target_folder, new_name)
            
            try:
              os.rename(full_path, target_filepath)
              if os.path.exists(target_filepath):
                  print(f"处理遗留文件: {item} -> {target_filepath}")
                  downloaded_files.add(original_name)
                  save_downloaded_file(original_name)
              else:
                  print(f"文件 {target_filepath} 不存在，处理失败")
            except Exception as e:
              print(f"处理遗留文件 {item} 失败: {e}")


def download_new_files():
    """
    建立SFTP连接，检查远程目录中新上传的文件，并下载到本地指定目录。
    使用持久化记录文件来避免重复下载已下载的文件。
    
    新增功能：
      1. 下载时自动给所有文件加上 .grib 后缀。
      2. 根据文件名中编码的生成时间进行分类存放，
         例如文件名 “A1D01010000010100011”：截取索引 3 到 9 得到 "010100"，表示1月1日00时，
         则该文件存放到 LOCAL_DIR/010100/ 目录下。
      3. 程序启动后，先检查本地是否存在未分类命名但已下载的遗留文件，先进行处理和记录。
    """
    # 加载之前已下载的文件集合（持久化方式）
    downloaded_files = load_downloaded_files()
    print('加载加载之前已下载的文件集合')
    # 如果本地根目录不存在，则创建之
    if not os.path.exists(LOCAL_DIR):
        os.makedirs(LOCAL_DIR)


    process_legacy_files(downloaded_files)
    print('遗留文件处理完成')
    try:
        # 建立Transport连接
        transport = paramiko.Transport((REMOTE_HOST, REMOTE_PORT))
        transport.connect(username=USERNAME, password=PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)
        print('远程连接成功')
        
        # 获取远程目录下的文件列表
        remote_files = sftp.listdir(REMOTE_DIR)
        if remote_files:
            print('获取文件列表成功')
        
        for filename in remote_files:
            # 如果该文件之前未下载（或未处理遗留文件），则执行下载
            if filename not in downloaded_files:
                remote_filepath = REMOTE_DIR.rstrip('/') + '/' + filename
                # 先下载到 LOCAL_DIR 根目录下
                local_filepath = os.path.join(LOCAL_DIR, filename)
                
                try:
                    sftp.get(remote_filepath, local_filepath)
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 下载文件: {filename} 到 {local_filepath}")
                    
                    # ===== 新增处理：分类和重命名 =====
                    # 根据示例，假设文件名结构为: 固定前三位 + 6位时间信息 + 其他内容，
                    # 如 "A1D01010000010100011" 中，filename[3:9] 得到 "010100"
                    if len(filename) >= 9:
                        subfolder = filename[3:9]
                    else:
                        subfolder = "others"
                    
                    target_folder = os.path.join(LOCAL_DIR, subfolder)
                    if not os.path.exists(target_folder):
                        os.makedirs(target_folder)
                    
                    # 拼接新的文件名，加上 .grib 后缀
                    new_file_name = filename + ".grib"
                    target_filepath = os.path.join(target_folder, new_file_name)
                    
                    # 将文件移动到分类目录下并重命名
                    os.rename(local_filepath, target_filepath)
                    print(f"文件已重命名并移至: {target_filepath}")
                    # ===== 处理结束 =====
                    
                    # 更新已下载记录（内存和持久化文件）
                    downloaded_files.add(filename)
                    save_downloaded_file(filename)
                except Exception as e:
                    print(f"下载文件 {filename} 失败: {e}")
        print('目前所有数据已经获取')
        # 关闭SFTP连接
        sftp.close()
        transport.close()
    except Exception as e:
        print(f"连接或操作过程中发生错误: {e}")
if __name__ == "__main__":
    download_new_files()
