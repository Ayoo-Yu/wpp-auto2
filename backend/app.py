import eventlet
eventlet.monkey_patch()
from flask import Flask, request, jsonify, current_app
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv
from database_config import Base, engine, minio_client, get_db
from config import Config, MINIO_CONFIG
from s3_error import S3Error
from models import Dataset
from datetime import datetime
from services.file_service import allowed_file, save_uploaded_file
import os
# 加载环境变量
load_dotenv()

from logging_config import configure_logging

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# 配置日志
configure_logging(app, socketio)

# 注册蓝图
# from routes.upload import upload_bp
from routes.modeltrain import modeltrain_bp
from routes.download import download_bp
from routes.predict import predict_bp
from routes.autopredict import autopredict_bp
from routes.training import training_bp
from routes.predict import predict_bp
from routes.autotask import autotask_bp
from routes.actual_power_router import actual_power_bp
from routes.prediction2database import prediction2database_bp
from routes.power_compare import bp as power_compare_bp

# app.register_blueprint(upload_bp, url_prefix='/')
app.register_blueprint(modeltrain_bp, url_prefix='/')
app.register_blueprint(download_bp, url_prefix='/')
app.register_blueprint(predict_bp, url_prefix='/')
app.register_blueprint(autopredict_bp, url_prefix='/')
app.register_blueprint(training_bp, url_prefix='/')
app.register_blueprint(autotask_bp, url_prefix='/')
app.register_blueprint(actual_power_bp)
app.register_blueprint(prediction2database_bp)
app.register_blueprint(power_compare_bp)
# 初始化数据库和存储桶
def initialize():
    with app.app_context():
        # 创建数据库表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建完成")
        
        # 初始化MinIO存储桶（更新为新的配置结构）
        required_buckets = list(MINIO_CONFIG["buckets"].values())
        existing_buckets = [b.name for b in minio_client.list_buckets()]
        
        for bucket in required_buckets:
            if bucket not in existing_buckets:
                minio_client.make_bucket(bucket)
                print(f"✅ 成功创建存储桶: {bucket}")
            else:
                print(f"✅ 存储桶已存在: {bucket}")

# 执行初始化
initialize()

@app.route('/upload_train_csv', methods=['POST'])
def upload_train_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 新增文件类型校验（来自代码1）
    if not allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        return jsonify({"error": "Invalid file type"}), 400

    # 生成唯一文件ID（来自代码1）
    file_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    try:
        # 新增本地保存逻辑（来自代码1）
        save_uploaded_file(file, file_id, current_app.config['UPLOAD_FOLDER'])
        
        # 重置文件指针以便后续上传
        file.stream.seek(0)

        # 根据数据类型选择存储路径
        data_type = request.form.get('data_type', 'traincsv')
        file_path = f"datasets/{data_type}/{datetime.now().strftime('%Y%m%d')}/{file.filename}"
        
        minio_client.put_object(
            MINIO_CONFIG["buckets"]["datasets"],  # 更新后的存储桶引用
            file_path,
            file.stream,
            length=-1,
            part_size=10*1024*1024
        )

        # 验证MinIO上传
        obj_info = minio_client.stat_object(
            MINIO_CONFIG["buckets"]["datasets"],  # 更新后的存储桶引用
            file_path
        )
        print(f"✅ MinIO验证 - 文件大小：{obj_info.size}")

        # 数据库操作
        db = next(get_db())
        try:
            # 生成本地路径（组合代码1和代码2的参数）
            ext = os.path.splitext(file.filename)[1]
            local_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], 
                f"{file_id}{ext}"
            )

            db_dataset = Dataset(
                file_id=file_id,
                filename=file.filename,
                file_path=file_path,
                upload_time=datetime.now(),
                file_size=file.content_length,
                file_type='traincsv',
                local_path=local_path,
                description=request.form.get('description', ''),
                data_type=data_type,
                wind_farm=request.form.get('wind_farm', 'unknown')
            )
            
            db.add(db_dataset)
            db.commit()
            return jsonify({
                "message": "File uploaded successfully",
                "dataset_id": db_dataset.id,
                "file_id": file_id  # 返回本地保存的ID
            })
        except Exception as e:
            db.rollback()
            print(f"数据库错误：{str(e)}")
            return jsonify({"error": "数据库操作失败"}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"全局异常：{str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/upload_predict_csv', methods=['POST'])
def upload_predict_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 新增文件类型校验（来自代码1）
    if not allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        return jsonify({"error": "Invalid file type"}), 400

    # 生成唯一文件ID（来自代码1）
    file_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    try:
        # 新增本地保存逻辑（来自代码1）
        save_uploaded_file(file, file_id, current_app.config['UPLOAD_FOLDER'])
        
        # 重置文件指针以便后续上传
        file.stream.seek(0)

        # 根据数据类型选择存储路径
        data_type = request.form.get('data_type', 'predictcsv')
        file_path = f"datasets/{data_type}/{datetime.now().strftime('%Y%m%d')}/{file.filename}"
        
        minio_client.put_object(
            MINIO_CONFIG["buckets"]["datasets"],  # 更新后的存储桶引用
            file_path,
            file.stream,
            length=-1,
            part_size=10*1024*1024
        )

        # 验证MinIO上传
        obj_info = minio_client.stat_object(
            MINIO_CONFIG["buckets"]["datasets"],  # 更新后的存储桶引用
            file_path
        )
        print(f"✅ MinIO验证 - 文件大小：{obj_info.size}")

        # 数据库操作
        db = next(get_db())
        try:
            # 生成本地路径（组合代码1和代码2的参数）
            ext = os.path.splitext(file.filename)[1]
            local_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], 
                f"{file_id}{ext}"
            )

            db_dataset = Dataset(
                file_id=file_id,
                filename=file.filename,
                file_path=file_path,
                upload_time=datetime.now(),
                file_size=file.content_length,
                file_type='predictcsv',
                local_path=local_path,
                description=request.form.get('description', ''),
                data_type=data_type,
                wind_farm=request.form.get('wind_farm', 'unknown')
            )
            
            db.add(db_dataset)
            db.commit()
            return jsonify({
                "message": "File uploaded successfully",
                "dataset_id": db_dataset.id,
                "file_id": file_id  # 返回本地保存的ID
            })
        except Exception as e:
            db.rollback()
            print(f"数据库错误：{str(e)}")
            return jsonify({"error": "数据库操作失败"}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"全局异常：{str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/upload_model', methods=['POST'])
def upload_model():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 新增文件类型校验（来自代码1）
    if not allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        return jsonify({"error": "Invalid file type"}), 400

    # 生成唯一文件ID（来自代码1）
    file_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    try:
        # 新增本地保存逻辑（来自代码1）
        save_uploaded_file(file, file_id, current_app.config['UPLOAD_FOLDER'])
        
        # 重置文件指针以便后续上传
        file.stream.seek(0)

        # 根据数据类型选择存储路径
        data_type = request.form.get('data_type', 'model')
        file_path = f"datasets/{data_type}/{datetime.now().strftime('%Y%m%d')}/{file.filename}"
        
        minio_client.put_object(
            MINIO_CONFIG["buckets"]["datasets"],  # 更新后的存储桶引用
            file_path,
            file.stream,
            length=-1,
            part_size=10*1024*1024
        )

        # 验证MinIO上传
        obj_info = minio_client.stat_object(
            MINIO_CONFIG["buckets"]["datasets"],  # 更新后的存储桶引用
            file_path
        )
        print(f"✅ MinIO验证 - 文件大小：{obj_info.size}")

        # 数据库操作
        db = next(get_db())
        try:
            # 生成本地路径（组合代码1和代码2的参数）
            ext = os.path.splitext(file.filename)[1]
            local_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], 
                f"{file_id}{ext}"
            )

            db_dataset = Dataset(
                file_id=file_id,
                filename=file.filename,
                file_path=file_path,
                upload_time=datetime.now(),
                file_size=file.content_length,
                file_type='model',
                local_path=local_path,
                description=request.form.get('description', ''),
                data_type=data_type,
                wind_farm=request.form.get('wind_farm', 'unknown')
            )
            
            db.add(db_dataset)
            db.commit()
            return jsonify({
                "message": "File uploaded successfully",
                "dataset_id": db_dataset.id,
                "file_id": file_id  # 返回本地保存的ID
            })
        except Exception as e:
            db.rollback()
            print(f"数据库错误：{str(e)}")
            return jsonify({"error": "数据库操作失败"}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"全局异常：{str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/upload_scaler', methods=['POST'])
def upload_scaler():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 新增文件类型校验（来自代码1）
    if not allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS']):
        return jsonify({"error": "Invalid file type"}), 400

    # 生成唯一文件ID（来自代码1）
    file_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    try:
        # 新增本地保存逻辑（来自代码1）
        save_uploaded_file(file, file_id, current_app.config['UPLOAD_FOLDER'])
        
        # 重置文件指针以便后续上传
        file.stream.seek(0)

        # 根据数据类型选择存储路径
        data_type = request.form.get('data_type', 'scaler')
        file_path = f"datasets/{data_type}/{datetime.now().strftime('%Y%m%d')}/{file.filename}"
        
        minio_client.put_object(
            MINIO_CONFIG["buckets"]["datasets"],  # 更新后的存储桶引用
            file_path,
            file.stream,
            length=-1,
            part_size=10*1024*1024
        )

        # 验证MinIO上传
        obj_info = minio_client.stat_object(
            MINIO_CONFIG["buckets"]["datasets"],  # 更新后的存储桶引用
            file_path
        )
        print(f"✅ MinIO验证 - 文件大小：{obj_info.size}")

        # 数据库操作
        db = next(get_db())
        try:
            # 生成本地路径（组合代码1和代码2的参数）
            ext = os.path.splitext(file.filename)[1]
            local_path = os.path.join(
                current_app.config['UPLOAD_FOLDER'], 
                f"{file_id}{ext}"
            )

            db_dataset = Dataset(
                file_id=file_id,
                filename=file.filename,
                file_path=file_path,
                upload_time=datetime.now(),
                file_size=file.content_length,
                file_type='scaler',
                local_path=local_path,
                description=request.form.get('description', ''),
                data_type=data_type,
                wind_farm=request.form.get('wind_farm', 'unknown')
            )
            
            db.add(db_dataset)
            db.commit()
            return jsonify({
                "message": "File uploaded successfully",
                "dataset_id": db_dataset.id,
                "file_id": file_id  # 返回本地保存的ID
            })
        except Exception as e:
            db.rollback()
            print(f"数据库错误：{str(e)}")
            return jsonify({"error": "数据库操作失败"}), 500
        finally:
            db.close()
            
    except Exception as e:
        print(f"全局异常：{str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large (max 200MB)'}), 413

@socketio.on('connect')
def handle_connect():
    app.logger.info("成功连接服务器！")
    socketio.emit('response', {'message': '连接成功！'})

@socketio.on('disconnect')
def handle_disconnect():
    app.logger.info("与服务器断开连接！")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
