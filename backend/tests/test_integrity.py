import os
import hashlib
import io

def test_file_integrity(minio_client):
    """测试文件完整性校验机制"""
    test_file = "checksum_test.bin"
    content = os.urandom(1024*1024)  # 1MB随机数据
    expected_hash = hashlib.sha256(content).hexdigest()
    
    # 上传时添加校验头
    minio_client.put_object(
        "datasets", test_file, io.BytesIO(content),
        length=len(content),
        metadata={'X-Hash-SHA256': expected_hash}
    )
    
    # 下载验证
    obj = minio_client.get_object("datasets", test_file)
    downloaded_hash = hashlib.sha256(obj.read()).hexdigest()
    assert downloaded_hash == expected_hash 