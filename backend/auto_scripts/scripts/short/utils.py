# utils.py

import matplotlib
# 设置后端为 Agg 以避免使用 Tkinter
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from config import Today

def visualize_results(results_dict, y_val, output_path):
    """
    可视化不同模型的预测结果与实际值
    """
    plt.figure(figsize=(20, 10))
    for model_name, result in results_dict.items():
        plt.plot(range(len(result['y_pred'])), result['y_pred'], label=f'{model_name} Predicted Power')
    
    plt.plot(range(len(y_val)), y_val, label='Actual Power', linestyle='dashed')
    plt.xlabel('Index')
    plt.ylabel('Power')
    plt.title('Verify set power predictions - Different LightGBM Models')
    plt.legend()
    
    # 确保输出目录存在
    output_dir = os.path.join(output_path, Today)
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存图像
    output_file = os.path.join(output_dir, 'Predictions.png')
    plt.savefig(output_file)
    plt.close()  # 关闭图表以释放资源
    print(f"图像已保存为 {output_file}")
          