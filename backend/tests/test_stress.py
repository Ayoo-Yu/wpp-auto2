import hashlib
from tempfile import SpooledTemporaryFile

def test_large_file_upload(test_db, minio_client):
    """测试大文件分片上传"""
    file_size = 150 * 1024 * 1024  # 150MB
    test_filename = "large_file.bin"
    
    # 生成临时大文件
    with SpooledTemporaryFile(max_size=file_size) as temp_file:
        temp_file.seek(file_size - 1)
        temp_file.write(b'\0')
        temp_file.seek(0)
        
        # 计算MD5
        file_hash = hashlib.md5()
        while chunk := temp_file.read(8192):
            file_hash.update(chunk)
        expected_md5 = file_hash.hexdigest()
        temp_file.seek(0)
        
        # 分片上传
        result = minio_client.put_object(
            "datasets", test_filename, temp_file, length=file_size,
            part_size=10*1024*1024  # 10MB分片
        )
        
    # 验证分片合并
    response = minio_client.get_object("datasets", test_filename)
    downloaded_hash = hashlib.md5(response.read()).hexdigest()
    assert downloaded_hash == expected_md5, "文件哈希不一致" 