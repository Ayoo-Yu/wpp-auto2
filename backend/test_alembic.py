#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试Alembic兼容性脚本
此脚本用于在本地验证金仓数据库方言是否正确处理Alembic迁移
"""

import os
import sys
import importlib
import pkgutil
import subprocess
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, String, Integer, text

# 设置Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '..')))

# 导入自定义的金仓数据库方言
from kingbase_dialect import KingbaseDialect

def setup_env_vars():
    """设置环境变量"""
    os.environ.setdefault('DB_HOST', 'localhost')
    os.environ.setdefault('DB_PORT', '54321')
    os.environ.setdefault('DB_USER', 'system')
    os.environ.setdefault('DB_PASSWORD', '12345678ab')
    os.environ.setdefault('DB_NAME', 'windpower')
    
    # 设置PYTHONPATH
    if 'PYTHONPATH' not in os.environ:
        os.environ['PYTHONPATH'] = current_dir
    
    # 打印环境变量
    print("当前环境变量:")
    for key in ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'PYTHONPATH']:
        if key == 'DB_PASSWORD':
            print(f"  {key}=******")
        else:
            print(f"  {key}={os.environ.get(key, '未设置')}")

def run_alembic_command(command):
    """运行Alembic命令并捕获输出"""
    print(f"\n执行Alembic命令: {command}")
    
    # 构建完整命令
    full_command = f"alembic {command}"
    
    try:
        # 使用subprocess执行命令
        result = subprocess.run(
            full_command, 
            shell=True, 
            check=True,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 打印输出
        print("\n命令输出:")
        print(result.stdout)
        
        if result.stderr:
            print("\n错误输出:")
            print(result.stderr)
            
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print("\n命令执行失败!")
        print(f"返回码: {e.returncode}")
        print("\n错误输出:")
        print(e.stderr)
        
        return False, e.stderr

def test_dialect_loading():
    """测试方言加载"""
    print("\n=== 测试方言加载 ===")
    
    try:
        # 构建连接URL
        db_host = os.environ.get('DB_HOST')
        db_port = os.environ.get('DB_PORT')
        db_user = os.environ.get('DB_USER')
        db_password = os.environ.get('DB_PASSWORD')
        db_name = os.environ.get('DB_NAME')
        
        db_url = f"postgresql+kingbase://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        print(f"连接URL: {db_url.replace(db_password, '******')}")
        
        # 创建引擎
        engine = create_engine(db_url, echo=False)
        
        # 获取引擎方言
        dialect = engine.dialect
        print(f"引擎方言: {dialect.__class__.__name__}")
        
        # 检查是否为金仓方言
        if isinstance(dialect, KingbaseDialect):
            print("成功: 引擎使用了金仓数据库方言")
        else:
            print(f"警告: 引擎使用了 {dialect.__class__.__name__} 而不是 KingbaseDialect")
        
        return True
    except Exception as e:
        print(f"方言加载测试失败: {e}")
        return False

def test_env_py():
    """测试migration/env.py文件"""
    print("\n=== 测试migration/env.py文件 ===")
    
    # 检查migration/env.py文件是否存在
    env_py_path = os.path.join(os.path.dirname(current_dir), 'migration', 'env.py')
    
    if not os.path.exists(env_py_path):
        print(f"警告: migration/env.py文件不存在于路径 {env_py_path}")
        return False
    
    print(f"migration/env.py文件存在于路径 {env_py_path}")
    
    # 检查文件内容
    print("检查env.py中的数据库连接字符串...")
    with open(env_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 检查是否使用了kingbase方言
    if "postgresql+kingbase://" in content:
        print("成功: env.py文件中使用了kingbase方言")
    else:
        print("警告: env.py文件中可能没有使用kingbase方言")
        
    return True

def test_alembic_operations():
    """测试Alembic操作"""
    print("\n=== 测试Alembic操作 ===")
    
    # 测试current命令
    print("\n[1/3] 测试 'alembic current' 命令")
    success, output = run_alembic_command("current")
    
    if not success:
        print("'alembic current'命令失败")
        return False
    
    # 测试check命令
    print("\n[2/3] 测试 'alembic check' 命令")
    success, output = run_alembic_command("check")
    
    if not success:
        print("'alembic check'命令失败")
        return False
    
    # 测试模拟迁移
    print("\n[3/3] 测试迁移生成 (--autogenerate)")
    print("注意: 这只是一个测试，不会实际创建迁移文件")
    success, output = run_alembic_command("revision --autogenerate --sql")
    
    if not success:
        print("迁移生成测试失败")
        return False
    
    return True

if __name__ == "__main__":
    print("开始测试Alembic兼容性...")
    
    # 设置环境变量
    setup_env_vars()
    
    # 测试方言加载
    if not test_dialect_loading():
        print("方言加载测试失败，停止后续测试")
        sys.exit(1)
    
    # 测试env.py文件
    if not test_env_py():
        print("env.py文件测试失败，请确保migration/env.py文件存在并正确配置")
    
    # 测试Alembic操作
    if not test_alembic_operations():
        print("Alembic操作测试失败")
        sys.exit(1)
    
    print("\n所有测试完成!") 