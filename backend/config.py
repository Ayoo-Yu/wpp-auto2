import os
from minio import Minio
from minio.commonconfig import ENABLED
import json

# 将配置提升到模块级别
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "user": "postgres",
    "password": "yzz0216yh",
    "database": "windpower"
}

MINIO_CONFIG = {
    "endpoint": "localhost:9000",
    "access_key": "minioadmin",
    "secret_key": "minioadmin",
    "secure": False,
    "dataset_bucket": "datasets",
    "model_bucket": "models",
    "access_control": {
        "datasets": "private",
        "models": "public-read"
    }
}

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'forecasts')
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB
    ALLOWED_EXTENSIONS = {'csv','joblib'}

    # 根据需要加载更多自定义配置，如数据库连接、模型路径等

    # 新增数据库配置
    POSTGRES_CONFIG = {
        "host": "localhost",
        "port": "5432",
        "user": "postgres",
        "password": "yzz0216yh",
        "database": "windpower"
    }
    
    MINIO_CONFIG = {
        "endpoint": "localhost:9000",
        "access_key": "minioadmin",
        "secret_key": "minioadmin",
        "secure": False,
        "dataset_bucket": "datasets",
        "model_bucket": "models",
        "access_control": {
            "datasets": "private",
            "models": "public-read"
        }
    }

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:yzz0216yh@localhost:5432/test_wind_power"
    PRESERVE_CONTEXT_ON_EXCEPTION = False

minio_client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)
print(minio_client.list_buckets())  # 应该返回空列表或已有存储桶

# 在Python交互环境中执行
if not minio_client.bucket_exists("datasets"):
    minio_client.make_bucket("datasets")
if not minio_client.bucket_exists("models"):
    minio_client.make_bucket("models")

# 设置存储桶策略
def set_bucket_policy(client, bucket_name, policy):
    """更精确的策略配置"""
    if policy == "private":
        policy_json = json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Principal": "*",
                    "Action": [
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:PutObjectAcl",
                        "s3:GetObjectAcl"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*",
                    "Condition": {
                        "StringEquals": {
                            "aws:UserAgent": "WindPowerForecast/1.0"
                        }
                    }
                }
            ]
        })
    elif policy == "public-read":
        policy_json = json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }]
        })
    client.set_bucket_policy(bucket_name, policy_json)

# 初始化时调用
set_bucket_policy(minio_client, "datasets", "private")
set_bucket_policy(minio_client, "models", "public-read")
