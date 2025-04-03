from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime
from .base import Base

class ActualPower(Base):
    """实际功率数据模型"""
    __tablename__ = "actual_power"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    wp_true = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now())

class SupershortlPower(Base):
    """超短期预测功率数据模型"""
    __tablename__ = "supershortl_power"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    wp_pred = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    pre_order = Column(Integer, nullable=False)
    pre_num = Column(Integer, nullable=False)

class ShortlPower(Base):
    """短期预测功率数据模型"""
    __tablename__ = "shortl_power"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    wp_pred = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    pre_at = Column(DateTime, nullable=False)
    pre_num = Column(Integer, nullable=False)

class MidPower(Base):
    """中期预测功率数据模型"""
    __tablename__ = "mid_power"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    wp_pred = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    pre_at = Column(DateTime, nullable=False)
    pre_num = Column(Integer, nullable=False) 