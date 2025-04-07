#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试金仓数据库中"char"后缀格式处理
此脚本专门测试金仓数据库方言是否正确处理带有"char"后缀的字段长度
"""

import os
import sys
from sqlalchemy import (
    create_engine, inspect, MetaData, Table, Column, String, 
    Integer, VARCHAR, CHAR, text, types
)
from sqlalchemy.ext.declarative import declarative_base

# 导入自定义的金仓数据库方言
from kingbase_dialect import KingbaseDialect

def test_char_format_handling():
    """测试"char"后缀格式的字段长度处理"""
    print("=== 测试'char'后缀格式处理 ===")
    
    # 创建方言实例
    dialect = KingbaseDialect()
    
    # 测试各种格式的长度提取
    test_cases = [
        ("255 char", 255),
        ("100char", 100),
        ("20  CHAR", 20),
        ("5char   ", 5),
        ("512 Char", 512),
        ("invalid", 255),  # 无效格式应返回默认值
        (123, 123),       # 整数应保持不变
        (None, None)      # None应保持不变
    ]
    
    print("\n长度提取测试结果:")
    for value, expected in test_cases:
        result = dialect._extract_length_value(value)
        status = "✓" if result == expected else "✗"
        print(f"  {status} 输入: '{value}', 提取结果: {result}, 预期: {expected}")
    
    # 创建模拟数据用于测试类型转换
    print("\n测试模拟列类型转换:")
    
    column_types = [
        {'name': 'col1', 'type': types.String("255 char")},
        {'name': 'col2', 'type': types.VARCHAR("100 char")},
        {'name': 'col3', 'type': types.CHAR("1 char")},
        {'name': 'col4', 'type': types.String(50)}  # 正常整数长度
    ]
    
    for col in column_types:
        original_length = col['type'].length
        original_type = type(original_length)
        
        # 使用方言的type_descriptor方法处理类型
        processed_type = dialect.type_descriptor(col['type'])
        
        # 检查长度是否已转换为整数
        is_int = isinstance(processed_type.length, int)
        print(f"  列 '{col['name']}': 原始长度='{original_length}'({original_type.__name__}), " +
              f"处理后长度={processed_type.length}({'int' if is_int else type(processed_type.length).__name__})")

def test_model_with_char_suffix():
    """测试使用带'char'后缀的模型定义"""
    print("\n=== 测试带'char'后缀的模型定义 ===")
    
    Base = declarative_base()
    
    # 定义测试模型，故意使用字符串长度
    class CharSuffixModel(Base):
        __tablename__ = 'char_suffix_test'
        
        id = Column(Integer, primary_key=True)
        name = Column(String("255 char"))            # 带空格的"char"后缀
        code = Column(VARCHAR("50char"))            # 无空格的"char"后缀
        flag = Column(CHAR("1 char"))              # 单字符带"char"后缀
        normal = Column(String(100))                # 正常整数长度
        
    # 检查模型的列类型
    print("模型列类型检查:")
    for column in CharSuffixModel.__table__.columns:
        if hasattr(column.type, 'length'):
            length_type = type(column.type.length).__name__
            is_correct = isinstance(column.type.length, int) or column.type.length is None
            status = "✓" if is_correct else "✗"
            print(f"  {status} 列 '{column.name}': 类型={column.type.__class__.__name__}, " +
                  f"长度={column.type.length}, 长度类型={length_type}")
            
    return CharSuffixModel

def create_test_table():
    """创建测试表并验证DDL生成"""
    print("\n=== 测试DDL生成 ===")
    
    # 获取测试模型
    TestModel = test_model_with_char_suffix()
    
    # 创建内存数据库引擎 (仅用于测试DDL生成)
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # 获取模型的DDL
    metadata = MetaData()
    table = Table(TestModel.__tablename__, metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String("255 char")),
        Column('code', VARCHAR("50char")),
        Column('flag', CHAR("1 char")),
        Column('normal', String(100))
    )
    
    # 生成创建表的DDL
    from sqlalchemy.schema import CreateTable
    ddl = str(CreateTable(table).compile(engine))
    
    print("生成的DDL:")
    print(ddl)
    
    # 检查DDL中的长度值
    import re
    varchar_matches = re.findall(r'VARCHAR\((\d+)\)', ddl)
    char_matches = re.findall(r'CHAR\((\d+)\)', ddl)
    
    print("\nDDL中的长度值:")
    for length in varchar_matches:
        print(f"  VARCHAR({length})")
    for length in char_matches:
        print(f"  CHAR({length})")
        
    # 检查是否所有长度都是整数
    all_lengths = varchar_matches + char_matches
    is_valid = all(length.isdigit() for length in all_lengths)
    
    print(f"\nDDL长度值检查: {'通过' if is_valid else '失败'}")
    
    return is_valid

if __name__ == "__main__":
    print("开始测试金仓数据库'char'后缀格式处理...")
    
    # 运行测试
    test_char_format_handling()
    create_test_table()
    
    print("\n测试完成!") 