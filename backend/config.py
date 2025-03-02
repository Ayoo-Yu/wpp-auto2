import os
from minio import Minio
from minio.commonconfig import ENABLED
import json

# 从环境变量读取配置，如果不存在则使用默认值
POSTGRES_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
    "user": "postgres",
    "password": "yzz0216yh",
    "database": "windpower",
    # "default_db": "postgres"  # 新增默认数据库配置
}

MINIO_CONFIG = {
    "endpoint": os.environ.get("MINIO_ENDPOINT", "localhost") + ":" + os.environ.get("MINIO_PORT", "9000"),
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
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "user": "postgres",
        "password": "yzz0216yh",
        "database": "windpower",
        "default_db": "postgres"  # 新增默认数据库配置
    }
    
    MINIO_CONFIG = {
        "endpoint": os.environ.get("MINIO_ENDPOINT", "localhost") + ":" + os.environ.get("MINIO_PORT", "9000"),
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
