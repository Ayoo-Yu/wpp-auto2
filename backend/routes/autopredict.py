import json
import subprocess
import datetime
import glob
from flask import Blueprint, request, jsonify, current_app
import os
import sys
import shutil
import traceback
import uuid
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database_config import Base, get_db

# 全局状态字典，其他代码依赖这个变量
prediction_status = {
    'ultra_short': False,
    'short': False,
    'medium': False
}

# 定义任务历史记录模型
class TaskHistory(Base):
    __tablename__ = 'task_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), nullable=False, index=True)  # UUID
    task_type = Column(String(20), nullable=False, index=True)  # ultra_short, short, medium
    action = Column(String(20), nullable=False)  # start, stop, delete, schedule, etc.
    status = Column(String(20), nullable=False)  # success, failed
    created_at = Column(DateTime, default=datetime.datetime.now)
    details = Column(Text, nullable=True)  # 详细信息，如错误原因等
    user = Column(String(50), nullable=True)  # 操作用户，可选

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 在Docker环境中，脚本应该在/app目录下
if os.path.exists('/app'):
    # Docker环境
    base_dir = '/app'
else:
    # 本地开发环境
    base_dir = os.path.abspath(os.path.join(current_dir, '../..'))

# 使用相对于应用根目录的路径
scripts = {
    'ultra_short': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'supershort', 'scheduler_supershort.py'),
    'short': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'short', 'scheduler_short.py'),
    'medium': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'middle', 'scheduler_middle.py')
}

# 额外定义超短期预测的两个脚本路径
ultra_short_scripts = {
    'training': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'supershort', 'scheduler_supershort.py'),
    'prediction': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'supershort', 'scheduler_predict.py')
}

# 检查脚本是否存在
for name, path in scripts.items():
    if os.path.exists(path):
        print(f"✅ 脚本存在: {name} -> {path}")
    else:
        print(f"❌ 脚本不存在: {name} -> {path}")
        # 尝试查找可能的位置
        possible_locations = [
            os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', name, f'scheduler_{name}.py'),
            os.path.join(base_dir, 'backend', 'scripts', name, f'scheduler_{name}.py'),
            os.path.join(base_dir, 'backend', 'scripts', f'scheduler_{name}.py')
        ]
        for loc in possible_locations:
            if os.path.exists(loc):
                print(f"✅ 找到替代脚本: {loc}")
                scripts[name] = loc
                break

# 定义日志目录路径
log_dirs = {
    'ultra_short': {
        'base': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'supershort', 'logs'),
        'train': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'supershort', 'logs', 'auto_train'),
        'predict': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'supershort', 'logs', 'scheduler_predict'),
        'param': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'supershort', 'logs', 'param_optimizer')
    },
    'short': {
        'base': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'short', 'logs'),
        'train': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'short', 'logs', 'auto_train'),
        'param': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'short', 'logs', 'param_optimizer')
    },
    'medium': {
        'base': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'middle', 'logs'),
        'train': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'middle', 'logs', 'auto_train'),
        'param': os.path.join(base_dir, 'backend', 'auto_scripts', 'scripts', 'middle', 'logs', 'param_optimizer')
    }
}

# 确保所有日志目录都存在
for type_dirs in log_dirs.values():
    for dir_path in type_dirs.values():
        os.makedirs(dir_path, exist_ok=True)

# 改进PM2路径检测
def find_pm2_path():
    # 使用shutil.which查找可执行文件路径
    pm2_path = shutil.which('pm2')
    if pm2_path:
        print(f"找到PM2路径: {pm2_path}")
        return pm2_path
    
    # 尝试从环境变量获取
    pm2_path = os.environ.get('PM2_PATH')
    if pm2_path and os.path.exists(pm2_path) and os.access(pm2_path, os.X_OK):
        print(f"从环境变量获取PM2路径: {pm2_path}")
        return pm2_path
    
    # 尝试常见的安装位置
    common_paths = [
        '/usr/local/bin/pm2',
        '/usr/bin/pm2',
        '/opt/node/bin/pm2',
        '/opt/nodejs/bin/pm2',
        '/opt/conda/bin/pm2',
        '/usr/local/nodejs/bin/pm2',
        os.path.expanduser('~/.nvm/versions/node/*/bin/pm2'),
        os.path.expanduser('~/node_modules/.bin/pm2')
    ]
    
    for path_pattern in common_paths:
        # 处理可能包含通配符的路径
        if '*' in path_pattern:
            import glob
            matching_paths = glob.glob(path_pattern)
            for path in matching_paths:
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    print(f"在扩展路径中找到PM2: {path}")
                    return path
        elif os.path.isfile(path_pattern) and os.access(path_pattern, os.X_OK):
            print(f"在常见位置找到PM2: {path_pattern}")
            return path_pattern
    
    # 如果在Windows上运行
    if sys.platform.startswith('win'):
        # 尝试使用npm路径
        npm_path = shutil.which('npm')
        if npm_path:
            npm_dir = os.path.dirname(npm_path)
            pm2_win_path = os.path.join(npm_dir, 'pm2.cmd')
            if os.path.exists(pm2_win_path):
                print(f"在Windows上找到PM2: {pm2_win_path}")
                return pm2_win_path
    
    # 最后的回退选项
    print(f"未找到PM2可执行文件，使用默认命令: pm2")
    return 'pm2'

# 使用改进的函数获取PM2路径
pm2_cmd = find_pm2_path()

# 安全的PM2命令执行函数
def safe_pm2_command(cmd_args, timeout=30, capture_output=True):
    """
    安全地执行PM2命令，添加超时和错误处理
    
    Args:
        cmd_args: PM2命令参数列表
        timeout: 命令执行超时时间（秒）
        capture_output: 是否捕获输出
        
    Returns:
        tuple: (成功与否, 结果对象或错误消息)
    """
    full_cmd = [pm2_cmd] + cmd_args
    try:
        print(f"执行命令: {' '.join(full_cmd)}")
        if capture_output:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                check=True
            )
            return True, result
        else:
            result = subprocess.run(
                full_cmd,
                timeout=timeout,
                check=True
            )
            return True, result
    except subprocess.TimeoutExpired as e:
        error_msg = f"命令执行超时 ({timeout}秒): {' '.join(full_cmd)}"
        print(error_msg)
        return False, error_msg
    except subprocess.CalledProcessError as e:
        error_msg = f"命令执行失败: {e}\n输出: {e.stdout if hasattr(e, 'stdout') else '无'}\n错误: {e.stderr if hasattr(e, 'stderr') else '无'}"
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"命令执行异常: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return False, error_msg

def query_pm2_state(script_path):
    """
    查询 pm2 中指定脚本的运行状态，
    只有当进程的 pm_exec_path 包含指定脚本且状态为 "online" 时才返回 True
    """
    success, result = safe_pm2_command(['jlist'])
    if not success:
        print(f"查询PM2状态失败: {result}")
        return False
        
    try:
        output = result.stdout
        if not output or output.strip() == '[]':
            print("PM2列表为空或未返回有效数据")
            return False
            
        processes = json.loads(output)
        script_basename = os.path.basename(script_path)
        
        for proc in processes:
            pm2_env = proc.get('pm2_env', {})
            exec_path = pm2_env.get('pm_exec_path', '')
            proc_name = pm2_env.get('name', '')
            status = pm2_env.get('status', '')
            
            # 检查脚本路径或进程名是否匹配
            path_match = script_path in exec_path
            name_match = script_basename == proc_name
            
            if (path_match or name_match) and status == "online":
                print(f"找到匹配的运行中进程: {proc_name}")
                return True
                
        return False
    except Exception as e:
        print(f"解析PM2状态时出错: {e}")
        return False

# 记录操作历史的辅助函数
def record_task_history(task_type, action, status, details=None, user=None):
    """
    记录任务操作历史
    
    Args:
        task_type: 任务类型 (ultra_short, short, medium)
        action: 操作类型 (start, stop, delete, schedule, etc.)
        status: 操作状态 (success, failed)
        details: 操作详情，可选
        user: 操作用户，可选
        
    Returns:
        UUID: 任务历史ID
    """
    task_id = str(uuid.uuid4())
    db = next(get_db())
    try:
        task_history = TaskHistory(
            task_id=task_id,
            task_type=task_type,
            action=action,
            status=status,
            details=details,
            user=user
        )
        db.add(task_history)
        db.commit()
        return task_id
    except Exception as e:
        db.rollback()
        print(f"记录任务历史出错: {e}")
        return None
    finally:
        db.close()

# 新建蓝图，所有接口的 URL 前缀为 /api
autopredict_bp = Blueprint('autopredict', __name__)

# 获取预测任务状态，同时更新全局字典 prediction_status
@autopredict_bp.route('/status', methods=['GET'])
def get_status():
    try:
        success, result = safe_pm2_command(['jlist'])
        if not success:
            return jsonify({'error': f"获取PM2状态失败: {result}"}), 500
            
        output = result.stdout
        if not output or output.strip() == '[]':
            # PM2可能没有运行任何进程，但不一定是错误
            processes = []
        else:
            processes = json.loads(output)
            
        # 更新每个预测任务的状态
        for key, script_path in scripts.items():
            script_basename = os.path.basename(script_path)
            prediction_status[key] = any(
                (script_path in proc.get('pm2_env', {}).get('pm_exec_path', '') or 
                 script_basename == proc.get('pm2_env', {}).get('name', ''))
                and proc.get('pm2_env', {}).get('status', '') == "online"
                for proc in processes
            )
            
        return jsonify(prediction_status)
    except Exception as e:
        error_msg = f"获取状态时出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500

# 启动指定预测任务
@autopredict_bp.route('/start', methods=['POST'])
def start_prediction():
    data = request.get_json() or {}
    prediction_type = data.get('type')
    if prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400

    script_path = scripts[prediction_type]
    
    # 检查脚本是否存在
    if not os.path.exists(script_path):
        error_msg = f'脚本文件不存在: {script_path}'
        record_task_history(prediction_type, 'start', 'failed', error_msg)
        return jsonify({'error': error_msg}), 400
    
    # 使用 os.path.basename 得到脚本文件的基本名称作为进程名称
    process_name = os.path.basename(script_path)
    
    # 先检查进程是否已经运行
    if query_pm2_state(script_path):
        prediction_status[prediction_type] = True
        record_task_history(prediction_type, 'start', 'success', f'进程已在运行中: {process_name}')
        return jsonify({'message': f'{prediction_type} 预测任务已经在运行', 'status': True})
    
    success, result = safe_pm2_command(['start', script_path, '--name', process_name])
    
    if success:
        # 启动命令执行成功，但需要验证进程是否真的启动
        verify_success, _ = safe_pm2_command(['list'])
        if verify_success:
            # 再次检查进程状态
            if query_pm2_state(script_path):
                prediction_status[prediction_type] = True
                record_task_history(prediction_type, 'start', 'success', f'进程启动成功: {process_name}')
                return jsonify({
                    'message': f'{prediction_type} 预测任务已启动',
                    'output': result.stdout if hasattr(result, 'stdout') else ''
                })
            else:
                # 命令成功但进程可能没有正常启动
                warning_msg = f'{prediction_type} 启动命令成功，但进程可能未正常运行'
                record_task_history(prediction_type, 'start', 'warning', warning_msg)
                return jsonify({
                    'warning': warning_msg,
                    'output': result.stdout if hasattr(result, 'stdout') else ''
                }), 202
        else:
            warning_msg = f'{prediction_type} 启动命令成功，但无法验证进程状态'
            record_task_history(prediction_type, 'start', 'warning', warning_msg)
            return jsonify({
                'warning': warning_msg,
                'output': result.stdout if hasattr(result, 'stdout') else ''
            }), 202
    else:
        # 启动命令执行失败
        error_msg = f'启动任务失败: {result}'
        record_task_history(prediction_type, 'start', 'failed', error_msg)
        return jsonify({'error': error_msg}), 500

# 停止预测任务
@autopredict_bp.route('/stop', methods=['POST'])
def stop_prediction():
    data = request.json
    prediction_type = data.get('type')
    
    if not prediction_type or prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400
    
    try:
        if prediction_type == 'ultra_short':
            # 停止超短期预测的两个脚本
            results = []
            
            # 停止训练脚本
            training_script = ultra_short_scripts['training']
            training_name = os.path.basename(training_script)
            training_success, training_result = safe_pm2_command(['stop', training_name])
            
            if training_success:
                results.append(f'训练脚本({training_name})停止成功')
            else:
                results.append(f'训练脚本停止失败: {training_result}')
            
            # 停止预测脚本
            prediction_script = ultra_short_scripts['prediction']
            prediction_name = os.path.basename(prediction_script)
            prediction_success, prediction_result = safe_pm2_command(['stop', prediction_name])
            
            if prediction_success:
                results.append(f'预测脚本({prediction_name})停止成功')
            else:
                results.append(f'预测脚本停止失败: {prediction_result}')
            
            # 只要有一个成功停止，就更新状态
            if training_success or prediction_success:
                prediction_status[prediction_type] = False
                # 更新全局状态
                _update_prediction_status()
                
                message = ' & '.join(results)
                record_task_history(prediction_type, 'stop', 'success', message)
                
                return jsonify({
                    'message': '超短期预测任务已停止',
                    'details': message
                })
            else:
                # 两个都失败
                error_msg = ' & '.join(results)
                record_task_history(prediction_type, 'stop', 'failed', error_msg)
                
                return jsonify({
                    'error': '停止超短期预测任务失败',
                    'details': error_msg
                }), 500
        else:
            # 正常停止单个脚本
            script_path = scripts[prediction_type]
            script_name = os.path.basename(script_path)
            
            success, result = safe_pm2_command(['stop', script_name])
            
            if success:
                prediction_status[prediction_type] = False
                # 更新全局状态
                _update_prediction_status()
                
                message = f'{script_name} 已停止'
                record_task_history(prediction_type, 'stop', 'success', message)
                
                return jsonify({
                    'message': f'{prediction_type}预测任务已停止'
                })
            else:
                error_msg = f'停止任务失败: {result}'
                record_task_history(prediction_type, 'stop', 'failed', error_msg)
                
                return jsonify({
                    'error': '停止预测任务失败',
                    'details': str(result)
                }), 500
    except Exception as e:
        error_msg = f'停止预测任务异常: {str(e)}'
        record_task_history(prediction_type, 'stop', 'failed', error_msg)
        
        return jsonify({
            'error': '停止预测任务失败',
            'details': str(e)
        }), 500

# 设置定时重启任务
@autopredict_bp.route('/schedule', methods=['POST'])
def schedule_restart():
    data = request.get_json() or {}
    prediction_type = data.get('type')
    schedule_time = data.get('time')  # 格式应为 HH:mm

    if prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400
    if not schedule_time:
        return jsonify({'error': '缺少重启时间参数'}), 400

    try:
        time_obj = datetime.datetime.strptime(schedule_time, '%H:%M')
    except ValueError:
        error_msg = '时间格式错误，要求 HH:mm'
        record_task_history(prediction_type, 'schedule', 'failed', error_msg)
        return jsonify({'error': error_msg}), 400

    script_path = scripts[prediction_type]
    # 使用 os.path.basename 获取脚本文件名作为进程名称
    process_name = os.path.basename(script_path)
    
    # 先停止现有进程
    stop_success, _ = safe_pm2_command(['stop', process_name])
    if not stop_success:
        print(f"警告: 无法停止现有进程 {process_name}, 将尝试继续设置定时任务")
    
    # 启动带定时重启的任务
    cron_expression = f'0 {time_obj.minute} {time_obj.hour} * * *'
    success, result = safe_pm2_command(['start', script_path, '--name', process_name, '--cron', cron_expression])
    
    if success:
        prediction_status[prediction_type] = True
        record_task_history(
            prediction_type, 
            'schedule', 
            'success', 
            f'设置定时重启: {schedule_time}'
        )
        return jsonify({'message': f'为 {prediction_type} 设置了每日 {schedule_time} 的定时重启'})
    else:
        error_msg = f'设置定时重启失败: {result}'
        record_task_history(prediction_type, 'schedule', 'failed', error_msg)
        return jsonify({'error': error_msg}), 500

# 从 PM2 中删除任务
@autopredict_bp.route('/delete', methods=['POST'])
def delete_prediction():
    data = request.json
    prediction_type = data.get('type')
    if not prediction_type or prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400
    
    try:
        if prediction_type == 'ultra_short':
            # 删除超短期预测的两个脚本
            results = []
            
            # 删除训练脚本
            training_script = ultra_short_scripts['training']
            training_name = os.path.basename(training_script)
            training_success, training_result = safe_pm2_command(['delete', training_name])
            
            if training_success:
                results.append(f'训练脚本({training_name})已从PM2删除')
            else:
                results.append(f'训练脚本删除失败: {training_result}')
            
            # 删除预测脚本
            prediction_script = ultra_short_scripts['prediction']
            prediction_name = os.path.basename(prediction_script)
            prediction_success, prediction_result = safe_pm2_command(['delete', prediction_name])
            
            if prediction_success:
                results.append(f'预测脚本({prediction_name})已从PM2删除')
            else:
                results.append(f'预测脚本删除失败: {prediction_result}')
            
            # 只要有一个成功删除，就更新状态
            if training_success or prediction_success:
                prediction_status[prediction_type] = False
                # 更新全局状态
                _update_prediction_status()
                
                message = ' & '.join(results)
                record_task_history(prediction_type, 'delete', 'success', message)
                
                return jsonify({
                    'message': '超短期预测任务已从PM2删除',
                    'details': message
                })
            else:
                # 两个都失败
                error_msg = ' & '.join(results)
                record_task_history(prediction_type, 'delete', 'failed', error_msg)
                
                return jsonify({
                    'error': '从PM2删除超短期预测任务失败',
                    'details': error_msg
                }), 500
        else:
            # 正常删除单个脚本
            script_path = scripts[prediction_type]
            script_name = os.path.basename(script_path)
            
            success, result = safe_pm2_command(['delete', script_name])
            
            if success:
                prediction_status[prediction_type] = False
                # 更新全局状态
                _update_prediction_status()
                
                message = f'{script_name} 已从PM2删除'
                record_task_history(prediction_type, 'delete', 'success', message)
                
                return jsonify({
                    'message': f'{prediction_type}预测任务已从PM2删除'
                })
            else:
                error_msg = f'删除任务失败: {result}'
                record_task_history(prediction_type, 'delete', 'failed', error_msg)
                
                return jsonify({
                    'error': '从PM2删除预测任务失败',
                    'details': str(result)
                }), 500
    except Exception as e:
        error_msg = f'删除预测任务异常: {str(e)}'
        record_task_history(prediction_type, 'delete', 'failed', error_msg)
        
        return jsonify({
            'error': '从PM2删除预测任务失败',
            'details': str(e)
        }), 500

# 保存当前 PM2 任务配置
@autopredict_bp.route('/save', methods=['POST'])
def save_pm2_config():
    success, result = safe_pm2_command(['save'])
    
    if success:
        record_task_history('all', 'save', 'success', '保存PM2配置')
        return jsonify({'message': 'PM2 任务配置已保存'})
    else:
        error_msg = f'保存配置失败: {result}'
        record_task_history('all', 'save', 'failed', error_msg)
        return jsonify({'error': error_msg}), 500

# 删除PM2保存的配置文件（新增）
@autopredict_bp.route('/clearsave', methods=['POST'])
def clear_pm2_save():
    success, result = safe_pm2_command(['cleardump'])
    
    if success:
        record_task_history('all', 'clearsave', 'success', '删除PM2保存的配置')
        return jsonify({'message': 'PM2 保存的配置已删除'})
    else:
        error_msg = f'删除保存配置失败: {result}'
        record_task_history('all', 'clearsave', 'failed', error_msg)
        return jsonify({'error': error_msg}), 500

# 查询指定脚本的详细 PM2 信息
@autopredict_bp.route('/script_info', methods=['GET'])
def get_script_info():
    prediction_type = request.args.get('type')
    if not prediction_type or prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400

    try:
        # 获取进程名称（保留.py后缀）
        process_name = os.path.basename(scripts[prediction_type])
        print(f"正在查询进程: {process_name}")  # 调试日志
        
        # 先检查进程是否存在
        list_success, list_result = safe_pm2_command(['list'])
        
        if not list_success:
            error_msg = '无法获取PM2进程列表'
            record_task_history(prediction_type, 'script_info', 'failed', error_msg)
            return jsonify({
                'error': error_msg,
                'details': str(list_result)
            }), 500
            
        list_output = list_result.stdout if hasattr(list_result, 'stdout') else ''
        print(f"PM2 进程列表: {list_output}")  # 输出所有进程列表
        
        # 检查是否在进程列表中找到对应进程
        if process_name not in list_output:
            # 尝试使用describe命令无论如何获取信息
            describe_success, describe_result = safe_pm2_command(['describe', process_name], timeout=10)
            
            if describe_success:
                # 即使进程名不在列表中，describe命令可能仍然返回信息
                record_task_history(prediction_type, 'script_info', 'warning', '进程未在PM2列表中找到，但describe命令返回了信息')
                return jsonify({
                    'info': describe_result.stdout,
                    'process_name': process_name,
                    'warning': '进程未在PM2列表中找到，但describe命令返回了信息'
                })
            else:
                error_msg = f'进程 {process_name} 未运行'
                record_task_history(prediction_type, 'script_info', 'failed', error_msg)
                return jsonify({
                    'error': error_msg,
                    'pm2_list': list_output,
                    'describe_error': str(describe_result)
                }), 404
            
        # 使用进程名称查询详情
        describe_success, describe_result = safe_pm2_command(['describe', process_name])
        
        if not describe_success:
            error_msg = '查询进程详情失败'
            record_task_history(prediction_type, 'script_info', 'failed', error_msg)
            return jsonify({
                'error': error_msg,
                'details': str(describe_result)
            }), 500
            
        describe_output = describe_result.stdout if hasattr(describe_result, 'stdout') else ''
        
        if not describe_output.strip():
            error_msg = '进程信息为空'
            record_task_history(prediction_type, 'script_info', 'failed', error_msg)
            return jsonify({
                'error': error_msg,
                'process_name': process_name
            }), 404
            
        record_task_history(prediction_type, 'script_info', 'success', '查询进程详情成功')
        return jsonify({
            'info': describe_output,
            'process_name': process_name
        })
        
    except Exception as e:
        error_msg = f"获取脚本详情出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        record_task_history(prediction_type, 'script_info', 'failed', error_msg)
        return jsonify({
            'error': '查询脚本详情失败',
            'details': error_msg
        }), 500

# 获取指定脚本的近期日志信息
@autopredict_bp.route('/logs', methods=['GET'])
def get_logs():
    prediction_type = request.args.get('type')
    log_type = request.args.get('logType', 'main') # main, train, predict, param
    date_str = request.args.get('date', datetime.datetime.now().strftime('%Y%m%d'))
    lines = request.args.get('lines', 500, type=int)
    
    if not prediction_type or prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400
    
    try:
        # 如果是通过PM2查询主日志
        if log_type == 'main':
            script_path = scripts[prediction_type]
            process_name = os.path.basename(script_path)
            
            success, result = safe_pm2_command(['logs', '--nostream', '--lines', str(lines), process_name])
            
            if success:
                record_task_history(prediction_type, 'logs', 'success', f'获取主日志 ({lines} 行)')
                return jsonify({'logs': result.stdout if hasattr(result, 'stdout') else '没有日志输出'})
            else:
                # 尝试只获取错误日志
                error_success, error_result = safe_pm2_command(['logs', '--nostream', '--err', '--lines', str(lines), process_name])
                if error_success:
                    warning_msg = '无法获取完整日志，仅显示错误日志'
                    record_task_history(prediction_type, 'logs', 'warning', warning_msg)
                    return jsonify({
                        'logs': f"警告: {warning_msg}:\n{error_result.stdout if hasattr(error_result, 'stdout') else '没有错误日志'}"
                    })
                else:
                    error_msg = '获取日志失败'
                    details = {
                        'details': str(result),
                        'error_log_details': str(error_result) if 'error_result' in locals() else '未尝试获取错误日志'
                    }
                    record_task_history(prediction_type, 'logs', 'failed', json.dumps(details))
                    return jsonify({
                        'error': error_msg, 
                        'details': str(result),
                        'error_log_details': str(error_result) if 'error_result' in locals() else '未尝试获取错误日志'
                    }), 500
        else:
            # 从对应的日志目录读取文件
            log_dir = log_dirs[prediction_type].get(log_type)
            if not log_dir:
                return jsonify({'error': f'无效的日志类型: {log_type}'}), 400
            
            # 查找日志文件
            log_files = []
            if log_type == 'train':
                # 训练日志格式可能是 YYYYMMDD.log 或包含日期的其他格式
                log_files = glob.glob(os.path.join(log_dir, f"{date_str}*.log"))
                train_flag_path = os.path.join(log_dir, f"{date_str}_train_done.flag")
                
                # 如果找不到日志但有完成标志文件，则尝试查找最近的可能相关日志
                if not log_files and os.path.exists(train_flag_path):
                    # 尝试用更宽松的模式查找日期相近的日志
                    year_month = date_str[:6]  # 提取年月
                    month_logs = glob.glob(os.path.join(log_dir, f"{year_month}*.log"))
                    if month_logs:
                        # 找到最接近但不超过所选日期的日志文件
                        filtered_logs = [log for log in month_logs 
                                        if os.path.basename(log).split('_')[0] <= date_str]
                        if filtered_logs:
                            log_files = [max(filtered_logs, key=lambda x: os.path.basename(x).split('_')[0])]
            elif log_type == 'predict':
                # 预测日志格式
                log_files = glob.glob(os.path.join(log_dir, f"{date_str}*.log"))
            elif log_type == 'param':
                # 参数优化日志 - 查找对应周的日志
                try:
                    # 解析所选日期
                    selected_date = datetime.datetime.strptime(date_str, '%Y%m%d')
                    # 计算所在周的周一
                    monday = selected_date - datetime.timedelta(days=selected_date.weekday())
                    monday_str = monday.strftime('%Y%m%d')
                    
                    # 查找该周的参数优化标志文件
                    param_flag_path = os.path.join(log_dir, f"{monday_str}_param_opt_done.flag")
                    
                    if os.path.exists(param_flag_path):
                        # 存在标志文件，查找最接近的日志
                        week_logs = glob.glob(os.path.join(log_dir, f"{monday_str}*.log"))
                        if not week_logs:
                            # 尝试查找该月的所有参数优化日志
                            year_month = monday_str[:6]  # 提取年月
                            month_logs = glob.glob(os.path.join(log_dir, f"{year_month}*.log"))
                            
                            if month_logs:
                                # 选择最近的一个日志
                                log_files = [max(month_logs, key=os.path.getmtime)]
                        else:
                            log_files = week_logs
                except ValueError:
                    # 日期格式错误，返回错误信息
                    record_task_history(prediction_type, 'logs', 'failed', f'日期格式无效: {date_str}')
                    return jsonify({'error': f'日期格式无效: {date_str}'}), 400
            
            if not log_files:
                record_task_history(prediction_type, 'logs', 'failed', f'未找到{date_str}的{log_type}类型日志文件')
                return jsonify({'logs': f'未找到{date_str}的{log_type}日志文件'})
            
            # 读取最新的日志文件
            latest_log = max(log_files, key=os.path.getmtime)
            try:
                with open(latest_log, 'r', encoding='utf-8', errors='replace') as f:
                    # 如果文件太大，只读取最后N行
                    all_lines = f.readlines()
                    log_content = ''.join(all_lines[-lines:]) if len(all_lines) > lines else ''.join(all_lines)
                
                # 添加日志文件信息到内容中
                file_info = f"文件: {os.path.basename(latest_log)}\n日期: {datetime.datetime.fromtimestamp(os.path.getmtime(latest_log)).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                log_content = file_info + log_content
                
                record_task_history(prediction_type, 'logs', 'success', f'获取{log_type}日志 ({lines} 行)')
                return jsonify({'logs': log_content})
            except Exception as e:
                error_msg = f'读取日志文件失败: {str(e)}'
                record_task_history(prediction_type, 'logs', 'failed', error_msg)
                return jsonify({'error': error_msg}), 500
    except Exception as e:
        error_msg = f'获取日志失败: {str(e)}'
        record_task_history(prediction_type, 'logs', 'failed', error_msg)
        return jsonify({'error': error_msg}), 500

# 加载已保存的 PM2 配置（基于 pm2 resurrect）
@autopredict_bp.route('/resurrect', methods=['POST'])
def resurrect():
    success, result = safe_pm2_command(['resurrect'])
    
    if success:
        # 更新状态字典，但不直接使用路由函数
        try:
            # 获取PM2状态并更新全局字典，但不返回响应
            _update_prediction_status()
            record_task_history('all', 'resurrect', 'success', '恢复PM2配置')
            return jsonify({"message": "成功恢复PM2配置"}), 200
        except Exception as e:
            error_msg = f"恢复配置后更新状态失败: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            record_task_history('all', 'resurrect', 'warning', error_msg)
            # 尽管更新状态失败，但resurrect命令已经成功执行，所以仍然返回成功
            return jsonify({"message": "PM2配置已恢复，但更新状态失败", "warning": "状态可能不准确，请刷新页面"}), 200
    else:
        error_msg = f"恢复PM2配置失败: {result}"
        record_task_history('all', 'resurrect', 'failed', error_msg)
        return jsonify({"error": error_msg}), 500

# 添加一个内部函数用于更新状态，但不返回HTTP响应
def _update_prediction_status():
    """更新全局prediction_status字典，但不返回响应"""
    try:
        success, result = safe_pm2_command(['jlist'])
        if not success:
            print(f"更新状态失败: {result}")
            return False
            
        output = result.stdout
        if not output or output.strip() == '[]':
            # PM2可能没有运行任何进程，但不一定是错误
            processes = []
        else:
            processes = json.loads(output)
            
        # 更新每个预测任务的状态
        for key, script_path in scripts.items():
            script_basename = os.path.basename(script_path)
            prediction_status[key] = any(
                (script_path in proc.get('pm2_env', {}).get('pm_exec_path', '') or 
                 script_basename == proc.get('pm2_env', {}).get('name', ''))
                and proc.get('pm2_env', {}).get('status', '') == "online"
                for proc in processes
            )
        return True
    except Exception as e:
        error_msg = f"更新状态时出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return False

# 获取任务历史记录
@autopredict_bp.route('/history', methods=['GET'])
def get_task_history():
    task_type = request.args.get('type')  # 可选，筛选特定类型的任务
    action = request.args.get('action')   # 可选，筛选特定操作
    limit = request.args.get('limit', 50, type=int)  # 默认返回最近50条记录
    offset = request.args.get('offset', 0, type=int)  # 分页偏移量
    
    try:
        db = next(get_db())
        query = db.query(TaskHistory).order_by(TaskHistory.created_at.desc())
        
        # 应用筛选条件
        if task_type:
            query = query.filter(TaskHistory.task_type == task_type)
        if action:
            query = query.filter(TaskHistory.action == action)
            
        # 应用分页
        total = query.count()
        history = query.offset(offset).limit(limit).all()
        
        # 转换为可序列化的字典
        result = []
        for item in history:
            result.append({
                'id': item.id,
                'task_id': item.task_id,
                'task_type': item.task_type,
                'action': item.action,
                'status': item.status,
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'details': item.details,
                'user': item.user
            })
        
        return jsonify({
            'total': total,
            'offset': offset,
            'limit': limit,
            'data': result
        })
        
    except Exception as e:
        error_msg = f"获取任务历史记录出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500
    finally:
        if 'db' in locals():
            db.close()

# 查询任务状态（训练、预测、参数优化）
@autopredict_bp.route('/task_status', methods=['GET'])
def get_task_status():
    prediction_type = request.args.get('type')
    date_str = request.args.get('date', datetime.datetime.now().strftime('%Y%m%d'))
    
    if not prediction_type or prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400
    
    # 初始化状态对象
    status = {
        'training': False,
        'prediction': False,
        'paramOpt': False,
        'trainingTime': '',
        'predictionTime': '',
        'paramOptTime': '',
        'predictionCount': 0
    }
    
    try:
        # 解析日期
        try:
            selected_date = datetime.datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            return jsonify({'error': '日期格式无效，请使用YYYYMMDD格式'}), 400
        
        is_today = selected_date.date() == datetime.datetime.now().date()
        is_current_week = (datetime.datetime.now() - selected_date).days < 7
        
        # 检查训练任务状态（通过flag文件）
        train_flag_path = os.path.join(log_dirs[prediction_type]['train'], f"{date_str}_train_done.flag")
        if os.path.exists(train_flag_path):
            status['training'] = True
            status['trainingTime'] = datetime.datetime.fromtimestamp(os.path.getmtime(train_flag_path)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查参数优化任务状态
        # 计算所选日期所在周的周一
        selected_monday = selected_date - datetime.timedelta(days=selected_date.weekday())
        monday_str = selected_monday.strftime('%Y%m%d')
        param_flag_path = os.path.join(log_dirs[prediction_type]['param'], f"{monday_str}_param_opt_done.flag")
        
        if os.path.exists(param_flag_path):
            status['paramOpt'] = True
            status['paramOptTime'] = datetime.datetime.fromtimestamp(os.path.getmtime(param_flag_path)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 检查预测任务状态
        if prediction_type == 'ultra_short':
            # 超短期预测需要检查预测日志
            predict_log_dir = log_dirs[prediction_type]['predict']
            
            # 查找指定日期的所有日志文件
            date_logs = glob.glob(os.path.join(predict_log_dir, f"{date_str}*.log"))
            
            # 计算当天预测完成次数
            status['predictionCount'] = len(date_logs)
            
            if date_logs:
                status['prediction'] = True
                latest_log = max(date_logs, key=os.path.getmtime)
                status['predictionTime'] = datetime.datetime.fromtimestamp(os.path.getmtime(latest_log)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 只有当天才检查进程状态
            if is_today:
                predict_script = ultra_short_scripts['prediction']
                predict_online = query_pm2_state(predict_script)
                status['prediction'] = predict_online or status['prediction']
        else:
            # 短期和中期预测查找日志文件
            predict_logs_dir = os.path.join(log_dirs[prediction_type]['base'], 'predictions')
            date_logs = glob.glob(os.path.join(predict_logs_dir, f"{date_str}*.log"))
            
            if date_logs:
                status['prediction'] = True
                latest_log = max(date_logs, key=os.path.getmtime)
                status['predictionTime'] = datetime.datetime.fromtimestamp(os.path.getmtime(latest_log)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 只有当天才检查进程状态
            if is_today:
                script_online = query_pm2_state(scripts[prediction_type])
                status['prediction'] = script_online or status['prediction']
        
        return jsonify({'status': status})
    except Exception as e:
        print(f"获取任务状态失败: {str(e)}")
        return jsonify({'error': '获取任务状态失败', 'details': str(e)}), 500

# 添加启动超短期预测的特殊接口
@autopredict_bp.route('/start_ultra', methods=['POST'])
def start_ultra_short():
    try:
        data = request.json
        options = data.get('options', {})
        
        # 检查选项
        start_training = options.get('training', True)
        start_prediction = options.get('prediction', True)
        
        if not start_training and not start_prediction:
            return jsonify({'error': '至少需要选择一个脚本启动'}), 400
        
        results = []
        
        # 启动训练脚本
        if start_training:
            training_script = ultra_short_scripts['training']
            success, result = safe_pm2_command([
                'start', 
                training_script, 
                '--name', os.path.basename(training_script)
            ])
            
            if success:
                results.append('训练脚本启动成功')
                prediction_status['ultra_short'] = True
            else:
                results.append(f'训练脚本启动失败: {result}')
        
        # 启动预测脚本
        if start_prediction:
            prediction_script = ultra_short_scripts['prediction']
            success, result = safe_pm2_command([
                'start', 
                prediction_script, 
                '--name', os.path.basename(prediction_script)
            ])
            
            if success:
                results.append('预测脚本启动成功')
                prediction_status['ultra_short'] = True
            else:
                results.append(f'预测脚本启动失败: {result}')
        
        # 记录操作历史
        message = ' & '.join(results)
        record_task_history('ultra_short', 'start', 'success', message)
        
        return jsonify({
            'message': '超短期预测任务启动成功',
            'details': message
        })
    except Exception as e:
        error_msg = f'启动超短期预测失败: {str(e)}'
        record_task_history('ultra_short', 'start', 'failed', error_msg)
        return jsonify({'error': error_msg}), 500

