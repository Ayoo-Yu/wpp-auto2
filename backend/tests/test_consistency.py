import pytest
from sqlalchemy import text
from unittest.mock import patch
from backend.s3_error import S3UploadError
from backend.database_config import Base
from sqlalchemy import inspect

def test_transaction_atomicity(test_db, minio_client):
    """测试数据库事务与文件操作的原子性"""
    # 创建测试表
    with test_db.begin() as conn:
        # 显式检查表是否存在
        inspector = inspect(conn)
        if not inspector.has_table("datasets"):
            print("创建表前现有表：", inspector.get_table_names())
            
        # 显示SQL日志
        test_db.echo = True
        Base.metadata.create_all(bind=conn)
        conn.execute(text("COMMIT"))
        
        # 验证表创建
        post_inspector = inspect(conn)
        print("当前数据库表：", post_inspector.get_table_names())
        assert post_inspector.has_table("datasets"), "表创建失败"
    
    test_db.dispose()  # 重置连接池
    
    test_filename = "atomic_test.txt"
    
    # 模拟上传失败
    with patch('minio.Minio.put_object') as mock_put:
        mock_put.side_effect = S3UploadError("模拟上传失败")
        
        db = test_db.connect()
        try:
            # 开始事务
            trans = db.begin()
            
            # 插入记录
            db.execute(text("SET search_path TO public"))  # 确保使用正确的schema
            db.execute(
                text("""INSERT INTO datasets 
                       (filename, file_path, upload_time, file_type, file_size, local_path)
                       VALUES 
                       (:name, :path, NOW(), 'txt', 1024, '/tmp')"""),
                {"name": test_filename, "path": "/test/path"}
            )
            
            # 应触发回滚
            with pytest.raises(S3UploadError):
                minio_client.put_object("datasets", test_filename, b"test")
                
            trans.rollback()
            
            # 验证数据库无记录
            result = db.execute(
                text("SELECT filename FROM datasets WHERE filename = :name"),
                {"name": test_filename}
            ).fetchone()
            assert result is None, "事务未正确回滚"
            
        finally:
            db.close()
    
    # 清理测试表
    Base.metadata.drop_all(bind=test_db) 