import json
import subprocess
import datetime
from flask import Blueprint, request, jsonify, current_app
import os
import sys
import shutil
import traceback

# 全局状态字典，其他代码依赖这个变量
prediction_status = {
    'ultra_short': False,
    'short': False,
    'medium': False
}

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
    'ultra_short': os.path.join(base_dir, 'auto_scripts', 'scripts', 'supershort', 'scheduler_supershort.py'),
    'short': os.path.join(base_dir, 'auto_scripts', 'scripts', 'short', 'scheduler_short.py'),
    'medium': os.path.join(base_dir, 'auto_scripts', 'scripts', 'middle', 'scheduler_middle.py')
}

# 检查脚本是否存在
for name, path in scripts.items():
    if os.path.exists(path):
        print(f"✅ 脚本存在: {name} -> {path}")
    else:
        print(f"❌ 脚本不存在: {name} -> {path}")
        # 尝试查找可能的位置
        possible_locations = [
            os.path.join(base_dir, 'auto_scripts', 'scripts', name, f'scheduler_{name}.py'),
            os.path.join(base_dir, 'scripts', name, f'scheduler_{name}.py'),
            os.path.join(base_dir, 'scripts', f'scheduler_{name}.py')
        ]
        for loc in possible_locations:
            if os.path.exists(loc):
                print(f"✅ 找到替代脚本: {loc}")
                scripts[name] = loc
                break

# 使用shutil.which查找可执行文件路径，这是更可靠的方法
pm2_cmd = shutil.which('pm2')
if pm2_cmd:
    print(f"找到PM2路径: {pm2_cmd}")
else:
    # 尝试从环境变量获取
    pm2_cmd = os.environ.get('PM2_PATH')
    if pm2_cmd:
        print(f"从环境变量获取PM2路径: {pm2_cmd}")
    else:
        # 尝试常见的安装位置
        common_paths = [
            '/usr/local/bin/pm2',
            '/usr/bin/pm2',
            '/opt/node/bin/pm2',
            '/opt/nodejs/bin/pm2',
            '/opt/conda/bin/pm2'
        ]
        for path in common_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                pm2_cmd = path
                print(f"在常见位置找到PM2: {pm2_cmd}")
                break
        
        if not pm2_cmd:
            # 最后的回退选项
            pm2_cmd = 'pm2'
            print(f"未找到PM2路径，使用默认命令: {pm2_cmd}")

def query_pm2_state(script_path):
    """
    查询 pm2 中指定脚本的运行状态，
    只有当进程的 pm_exec_path 包含指定脚本且状态为 "online" 时才返回 True
    """
    try:
        result = subprocess.run(
            [pm2_cmd, 'jlist'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=True
        )
        output = result.stdout
        if not output:
            raise ValueError("没有获取到 pm2 输出")
        processes = json.loads(output)
        for proc in processes:
            pm2_env = proc.get('pm2_env', {})
            exec_path = os.path.normcase(os.path.abspath(pm2_env.get('pm_exec_path', '')))
            status = pm2_env.get('status', '')
            if script_path in exec_path and status == "online":
                return True
        return False
    except Exception as e:
        print(f"查询 pm2 状态时出错: {e}")
        return False

# 新建蓝图，所有接口的 URL 前缀为 /api
autopredict_bp = Blueprint('autopredict', __name__)

# 获取预测任务状态，同时更新全局字典 prediction_status
@autopredict_bp.route('/status', methods=['GET'])
def get_status():
    try:
        result = subprocess.run(
            [pm2_cmd, 'jlist'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=True
        )
        processes = json.loads(result.stdout)
    except Exception as e:
        print(f"查询 pm2 状态时出错: {e}")
        processes = []

    for key, script_path in scripts.items():
        # 判断返回的所有进程中是否有匹配当前脚本且状态为 "online" 的进程
        prediction_status[key] = any(
            script_path in proc.get('pm2_env', {}).get('pm_exec_path', '')
            and proc.get('pm2_env', {}).get('status', '') == "online"
            for proc in processes
        )

    return jsonify(prediction_status)

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
        return jsonify({'error': f'脚本文件不存在: {script_path}'}), 400
    
    # 使用 os.path.basename 得到脚本文件的基本名称作为进程名称
    process_name = os.path.basename(script_path)
    
    try:
        # 打印详细的调试信息
        print(f"尝试启动脚本: {script_path}")
        print(f"使用PM2路径: {pm2_cmd}")
        print(f"进程名称: {process_name}")
        
        # 使用完整路径执行命令
        cmd = [pm2_cmd, 'start', script_path, '--name', process_name]
        print(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # 打印命令输出
        print(f"命令输出: {result.stdout}")
        if result.stderr:
            print(f"命令错误: {result.stderr}")
        
        # 启动成功后更新状态为 True
        prediction_status[prediction_type] = True
        return jsonify({'message': f'{prediction_type} 预测任务已启动', 'output': result.stdout})
    except subprocess.CalledProcessError as e:
        error_msg = f"启动任务失败: {e}\n输出: {e.stdout}\n错误: {e.stderr}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500
    except Exception as e:
        error_msg = f"启动任务时发生异常: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': error_msg}), 500

# 停止指定预测任务
@autopredict_bp.route('/stop', methods=['POST'])
def stop_prediction():
    data = request.get_json() or {}
    prediction_type = data.get('type')
    if prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400

    script_path = scripts[prediction_type]
    # 使用进程名而不是脚本路径
    process_name = os.path.basename(script_path)
    
    try:
        subprocess.run(
            [pm2_cmd, 'stop', process_name],
            check=True
        )
        prediction_status[prediction_type] = False
        return jsonify({'message': f'{prediction_type} 预测任务已停止'})
    except subprocess.CalledProcessError:
        return jsonify({'error': '停止任务失败'}), 500

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
        return jsonify({'error': '时间格式错误，要求 HH:mm'}), 400

    script_path = scripts[prediction_type]
    # 使用 os.path.basename 获取脚本文件名作为进程名称
    process_name = os.path.basename(script_path)
    
    try:
        subprocess.run(
            [pm2_cmd, 'start', script_path, '--name', process_name, '--cron', f'0 {time_obj.minute} {time_obj.hour} * * *'],
            check=True
        )
        return jsonify({'message': f'为 {prediction_type} 设置了每日 {schedule_time} 的定时重启'})
    except subprocess.CalledProcessError:
        return jsonify({'error': '设置定时重启失败'}), 500

# ---------------- 新增接口 ----------------

# 删除指定预测任务（从 pm2 列表中删除）
@autopredict_bp.route('/delete', methods=['POST'])
def delete_prediction():
    data = request.get_json() or {}
    prediction_type = data.get('type')
    if prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400

    script_path = scripts[prediction_type]
    # 使用进程名而不是脚本路径
    process_name = os.path.basename(script_path)
    
    try:
        subprocess.run(
            [pm2_cmd, 'delete', process_name],
            check=True
        )
        prediction_status[prediction_type] = False
        return jsonify({'message': f'{prediction_type} 预测任务已删除'})
    except subprocess.CalledProcessError:
        return jsonify({'error': '删除任务失败'}), 500

# 保存当前 PM2 任务配置
@autopredict_bp.route('/save', methods=['POST'])
def save_pm2_config():
    try:
        subprocess.run(
            [pm2_cmd, 'save'],
            check=True
        )
        return jsonify({'message': 'PM2 任务配置已保存'})
    except subprocess.CalledProcessError:
        return jsonify({'error': '保存配置失败'}), 500

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
        list_result = subprocess.run(
            [pm2_cmd, 'list'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        print(f"PM2 进程列表: {list_result.stdout}")  # 输出所有进程列表
        
        if process_name not in list_result.stdout:
            return jsonify({
                'error': f'进程 {process_name} 未运行',
                'pm2_list': list_result.stdout
            }), 400
            
        # 使用进程名称查询详情
        result = subprocess.run(
            [pm2_cmd, 'describe', process_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 输出详细的调试信息
        print(f"PM2 describe 返回码: {result.returncode}")
        print(f"PM2 describe 标准输出: {result.stdout}")
        print(f"PM2 describe 错误输出: {result.stderr}")
        
        if result.returncode != 0:
            return jsonify({
                'error': '查询失败',
                'details': {
                    'process_name': process_name,
                    'return_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            }), 400
            
        if not result.stdout.strip():
            return jsonify({
                'error': '进程信息为空',
                'process_name': process_name
            }), 400
            
        return jsonify({
            'info': result.stdout,
            'process_name': process_name
        })
        
    except Exception as e:
        print(f"获取脚本详情出错: {str(e)}")
        return jsonify({
            'error': '查询脚本详情失败',
            'details': str(e)
        }), 500

# 获取指定脚本的近期日志信息
@autopredict_bp.route('/logs', methods=['GET'])
def get_logs():
    prediction_type = request.args.get('type')
    lines = request.args.get('lines', 100, type=int)
    if not prediction_type or prediction_type not in prediction_status:
        return jsonify({'error': '无效的预测类型'}), 400
    script_path = scripts[prediction_type]
    try:
        # 使用 pm2 logs --nostream 命令获取日志
        result = subprocess.run(
            [pm2_cmd, 'logs', '--nostream', '--lines', str(lines), os.path.basename(script_path)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=True
        )
        return jsonify({'logs': result.stdout})
    except Exception as e:
        print(f"获取日志出错: {e}")
        return jsonify({'error': '获取日志失败', 'details': str(e)}), 500

# 加载已保存的 PM2 配置（基于 pm2 resurrect）
@autopredict_bp.route('/resurrect', methods=['POST'])
def resurrect():
    try:
        # 你的重启逻辑
        subprocess.run(
            [pm2_cmd, 'resurrect'],
            check=True
        )
        return jsonify({"message": "Service resurrected successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

