import sys
import os
import pytest
import io
from datetime import datetime
from sqlalchemy import text, inspect
from backend.s3_error import S3Error

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database_config import engine, minio_client, get_db
from config import MINIO_CONFIG
from backend.models import Base  # 使用绝对路径

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """测试前创建表，测试后清理"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    yield
    # 清理所有表
    Base.metadata.drop_all(bind=engine)

def test_postgres_connection(test_db):
    """测试PostgreSQL数据库连接"""
    try:
        with test_db.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"当前连接的数据库: {db_name}")
        print("✅ PostgreSQL连接成功")
    except Exception as e:
        pytest.fail(f"PostgreSQL连接失败: {str(e)}")

def test_minio_connection():
    """测试MinIO存储服务连接"""
    try:
        buckets = minio_client.list_buckets()
        required_buckets = [
            MINIO_CONFIG["dataset_bucket"],
            MINIO_CONFIG["model_bucket"]
        ]
        
        # 验证必需存储桶存在
        existing_buckets = [b.name for b in buckets]
        for bucket in required_buckets:
            assert bucket in existing_buckets, f"缺少必需存储桶: {bucket}"
        
        print("✅ MinIO连接成功")
    except S3Error as e:
        pytest.fail(f"MinIO连接失败: {str(e)}")

def test_file_upload_download():
    """测试文件上传下载全流程"""
    test_filename = "test_file.txt"
    test_content = b"Hello, Wind Power Forecast!"
    
    # 上传测试文件
    try:
        minio_client.put_object(
            MINIO_CONFIG["dataset_bucket"],
            test_filename,
            data=io.BytesIO(test_content),
            length=len(test_content)
        )
        print("✅ 测试文件上传成功")
    except S3Error as e:
        pytest.fail(f"文件上传失败: {str(e)}")
    
    # 数据库记录测试
    db = next(get_db())
    try:
        # 插入测试记录
        db.execute(
            text("""
            INSERT INTO datasets 
            (filename, file_path, upload_time, file_type, file_size)
            VALUES (:filename, :path, NOW(), 'text/plain', :size)
            """),
            {"filename": test_filename, "path": test_filename, "size": len(test_content)}
        )
        db.commit()
        
        # 查询测试记录
        result = db.execute(
            text("SELECT filename FROM datasets WHERE filename = :name"),
            {"name": test_filename}
        ).fetchone()
        
        assert result is not None, "数据库记录插入失败"
        print(result)
        print("✅ 数据库记录操作成功")
    except Exception as e:
        db.rollback()
        pytest.fail(f"数据库操作失败: {str(e)}")
    finally:
        db.close()
    
    # 下载验证
    try:
        response = minio_client.get_object(
            MINIO_CONFIG["dataset_bucket"],
            test_filename
        )
        downloaded_content = response.read()
        assert downloaded_content == test_content, "下载内容不一致"
        print("✅ 文件下载验证成功")
    except S3Error as e:
        pytest.fail(f"文件下载失败: {str(e)}")
    finally:
        response.close()
        response.release_conn()
    
    # 清理测试数据
    try:
        minio_client.remove_object(
            MINIO_CONFIG["dataset_bucket"],
            test_filename
        )
        db.execute(
            text("DELETE FROM datasets WHERE filename = :name"),
            {"name": test_filename}
        )
        db.commit()
        print("✅ 测试数据清理完成")
    except Exception as e:
        print(f"⚠️ 清理测试数据时出错: {str(e)}")

def test_table_creation():
    """验证表是否成功创建"""
    inspector = inspect(engine)
    assert inspector.has_table("datasets"), "datasets表不存在"
    assert inspector.has_table("models"), "models表不存在"
    print("✅ 数据库表验证成功")

if __name__ == "__main__":
    pytest.main(["-s", __file__]) 