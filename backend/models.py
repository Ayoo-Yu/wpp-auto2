from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from base import Base

class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    upload_time = Column(DateTime, nullable=False)
    file_id = Column(String(255), unique=True, nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    local_path = Column(String(512))
    description = Column(Text)
    data_type = Column(String(20))
    wind_farm = Column(String(100))


class Model(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(255), nullable=False)
    model_path = Column(String(512))
    scaler_path = Column(String(512))
    train_time = Column(DateTime, default=datetime.now())
    accuracy = Column(Float)
    model_type = Column(String(20))
    dataset_id = Column(String(255), ForeignKey('datasets.file_id'))
    metrics_path = Column(String(512))
    is_active = Column(Boolean, default=False)
    version = Column(String(50), default="1.0")
    is_production = Column(Boolean, default=False)
    
    dataset = relationship("Dataset")
    evaluation_metrics = relationship("EvaluationMetrics", back_populates="model")

class TrainingRecord(Base):
    __tablename__ = 'training_records'
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    dataset_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.now())
    duration = Column(Float)
    log_path = Column(String(512))
    
    def __repr__(self):
        return f"<TrainingRecord {self.model_name} ({self.status})>"

class PredictionRecord(Base):
    __tablename__ = 'prediction_records'
    
    id = Column(Integer, primary_key=True)
    model_id = Column(String(255), ForeignKey('datasets.file_id'))
    input_data_id = Column(String(255), ForeignKey('datasets.file_id'))
    scaler_id = Column(String(255), ForeignKey('datasets.file_id'))
    prediction_time = Column(DateTime, default=datetime.now())
    output_path = Column(String(512))
    prediction_type = Column(String(20))
    status = Column(String(20))
    
    model = relationship("Dataset", foreign_keys=[model_id])
    input_data = relationship("Dataset", foreign_keys=[input_data_id])
    scaler = relationship("Dataset", foreign_keys=[scaler_id])
class AutoPredictionTask(Base):
    __tablename__ = 'auto_prediction_tasks'
    
    id = Column(Integer, primary_key=True)
    task_type = Column(String(20))
    schedule_time = Column(String(5))
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    output_dir = Column(String(512))
    is_active = Column(Boolean, default=True)

class EvaluationMetrics(Base):
    __tablename__ = 'evaluation_metrics'
    
    id = Column(Integer, primary_key=True)
    dataset_id = Column(String(255), ForeignKey('datasets.file_id'))
    model_id = Column(Integer, ForeignKey('models.id'))
    mae = Column(Float)
    mse = Column(Float)
    rmse = Column(Float)
    acc = Column(Float)
    k = Column(Float)
    pe = Column(Float)
    created_at = Column(DateTime, default=datetime.now())
    
    model = relationship("Model", back_populates="evaluation_metrics")
    dataset = relationship("Dataset")

class ActualPower(Base):
    __tablename__ = "actual_power"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    wp_true = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now())

class SupershortlPower(Base):
    __tablename__ = "supershortl_power"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    wp_pred = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    pre_order = Column(Integer, nullable=False)
    pre_num = Column(Integer, nullable=False)


class ShortlPower(Base):
    __tablename__ = "shortl_power"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    wp_pred = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    pre_at = Column(DateTime, nullable=False)
    pre_num = Column(Integer, nullable=False)

class MidPower(Base):
    __tablename__ = "mid_power"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    wp_pred = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    pre_at = Column(DateTime, nullable=False)
    pre_num = Column(Integer, nullable=False)
    
class DailyMetrics(Base):
    __tablename__ = "daily_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    mae = Column(Float)
    mse = Column(Float)
    rmse = Column(Float)
    acc = Column(Float)
    k = Column(Float)
    pe = Column(Float)
    sample_count = Column(Integer)
    metric_type = Column(String(20))
