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
    "database": "windpower",
    # "default_db": "postgres"  # 新增默认数据库配置
}

MINIO_CONFIG = {
    "endpoint": "localhost:9000",
    "access_key": "minioadmin",
    "secret_key": "minioadmin",
    "secure": False,
    "buckets": {
        "datasets": "wind-datasets",
        "models": "wind-models",
        "predictions": "wind-predictions",
        "scalers": "wind-scalers",
        "metrics": "wind-metrics",
        "logs": "wind-logs"
    },
    "access_control": {
        "wind-datasets": "private",
        "wind-models": "public-read",
        "wind-predictions": "private",
        "wind-scalers": "private",
        "wind-metrics": "public-read",
        "wind-logs": "public-read"
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
        "database": "windpower",
        "default_db": "postgres"  # 新增默认数据库配置
    }
    
    MINIO_CONFIG = {
        "endpoint": "localhost:9000",
        "access_key": "minioadmin",
        "secret_key": "minioadmin",
        "secure": False,
        "buckets": {
            "datasets": "wind-datasets",
            "models": "wind-models",
            "predictions": "wind-predictions",
            "scalers": "wind-scalers",
            "metrics": "wind-metrics",
            "logs": "wind-logs"
        },
        "access_control": {
            "wind-datasets": "private",
            "wind-models": "public-read",
            "wind-predictions": "private",
            "wind-scalers": "private",
            "wind-metrics": "public-read",
            "wind-logs": "public-read"
        }
    }

    MODEL_STORAGE = {
        'model_dir': os.path.join(BASE_DIR, 'saved_models'),
        'scaler_dir': os.path.join(BASE_DIR, 'saved_scalers'),
        'metrics_dir': os.path.join(BASE_DIR, 'saved_metrics')
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
required_buckets = list(MINIO_CONFIG["buckets"].values())

# 在创建存储桶后添加策略设置函数
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

# 先创建存储桶
for bucket in required_buckets:
    if not minio_client.bucket_exists(bucket):
        minio_client.make_bucket(bucket)
        print(f"✅ 成功创建存储桶: {bucket}")

# 再设置策略（此时存储桶已存在）
set_bucket_policy(minio_client, "wind-datasets", "private")
set_bucket_policy(minio_client, "wind-models", "public-read")
set_bucket_policy(minio_client, "wind-predictions", "private")
set_bucket_policy(minio_client, "wind-scalers", "private")
set_bucket_policy(minio_client, "wind-metrics", "public-read")
set_bucket_policy(minio_client, "wind-logs", "public-read")
