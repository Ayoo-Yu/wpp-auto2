from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.dialects.postgresql import JSON as PostgresJSON
from .base import Base, TimeStampMixin

class UserRole(Base, TimeStampMixin):
    """用户角色表，存储各种角色及其权限配置"""
    __tablename__ = 'user_roles'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    permissions = Column(PostgresJSON, nullable=True)  # 存储权限配置JSON
    
    def __repr__(self):
        return f"<UserRole {self.name}>" 