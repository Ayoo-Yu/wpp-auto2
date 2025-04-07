#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试金仓数据库方言脚本
此脚本用于在本地验证金仓数据库方言是否正确处理VARCHAR长度问题
"""

import os
import sys
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, String, Integer, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 导入自定义的金仓数据库方言
from kingbase_dialect import KingbaseDialect

def test_connection():
    """测试数据库连接"""
    print("=== 测试数据库连接 ===")
    
    # 从环境变量获取数据库连接信息，或使用默认值
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "54321")
    db_user = os.environ.get("DB_USER", "system")
    db_password = os.environ.get("DB_PASSWORD", "12345678ab")
    db_name = os.environ.get("DB_NAME", "windpower")
    
    # 构建连接URL
    db_url = f"postgresql+kingbase://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    print(f"连接URL: {db_url}")
    
    try:
        # 创建引擎
        engine = create_engine(db_url, echo=True)
        
        # 测试连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"连接测试结果: {result.scalar()}")
        
        print("数据库连接成功!")
        return engine
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def test_column_types(engine):
    """测试列类型处理"""
    if not engine:
        print("引擎未初始化，跳过列类型测试")
        return
    
    print("\n=== 测试列类型处理 ===")
    
    try:
        # 使用检查器获取表结构
        inspector = inspect(engine)
        
        # 获取所有表
        tables = inspector.get_table_names()
        print(f"数据库中的表: {tables}")
        
        if not tables:
            print("没有找到表，跳过列类型测试")
            return
        
        # 选择第一个表进行测试
        test_table = tables[0]
        print(f"测试表: {test_table}")
        
        # 获取列信息
        columns = inspector.get_columns(test_table)
        print(f"表 {test_table} 的列数: {len(columns)}")
        
        # 打印列信息
        for col in columns:
            col_type = col['type']
            col_length = getattr(col_type, 'length', None)
            print(f"列: {col['name']}, 类型: {col_type}, 长度: {col_length}, 长度类型: {type(col_length)}")
            
            # 验证字符串类型的长度是整数
            if hasattr(col_type, 'length') and col_type.length is not None:
                assert isinstance(col_type.length, int), f"列 {col['name']} 的长度 {col_type.length} 不是整数类型"
        
        print("所有列的类型和长度验证通过!")
    except Exception as e:
        print(f"列类型测试失败: {e}")

def create_test_table(engine):
    """创建测试表来验证方言处理"""
    if not engine:
        print("引擎未初始化，跳过测试表创建")
        return
    
    print("\n=== 创建测试表 ===")
    
    Base = declarative_base()
    
    # 定义测试模型
    class TestModel(Base):
        __tablename__ = 'dialect_test'
        
        id = Column(Integer, primary_key=True)
        name = Column(String(255))  # 正常长度
        description = Column(String("100"))  # 字符串长度，应该被自动转换
        
    try:
        # 创建表
        Base.metadata.create_all(engine)
        print(f"测试表 {TestModel.__tablename__} 创建成功")
        
        # 检查表结构
        inspector = inspect(engine)
        columns = inspector.get_columns(TestModel.__tablename__)
        
        # 验证列
        for col in columns:
            if col['name'] == 'description':
                assert isinstance(col['type'].length, int), "String长度未被转换为整数"
                print(f"description列长度为 {col['type'].length}，类型为 {type(col['type'].length)}")
        
        print("测试表验证通过!")
        
        # 删除测试表
        Base.metadata.drop_all(engine, tables=[TestModel.__table__])
        print(f"测试表 {TestModel.__tablename__} 已删除")
    except Exception as e:
        print(f"测试表创建/验证失败: {e}")

def run_alembic_commands():
    """测试Alembic命令"""
    print("\n=== 测试Alembic命令（不需要进入容器）===")
    print("使用以下命令可以在本地测试Alembic:")
    print("1. 查看当前迁移版本:")
    print("   PYTHONPATH=. alembic current")
    print("2. 创建新的迁移脚本:")
    print("   PYTHONPATH=. alembic revision --autogenerate -m \"测试迁移\"")
    print("3. 升级到最新版本:")
    print("   PYTHONPATH=. alembic upgrade head")
    print("\n注意: 需要先设置正确的环境变量才能连接到金仓数据库")
    print("例如:")
    print("   DB_HOST=localhost DB_PORT=54321 DB_USER=system DB_PASSWORD=12345678ab DB_NAME=windpower PYTHONPATH=. alembic current")

if __name__ == "__main__":
    print("开始测试金仓数据库方言...")
    engine = test_connection()
    test_column_types(engine)
    create_test_table(engine)
    run_alembic_commands()
    print("\n测试完成!") 