from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from base import Base

class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    upload_time = Column(DateTime, nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    local_path = Column(String(512))

class Model(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(255), nullable=False)
    model_path = Column(String(512))
    train_time = Column(DateTime, default=datetime.utcnow)
    accuracy = Column(Float)
    parameters = Column(JSON)

class TrainingRecord(Base):
    __tablename__ = 'training_records'
    
    id = Column(Integer, primary_key=True)
    model_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    dataset_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TrainingRecord {self.model_name} ({self.status})>" 