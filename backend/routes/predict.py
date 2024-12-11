import os
import pandas as pd
from flask import Blueprint, request, jsonify, current_app, send_file
import glob
import datetime
import shutil
from services.file_service import find_file_by_id
from services.prediction_service import run_prediction
from services.evaluation_service import run_evaluation
from werkzeug.utils import secure_filename
# 预测蓝图
predict_bp = Blueprint('predict', __name__)

@predict_bp.route('/predict', methods=['POST'])
def predict():
    current_app.logger.info("Received /predict request")
    data = request.get_json()
    if not data or 'file_id' not in data or 'model' not in data:
        current_app.logger.warning("Missing 'file_id' or 'model' in request data")
        return jsonify({'error': "缺少 'file_id' 或 'model' 参数"}), 400

    file_id = data['file_id']
    model = data['model']
    current_app.logger.info(f"Received file_id: {file_id}, model: {model}")

    upload_path = find_file_by_id(file_id, current_app.config['UPLOAD_FOLDER'])
    if not upload_path:
        current_app.logger.warning(f"No file found for file_id: {file_id}")
        return jsonify({'error': '无效的 file_id'}), 400

    # 运行预测与后处理
    try:
        forecast_file_path = run_prediction(upload_path, model)
    except Exception as e:
        current_app.logger.error(f"预测过程中出错: {e}")
        return jsonify({'error': '预测过程中出错', 'details': str(e)}), 500

    if not isinstance(forecast_file_path, str) or not os.path.isfile(forecast_file_path):
        current_app.logger.error("Prediction did not return a valid file path")
        return jsonify({'error': '预测文件生成失败'}), 500

    # 保存预测结果到 DOWNLOAD_FOLDER
    forecast_timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename_wo_ext = os.path.splitext(os.path.basename(upload_path))[0]
    output_filename = f"forecast_{filename_wo_ext}_{forecast_timestamp_str}.csv"
    output_path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], output_filename)

    try:
        shutil.copy(forecast_file_path, output_path)
        current_app.logger.info(f"Copied forecast result to {output_path}")
    except Exception as e:
        current_app.logger.error(f"无法保存预测结果文件: {e}")
        return jsonify({'error': '无法保存预测结果文件', 'details': str(e)}), 500

    # 评估模型
    try:
        evaluation_output_dir = os.path.join(current_app.config['DOWNLOAD_FOLDER'], f"evaluation_{filename_wo_ext}_{forecast_timestamp_str}")
        evaluation_result, report_path = run_evaluation(output_path, evaluation_output_dir)
        current_app.logger.info(f"Model evaluation completed. Results in {evaluation_output_dir}")
    except Exception as e:
        current_app.logger.error(f"模型评估过程中出错: {e}")
        return jsonify({'error': '模型评估过程中出错', 'details': str(e)}), 500

    # 准备报告下载链接（如果存在）
    if report_path and os.path.exists(report_path):
        report_output_filename = f"report_{filename_wo_ext}_{forecast_timestamp_str}.txt"
        report_output_path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], report_output_filename)
        try:
            shutil.copy(report_path, report_output_path)
            current_app.logger.info(f"Copied evaluation report to {report_output_path}")
            report_download_url = f"/download/{secure_filename(report_output_filename)}"
        except Exception as e:
            current_app.logger.error(f"无法保存评估报告文件: {e}")
            return jsonify({'error': '无法保存评估报告文件', 'details': str(e)}), 500
    else:
        report_download_url = None

    download_url = f"/download/{secure_filename(output_filename)}"
    current_app.logger.info(f"Generated forecast download URL: {download_url}")
    if report_download_url:
        current_app.logger.info(f"Generated report download URL: {report_download_url}")

    return jsonify({
        'download_url': download_url,
        'report_download_url': report_download_url
    }), 200

# 新增接口：获取 daily_metrics.csv 文件
@predict_bp.route('/get-daily-metrics', methods=['GET'])
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
