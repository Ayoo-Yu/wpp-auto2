import os
import glob
import pygrib
import csv
import datetime
# 获取当前日期和时间
now = datetime.datetime.now()
# 提取年份
year = now.year
# ================================
# 1. 参数设定
# ================================
# 包含多个以预测起报时刻命名的文件夹的根目录
root_folder = f'D:\\my-vue-project\\wind-power-forecast\\backend\\auto_scripts\\hust_scripts\\ecdata\\{year}'
# CSV 输出目录，处理后的结果会保存在 output_dir 下对应的子文件夹内
output_dir = f"D:\\my-vue-project\\wind-power-forecast\\backend\\auto_scripts\\hust_scripts\\csv_output\\{year}"
os.makedirs(output_dir, exist_ok=True)

# 记录已处理文件夹名称的 txt 文件路径
processed_record_file = os.path.join(output_dir, "processed_folders.txt")

# 读取已经处理的文件夹名称
if os.path.exists(processed_record_file):
    with open(processed_record_file, 'r', encoding='utf-8') as f:
        processed_folders = set(line.strip() for line in f if line.strip())
else:
    processed_folders = set()

# ================================
# 2. 解析预测有效时刻的函数
# ================================
def extract_valid_time(filename):
    """
    根据给定文件命名规则，从文件名中提取预测有效时刻，并转换为便于排序的元组。
    假设文件命名格式为：
        A1S{起报时刻}{其他部分}
    其中有效时刻位于文件名的索引 11 到 17（6位数字，格式为 MMDDHH），如：
        "A1S01010600010113001.grib" -> filename[11:17] == "010113"
    返回：(month, day, hour) 例如 (1, 1, 13)
    """
    try:
        valid_str = filename[11:17]
        month = int(valid_str[0:2])
        day   = int(valid_str[2:4])
        hour  = int(valid_str[4:6])
        return (month, day, hour)
    except Exception as e:
        print(f"解析文件 {filename} 的预测时刻失败: {e}")
        # 出问题时返回一个较大的元组，使其排在最后
        return (99, 99, 99)

# ================================
# 3. 遍历所有子文件夹进行处理
# ================================
# 遍历 root_folder 下的每个子文件夹
for folder_name in os.listdir(root_folder):
    folder_path = os.path.join(root_folder, folder_name)
    if not os.path.isdir(folder_path):
        continue

    # 如果该文件夹已经处理过，则跳过
    if folder_name in processed_folders:
        print(f"文件夹 {folder_name} 已处理，跳过。")
        continue

    print(f"开始处理文件夹 {folder_name} ...")

    # 在输出目录中为该文件夹创建对应的子目录
    output_subfolder = os.path.join(output_dir, folder_name)
    os.makedirs(output_subfolder, exist_ok=True)

    # 获取该文件夹下所有 grib 文件
    all_grib_files = glob.glob(os.path.join(folder_path, '*.grib'))
    if not all_grib_files:
        print(f"文件夹 {folder_name} 下没有找到 grib 文件，跳过。")
        # 记录为已处理，也可以选择不记录
        processed_folders.add(folder_name)
        with open(processed_record_file, 'a', encoding='utf-8') as f:
            f.write(folder_name + "\n")
        continue

    # 根据预测有效时刻对文件进行排序
    sorted_files = sorted(all_grib_files, key=lambda f: extract_valid_time(os.path.basename(f)))
    print(f"{folder_name} 中找到 {len(sorted_files)} 个 grib 文件，排序结果如下：")
    for f in sorted_files:
        print(os.path.basename(f), extract_valid_time(os.path.basename(f)))

    # ================================
    # 4. 解析 grib 文件并提取特征数据
    # ================================
    # 建立一个字典，存放各特征数据：
    # key: 特征标识 (例如 shortName)
    # value: 每个元素为一个列表，列表内第一项为预测时刻字符串，其余为该时刻对应的数值列表
    features_data = {}

    for grib_file in sorted_files:
        # 若打开文件失败，则跳过
        try:
            grbs = pygrib.open(grib_file)
        except Exception as e:
            print(f"无法打开 {grib_file} : {e}")
            continue

        # 从文件名中提取预测有效时刻，转换为字符串，如 "01-01 13:00"
        valid_time_tuple = extract_valid_time(os.path.basename(grib_file))
        valid_time_str = f"{valid_time_tuple[0]:02d}-{valid_time_tuple[1]:02d} {valid_time_tuple[2]:02d}:00"

        for grb in grbs:
            # 仅处理包含二维数据的消息（即具备 values 属性的消息）
            if not hasattr(grb, 'values'):
                continue

            # 将 grb 中的数据作为一个特征，用 shortName 作为标识（根据需要可修改为其它属性）
            feature = grb.shortName

            # 获取二维数据，并转换为一维列表（如果不希望 flatten，则需考虑二维数据存储方式）
            data_flat = grb.values.flatten().tolist()
            # 在数据前面加入预测时刻信息
            row = [valid_time_str] + data_flat

            # 如果字典中没有该特征，初始化为列表
            if feature not in features_data:
                features_data[feature] = []
            features_data[feature].append(row)

        grbs.close()

    # ================================
    # 5. 将各特征数据写入 CSV 文件
    # ================================
    for feature, rows in features_data.items():
        # CSV 文件命名可采用特征名称，如 "H.csv"、"T.csv" 等
        csv_filename = os.path.join(output_subfolder, f"{feature}.csv")
        try:
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # 写入表头，第一列为 "预测有效时刻"，后续列名以 "值1", "值2", … 标识
                n_values = len(rows[0]) - 1  # 第一项为预测有效时刻
                header = ['Timestamp'] + [f"point{i}" for i in range(1, n_values+1)]
                writer.writerow(header)
                # 写入所有数据行
                for row in rows:
                    writer.writerow(row)
            print(f"特征 {feature} 的 CSV 文件 {csv_filename} 写入成功，共 {len(rows)} 行数据。")
        except Exception as e:
            print(f"写入 {csv_filename} 时出错: {e}")

    # 将处理完成的文件夹名称追加写入记录文件
    with open(processed_record_file, 'a', encoding='utf-8') as f:
        f.write(folder_name + "\n")
    processed_folders.add(folder_name)
    print(f"文件夹 {folder_name} 处理完毕。\n")
    
print("所有文件夹处理结束。")
