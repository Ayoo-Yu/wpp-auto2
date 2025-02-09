import os
import pandas as pd
from flask import Blueprint, request, jsonify, current_app, send_file
import glob
import datetime
import shutil
from services.file_service import find_file_by_id
from services.modeltrain_service import run_modeltrain
from services.evaluation_service import run_evaluation
from werkzeug.utils import secure_filename
# 预测蓝图
modeltrain_bp = Blueprint('modeltrain', __name__)

@modeltrain_bp.route('/modeltrain', methods=['POST'])
def modeltrain():
    data = request.get_json()
    current_app.logger.info(f"收到模型训练请求: {data}")
    if not data or 'file_id' not in data or 'model' not in data or 'wfcapacity' not in data:
        current_app.logger.warning("缺少训练数据集或模型参数")
        return jsonify({'error': "缺少 'file_id' 或 'model' 参数"}), 400

    file_id = data['file_id']
    model = data['model']
    wfcapacity = pd.to_numeric(data['wfcapacity'])
    current_app.logger.info(f"训练集id: {file_id}, 模型选择: {model}, 装机容量: {wfcapacity},类型: {type(wfcapacity)}")

    upload_path = find_file_by_id(file_id, current_app.config['UPLOAD_FOLDER'])
    if not upload_path:
        current_app.logger.warning(f"没有找到对应id的训练集: {file_id}")
        return jsonify({'error': '无效的 file_id'}), 400

    # 运行预测与后处理
    try:
        forecast_file_path = run_modeltrain(upload_path, model)
    except Exception as e:
        current_app.logger.error(f"预测过程中出错: {e}")
        return jsonify({'error': '预测过程中出错', 'details': str(e)}), 500

    if not isinstance(forecast_file_path, str) or not os.path.isfile(forecast_file_path):
        current_app.logger.error("预测时没有返回可用的文件路径")
        return jsonify({'error': '预测文件生成失败'}), 500

    # 保存预测结果到 DOWNLOAD_FOLDER
    forecast_timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename_wo_ext = os.path.splitext(os.path.basename(upload_path))[0]
    output_filename = f"forecast_{filename_wo_ext}_{forecast_timestamp_str}.csv"
    output_path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], output_filename)

    try:
        shutil.copy(forecast_file_path, output_path)
        current_app.logger.info(f"将原生预测文件复制到以下路径： {output_path}")
    except Exception as e:
        current_app.logger.error(f"无法保存预测结果文件: {e}")
        return jsonify({'error': '无法保存预测结果文件', 'details': str(e)}), 500

    # 评估模型
    try:
        evaluation_output_dir = os.path.join(current_app.config['DOWNLOAD_FOLDER'], f"evaluation_{filename_wo_ext}_{forecast_timestamp_str}")
        evaluation_result, report_path = run_evaluation(output_path, evaluation_output_dir, wfcapacity=wfcapacity)
        current_app.logger.info(f"测试集评估完成。相关结果保存在以下路径：{evaluation_output_dir}")
    except Exception as e:
        current_app.logger.error(f"模型评估过程中出错: {e}")
        return jsonify({'error': '模型评估过程中出错', 'details': str(e)}), 500

    # 准备报告下载链接（如果存在）
    if report_path and os.path.exists(report_path):
        report_output_filename = f"report_{filename_wo_ext}_{forecast_timestamp_str}.txt"
        report_output_path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], report_output_filename)
        try:
            shutil.copy(report_path, report_output_path)
            current_app.logger.info(f"将原生报告复制到以下路径： {report_output_path}")
            report_download_url = f"/download/{secure_filename(report_output_filename)}"
        except Exception as e:
            current_app.logger.error(f"无法保存评估报告文件: {e}")
            return jsonify({'error': '无法保存评估报告文件', 'details': str(e)}), 500
    else:
        report_download_url = None

    download_url = f"/download/{secure_filename(output_filename)}"
    current_app.logger.info(f"预测文件下载url为: {download_url}")
    current_app.logger.info(f"训练报告下载url为: {report_download_url}")

    return jsonify({
        'download_url': download_url,
        'report_download_url': report_download_url
    }), 200

# 新增接口：获取 daily_metrics.csv 文件
@modeltrain_bp.route('/get-daily-metrics', methods=['GET'])
def get_daily_metrics():
    file_id = request.args.get('file_id')
    if not file_id:
        return jsonify({'error': '缺少 file_id 参数'}), 400

    # 假设动态目录为 evaluation_output_dir
    upload_path = find_file_by_id(file_id, current_app.config['UPLOAD_FOLDER'])
    if not upload_path:
        return jsonify({'error': '无效的 file_id'}), 400

    filename_wo_ext = os.path.splitext(os.path.basename(upload_path))[0]
    evaluation_output_dir = os.path.join(current_app.config['DOWNLOAD_FOLDER'], f"evaluation_{filename_wo_ext}_*")

    # 找到动态目录下的 daily_metrics.csv 文件
    evaluation_dir = glob.glob(evaluation_output_dir)
    if not evaluation_dir:
        return jsonify({'error': '找不到评估结果文件'}), 404

    daily_metrics_path = os.path.join(evaluation_dir[0], 'daily_metrics.csv')
    if not os.path.exists(daily_metrics_path):
        return jsonify({'error': '找不到 daily_metrics.csv 文件'}), 404

    # 返回 CSV 文件内容给前端
    return send_file(daily_metrics_path, mimetype='text/csv', as_attachment=False)
