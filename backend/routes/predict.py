import os
from flask import Blueprint, request, jsonify, current_app
import datetime
import shutil
from services.file_service import find_file_by_id
from services.predict_service import run_predict
from werkzeug.utils import secure_filename
# 预测蓝图
predict_bp = Blueprint('predict', __name__)

@predict_bp.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    current_app.logger.info(f"收到预测请求: {data}")
    if not data or 'csvfileId' not in data or 'modelfileId' not in data or 'scalerfileId' not in data:
        current_app.logger.warning("缺少部分数据ID参数")
        return jsonify({'error': "缺少 'file_id' 或 'model' 参数"}), 400

    csvfileId = data['csvfileId']
    modelfileId = data['modelfileId']
    scalerfileId = data['scalerfileId']
    current_app.logger.info(f"预测数据选择: {csvfileId}, 预测模型选择: {modelfileId}, 归一化模型选择: {scalerfileId}")

    csvupload_path = find_file_by_id(csvfileId, current_app.config['UPLOAD_FOLDER'])
    modelupload_path = find_file_by_id(modelfileId, current_app.config['UPLOAD_FOLDER'])
    scalerupload_path = find_file_by_id(scalerfileId, current_app.config['UPLOAD_FOLDER'])
    if not csvupload_path:
        current_app.logger.warning(f"没有找到对应id的预测数据: {csvfileId}")
        return jsonify({'error': '无效的csvfileId'}), 400
    if not modelupload_path:
        current_app.logger.warning(f"没有找到对应id的预测模型: {modelfileId}")
        return jsonify({'error': '无效的modelfileId'}), 400
    if not scalerupload_path:
        current_app.logger.warning(f"没有找到对应id的归一化模型: {scalerfileId}")
        return jsonify({'error': '无效的scalerfileId'}), 400

    # 运行预测与后处理
    try:
        forecast_file_path = run_predict(CSV_FILE_PATH=csvupload_path, MODEL_PATH=modelupload_path, SCALER_PATH=scalerupload_path)
    except Exception as e:
        current_app.logger.error(f"预测过程中出错: {e}")
        return jsonify({'error': '预测过程中出错', 'details': str(e)}), 500

    if not isinstance(forecast_file_path, str) or not os.path.isfile(forecast_file_path):
        current_app.logger.error("预测时没有返回可用的文件路径")
        return jsonify({'error': '预测文件生成失败'}), 500

    # 保存预测结果到 DOWNLOAD_FOLDER
    forecast_timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename_wo_ext = os.path.splitext(os.path.basename(csvupload_path))[0]
    output_filename = f"forecast_{filename_wo_ext}_{forecast_timestamp_str}.csv"
    output_path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], output_filename)

    try:
        shutil.copy(forecast_file_path, output_path)
        current_app.logger.info(f"将原生预测文件复制到以下路径： {output_path}")
    except Exception as e:
        current_app.logger.error(f"无法保存预测结果文件: {e}")
        return jsonify({'error': '无法保存预测结果文件', 'details': str(e)}), 500

    download_url = f"/download/{secure_filename(output_filename)}"
    current_app.logger.info(f"预测文件下载url为: {download_url}")

    return jsonify({
        'download_url': download_url,
    }), 200