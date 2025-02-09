import sys
import os
import pytest

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import create_engine, text
from minio import Minio
from backend.config import MINIO_CONFIG # type: ignore
from backend.database_config import engine, Base


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# 修改后的 test_db fixture
@pytest.fixture(scope="session")
def test_db():
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:yzz0216yh@localhost:5432/test_wind_power"
    
    # 创建测试数据库
    admin_engine = create_engine(
        "postgresql://postgres:yzz0216yh@localhost:5432/postgres",
        isolation_level="AUTOCOMMIT"
    )
    with admin_engine.connect() as conn:
        try:
            conn.execute(text("CREATE DATABASE test_wind_power"))
            conn.execute(text("DROP DATABASE IF EXISTS windpower"))  # 防止数据库名冲突
        except Exception as e:
            print(f"Database exists: {str(e)}")
    
    # 应用模型到测试数据库
    test_engine = create_engine(
        SQLALCHEMY_DATABASE_URI,
        pool_size=10,
        max_overflow=20,
        pool_recycle=300
    )
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    
    # 清理阶段
    test_engine.dispose()  # 释放所有连接
    
    # 强制清理数据库
    with admin_engine.connect() as conn:
        # 终止所有活动连接
        conn.execute(text("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'test_wind_power'
              AND pid <> pg_backend_pid()
        """))
        # 删除数据库
        conn.execute(text("DROP DATABASE IF EXISTS test_wind_power"))

# 添加自动使用fixture
@pytest.fixture(autouse=True)
def auto_use_fixtures(test_db):
    pass

@pytest.fixture(scope="session")
def minio_client():
    """提供MinIO客户端实例"""
    client = Minio(
        MINIO_CONFIG["endpoint"],
        access_key=MINIO_CONFIG["access_key"],
        secret_key=MINIO_CONFIG["secret_key"],
        secure=MINIO_CONFIG["secure"]
    )
    
    # 确保测试存储桶存在
    for bucket in [MINIO_CONFIG["dataset_bucket"], MINIO_CONFIG["model_bucket"]]:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    
    yield client
    
    # 清理测试文件
    objects = client.list_objects(MINIO_CONFIG["dataset_bucket"], recursive=True)
    for obj in objects:
        client.remove_object(MINIO_CONFIG["dataset_bucket"], obj.object_name)

# 临时添加打印语句
print("当前工作目录：", os.getcwd())
print("数据库配置路径：", os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.py')))

# 临时添加打印语句验证路径
print("当前Python路径：", sys.path) 